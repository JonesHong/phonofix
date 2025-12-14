"""
ASR/LLM 增量輸入示範（無串流 API）

自 v0.2.0 起，StreamingCorrector/ChunkStreamingCorrector 已在語言模組重構中移除。
本範例示範在增量輸入下，使用「累積全文 + 重新 correct」的方式處理。
"""

from _example_utils import add_repo_to_sys_path

add_repo_to_sys_path()

from phonofix import ChineseEngine


engine = ChineseEngine(verbose=False)


def demo_asr_accumulated():
    print("=" * 60)
    print("範例 1: Realtime ASR（累積全文輸入）")
    print("=" * 60)

    corrector = engine.create_corrector(["台北車站", "牛奶", "發揮", "然後"])

    asr_outputs = [
        "我在",
        "我在胎",
        "我在胎北",
        "我在胎北車站",
        "我在胎北車站買了流奶",
        "我在胎北車站買了流奶蘭後回家",
    ]

    for i, text in enumerate(asr_outputs, start=1):
        corrected = corrector.correct(text)
        print(f"[{i:02d}] ASR: {text}")
        print(f"     →  {corrected}")
        print()


def demo_llm_chunks():
    print("=" * 60)
    print("範例 2: LLM Streaming（chunk 累積後再修正）")
    print("=" * 60)

    corrector = engine.create_corrector(["聖靈", "聖經", "恩典"])

    llm_chunks = ["聖林", "借著默氏", "寫了這本", "生經，", "是安點。"]

    buffer = ""
    for chunk in llm_chunks:
        buffer += chunk
        print(f"Chunk: {chunk}")

    print()
    print("Raw:      ", buffer)
    print("Corrected:", corrector.correct(buffer))
    print()


def main():
    demo_asr_accumulated()
    demo_llm_chunks()


if __name__ == "__main__":
    main()
