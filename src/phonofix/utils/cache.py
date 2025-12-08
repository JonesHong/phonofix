"""
性能優化緩存工具 (Task 7.3)

提供 LRU 緩存裝飾器和緩存統計工具。

用法：
    from phonofix.utils.cache import cached_method, get_cache_stats

    class MyGenerator:
        @cached_method(maxsize=1000)
        def expensive_operation(self, term: str) -> str:
            # 耗時操作
            return result
"""

from functools import lru_cache, wraps
from typing import Callable, Dict, Any
import threading


# 全域緩存統計
_cache_stats_lock = threading.Lock()
_cache_stats: Dict[str, Dict[str, int]] = {}


def cached_method(maxsize: int = 1000):
    """
    為類方法添加 LRU 緩存的裝飾器

    與 functools.lru_cache 不同，這個裝飾器：
    1. 正確處理 self 參數（不將 self 包含在緩存 key 中）
    2. 提供緩存統計功能
    3. 支持多線程環境

    Args:
        maxsize: 最大緩存項數量（預設 1000）

    Returns:
        裝飾器函數

    範例：
        >>> class MyClass:
        ...     @cached_method(maxsize=100)
        ...     def slow_method(self, x):
        ...         return x * 2
        >>>
        >>> obj = MyClass()
        >>> obj.slow_method(5)  # 首次調用，執行實際計算
        10
        >>> obj.slow_method(5)  # 第二次調用，從緩存返回
        10
    """
    def decorator(func: Callable) -> Callable:
        # 為每個方法創建獨立的 LRU 緩存
        # 關鍵：使用除 self 外的所有參數作為緩存 key
        cache_key = f"{func.__module__}.{func.__qualname__}"

        # 初始化統計
        with _cache_stats_lock:
            _cache_stats[cache_key] = {
                "hits": 0,
                "misses": 0,
                "size": 0,
                "maxsize": maxsize
            }

        # 儲存實例引用以便在內部函數中使用
        self_instance = None

        # 創建內部緩存函數（不包含 self）
        @lru_cache(maxsize=maxsize)
        def cached_func(*args, **kwargs):
            # 使用外部作用域的 self_instance
            return func(self_instance, *args, **kwargs)

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 更新 self_instance 引用
            nonlocal self_instance
            self_instance = self

            # 統計緩存命中/未命中
            cache_info = cached_func.cache_info()

            # 嘗試從緩存獲取
            try:
                result = cached_func(*args, **kwargs)

                # 更新統計
                new_cache_info = cached_func.cache_info()
                if new_cache_info.hits > cache_info.hits:
                    # 緩存命中
                    with _cache_stats_lock:
                        _cache_stats[cache_key]["hits"] += 1
                        _cache_stats[cache_key]["size"] = new_cache_info.currsize
                else:
                    # 緩存未命中
                    with _cache_stats_lock:
                        _cache_stats[cache_key]["misses"] += 1
                        _cache_stats[cache_key]["size"] = new_cache_info.currsize

                return result
            except TypeError:
                # 參數不可哈希，直接調用原函數
                with _cache_stats_lock:
                    _cache_stats[cache_key]["misses"] += 1
                return func(self, *args, **kwargs)

        # 添加緩存控制方法
        wrapper.cache_info = cached_func.cache_info
        wrapper.cache_clear = cached_func.cache_clear
        wrapper.cache_key = cache_key

        return wrapper

    return decorator


def get_cache_stats(method_name: str = None) -> Dict[str, Any]:
    """
    獲取緩存統計信息

    Args:
        method_name: 方法名稱（如 "phonetic_transform"），
                    如果為 None，返回所有緩存統計

    Returns:
        Dict: 緩存統計信息，包含：
            - hits: 緩存命中次數
            - misses: 緩存未命中次數
            - hit_rate: 緩存命中率（0.0-1.0）
            - size: 當前緩存大小
            - maxsize: 最大緩存大小

    範例：
        >>> stats = get_cache_stats()
        >>> print(f"命中率: {stats['overall_hit_rate']:.2%}")
        命中率: 85.30%
    """
    with _cache_stats_lock:
        if method_name:
            # 返回特定方法的統計（合並所有匹配的方法）
            total_hits = 0
            total_misses = 0
            total_size = 0
            maxsize = 0
            matched_methods = []

            for key, stats in _cache_stats.items():
                if method_name in key:
                    total_hits += stats["hits"]
                    total_misses += stats["misses"]
                    total_size = max(total_size, stats["size"])
                    maxsize = max(maxsize, stats["maxsize"])
                    matched_methods.append(key)

            if matched_methods:
                total = total_hits + total_misses
                hit_rate = total_hits / total if total > 0 else 0.0
                return {
                    "methods": matched_methods,
                    "hits": total_hits,
                    "misses": total_misses,
                    "hit_rate": hit_rate,
                    "size": total_size,
                    "maxsize": maxsize
                }
            return {}
        else:
            # 返回所有統計的摘要
            total_hits = sum(s["hits"] for s in _cache_stats.values())
            total_misses = sum(s["misses"] for s in _cache_stats.values())
            total_calls = total_hits + total_misses
            overall_hit_rate = total_hits / total_calls if total_calls > 0 else 0.0

            return {
                "overall_hit_rate": overall_hit_rate,
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_calls": total_calls,
                "methods": dict(_cache_stats)
            }


def clear_all_caches():
    """
    清除所有緩存

    用於測試或在記憶體壓力下手動清理

    範例:
        >>> clear_all_caches()
        >>> stats = get_cache_stats()
        >>> print(stats['total_hits'])
        0
    """
    with _cache_stats_lock:
        for key in _cache_stats:
            _cache_stats[key] = {
                "hits": 0,
                "misses": 0,
                "size": 0,
                "maxsize": _cache_stats[key]["maxsize"]
            }


def reset_cache_stats():
    """
    重置緩存統計（用於測試隔離）

    只重置統計計數，不清除緩存內容

    範例:
        >>> reset_cache_stats()
        >>> stats = get_cache_stats()
        >>> print(stats['total_calls'])
        0
    """
    with _cache_stats_lock:
        for key in _cache_stats:
            _cache_stats[key]["hits"] = 0
            _cache_stats[key]["misses"] = 0


def get_hit_rate(method_name: str = None) -> float:
    """
    獲取緩存命中率（便捷函數）

    Args:
        method_name: 方法名稱，如果為 None，返回總體命中率

    Returns:
        float: 命中率（0.0-1.0）

    範例:
        >>> hit_rate = get_hit_rate("phonetic_transform")
        >>> print(f"Phonetic transform 緩存命中率: {hit_rate:.2%}")
        Phonetic transform 緩存命中率: 87.50%
    """
    stats = get_cache_stats(method_name)
    if not stats:
        return 0.0
    return stats.get("hit_rate") or stats.get("overall_hit_rate", 0.0)
