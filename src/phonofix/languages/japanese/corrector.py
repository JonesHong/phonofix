"""
日文修正器模組

實作針對日文語音識別 (ASR) 錯誤的修正邏輯。
核心演算法基於羅馬拼音 (Romaji) 的相似度比對與滑動視窗掃描。

使用方式:
    from phonofix import JapaneseEngine
    
    engine = JapaneseEngine()
    corrector = engine.create_corrector({'アスピリン': ['asupirin']})
    result = corrector.correct('頭が痛いのでasupirinを飲みました')
"""

from typing import Dict, List, Optional, Any, Tuple, Generator, Callable, TYPE_CHECKING
import logging

from phonofix.core.protocols.corrector import CorrectorProtocol
from .phonetic_impl import JapanesePhoneticSystem
from .tokenizer import JapaneseTokenizer
from .config import JapanesePhoneticConfig
from phonofix.utils.logger import get_logger, TimingContext

if TYPE_CHECKING:
    from phonofix.languages.japanese.engine import JapaneseEngine


class JapaneseCorrector:
    """
    日文修正器

    功能:
    - 針對日文文本進行專有名詞修正
    - 使用滑動視窗掃描文本
    - 結合羅馬拼音相似度進行模糊比對
    - 支援 keywords 條件過濾 (需要上下文關鍵字才替換)
    - 支援 exclude_when 上下文排除 (看到排除詞時不替換)
    
    建立方式:
        使用 JapaneseEngine.create_corrector() 建立實例
    """

    @classmethod
    def _from_engine(
        cls,
        engine: "JapaneseEngine",
        term_mapping: Dict[str, Dict],
    ) -> "JapaneseCorrector":
        """
        從 Engine 建立輕量 Corrector 實例 (內部方法)
        
        Args:
            engine: JapaneseEngine 實例
            term_mapping: 正規化的專有名詞映射 (canonical -> config dict)
            
        Returns:
            JapaneseCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.japanese")
        instance.phonetic_system = engine.phonetic
        instance.tokenizer = engine.tokenizer
        
        # 建立搜尋索引
        instance.search_index = instance._build_search_index(term_mapping)
        
        return instance

    def _build_search_index(self, term_mapping: Dict[str, Dict]) -> List[Dict]:
        """
        建立搜尋索引
        
        將別名映射轉換為列表結構，並預先計算拼音與 Token 數量。
        索引按 Token 數量降序排列，以優先匹配長詞。
        """
        search_index = []
        
        for canonical, config in term_mapping.items():
            aliases = config.get("aliases", [])
            weight = config.get("weight", 1.0)
            keywords = config.get("keywords", [])
            exclude_when = config.get("exclude_when", [])
            
            # 收集所有目標詞 (別名 + 正確詞本身)
            targets = set(aliases)
            
            for alias in targets:
                # 計算別名的拼音
                phonetic = self.phonetic_system.to_phonetic(alias)
                if not phonetic:
                    continue
                    
                # 計算別名的 Token 數量 (用於滑動視窗)
                tokens = self.tokenizer.tokenize(alias)
                token_count = len(tokens)
                
                search_index.append({
                    "term": alias,
                    "canonical": canonical,
                    "phonetic": phonetic,
                    "token_count": token_count,
                    "weight": weight,
                    "keywords": keywords,
                    "exclude_when": exclude_when
                })
                
        # 按 Token 數量降序排列
        search_index.sort(key=lambda x: x["token_count"], reverse=True)
        return search_index

    def _check_context_bonus(self, full_text, start_idx, end_idx, keywords, window_size=50):
        """
        檢查上下文關鍵字加分

        若在修正目標附近的視窗內發現相關關鍵字，則給予額外加分 (降低距離分數)。
        這有助於區分同音異義詞。

        Args:
            full_text: 完整文本
            start_idx: 目標詞起始索引
            end_idx: 目標詞結束索引
            keywords: 關鍵字列表
            window_size: 上下文視窗大小 (預設 50 字符)

        Returns:
            (bool, float): (是否命中關鍵字, 關鍵字距離)
        """
        if not keywords:
            return False, None
        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(full_text), end_idx + window_size)
        context_text = full_text[ctx_start:ctx_end] # 日文不轉小寫，因為包含漢字
        
        min_distance = None
        for kw in keywords:
            kw_idx = context_text.find(kw)
            if kw_idx != -1:
                kw_abs_pos = ctx_start + kw_idx
                if kw_abs_pos < start_idx:
                    distance = start_idx - (kw_abs_pos + len(kw))
                elif kw_abs_pos >= end_idx:
                    distance = kw_abs_pos - end_idx
                else:
                    distance = 0
                if min_distance is None or distance < min_distance:
                    min_distance = distance
        if min_distance is not None:
            return True, min_distance
        return False, None

    def _calculate_final_score(self, error_ratio, item, has_context, context_distance=None):
        """
        計算最終分數 (越低越好)

        公式: 錯誤率 - 詞彙權重 - 上下文加分
        """
        final_score = error_ratio
        final_score -= item["weight"]
        if has_context and context_distance is not None:
            # 上下文加分邏輯
            distance_factor = 1.0 - (min(context_distance, 50) / 50.0 * 0.6)
            context_bonus = 0.8 * distance_factor
            final_score -= context_bonus
        return final_score

    def _create_candidate(self, start_idx, end_idx, original, item, score, has_context):
        """建立候選修正物件"""
        return {
            "start": start_idx,
            "end": end_idx,
            "original": original,
            "replacement": item["canonical"],
            "score": score,
            "has_context": has_context,
            "alias": item["term"]
        }

    def _should_exclude_by_context(self, exclude_when: List[str], context: str) -> bool:
        """檢查是否應根據上下文排除修正"""
        if not exclude_when:
            return False
        for condition in exclude_when:
            if condition in context:
                return True
        return False
    
    def _has_required_keyword(self, keywords: List[str], context: str) -> bool:
        """檢查是否滿足關鍵字必要條件"""
        if not keywords:
            return True
        for kw in keywords:
            if kw in context:
                return True
        return False

    def correct(
        self, text: str, full_context: str | None = None, silent: bool = False
    ) -> str:
        """
        修正日文文本

        Args:
            text: 輸入文本
            full_context: 完整上下文 (用於關鍵字判斷)
            silent: 是否靜默模式 (不輸出修正日誌)

        Returns:
            str: 修正後的文本
        """
        if not text or not self.search_index:
            return text
            
        with TimingContext("JapaneseCorrector.correct", self._logger, logging.DEBUG):
            candidates = self._find_candidates(text, full_context)
            final_candidates = self._resolve_conflicts(candidates)
            return self._apply_replacements(text, final_candidates, silent=silent)

    # 串流 API 已移除（Phase 6：精簡對外介面，改由上層自行分段/多次呼叫 correct()）

    def _find_candidates(self, text: str, full_context: str = None) -> List[Dict]:
        """搜尋所有可能的修正候選"""
        context = full_context if full_context is not None else text
        
        # 1. 分詞與索引
        tokens = self.tokenizer.tokenize(text)
        indices = self.tokenizer.get_token_indices(text)
        
        if not tokens:
            return []
            
        # 預先計算每個 token 的拼音
        token_phonetics = [self.phonetic_system.to_phonetic(t) for t in tokens]
        
        candidates = []
        n = len(tokens)
        
        # 2. 滑動視窗掃描
        for item in self.search_index:
            target_len = item["token_count"]
            # 允許視窗大小彈性 +/- 2 (處理 ASR 分割錯誤)
            min_len = max(1, target_len - 2)
            max_len = min(n, target_len + 2)
            
            for length in range(max_len, min_len - 1, -1):
                for i in range(n - length + 1):
                    # 組合視窗內的拼音
                    window_phonetic = "".join(token_phonetics[i : i + length])
                    
                    # 快速長度檢查
                    if abs(len(window_phonetic) - len(item["phonetic"])) > max(len(item["phonetic"]), 5) * 0.5:
                        continue
                        
                    # 模糊比對
                    error_ratio, is_match = self.phonetic_system.calculate_similarity_score(
                        window_phonetic, item["phonetic"]
                    )
                    
                    if is_match:
                        # 檢查上下文排除
                        if self._should_exclude_by_context(item["exclude_when"], context):
                            continue
                        # 檢查關鍵字要求
                        if not self._has_required_keyword(item["keywords"], context):
                            continue
                            
                        start_char = indices[i][0]
                        end_char = indices[i + length - 1][1]
                        original_text = text[start_char:end_char]
                        
                        # 避免自我替換
                        if original_text == item["canonical"]:
                            continue

                        # 計算上下文加分
                        has_context, context_distance = self._check_context_bonus(
                            context, start_char, end_char, item["keywords"]
                        )
                        
                        # 計算分數 (越低越好)
                        score = self._calculate_final_score(
                            error_ratio, item, has_context, context_distance
                        )
                        
                        candidate = self._create_candidate(
                            start_char, end_char, original_text, item, score, has_context
                        )
                        
                        candidates.append(candidate)
                        self._logger.debug(f"Candidate found: '{original_text}' -> '{item['canonical']}' (via '{item['term']}') score={score:.3f}")
        return candidates

    def _resolve_conflicts(self, candidates: List[Dict]) -> List[Dict]:
        """解決候選衝突"""
        # 按分數排序 (越低越好)
        candidates.sort(key=lambda x: x["score"])
        
        final_candidates = []
        for cand in candidates:
            is_conflict = False
            for accepted in final_candidates:
                if max(cand["start"], accepted["start"]) < min(cand["end"], accepted["end"]):
                    is_conflict = True
                    break
            if not is_conflict:
                final_candidates.append(cand)
            else:
                self._logger.debug(f"Conflict resolved: Dropped '{cand['original']}' (score={cand['score']}) in favor of existing match")
                
        return final_candidates

    def _apply_replacements(self, text: str, candidates: List[Dict], silent: bool = False) -> str:
        """應用修正並輸出日誌"""
        candidates.sort(key=lambda x: x["start"])
        
        result = []
        last_pos = 0
        for cand in candidates:
            # 如果原文與替換文相同，則不進行替換操作，但它佔用了位置防止錯誤修正
            if cand["original"] == cand["replacement"]:
                continue
            
            result.append(text[last_pos : cand["start"]])
            result.append(cand["replacement"])
            
            # 輸出修正日誌 (用戶可見的修正反饋)
            if not silent:
                tag = "[上下文命中]" if cand.get("has_context") else "[發音修正]"
                print(
                    f"{tag} '{cand['original']}' -> '{cand['replacement']}' (Score: {cand['score']:.3f})"
                )
            
            self._logger.debug(
                f"  [Match] '{cand['original']}' -> '{cand['replacement']}' "
                f"(via '{cand['alias']}', score={cand['score']:.3f})"
            )
            
            last_pos = cand["end"]
        result.append(text[last_pos:])
        return "".join(result)
