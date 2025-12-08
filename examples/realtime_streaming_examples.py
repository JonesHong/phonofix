"""
ASR/LLM 串流修正範例

本範例展示如何在即時串流場景中使用 phonofix：
1. ASR 模式：累積文本持續更新（Realtime ASR）
2. LLM 模式：增量 chunk 持續進來（LLM Streaming）

核心概念：
- 快取已確認的修正結果，避免重複計算
- 滑動視窗保留重疊區域，防止詞彙被切斷誤判
- 自動偵測新段落，重置快取狀態
- **動態 overlap**：根據 terms/keywords 長度自動計算安全的緩衝區大小
"""

import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phonofix import (
    ChineseEngine, 
    StreamingCorrector, 
    ChunkStreamingCorrector,
    calculate_safe_overlap,
)


# 全域 Engine (不顯示 verbose 訊息)
engine = ChineseEngine(verbose=False)


def demo_asr_streaming():
    """
    模擬 Realtime ASR 場景
    
    ASR 特性：
    - 每次回傳累積的完整識別結果
    - 之前的識別可能會被修正
    - 使用 StreamingCorrector (accumulated 模式)
    - **自動計算 overlap_size**：根據 terms 長度動態調整
    """
    print("=" * 60)
    print("範例 1: ASR Realtime Streaming")
    print("=" * 60)
    print()
    
    # 建立修正器
    corrector = engine.create_corrector([
        "台北車站", "牛奶", "發揮", "然後", "TensorFlow"
    ])
    
    # 查看自動計算的 overlap (根據 terms 長度)
    auto_overlap = calculate_safe_overlap(corrector)
    print(f"自動計算的 overlap_size: {auto_overlap}")
    print(f"(基於最長 term 'TensorFlow' = 10 字母 + margin 5 = 15，取 max(15, 20) = 20)")
    print()
    
    # 建立串流處理器 - 不指定 overlap_size，讓它自動計算
    streamer = StreamingCorrector(corrector)
    print(f"StreamingCorrector 實際使用的 overlap_size: {streamer.overlap_size}")
    print()
    
    # 模擬 ASR 輸出（每次是累積的完整文本）
    asr_outputs = [
        "我在",
        "我在胎",
        "我在胎北",
        "我在胎北車",
        "我在胎北車站",
        "我在胎北車站買了",
        "我在胎北車站買了流",
        "我在胎北車站買了流奶",
        "我在胎北車站買了流奶蘭",
        "我在胎北車站買了流奶蘭後",
        "我在胎北車站買了流奶蘭後回家",
    ]
    
    print("📡 模擬 ASR 串流輸入:")
    print("-" * 60)
    
    for i, asr_text in enumerate(asr_outputs):
        result = streamer.feed(asr_text)
        
        # 顯示狀態
        confirmed_display = result.confirmed if result.confirmed else "(空)"
        pending_display = result.pending if result.pending else "(空)"
        
        print(f"[{i+1:02d}] ASR: {asr_text}")
        print(f"     ✅ 已確認: {confirmed_display}")
        print(f"     ⏳ 待確認: {pending_display}")
        print()
        
        time.sleep(0.1)  # 模擬延遲
    
    # 最後確認
    final = streamer.finalize()
    print("-" * 60)
    print(f"🏁 最終結果: {final}")
    print()


def demo_llm_streaming():
    """
    模擬 LLM Streaming 場景
    
    LLM 特性：
    - 每次收到新的 token/chunk（增量）
    - 之前的輸出不會改變
    - 使用 ChunkStreamingCorrector (chunk 模式)
    """
    print("=" * 60)
    print("範例 2: LLM Streaming Output")
    print("=" * 60)
    print()
    
    # 建立修正器
    corrector = engine.create_corrector([
        "聖靈", "恩典", "道成肉身", "聖經", "PyTorch", "NumPy"
    ])
    
    # 建立 chunk 模式串流處理器
    streamer = ChunkStreamingCorrector(corrector, overlap_size=6)
    
    # 模擬 LLM 輸出（每次是增量的 chunk）
    llm_chunks = [
        "聖林",
        "借著默氏",
        "寫了這本",
        "生經，",
        "道成的路生",
        "是安點。",
        "我用排炬",
        "和南派",
        "做機器學習。",
    ]
    
    print("🤖 模擬 LLM 串流輸出:")
    print("-" * 60)
    print("即時輸出: ", end="", flush=True)
    
    full_output = ""
    for chunk in llm_chunks:
        result = streamer.feed_chunk(chunk)
        
        # 即時輸出已確認的部分
        if result.confirmed:
            print(result.confirmed, end="", flush=True)
            full_output += result.confirmed
        
        time.sleep(0.15)  # 模擬 LLM 生成延遲
    
    # 結束時輸出剩餘部分
    remaining = streamer.finalize()
    if remaining:
        print(remaining, end="", flush=True)
        full_output += remaining
    
    print()  # 換行
    print("-" * 60)
    print(f"🏁 完整結果: {full_output}")
    print()


def demo_new_segment_detection():
    """
    展示新段落偵測
    
    當輸入文本與快取不匹配時，自動視為新段落並重置快取。
    這適用於：
    - ASR 靜音後重新開始
    - 使用者切換話題
    - 網路斷線重連
    """
    print("=" * 60)
    print("範例 3: 新段落偵測")
    print("=" * 60)
    print()
    
    corrector = engine.create_corrector(["台北車站", "高雄車站"])
    streamer = StreamingCorrector(corrector, overlap_size=5)
    
    # 模擬兩個不連續的段落
    segments = [
        # 第一段
        ["我在", "我在胎北", "我在胎北車站"],
        # 第二段（完全不同的開頭）
        ["今天去", "今天去高雄", "今天去高雄車站"],
    ]
    
    print("📝 模擬多段落輸入:")
    print("-" * 60)
    
    for seg_idx, segment in enumerate(segments):
        print(f"\n--- 段落 {seg_idx + 1} ---")
        for text in segment:
            result = streamer.feed(text)
            
            status = "🆕 新段落!" if result.is_new_segment else "   延續"
            print(f"{status} 輸入: {text}")
            print(f"         確認: {result.confirmed} | 待確認: {result.pending}")
    
    print()


def demo_performance_comparison():
    """
    效能比較：串流 vs 每次全文修正
    """
    print("=" * 60)
    print("範例 4: 效能比較")
    print("=" * 60)
    print()
    
    corrector = engine.create_corrector([
        "聖靈", "恩典", "道成肉身", "聖經", "福音", "使徒",
        "台北車站", "高雄車站", "TensorFlow", "PyTorch"
    ])
    
    # 生成長文本序列
    base_text = "我在胎北車站聽到了聖林的生音，道成的路生是安點的恩點"
    asr_sequence = [base_text[:i] for i in range(5, len(base_text) + 1, 3)]
    
    print(f"測試序列長度: {len(asr_sequence)} 次輸入")
    print(f"最終文本長度: {len(base_text)} 字符")
    print()
    
    # 方式 1: 每次全文修正
    start = time.perf_counter()
    for text in asr_sequence:
        _ = corrector.correct(text)
    time_full = time.perf_counter() - start
    
    # 方式 2: 串流修正（帶快取）
    streamer = StreamingCorrector(corrector, overlap_size=8)
    start = time.perf_counter()
    for text in asr_sequence:
        _ = streamer.feed(text)
    _ = streamer.finalize()
    time_stream = time.perf_counter() - start
    
    print(f"⏱️ 每次全文修正: {time_full:.4f} 秒")
    print(f"⏱️ 串流修正:     {time_stream:.4f} 秒")
    print(f"📈 效能提升:     {time_full/time_stream:.2f}x")
    print()
    
    # 注意：由於 overlap 機制，串流模式仍需重算部分內容
    # 主要優勢在於已確認部分不再重算


def demo_practical_usage():
    """
    實際應用範例：WebSocket ASR 處理
    """
    print("=" * 60)
    print("範例 5: 實際應用 - WebSocket ASR")  
    print("=" * 60)
    print()
    
    code = '''
# 實際應用範例 (虛擬碼)

from phonofix import ChineseEngine, StreamingCorrector

# 應用啟動時初始化
engine = ChineseEngine()
corrector = engine.create_corrector(my_terms)

# WebSocket 處理 - overlap_size 自動根據 terms 計算
async def handle_asr_websocket(websocket):
    streamer = StreamingCorrector(corrector)  # 自動計算 overlap
    
    async for message in websocket:
        asr_result = json.loads(message)
        
        if asr_result["type"] == "partial":
            # 部分識別結果
            result = streamer.feed(asr_result["text"])
            await websocket.send(json.dumps({
                "confirmed": result.confirmed,
                "pending": result.pending,
            }))
            
        elif asr_result["type"] == "final":
            # 最終識別結果
            final = streamer.finalize()
            await websocket.send(json.dumps({
                "final": final,
            }))
            streamer.reset()  # 重置，準備下一段
'''
    print(code)
    print()


def demo_dynamic_overlap():
    """
    展示動態 overlap 計算
    
    根據 terms/keywords/exclusions 的長度自動調整 overlap，
    確保長詞彙不會被截斷導致無法修正。
    """
    print("=" * 60)
    print("範例 5: 動態 Overlap 計算")
    print("=" * 60)
    print()
    
    # Case 1: 一般詞彙
    terms1 = ["台北車站", "高雄港"]  # 最長 4 字
    corrector1 = engine.create_corrector(terms1)
    overlap1 = calculate_safe_overlap(corrector1)
    print(f"一般詞彙 (台北車站 4字):")
    print(f"  自動 overlap = {overlap1} (使用預設值 20)")
    print()
    
    # Case 2: 長英文詞彙
    terms2 = {
        "TensorFlow": {},           # 10 字母
        "Kubernetes": {},           # 10 字母  
        "ElasticSearch": {},        # 13 字母
    }
    corrector2 = engine.create_corrector(terms2)
    overlap2 = calculate_safe_overlap(corrector2)
    print(f"長英文詞彙 (ElasticSearch 13字母):")
    print(f"  自動 overlap = {overlap2} (13 + margin 5 = 18，取 max(18, 20) = 20)")
    print()
    
    # Case 3: 超長 keyword
    terms3 = {
        "API": {"keywords": ["ApplicationProgrammingInterface"]},  # 31 字母!
    }
    corrector3 = engine.create_corrector(terms3)
    overlap3 = calculate_safe_overlap(corrector3)
    print(f"超長 keyword (ApplicationProgrammingInterface 31字母):")
    print(f"  自動 overlap = {overlap3} (31 + margin 5 = 36)")
    print()
    
    # Case 4: 長 exclusion
    terms4 = {
        "React": {"exclusions": ["ReactNativeFramework"]},  # 20 字母
    }
    corrector4 = engine.create_corrector(terms4)
    overlap4 = calculate_safe_overlap(corrector4)
    print(f"長 exclusion (ReactNativeFramework 20字母):")
    print(f"  自動 overlap = {overlap4} (20 + margin 5 = 25)")
    print()
    
    # 實際使用
    print("實際使用:")
    streamer = StreamingCorrector(corrector3)  # 使用有超長 keyword 的 corrector
    print(f"  StreamingCorrector.overlap_size = {streamer.overlap_size}")
    print(f"  StreamingCorrector.min_confirm_size = {streamer.min_confirm_size}")
    print()
    
    # 也可以手動覆蓋
    streamer_manual = StreamingCorrector(corrector3, overlap_size=50)
    print(f"手動覆蓋 overlap_size=50:")
    print(f"  StreamingCorrector.overlap_size = {streamer_manual.overlap_size}")
    print()


if __name__ == "__main__":
    print("\n" + "🌊" * 30)
    print("  ASR/LLM 串流修正範例")
    print("🌊" * 30 + "\n")
    
    demo_asr_streaming()
    demo_llm_streaming()
    demo_new_segment_detection()
    demo_dynamic_overlap()  # 新增：動態 overlap 計算範例
    demo_performance_comparison()
    demo_practical_usage()
    
    print("=" * 60)
    print("✅ 所有範例執行完成!")
    print("=" * 60)
