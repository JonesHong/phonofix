"""
串流輸出範例 - 展示即時修正回報

這個範例展示如何使用 correct_streaming() 方法，
讓使用者可以看到即時的修正進度，減少等待感。
"""

import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phonofix import ChineseEngine

# 全域 Engine (單例模式)
engine = ChineseEngine()


def demo_streaming_correction():
    """展示串流式修正"""
    
    print("=" * 60)
    print("串流式修正展示")
    print("=" * 60)
    print()
    
    # 準備測試資料
    term_list = [
        "聖靈", "道成肉身", "聖經", "新約", "舊約", "新舊約",
        "榮光", "使徒", "福音", "默示", "感孕", "充滿",
        "章節", "恩典", "上帝", "這就是", "太初", "放縱", "父獨生子",
    ]
    exclusions = ["什麼是", "道成的文字"]
    
    article = (
        "什麼是上帝的道那你應該知道這本聖經就是上帝的道上帝的話就是上帝的道"
        "沒有錯我在說道太出與上帝同在道是聖林帶到人間的所以聖林借著莫氏就約的先知跟新約的使徒 "
        "寫一下這一本新就月生經這個是文字的道叫做真理那聖林又把道帶到人間"
        "就是借著馬利亞聖林敢運生下了倒成肉生的耶穌基督就是基督降生在地上"
        "這是道就是倒成了肉生對不對所以道被帶到人間都是聖林帶下來的 "
        "都是勝領帶下來的道成的文字就是這本新舊月聖經道成的路生就是耶穌基督自己道成的文字"
        "是真理那道成的路生呢安點注意再聽我講一次道成的文字是真理道成的路生是安點"
        "所以約翰福音第一張十四節道成的路生匆忙 充滿有恩典有真理我們也見過他的農光"
        "就是副獨生子的農光現在請你注意聽一下的話道成的文字是真理這個我們都在追求很多地方"
        "姐妹都很追求讀很好的書很好但是道成的肉身是恩點你可能忽略了這兩者都是攻擊性的武器"
        "都是攻擊性的武器除了你在上帝的話題當中要建造之外你也要明白恩典來我簡單講一句話"
        "就是沒有恩典的真理是冷酷的再聽我講一次沒有恩典的真理是冷酷的是會定人的罪的"
        "是會挑人家的錯誤的是像法律塞人一樣的但是當然反之沒有真理的恩典 "
        "沒有真理的恩典是為叫人放重的沒有錯所以這兩者你必須多了解"
    )
    
    print(f"文章長度: {len(article)} 字符")
    print()
    
    # 建立修正器
    corrector = engine.create_corrector(term_list, exclusions=exclusions)
    
    print("📍 開始串流修正...")
    print("-" * 60)
    
    start_time = time.perf_counter()
    correction_count = 0
    final_result = None
    
    # 使用串流方式處理
    for item in corrector.correct_streaming(article):
        if isinstance(item, dict):
            # 這是一個修正項目
            correction_count += 1
            elapsed = time.perf_counter() - start_time
            
            # 即時顯示修正
            tag = "📝" if item.get("has_context") else "🔧"
            print(f"  {tag} [{elapsed:.2f}s] #{correction_count:02d}: "
                  f"'{item['original']}' → '{item['replacement']}'")
        else:
            # 這是最終結果字串
            final_result = item
    
    elapsed = time.perf_counter() - start_time
    
    print("-" * 60)
    print(f"✅ 完成！共 {correction_count} 處修正，耗時 {elapsed:.3f} 秒")
    print()
    
    # 顯示部分結果
    print("修正後文章 (前 200 字):")
    print(final_result[:200] + "...")
    print()


def demo_callback_style():
    """展示 callback 風格的串流處理"""
    
    print("=" * 60)
    print("Callback 風格串流處理")
    print("=" * 60)
    print()
    
    term_list = ["台北車站", "牛奶", "發揮", "然後", "學校"]
    
    test_cases = [
        "我在胎北車站買了流奶",
        "蘭後去些校",
        "他充分花揮了才能",
    ]
    
    corrector = engine.create_corrector(term_list)
    
    for text in test_cases:
        print(f"原文: {text}")
        
        corrections = []
        
        def on_fix(c):
            corrections.append(c)
            print(f"  🔧 發現: '{c['original']}' → '{c['replacement']}'")
        
        # 使用 callback 收集修正
        result = None
        for item in corrector.correct_streaming(text, on_correction=on_fix):
            if isinstance(item, str):
                result = item
        
        print(f"結果: {result}")
        print(f"共 {len(corrections)} 處修正")
        print()


def demo_progress_bar():
    """展示進度條風格的串流處理"""
    
    print("=" * 60)
    print("進度條風格展示 (模擬)")
    print("=" * 60)
    print()
    
    term_list = ["聖靈", "聖經", "恩典", "道成肉身"]
    
    text = "聖林借著默氏寫了這本生經,道成的路生是安點的恩點"
    
    print(f"處理: {text}")
    print()
    
    corrector = engine.create_corrector(term_list)
    
    total_len = len(text)
    
    for item in corrector.correct_streaming(text):
        if isinstance(item, dict):
            # 計算進度 (基於位置)
            progress = item['end'] / total_len * 100
            bar_len = int(progress / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            
            print(f"\r[{bar}] {progress:5.1f}% - 修正 '{item['original']}' → '{item['replacement']}'", end="")
            time.sleep(0.1)  # 模擬視覺效果
        else:
            print()  # 換行
            print()
            print(f"✅ 完成: {item}")


if __name__ == "__main__":
    print("\n" + "🌊" * 20)
    print("  串流輸出範例")
    print("🌊" * 20 + "\n")
    
    demo_streaming_correction()
    print()
    
    demo_callback_style()
    print()
    
    demo_progress_bar()
    print()
    
    print("=" * 60)
    print("✅ 所有範例執行完成!")
    print("=" * 60)
