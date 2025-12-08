"""
修正器抽象基類

定義所有語言修正器必須實作的統一接口。

設計原則：
- 統一方法簽名（text, full_context, silent）
- 共享工廠方法模式（_from_engine）
- 強制接口一致性
- 支持多語言擴展

架構一致性：
本模組與其他核心組件保持一致的 ABC 模式：
- PhoneticSystem(ABC) in core/phonetic_interface.py
- Tokenizer(ABC) in core/tokenizer_interface.py
- BaseFuzzyGenerator(ABC) in core/fuzzy_generator_interface.py
- BaseCorrector(ABC) in core/corrector_interface.py (本模組)
- CorrectorEngine(ABC) in engine/base.py

使用範例:
    >>> from phonofix.core import BaseCorrector
    >>>
    >>> class MyCorrector(BaseCorrector):
    ...     def correct(self, text, full_context=None, silent=False):
    ...         # 實現修正邏輯
    ...         return text.upper()
    ...
    ...     @classmethod
    ...     def _from_engine(cls, engine, term_dict, **kwargs):
    ...         # 實現工廠方法
    ...         return cls()
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from phonofix.engine.base import CorrectorEngine


class BaseCorrector(ABC):
    """
    修正器抽象基類

    職責：
    - 定義統一的修正接口 (correct 方法)
    - 定義統一的工廠方法 (_from_engine)
    - 強制子類實現一致的接口

    設計模式：
    - 工廠方法模式：透過 Engine 創建輕量 Corrector 實例
    - 策略模式：不同語言使用不同的修正策略
    - 模板方法模式：correct() 定義標準流程

    子類實現：
    - ChineseCorrector: 中文 Pinyin 模糊修正
    - EnglishCorrector: 英文 IPA 語音修正
    - JapaneseCorrector: 日文 Romaji 語音修正

    使用範例：
        >>> # 透過 Engine 創建（推薦）
        >>> from phonofix import ChineseEngine
        >>> engine = ChineseEngine()
        >>> corrector = engine.create_corrector(["台北車站", "牛奶"])
        >>>
        >>> # 基本使用
        >>> result = corrector.correct("我在北車買流奶")
        >>> print(result)
        我在台北車站買牛奶
        >>>
        >>> # 使用完整上下文
        >>> result = corrector.correct("北車", full_context="我在北車等你")
        >>> print(result)
        台北車站
        >>>
        >>> # 靜默模式（不打印日誌）
        >>> result = corrector.correct("北車", silent=True)
    """

    @abstractmethod
    def correct(
        self,
        text: str,
        full_context: Optional[str] = None,
        silent: bool = False
    ) -> str:
        """
        執行文本修正

        這是修正器的核心方法，負責將輸入文本中的錯誤替換為正確的形式。

        參數說明：
        -----------
        text : str
            待修正的文本。
            - 對於單語言 Corrector（如 ChineseCorrector），這是待修正的片段
            - 對於 UnifiedCorrector，這可能是混合語言文本

        full_context : Optional[str], default=None
            完整的上下文文本，用於 keyword 和 exclude_when 判斷。

            **為什麼需要 full_context？**
            某些修正需要根據上下文決定是否執行：
            - keyword 匹配：只有當上下文包含特定關鍵字時才修正
            - exclude_when 排除：當上下文包含排除詞時不修正

            **範例**：
            >>> # 不使用 full_context
            >>> corrector.correct("永豆")  # 可能修正為 "永和豆漿" 或 "勇者鬥惡龍"

            >>> # 使用 full_context（正確）
            >>> corrector.correct("永豆", full_context="我去買永豆當宵夜")
            永和豆漿  # 因為有 "買"、"宵夜" 關鍵字

            >>> corrector.correct("永豆", full_context="我在玩永豆的遊戲")
            勇者鬥惡龍  # 因為有 "玩"、"遊戲" 關鍵字

            **實現注意事項**：
            - 如果子類不需要上下文判斷，可以忽略此參數
            - 如果 full_context 為 None，使用 text 本身作為上下文

        silent : bool, default=False
            是否靜默模式（不打印修正日誌）。
            - True: 不輸出 [發音修正] 日誌
            - False: 輸出修正日誌（預設）

            **使用場景**：
            - 批量處理時使用 silent=True 避免日誌氾濫
            - UnifiedCorrector 內部調用時使用 silent=True
            - 測試時使用 silent=True 保持輸出乾淨

        返回值：
        -------
        str
            修正後的文本。如果沒有匹配到任何修正規則，返回原文本。

        範例：
        -----
        >>> from phonofix import ChineseEngine
        >>> engine = ChineseEngine()
        >>> corrector = engine.create_corrector({
        ...     "台北車站": ["北車"],
        ...     "牛奶": ["流奶"]
        ... })
        >>>
        >>> # 基本使用
        >>> result = corrector.correct("我在北車")
        [發音修正] '北車' -> '台北車站' (Score: 0.85)
        >>> print(result)
        我在台北車站
        >>>
        >>> # 靜默模式
        >>> result = corrector.correct("我在北車", silent=True)
        >>> print(result)
        我在台北車站
        >>>
        >>> # 使用上下文
        >>> corrector2 = engine.create_corrector({
        ...     "永和豆漿": {
        ...         "aliases": ["永豆"],
        ...         "keywords": ["買", "吃", "宵夜"],
        ...         "weight": 0.3
        ...     }
        ... })
        >>> result = corrector2.correct("永豆", full_context="我去買永豆")
        >>> print(result)
        永和豆漿

        注意事項：
        ---------
        1. 子類實現時必須處理空字符串和 None 的情況
        2. 修正邏輯應該是冪等的（多次調用結果相同）
        3. 不應該修改輸入參數（返回新字符串）
        4. 複雜度應該是 O(n) 或 O(n*m)，避免指數級複雜度
        """
        pass

    @classmethod
    @abstractmethod
    def _from_engine(
        cls,
        engine: "CorrectorEngine",
        term_dict,
        **kwargs
    ) -> "BaseCorrector":
        """
        由 Engine 調用的工廠方法

        這個方法讓 Engine 可以建立輕量的 Corrector 實例，
        共享 Engine 中的昂貴資源（PhoneticSystem, Tokenizer, FuzzyGenerator）。

        設計模式：工廠方法模式
        - Engine 持有共享資源（singleton 模式）
        - Corrector 透過工廠方法獲取資源引用
        - 避免重複初始化昂貴資源（如 espeak-ng）

        參數說明：
        -----------
        engine : CorrectorEngine
            CorrectorEngine 實例，提供共享的語音系統、分詞器和模糊生成器。

            **Engine 提供的資源**：
            - phonetic: PhoneticSystem 實例（語音轉換）
            - tokenizer: Tokenizer 實例（文本分詞）
            - fuzzy_generator: FuzzyGenerator 實例（變體生成）
            - logger: Logger 實例（日誌記錄）

        term_dict : List[str] | Dict[str, List[str]] | Dict[str, dict]
            詞彙配置，支援多種格式：

            **格式 1: 純詞彙列表**
            >>> term_dict = ["台北車站", "牛奶", "Python"]
            自動生成語音變體作為別名

            **格式 2: 詞彙 + 手動別名**
            >>> term_dict = {
            ...     "台北車站": ["北車", "台北站"],
            ...     "牛奶": ["流奶"]
            ... }

            **格式 3: 完整配置**
            >>> term_dict = {
            ...     "永和豆漿": {
            ...         "aliases": ["永豆", "勇豆"],
            ...         "keywords": ["吃", "喝", "買", "宵夜"],
            ...         "exclude_when": ["遊戲", "玩"],
            ...         "weight": 0.3
            ...     }
            ... }

            **配置選項說明**：
            - aliases: 手動指定的別名列表（會與自動生成的合併）
            - keywords: 上下文關鍵字（用於加權評分）
            - exclude_when: 排除關鍵字（包含這些詞時不修正）
            - weight: 基礎權重（0.0-1.0，影響評分）

        **kwargs : dict
            額外配置選項，常見參數：

            - protected_terms: List[str]
              保護詞列表，這些詞不會被修正
              >>> protected_terms=["北側", "南側"]

            - enable_fuzzy: bool
              是否啟用模糊匹配（預設 True）

            - tolerance: float
              容錯率（0.0-1.0，預設由語言特定配置決定）

            - max_variants: int
              每個詞最大變體數量（預設 30）

        返回值：
        -------
        BaseCorrector
            修正器實例，可立即使用。

        範例：
        -----
        >>> from phonofix import ChineseEngine
        >>>
        >>> # 透過 Engine 創建（推薦方式）
        >>> engine = ChineseEngine()
        >>> corrector = engine.create_corrector(["台北車站", "牛奶"])
        >>>
        >>> # 內部實際調用
        >>> # corrector = ChineseCorrector._from_engine(engine, ["台北車站", "牛奶"])
        >>>
        >>> # 進階配置
        >>> corrector = engine.create_corrector(
        ...     {
        ...         "台北車站": {
        ...             "aliases": ["北車"],
        ...             "keywords": ["等", "車站"],
        ...             "weight": 0.3
        ...         }
        ...     },
        ...     protected_terms=["北側", "南側"]
        ... )

        實現指南：
        ---------
        子類實現此方法時應該：
        1. 從 engine 獲取共享資源（phonetic, tokenizer, fuzzy_generator）
        2. 處理 term_dict 的不同格式
        3. 生成語音變體和別名
        4. 建立內部詞典結構
        5. 返回輕量級 Corrector 實例

        典型實現模式：
        ```python
        @classmethod
        def _from_engine(cls, engine, term_dict, **kwargs):
            # 1. 獲取共享資源
            phonetic = engine.phonetic
            tokenizer = engine.tokenizer
            fuzzy_generator = engine.fuzzy_generator

            # 2. 處理 term_dict
            normalized_dict = cls._normalize_term_dict(term_dict)

            # 3. 建立實例
            instance = cls.__new__(cls)
            instance._engine = engine
            instance.phonetic = phonetic
            instance.tokenizer = tokenizer
            instance.normalized_dict = normalized_dict

            # 4. 返回實例
            return instance
        ```

        注意事項：
        ---------
        1. 不要在此方法中初始化昂貴資源（使用 Engine 提供的）
        2. 返回的實例應該是輕量的（<10ms 創建時間）
        3. 多個 Corrector 實例應該共享相同的 Engine 資源
        """
        pass
