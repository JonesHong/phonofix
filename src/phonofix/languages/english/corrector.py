"""
英文修正器模組

實作基於滑動視窗 (Sliding Window) 與語音相似度的英文專有名詞修正。

使用方式:
    from phonofix import EnglishEngine
    
    engine = EnglishEngine()
    corrector = engine.create_corrector({'Python': ['Pyton', 'Pyson']})
    result = corrector.correct('I use Pyton for ML')
"""

import re
import logging
from typing import List, Dict, Union, Optional, Set, TYPE_CHECKING, Any, Generator, Callable
from .phonetic_impl import EnglishPhoneticSystem
from .tokenizer import EnglishTokenizer
from phonofix.utils.logger import get_logger, TimingContext

if TYPE_CHECKING:
    from phonofix.engine.english_engine import EnglishEngine


class EnglishCorrector:
    """
    英文修正器

    功能:
    - 針對英文文本進行專有名詞修正
    - 使用滑動視窗掃描文本
    - 結合 IPA 發音相似度進行模糊比對
    - 支援自動生成 ASR 錯誤變體
    - 支援 keywords 條件過濾 (需要上下文關鍵字才替換)
    - 支援 exclude_when 上下文排除 (看到排除詞時不替換)
    
    建立方式:
        使用 EnglishEngine.create_corrector() 建立實例
    """

    @classmethod
    def _from_engine(
        cls,
        engine: "EnglishEngine",
        term_mapping: Dict[str, Dict],
    ) -> "EnglishCorrector":
        """
        從 Engine 建立輕量 Corrector 實例 (內部方法)
        
        Args:
            engine: EnglishEngine 實例
            term_mapping: 正規化的專有名詞映射 (canonical -> config dict)
            
        Returns:
            EnglishCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.english")
        instance.phonetic = engine.phonetic
        instance.tokenizer = engine.tokenizer
        
        # 建立搜尋索引
        instance.search_index = instance._build_search_index(term_mapping)
        
        return instance
    
    def _build_search_index(self, term_mapping: Dict[str, Dict]) -> List[Dict]:
        """
        建立搜尋索引
        
        將別名映射轉換為列表結構，並預先計算 IPA。
        索引按 Token 數量降序排列，以優先匹配長詞。
        """
        # 1. 收集所有需要計算 IPA 的 tokens
        all_tokens = set()
        alias_tokens_map = {}
        
        # 展開所有別名
        flat_mapping = []
        for canonical, config in term_mapping.items():
            aliases = config.get("aliases", [])
            # 確保正確詞本身也在搜尋範圍 (如果需要)
            # 通常我們只搜尋別名，但有時正確詞也需要被處理 (例如大小寫修正)
            # 這裡我們將正確詞也視為一個潛在的目標，但通常它會是完全匹配
            targets = set(aliases)
            
            for alias in targets:
                flat_mapping.append({
                    "term": alias,
                    "canonical": canonical,
                    "keywords": config.get("keywords", []),
                    "exclude_when": config.get("exclude_when", []),
                    "weight": config.get("weight", 0.0)
                })
                
                tokens = self.tokenizer.tokenize(alias)
                alias_tokens_map[alias] = tokens
                all_tokens.update(tokens)
            
        # 2. 批次計算 IPA
        token_ipa_map = self._engine._backend.to_phonetic_batch(list(all_tokens))
        
        # 3. 建立索引項目
        search_index = []
        for item in flat_mapping:
            alias = item["term"]
            tokens = alias_tokens_map[alias]
            ipa_parts = [token_ipa_map.get(t, '') for t in tokens]
            # 合併 IPA，移除空格以進行模糊比對
            alias_phonetic = "".join(ipa_parts)
            
            search_index.append({
                "term": alias,
                "canonical": item["canonical"],
                "phonetic": alias_phonetic,
                "token_count": len(tokens),
                "keywords": item["keywords"],
                "exclude_when": item["exclude_when"],
                "weight": item["weight"]
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
            window_size: 上下文視窗大小 (預設 50 字符，英文句子較長)

        Returns:
            (bool, float): (是否命中關鍵字, 關鍵字距離)
        """
        if not keywords:
            return False, None
        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(full_text), end_idx + window_size)
        context_text = full_text[ctx_start:ctx_end].lower()
        
        min_distance = None
        for kw in keywords:
            kw_lower = kw.lower()
            kw_idx = context_text.find(kw_lower)
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
            # 距離越近，加分越多 (最大 0.8)
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
        context_lower = context.lower()
        for condition in exclude_when:
            if condition.lower() in context_lower:
                return True
        return False
    
    def _has_required_keyword(self, keywords: List[str], context: str) -> bool:
        """檢查是否滿足關鍵字必要條件"""
        if not keywords:
            return True
        context_lower = context.lower()
        for kw in keywords:
            if kw.lower() in context_lower:
                return True
        return False

    def correct(self, text: str, full_context: str = None, silent: bool = False) -> str:
        """
        執行英文文本修正

        Args:
            text: 待修正的英文文本
            full_context: 完整的原始句子 (用於 keyword 和 exclude_when 檢查)
            silent: 是否靜默模式 (不輸出修正日誌)

        Returns:
            str: 修正後的文本
        """
        with TimingContext("EnglishCorrector.correct", self._logger, logging.DEBUG):
            candidates = self._find_candidates(text, full_context)
            final_candidates = self._resolve_conflicts(candidates)
            return self._apply_replacements(text, final_candidates, silent=silent)

    def correct_streaming(
        self,
        text: str,
        on_correction: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Generator[Dict[str, Any], None, str]:
        """
        串流式修正 - 邊處理邊回報進度

        Args:
            text: 輸入文本
            on_correction: 找到有效修正時的回調函數

        Yields:
            Dict: 每個有效的修正候選
        
        Returns:
            str: 最終修正後的文本
        """
        candidates = self._find_candidates(text, text)
        final_candidates = self._resolve_conflicts(candidates)
        
        # 按位置排序
        final_candidates.sort(key=lambda x: x["start"])
        
        for cand in final_candidates:
            if cand["original"] != cand["replacement"]:
                if on_correction:
                    on_correction(cand)
                yield cand
        
        result = self._apply_replacements(text, final_candidates, silent=True)
        yield result

    def _find_candidates(self, text: str, full_context: str = None) -> List[Dict]:
        """搜尋所有可能的修正候選"""
        context = full_context if full_context else text
        tokens = self.tokenizer.tokenize(text)
        indices = self.tokenizer.get_token_indices(text)
        
        if not tokens:
            return []
        
        # 預先計算每個 token 的 IPA
        unique_tokens = list(set(tokens))
        token_ipa_map = self._engine._backend.to_phonetic_batch(unique_tokens)
        token_ipas = [token_ipa_map.get(token, '') for token in tokens]
            
        candidates = []
        n = len(tokens)
        
        # 遍歷搜尋索引
        for item in self.search_index:
            # 允許視窗大小有彈性，以處理 ASR 分割錯誤
            target_len = item["token_count"]
            min_len = max(1, target_len - 2)
            max_len = min(n, target_len + 3)
            
            for length in range(max_len, min_len - 1, -1):
                # 滑動視窗
                for i in range(n - length + 1):
                    # 組合視窗內的 IPA
                    window_phonetic = "".join(token_ipas[i : i + length])
                    
                    # 快速檢查：長度差異太大就不比對
                    if abs(len(window_phonetic) - len(item["phonetic"])) > max(len(item["phonetic"]), 5) * 0.6:
                         continue

                    # 計算相似度
                    error_ratio, is_match = self.phonetic.calculate_similarity_score(
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
                        
                        # 避免自我替換 (如果原文已經是標準詞)
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
        """
        解決候選衝突

        當多個候選修正重疊時，選擇分數最低 (最佳) 的候選。
        """
        # 按分數排序 (越低越好)
        candidates.sort(key=lambda x: x["score"])
        
        final_candidates = []
        for cand in candidates:
            is_conflict = False
            for accepted in final_candidates:
                # 檢查區間重疊
                if max(cand["start"], accepted["start"]) < min(cand["end"], accepted["end"]):
                    is_conflict = True
                    break
            if not is_conflict:
                final_candidates.append(cand)
                
        return final_candidates

    def _apply_replacements(self, text: str, candidates: List[Dict], silent: bool = False) -> str:
        """應用修正並輸出日誌"""
        # 按位置從後往前替換，避免索引偏移 (或者重建字串)
        # 這裡使用重建字串的方式
        candidates.sort(key=lambda x: x["start"])
        
        result = []
        last_pos = 0
        for cand in candidates:
            # 加入未修正部分
            result.append(text[last_pos : cand["start"]])
            # 加入修正詞
            result.append(cand["replacement"])
            
            # 輸出修正日誌 (用戶可見的修正反饋)
            if not silent and cand["original"] != cand["replacement"]:
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
