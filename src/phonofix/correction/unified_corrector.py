"""
統一修正器模組 (Unified Corrector)

這是多語言修正系統的主要入口點。
負責協調語言路由與特定語言的修正器，以處理混合語言的文本。

設計原則：
- 使用 Dict[str, CorrectorProtocol] 而非寫死的 zh/en
- 新增語言只需在 dict 中加入對應的 corrector
- 符合開放封閉原則 (OCP)

路由策略 (方案 A)：
- 對「短英數片段」(≤5字元) 採用雙重處理策略
- 同時讓中文和英文修正器嘗試，選擇有修正的結果
- 解決 "1kg" → "EKG" 這類中文語境下的誤識問題

使用方式:
    from phonofix import UnifiedEngine

    engine = UnifiedEngine()
    corrector = engine.create_corrector({
        '台北車站': ['北車'],
        'Python': ['Pyton'],
    })
    result = corrector.correct('我在北車學習Pyton')

    # 進階：手動組合 correctors
    from phonofix.correction import UnifiedCorrector

    unified = UnifiedCorrector(
        correctors={'zh': zh_corrector, 'en': en_corrector},
        router=language_router,
    )
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from phonofix.router.language_router import LanguageRouter
from phonofix.correction.protocol import CorrectorProtocol
from phonofix.utils.logger import get_logger, TimingContext

if TYPE_CHECKING:
    from phonofix.engine.unified_engine import UnifiedEngine


class UnifiedCorrector:
    """
    統一修正器 (Unified Corrector)

    功能:
    - 接收混合語言文本
    - 自動識別並分割不同語言的片段
    - 將片段分派給對應的語言修正器
    - 合併修正後的結果

    設計:
    - 使用 Dict[str, CorrectorProtocol] 儲存各語言修正器
    - 語言代碼與 LanguageRouter 的分割結果對應
    - 新增語言無需修改此類別

    建立方式:
        # 透過 UnifiedEngine（推薦）
        engine = UnifiedEngine()
        corrector = engine.create_corrector(terms)

        # 手動建立（進階）
        corrector = UnifiedCorrector(
            correctors={'zh': zh_corrector, 'en': en_corrector},
            router=language_router,
        )
    """

    def __init__(
        self,
        correctors: Dict[str, CorrectorProtocol],
        router: LanguageRouter,
    ):
        """
        初始化統一修正器

        Args:
            correctors: 語言代碼到修正器的映射
                例如 {'zh': ChineseCorrector, 'en': EnglishCorrector}
            router: 語言路由器，負責分割混合語言文本
        """
        self._correctors = correctors
        self.router = router
        self._logger = get_logger("corrector.unified")
        self._cross_lingual_mappings = (
            []
        )  # 跨語言詞彙映射，格式: [(alias, canonical), ...]

        self._logger.debug(
            f"UnifiedCorrector initialized with languages: {list(correctors.keys())}"
        )

    @classmethod
    def _from_engine(
        cls,
        engine: "UnifiedEngine",
        correctors: Dict[str, CorrectorProtocol],
    ) -> "UnifiedCorrector":
        """
        由 UnifiedEngine 調用的內部工廠方法

        此方法使用 Engine 提供的子 Corrector，避免重複初始化。

        Args:
            engine: UnifiedEngine 實例
            correctors: 語言代碼到修正器的映射

        Returns:
            UnifiedCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.unified")
        instance.router = engine.router
        instance._correctors = correctors
        instance._cross_lingual_mappings = []  # 將在 set_cross_lingual_mappings 中設定

        instance._logger.debug(
            f"UnifiedCorrector created via engine with languages: {list(correctors.keys())}"
        )

        return instance

    @property
    def correctors(self) -> Dict[str, CorrectorProtocol]:
        """取得所有語言修正器"""
        return self._correctors

    @property
    def supported_languages(self) -> list:
        """取得支援的語言列表"""
        return list(self._correctors.keys())

    def _is_short_alphanumeric(self, text: str) -> bool:
        """
        判斷是否為短英數字串（可能需要雙重處理）

        這類片段在中文語境中可能是誤識，例如：
        - "1kg" 可能應該是 "EKG"（醫療設備）
        - "2B" 可能是鉛筆型號，不需替換
        - "A4" 可能是紙張大小

        Args:
            text: 待判斷的文本片段

        Returns:
            bool: 是否為短英數字串
        """
        cleaned = text.replace(" ", "").replace(".", "")
        # 長度 ≤ 5 且全是英數字
        return len(cleaned) <= 5 and len(cleaned) > 0 and cleaned.isalnum()

    def _competitive_correct(
        self,
        segment: str,
        full_context: str,
        primary_lang: str,
    ) -> str:
        """
        競爭式修正：讓多個修正器同時嘗試，選擇最佳結果

        策略：
        1. 先讓原本被指派的修正器嘗試
        2. 如果無修正，讓其他修正器也嘗試
        3. 選擇有修正的結果（優先採用）

        Args:
            segment: 待修正的片段
            full_context: 完整上下文（用於 keyword/exclude_when 判斷）
            primary_lang: 原本被路由指派的語言

        Returns:
            str: 修正後的結果
        """
        candidates: List[Tuple[str, str]] = []  # [(lang, result), ...]

        # 定義嘗試順序
        # 1. 日文 (ja): 優先處理 Romaji，因為它最容易被誤判為英文
        # 2. 中文 (zh): 處理短代碼誤識 (如 1kg -> EKG)
        # 3. 英文 (en): 最後處理標準英文
        try_order = ["ja", "zh", "en"]

        for lang in try_order:
            if lang not in self._correctors:
                continue

            corrector = self._correctors[lang]

            try:
                # 使用 silent=True 避免重複 print
                result = corrector.correct(
                    segment, full_context=full_context, silent=True
                )
            except TypeError:
                # 如果不支援 full_context 或 silent 參數，嘗試其他組合
                try:
                    result = corrector.correct(segment, silent=True)
                except TypeError:
                    result = corrector.correct(segment)

            # 如果有修正（結果與原文不同）
            if result != segment:
                candidates.append((lang, result))
                self._logger.debug(
                    f"Competitive correction: '{segment}' → '{result}' (by {lang})"
                )

        # 選擇結果
        if candidates:
            # 採用第一個有修正的結果
            chosen_lang, chosen_result = candidates[0]
            self._logger.debug(
                f"Competitive winner: {chosen_lang} with '{chosen_result}'"
            )
            # 手動 print 獲勝的修正結果（只 print 一次）
            print(f"[發音修正] '{segment}' -> '{chosen_result}' (Score: N/A)")
            return chosen_result

        # 都沒有修正，保持原樣
        return segment

    def set_cross_lingual_mappings(self, mappings: List[Tuple[str, str]]) -> None:
        """
        設定跨語言詞彙映射

        這些映射會在 Router 切分之前先進行預匹配替換，
        解決跨語言詞彙被切斷的問題。

        Args:
            mappings: 映射列表，格式為 [(alias, canonical), ...]
                      例如 [("PCN的引流袋", "PCN引流袋"), ("11位", "3-Way")]
        """
        # 按 alias 長度降序排列，優先匹配長的
        self._cross_lingual_mappings = sorted(
            mappings, key=lambda x: len(x[0]), reverse=True
        )
        self._logger.debug(f"Set {len(mappings)} cross-lingual mappings")

    def _pre_match_cross_lingual(self, text: str) -> str:
        """
        預匹配跨語言詞彙

        在 Router 切分之前，先對跨語言的完整詞彙進行直接替換。
        這解決了如 "PCN的引流袋" 被切成 "PCN" + "的引流袋" 導致無法匹配的問題。

        Args:
            text: 原始文本

        Returns:
            str: 預處理後的文本
        """
        if not self._cross_lingual_mappings:
            return text

        result = text
        for alias, canonical in self._cross_lingual_mappings:
            if alias in result:
                result = result.replace(alias, canonical)
                self._logger.debug(f"Pre-match: '{alias}' → '{canonical}'")

        return result

    def _add_boundary_spaces(self, text: str) -> str:
        """
        在中英文邊界智能補充空格

        規則:
        1. 只在「原本就分開」的中英文邊界補充空格
        2. 如果是替換產生的邊界（原本就黏在一起），不補充空格

        注意：這個功能目前禁用，因為判斷「原本是否分開」需要更多上下文資訊。
        未來可以透過追蹤修正位置來實現更精確的空格補充。

        Args:
            text: 修正後的文本

        Returns:
            str: 文本（目前直接返回，不做處理）
        """
        # 目前禁用自動空格補充，因為會破壞原有格式
        # 如 "12號Folly" -> "12號Foley" 不應該變成 "12號 Foley"
        return text

    def correct(self, text: str, add_boundary_spaces: bool = True) -> str:
        """
        執行混合語言文本修正

        流程:
        0. 預匹配跨語言詞彙（解決詞彙被 Router 切斷的問題）
        1. 使用 LanguageRouter 將文本分割為語言片段
           例如: [('zh', '我有一台'), ('en', 'computer')]
        2. 遍歷每個片段，根據語言標籤呼叫對應的修正器
        3. 對於「短英數片段」，採用雙重處理策略（方案 A）
        4. 將修正後的片段重新組合成完整字串
        5. 智能補充中英文邊界空格

        方案 A (雙重處理):
        - 對於 ≤5 字元的英數片段（如 "1kg", "2B"）
        - 同時讓中文和英文修正器嘗試
        - 這解決了中文語境下的誤識問題（如 "1kg" → "EKG"）

        Args:
            text: 原始混合語言文本
            add_boundary_spaces: 是否在中英文邊界自動補充空格 (預設 True)

        Returns:
            str: 修正後的文本
        """
        with TimingContext("UnifiedCorrector.correct", self._logger, logging.DEBUG):
            # 0. 預匹配跨語言詞彙
            # 解決 "PCN的引流袋" 被切成 "PCN" + "的引流袋" 的問題
            text = self._pre_match_cross_lingual(text)

            # 1. 路由分割
            # 範例輸入: "我有一台1kg的computer"
            # 分割結果: [('zh', '我有一台'), ('en', '1kg'), ('zh', '的'), ('en', 'computer')]
            segments = self.router.split_by_language(text)
            corrected_segments = []

            for lang, segment in segments:
                # 方案 A：短英數片段的雙重處理
                # 如果啟用了日文支援，則對所有英文片段嘗試競爭式修正 (支援 Romaji)
                # 否則僅對短英數片段進行競爭式修正 (支援 1kg -> EKG)
                is_en_segment = lang == "en"
                has_ja_support = "ja" in self._correctors
                is_short_code = self._is_short_alphanumeric(segment)

                if is_en_segment and (has_ja_support or is_short_code):
                    # 對英文片段，讓多個修正器競爭
                    corrected = self._competitive_correct(segment, text, lang)
                    corrected_segments.append(corrected)
                    continue

                # 正常路由處理
                if lang in self._correctors:
                    corrector = self._correctors[lang]

                    # 嘗試傳入完整上下文（如果 corrector 支援）
                    # 這對於 keyword/exclude_when 判斷很重要
                    try:
                        corrected = corrector.correct(segment, full_context=text)
                    except TypeError:
                        # 如果 corrector 不接受 full_context 參數
                        corrected = corrector.correct(segment)

                    corrected_segments.append(corrected)
                else:
                    # 無對應修正器，保持原樣
                    corrected_segments.append(segment)

            # 2. 結果合併
            result = "".join(corrected_segments)

            # 3. 智能補充中英文邊界空格
            if add_boundary_spaces:
                result = self._add_boundary_spaces(result)

            return result

    def add_corrector(self, lang: str, corrector: CorrectorProtocol) -> None:
        """
        動態新增語言修正器

        Args:
            lang: 語言代碼 (如 'zh', 'en', 'ja', 'ko')
            corrector: 符合 CorrectorProtocol 的修正器實例
        """
        self._correctors[lang] = corrector
        self._logger.info(f"Added corrector for language: {lang}")

    def remove_corrector(self, lang: str) -> Optional[CorrectorProtocol]:
        """
        移除語言修正器

        Args:
            lang: 語言代碼

        Returns:
            移除的修正器實例，若不存在則返回 None
        """
        corrector = self._correctors.pop(lang, None)
        if corrector:
            self._logger.info(f"Removed corrector for language: {lang}")
        return corrector
