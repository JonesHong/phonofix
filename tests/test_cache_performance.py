"""
性能測試：驗證 LRU 緩存效果 (Task 7.3)

驗收標準：
1. 緩存命中率 >80%
2. 性能提升 30-50%
"""

import time
import pytest
from phonofix.languages.chinese.fuzzy_generator import ChineseFuzzyGenerator
from phonofix.languages.japanese.fuzzy_generator import JapaneseFuzzyGenerator
from phonofix.utils.cache import get_cache_stats, get_hit_rate, reset_cache_stats


class TestCachingPerformance:
    """測試緩存性能提升"""

    def test_chinese_phonetic_transform_cache_hit_rate(self):
        """測試中文 phonetic_transform 緩存命中率"""
        generator = ChineseFuzzyGenerator()

        # 清除緩存和統計
        if hasattr(generator.phonetic_transform, 'cache_clear'):
            generator.phonetic_transform.cache_clear()
        reset_cache_stats()

        # 測試詞彙（模擬實際使用場景：重複查詢相同詞彙）
        test_terms = ["台北", "牛奶", "永和豆漿", "發揮", "東京"]

        # 第一輪：全部 cache miss
        for _ in range(10):
            for term in test_terms:
                generator.phonetic_transform(term)

        # 檢查緩存命中率
        hit_rate = get_hit_rate("phonetic_transform")

        # 因為有重複調用，命中率應該 >80%
        # 計算：第一次 5 個詞 miss，後續 9*5 次全部 hit
        # 命中率 = 45 / 50 = 90%
        assert hit_rate >= 0.80, f"緩存命中率不足: {hit_rate:.2%} < 80%"

        print(f"\n✅ phonetic_transform 緩存命中率: {hit_rate:.2%}")

    def test_chinese_generate_phonetic_variants_cache_hit_rate(self):
        """測試中文 generate_phonetic_variants 緩存命中率"""
        generator = ChineseFuzzyGenerator()

        # 清除緩存和統計
        if hasattr(generator.generate_phonetic_variants, 'cache_clear'):
            generator.generate_phonetic_variants.cache_clear()
        reset_cache_stats()

        # 測試 Pinyin（模擬變體生成場景）
        test_pinyins = ["taibei", "niunai", "yonghe", "fahui", "dongjing"]

        # 第一輪：全部 cache miss
        for _ in range(10):
            for pinyin in test_pinyins:
                generator.generate_phonetic_variants(pinyin)

        # 檢查緩存命中率
        hit_rate = get_hit_rate("generate_phonetic_variants")

        # 命中率應該 >80%
        assert hit_rate >= 0.80, f"緩存命中率不足: {hit_rate:.2%} < 80%"

        print(f"\n✅ generate_phonetic_variants 緩存命中率: {hit_rate:.2%}")

    def test_chinese_generate_variants_performance_improvement(self):
        """測試中文 generate_variants 性能提升"""
        generator = ChineseFuzzyGenerator()

        # 清除緩存
        if hasattr(generator.phonetic_transform, 'cache_clear'):
            generator.phonetic_transform.cache_clear()
        if hasattr(generator.generate_phonetic_variants, 'cache_clear'):
            generator.generate_phonetic_variants.cache_clear()

        test_terms = ["台北車站", "永和豆漿", "牛奶", "發揮", "東京"]

        # === 測試無緩存性能（第一次調用）===
        start_time = time.perf_counter()
        for term in test_terms:
            generator.generate_variants(term, max_variants=20)
        first_run_time = time.perf_counter() - start_time

        # === 測試有緩存性能（重複調用）===
        start_time = time.perf_counter()
        for _ in range(10):
            for term in test_terms:
                generator.generate_variants(term, max_variants=20)
        repeated_run_time = time.perf_counter() - start_time

        # 計算平均單次調用時間
        avg_first_run = first_run_time / len(test_terms)
        avg_repeated_run = repeated_run_time / (10 * len(test_terms))

        # 性能提升比例
        improvement = (1 - avg_repeated_run / avg_first_run) * 100

        print(f"\n📊 性能測試結果:")
        print(f"   第一次調用平均時間: {avg_first_run*1000:.2f} ms")
        print(f"   緩存後平均時間: {avg_repeated_run*1000:.2f} ms")
        print(f"   性能提升: {improvement:.1f}%")

        # 驗收標準：性能提升 30-50%
        assert improvement >= 30, f"性能提升不足: {improvement:.1f}% < 30%"

        print(f"\n✅ 性能提升達標: {improvement:.1f}% >= 30%")

    @pytest.mark.skipif(True, reason="日文測試需要 fugashi 和 cutlet 系統套件")
    def test_japanese_phonetic_transform_cache_hit_rate(self):
        """測試日文 phonetic_transform 緩存命中率"""
        generator = JapaneseFuzzyGenerator()

        # 清除緩存和統計
        if hasattr(generator.phonetic_transform, 'cache_clear'):
            generator.phonetic_transform.cache_clear()
        reset_cache_stats()

        # 測試詞彙
        test_terms = ["東京", "会社", "学校", "先生", "時間"]

        # 第一輪：全部 cache miss
        for _ in range(10):
            for term in test_terms:
                generator.phonetic_transform(term)

        # 檢查緩存命中率
        hit_rate = get_hit_rate("phonetic_transform")

        # 命中率應該 >80%
        assert hit_rate >= 0.80, f"緩存命中率不足: {hit_rate:.2%} < 80%"

        print(f"\n✅ 日文 phonetic_transform 緩存命中率: {hit_rate:.2%}")

    def test_cache_stats_api(self):
        """測試緩存統計 API"""
        generator = ChineseFuzzyGenerator()

        # 清除緩存和統計
        if hasattr(generator.phonetic_transform, 'cache_clear'):
            generator.phonetic_transform.cache_clear()
        reset_cache_stats()

        # 執行一些操作
        for _ in range(5):
            generator.phonetic_transform("台北")
            generator.phonetic_transform("東京")

        # 獲取統計
        stats = get_cache_stats()

        print(f"\n📊 緩存統計:")
        print(f"   總命中率: {stats.get('overall_hit_rate', 0):.2%}")
        print(f"   總命中次數: {stats.get('total_hits', 0)}")
        print(f"   總未命中次數: {stats.get('total_misses', 0)}")
        print(f"   總調用次數: {stats.get('total_calls', 0)}")

        # 驗證統計正確（只統計本測試的調用）
        assert stats['total_calls'] == 10, f"總調用次數應該是 10，實際是 {stats['total_calls']}"
        assert stats['total_hits'] >= 8, f"應該有至少 8 次命中，實際是 {stats['total_hits']}"

        print(f"\n✅ 緩存統計 API 正常工作")


class TestCacheCorrectness:
    """測試緩存不影響功能正確性"""

    def test_chinese_cache_returns_same_results(self):
        """測試中文緩存返回相同結果"""
        generator = ChineseFuzzyGenerator()

        # 清除緩存和統計
        if hasattr(generator.phonetic_transform, 'cache_clear'):
            generator.phonetic_transform.cache_clear()
        reset_cache_stats()

        term = "台北"

        # 第一次調用（cache miss）
        result1 = generator.phonetic_transform(term)

        # 第二次調用（cache hit）
        result2 = generator.phonetic_transform(term)

        # 結果應該完全相同
        assert result1 == result2, "緩存結果與原始結果不一致"

        print(f"\n✅ 緩存結果正確: {result1} == {result2}")

    @pytest.mark.skipif(True, reason="日文測試需要 fugashi 和 cutlet 系統套件")
    def test_japanese_cache_returns_same_results(self):
        """測試日文緩存返回相同結果"""
        generator = JapaneseFuzzyGenerator()

        # 清除緩存和統計
        if hasattr(generator.phonetic_transform, 'cache_clear'):
            generator.phonetic_transform.cache_clear()
        reset_cache_stats()

        term = "東京"

        # 第一次調用（cache miss）
        result1 = generator.phonetic_transform(term)

        # 第二次調用（cache hit）
        result2 = generator.phonetic_transform(term)

        # 結果應該完全相同
        assert result1 == result2, "緩存結果與原始結果不一致"

        print(f"\n✅ 日文緩存結果正確: {result1} == {result2}")

    def test_cache_with_different_inputs(self):
        """測試緩存正確區分不同輸入"""
        generator = ChineseFuzzyGenerator()

        # 清除緩存和統計
        if hasattr(generator.phonetic_transform, 'cache_clear'):
            generator.phonetic_transform.cache_clear()
        reset_cache_stats()

        # 不同的輸入應該有不同的緩存
        result_taipei = generator.phonetic_transform("台北")
        result_milk = generator.phonetic_transform("牛奶")

        assert result_taipei != result_milk, "不同輸入應該有不同結果"

        # 重複調用應該返回相同結果
        assert generator.phonetic_transform("台北") == result_taipei
        assert generator.phonetic_transform("牛奶") == result_milk

        print(f"\n✅ 緩存正確區分不同輸入: {result_taipei} != {result_milk}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
