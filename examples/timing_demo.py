"""
計時與日誌範例

展示如何使用 verbose=True 來啟用計時日誌，
以便監控初始化和修正的效能。
"""

from multi_language_corrector import (
    UnifiedEngine,
    ChineseEngine,
    EnglishEngine,
    enable_timing_logging,
)


def demo_timing_with_verbose():
    """使用 verbose=True 啟用計時"""
    print("=" * 60)
    print("範例 1: 使用 verbose=True 啟用計時")
    print("=" * 60)
    
    # 使用 verbose=True 初始化 Engine
    engine = UnifiedEngine(verbose=True)
    
    # 建立 Corrector (會輸出計時與變體)
    corrector = engine.create_corrector({
        "台北車站": ["北車"],
        "TensorFlow": ["Ten so floor"],
        "Python": ["Pyton"],
    })
    
    # 執行修正 (會輸出計時)
    result = corrector.correct("我在北車用Pyton寫Ten so floor")
    print(f"\n結果: {result}")
    print()


def demo_timing_with_callback():
    """使用 on_timing 回呼收集計時資訊"""
    print("=" * 60)
    print("範例 2: 使用 on_timing 回呼收集計時資訊")
    print("=" * 60)
    
    timing_data = []
    
    def collect_timing(operation: str, elapsed: float):
        timing_data.append({
            "operation": operation,
            "elapsed": elapsed
        })
    
    # 配置 callback
    engine = ChineseEngine(verbose=True, on_timing=collect_timing)
    corrector = engine.create_corrector(["台北車站", "高雄車站", "牛奶", "發揮"])
    
    # 執行多次修正
    texts = [
        "我在北車等你",
        "我買了流奶回家",
        "他充分花揮了才能",
    ]
    
    for text in texts:
        corrector.correct(text, silent=True)
    
    print("\n收集到的計時資訊:")
    for item in timing_data:
        print(f"  {item['operation']}: {item['elapsed']:.4f}s")
    
    # 計算統計
    correct_times = [
        item['elapsed'] for item in timing_data 
        if 'correct' in item['operation'].lower()
    ]
    if correct_times:
        print(f"\n修正操作統計:")
        print(f"  平均耗時: {sum(correct_times) / len(correct_times):.4f}s")
        print(f"  最小耗時: {min(correct_times):.4f}s")
        print(f"  最大耗時: {max(correct_times):.4f}s")
    print()


def demo_english_engine():
    """英文 Engine 計時範例"""
    print("=" * 60)
    print("範例 3: 英文 Engine (顯示變體生成)")
    print("=" * 60)
    
    engine = EnglishEngine(verbose=True)
    corrector = engine.create_corrector(["TensorFlow", "PyTorch", "NumPy"])
    
    result = corrector.correct("I use Ten so floor and Pie torch")
    print(f"\n結果: {result}")
    print()


def demo_silent_mode():
    """靜默模式 - 不輸出任何日誌"""
    print("=" * 60)
    print("範例 4: 靜默模式 (不傳 verbose)")
    print("=" * 60)
    
    # 預設不傳 verbose 就是靜默模式
    engine = UnifiedEngine()
    corrector = engine.create_corrector({
        "台北車站": ["北車"],
        "Python": ["Pyton"],
    })
    
    result = corrector.correct("我在北車用Pyton寫code")
    print(f"結果: {result}")
    print("(沒有計時日誌輸出)")
    print()


def demo_manual_logging():
    """手動控制日誌等級"""
    print("=" * 60)
    print("範例 5: 手動控制日誌等級 (使用標準 logging)")
    print("=" * 60)
    
    import logging
    
    # 方法 1: 使用便利函數
    enable_timing_logging()
    
    # 方法 2: 直接設定標準 logging
    # logging.getLogger("multi_language_corrector").setLevel(logging.DEBUG)
    
    # 現在所有 Engine/Corrector 都會輸出計時
    engine = ChineseEngine()  # 不需要傳入 verbose
    corrector = engine.create_corrector(["台北車站"])
    corrector.correct("我在北車", silent=True)
    print()


if __name__ == "__main__":
    print()
    print("🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐")
    print("  計時與日誌功能範例")
    print("🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐🕐")
    print()
    
    demo_timing_with_verbose()
    demo_timing_with_callback()
    demo_english_engine()
    demo_silent_mode()
    demo_manual_logging()
    
    print("=" * 60)
    print("✅ 所有範例執行完成!")
    print("=" * 60)
