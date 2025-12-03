"""
英文 G2P 效能基準測試

比較 phonemizer + espeak-ng vs eng-to-ipa 的效能
"""

import time
from typing import Callable, List


def benchmark_g2p(
    convert_func: Callable[[str], str],
    words: List[str],
    name: str,
    iterations: int = 1
) -> float:
    """
    測試 G2P 函式的效能
    
    Returns:
        float: 平均每個單字的轉換時間 (毫秒)
    """
    total_time = 0
    total_words = 0
    
    for _ in range(iterations):
        start = time.perf_counter()
        for word in words:
            convert_func(word)
        end = time.perf_counter()
        total_time += (end - start)
        total_words += len(words)
    
    avg_per_word_ms = (total_time / total_words) * 1000
    total_ms = total_time * 1000
    
    print(f"\n{name}")
    print(f"  總時間: {total_ms:.2f} ms")
    print(f"  單字數: {total_words}")
    print(f"  平均每字: {avg_per_word_ms:.4f} ms")
    
    return avg_per_word_ms


def main():
    # 測試詞彙
    common_words = [
        "hello", "world", "python", "programming", "computer",
        "algorithm", "function", "variable", "database", "network",
        "application", "development", "framework", "library", "module",
    ]
    
    oov_words = [
        "ChatGPT", "OpenAI", "TensorFlow", "Kubernetes", "iPhone",
        "LLaMA", "GPT4", "TypeScript", "PostgreSQL", "MongoDB",
    ]
    
    all_words = common_words + oov_words
    
    print("=" * 60)
    print("英文 G2P 效能基準測試")
    print("=" * 60)
    
    # 測試 phonemizer
    print("\n--- phonemizer + espeak-ng ---")
    try:
        from multi_language_corrector.languages.english.phonetic_impl import (
            cached_ipa_convert,
            clear_english_cache,
            is_phonemizer_available,
        )
        
        if not is_phonemizer_available():
            print("phonemizer 不可用，跳過測試")
        else:
            # 清除快取以測試冷啟動效能
            clear_english_cache()
            
            # 冷啟動測試
            benchmark_g2p(
                cached_ipa_convert, 
                all_words, 
                "phonemizer (冷啟動)",
                iterations=1
            )
            
            # 快取命中測試
            benchmark_g2p(
                cached_ipa_convert, 
                all_words, 
                "phonemizer (快取命中)",
                iterations=10
            )
            
            # 示範 OOV 處理
            print("\n  OOV 處理範例:")
            for word in oov_words[:5]:
                result = cached_ipa_convert(word)
                print(f"    {word} -> {result}")
    
    except ImportError as e:
        print(f"匯入錯誤: {e}")
    
    # 測試 eng-to-ipa (如果可用)
    print("\n--- eng-to-ipa (舊版，供比較) ---")
    try:
        import eng_to_ipa as ipa
        
        def old_convert(text):
            return ipa.convert(text)
        
        benchmark_g2p(
            old_convert,
            all_words,
            "eng-to-ipa",
            iterations=1
        )
        
        # 示範 OOV 處理（會有 * 號）
        print("\n  OOV 處理範例:")
        for word in oov_words[:5]:
            result = ipa.convert(word)
            print(f"    {word} -> {result}")
    
    except ImportError:
        print("eng-to-ipa 未安裝，跳過比較")
    
    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
