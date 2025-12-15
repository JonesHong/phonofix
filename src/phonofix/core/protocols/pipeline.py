"""
Corrector pipeline protocols

目標：
- 讓各語言 corrector 可以把「管線編排」抽到 core
- 同時保留各語言在候選生成/計分/分桶等差異化邏輯

注意：
- 這裡用 Protocol 提供型別約束；實作可以是 class 或函式型物件
- 先以中文作為樣板導入，其他語言可逐步遷移
"""

from __future__ import annotations

from typing import Any, Protocol


class ProtectionMaskBuilderProtocol(Protocol):
    """
    產生保護遮罩（Protection Mask）。

    用途：
    - 在替換前先標記「不應被修正」的位置（例如 protected_terms 命中的區段）
    - 後續候選生成/替換套用可用此遮罩跳過受保護區域
    """

    def build(self, text: str) -> set[int]:
        """
        建立保護遮罩。

        Args:
            text: 原始輸入文字

        Returns:
            set[int]: 不可被替換的字元索引集合（通常是 0-based index）
        """
        ...


class ExactDraftGeneratorProtocol(Protocol):
    """
    精準比對候選（exact-match）生成器。

    一般策略：
    - 透過 Aho-Corasick 或其他 index，找到 alias 的精準命中區段
    - 產生 draft（候選草稿），交由後續 scoring / conflict resolution 處理
    """

    def generate(self, text: str, context: str, protected_indices: set[int]) -> list[dict[str, Any]]:
        """
        產生 exact-match 候選草稿。

        Args:
            text: 待修正文本
            context: 上下文（通常等於 full_context；也可能是 pipeline 前一階段的輸出）
            protected_indices: 保護遮罩索引集合

        Returns:
            list[dict[str, Any]]: draft 列表（結構由各語言定義，但需能被 scorer/replace 處理）
        """
        ...


class FuzzyDraftGeneratorProtocol(Protocol):
    """
    模糊比對候選（fuzzy-match）生成器。

    一般策略：
    - 依語言特性（拼音/IPA/romaji）計算相似度
    - 搭配分桶/剪枝（bucket / pruning）避免 O(N*M) 退化
    - 生成 draft，交由後續 scoring / conflict resolution 處理
    """

    def generate(self, text: str, context: str, protected_indices: set[int]) -> list[dict[str, Any]]:
        """
        產生 fuzzy-match 候選草稿。

        Args:
            text: 待修正文本
            context: 上下文（通常等於 full_context；也可能是 pipeline 前一階段的輸出）
            protected_indices: 保護遮罩索引集合

        Returns:
            list[dict[str, Any]]: draft 列表
        """
        ...


class DraftScorerProtocol(Protocol):
    """
    候選草稿計分器。

    - 將 draft 轉成可比較/可排序的 candidate（通常會補上 score/error_ratio 等欄位）
    - score 的定義由各語言決定，但需能被 conflict resolver 使用
    """

    def score(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        對 drafts 計分並回傳 candidates。

        Args:
            drafts: 候選草稿

        Returns:
            list[dict[str, Any]]: 計分後 candidates
        """
        ...


class ConflictResolverProtocol(Protocol):
    """
    候選衝突解決器。

    常見衝突：
    - span 重疊（兩個替換區段互相覆蓋）
    - 同一 span 多種候選（需要選「更好」的一個）
    """

    def resolve(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        解決候選衝突，回傳最後要套用的候選列表。

        Args:
            candidates: 計分後候選

        Returns:
            list[dict[str, Any]]: 已去衝突、可直接套用的候選
        """
        ...


class ReplacementApplierProtocol(Protocol):
    """
    替換套用器。

    - 將最後 candidates 套用到原文字串上
    - 通常會「從後往前」或「重建字串」以避免索引偏移
    - 可以在套用過程 emit replacement event（由 corrector 決定）
    """

    def apply(
        self,
        text: str,
        candidates: list[dict[str, Any]],
        *,
        silent: bool,
        trace_id: str | None,
    ) -> str:
        """
        套用候選替換。

        Args:
            text: 原始文本
            candidates: 最終候選列表
            silent: 是否靜默（不輸出日誌/事件）
            trace_id: 追蹤 ID（利於串接 observability）

        Returns:
            str: 套用替換後的文本
        """
        ...
