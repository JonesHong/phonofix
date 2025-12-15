"""
英文 G2P 效能基準測試（更新版）

目的：
- 比較 phonofix 英文 backend（phonemizer + espeak-ng）與 eng-to-ipa（如有安裝）的效能
- 提供「逐字」與「批次」兩種測試模式（phonofix backend 支援 batch）

為什麼要更新？
- 舊版腳本會從 `phonofix.languages.english.phonetic_impl` 匯入快取函式與可用性檢查
- 新版專案已改為 Backend → Engine → Corrector 架構：
  英文 G2P 初始化/快取/批次轉換皆由 `phonofix.backend.get_english_backend()` 統一管理

使用方式：
    uv run python .\\tools\\benchmark_phonetic.py

注意：
- 若系統未安裝 espeak-ng，phonofix 英文 backend 會回報不可用並跳過測試
- 「冷啟動」在此指「冷快取」（clear_cache 後），不是 OS/進程層級冷啟動
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable

# 讓此腳本可在「未安裝套件」的情況下直接從 repo 執行（uv run / python）
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))


def benchmark_g2p(
    convert_func: Callable[[str], str],
    words: list[str],
    name: str,
    iterations: int = 1,
) -> float:
    """
    測試逐字 G2P 函式的效能。

    Returns:
        float: 平均每個單字的轉換時間（毫秒）
    """
    total_time = 0.0
    total_words = 0

    for _ in range(max(1, int(iterations))):
        start = time.perf_counter()
        for word in words:
            _ = convert_func(word)
        end = time.perf_counter()
        total_time += (end - start)
        total_words += len(words)

    avg_per_word_ms = (total_time / max(1, total_words)) * 1000
    total_ms = total_time * 1000

    print(f"\n{name}")
    print(f"  總時間: {total_ms:.2f} ms")
    print(f"  單字數: {total_words}")
    print(f"  平均每字: {avg_per_word_ms:.4f} ms")

    return avg_per_word_ms


def benchmark_g2p_batch(
    convert_batch_func: Callable[[list[str]], dict[str, str]],
    words: list[str],
    name: str,
    iterations: int = 1,
) -> float:
    """
    測試批次 G2P 函式的效能（一次轉換多個字串）。

    Returns:
        float: 平均每個單字的轉換時間（毫秒）
    """
    total_time = 0.0
    total_words = 0

    for _ in range(max(1, int(iterations))):
        start = time.perf_counter()
        result = convert_batch_func(words)
        end = time.perf_counter()
        total_time += (end - start)
        total_words += len(words)

        if not isinstance(result, dict):
            raise TypeError("batch G2P 必須回傳 dict[str, str]")

    avg_per_word_ms = (total_time / max(1, total_words)) * 1000
    total_ms = total_time * 1000

    print(f"\n{name}")
    print(f"  總時間: {total_ms:.2f} ms")
    print(f"  單字數: {total_words}")
    print(f"  平均每字: {avg_per_word_ms:.4f} ms")

    return avg_per_word_ms


def main() -> None:
    common_words = [
        "hello",
        "world",
        "python",
        "programming",
        "computer",
        "algorithm",
        "function",
        "variable",
        "database",
        "network",
        "application",
        "development",
        "framework",
        "library",
        "module",
    ]

    oov_words = [
        "ChatGPT",
        "OpenAI",
        "TensorFlow",
        "Kubernetes",
        "iPhone",
        "LLaMA",
        "GPT4",
        "TypeScript",
        "PostgreSQL",
        "MongoDB",
    ]

    all_words = common_words + oov_words

    print("=" * 60)
    print("英文 G2P 效能基準測試")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # phonofix backend（phonemizer + espeak-ng）
    # -------------------------------------------------------------------------
    print("\n--- phonofix (phonemizer + espeak-ng) ---")
    try:
        from phonofix.backend import get_english_backend

        backend = get_english_backend()

        try:
            backend.initialize()
        except (ImportError, RuntimeError) as exc:
            print("英文 backend 不可用，跳過測試。")
            print(f"原因: {exc}")
        else:
            def to_ipa(word: str) -> str:
                return backend.to_phonetic(word)

            def to_ipa_batch(words: list[str]) -> dict[str, str]:
                return backend.to_phonetic_batch(words)

            backend.clear_cache()
            benchmark_g2p_batch(to_ipa_batch, all_words, "phonofix backend（冷快取，批次）", iterations=1)

            backend.clear_cache()
            benchmark_g2p(to_ipa, all_words, "phonofix backend（冷快取，逐字）", iterations=1)

            # 熱快取：先用 batch 跑一次把 cache 填滿，再量測多次命中
            backend.clear_cache()
            _ = to_ipa_batch(all_words)
            benchmark_g2p(to_ipa, all_words, "phonofix backend（快取命中，逐字）", iterations=10)
            benchmark_g2p_batch(to_ipa_batch, all_words, "phonofix backend（快取命中，批次）", iterations=10)

            stats = backend.get_cache_stats()
            print("\n  backend 快取統計:")
            ipa_stats = (stats.get("caches") or {}).get("ipa") or {}
            print(
                "    "
                f"hits={ipa_stats.get('hits')}, misses={ipa_stats.get('misses')}, currsize={ipa_stats.get('currsize')}"
            )

            print("\n  OOV（不在字典內）轉換範例:")
            for word in oov_words[:5]:
                print(f"    {word} -> {to_ipa(word)}")
    except Exception as exc:
        print(f"執行 phonofix 測試時發生錯誤: {exc}")

    # -------------------------------------------------------------------------
    # eng-to-ipa（舊版供比較）
    # -------------------------------------------------------------------------
    print("\n--- eng-to-ipa (舊版，供比較) ---")
    try:
        import eng_to_ipa as ipa  # type: ignore[import-not-found]

        def old_convert(text: str) -> str:
            return ipa.convert(text)

        benchmark_g2p(old_convert, all_words, "eng-to-ipa", iterations=1)

        print("\n  OOV 處理範例（eng-to-ipa 可能以 * 標註未知）:")
        for word in oov_words[:5]:
            print(f"    {word} -> {ipa.convert(word)}")

    except ImportError:
        print("eng-to-ipa 未安裝，跳過比較")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
