"""
串流修正器模組 - 支援 ASR/LLM 即時串流修正

本模組提供針對串流輸入的即時修正能力，適用於：
- ASR (語音識別) 即時字幕
- LLM Streaming 輸出後處理
- 即時翻譯/轉寫系統

核心概念：
- 差異比對：只處理新增的部分
- 快取機制：已確認的修正不重複計算
- 滑動視窗：保留重疊區域防止誤判
- 動態 overlap：根據 keywords/exclusions 長度自動調整

使用方式:
    from phonofix import ChineseEngine
    from phonofix.correction.streaming_corrector import StreamingCorrector
    
    engine = ChineseEngine()
    corrector = engine.create_corrector(["台北車站", "TensorFlow"])
    
    # 自動根據 terms 計算安全的 overlap_size
    streamer = StreamingCorrector(corrector)
    
    # 或手動指定
    streamer = StreamingCorrector(corrector, overlap_size=25)
    
    # ASR 串流輸入
    for chunk in asr_stream:
        result = streamer.feed(chunk)
        print(result.confirmed)  # 已確認的修正文本
    
    # 結束時取得完整結果
    final = streamer.finalize()
"""

from dataclasses import dataclass
from typing import Any

from phonofix.correction.protocol import CorrectorProtocol
from phonofix.utils.logger import get_logger


# =============================================================================
# 常數定義
# =============================================================================

# 預設 overlap 大小（當無法從 corrector 取得 terms 時使用）
DEFAULT_OVERLAP_SIZE = 20

# 最小 overlap 大小（保底值）
MIN_OVERLAP_SIZE = 10

# 計算動態 overlap 時的額外邊界（防止邊界切斷）
OVERLAP_MARGIN = 5

# 預設最小確認長度
DEFAULT_MIN_CONFIRM_SIZE = 10


def calculate_safe_overlap(
    corrector: Any,
    default: int = DEFAULT_OVERLAP_SIZE,
    margin: int = OVERLAP_MARGIN,
) -> int:
    """
    根據 corrector 的 terms 資訊計算安全的 overlap size
    
    計算邏輯：
    1. 嘗試從 corrector 取得所有 terms、keywords、exclude_when
    2. 找出最長的字串長度
    3. 加上 margin 作為安全邊界
    4. 與 default 取較大值
    
    Args:
        corrector: 修正器實例
        default: 預設值（無法取得 terms 時使用）
        margin: 額外邊界
        
    Returns:
        int: 建議的 overlap size
    """
    max_len = 0
    
    try:
        # 嘗試取得 Chinese corrector 的 search_index
        if hasattr(corrector, 'search_index') and corrector.search_index:
            for item in corrector.search_index:
                # term 本身
                if 'term' in item:
                    max_len = max(max_len, len(item['term']))
                if 'canonical' in item:
                    max_len = max(max_len, len(item['canonical']))
                # keywords
                if 'keywords' in item:
                    for kw in item['keywords']:
                        max_len = max(max_len, len(kw))
                # exclude_when (上下文排除條件)
                if 'exclude_when' in item:
                    for ex in item['exclude_when']:
                        max_len = max(max_len, len(ex))
    except Exception:
        pass
    
    try:
        # 嘗試取得 English corrector 的 terms
        if hasattr(corrector, 'terms') and corrector.terms:
            for term in corrector.terms:
                max_len = max(max_len, len(term))
        
        # English corrector 的 keywords
        if hasattr(corrector, 'keywords') and corrector.keywords:
            for term, kw_list in corrector.keywords.items():
                max_len = max(max_len, len(term))
                for kw in kw_list:
                    max_len = max(max_len, len(kw))
        
        # English corrector 的 exclude_when (dict 形式)
        if hasattr(corrector, 'exclude_when') and isinstance(corrector.exclude_when, dict):
            for term, ex_list in corrector.exclude_when.items():
                for ex in ex_list:
                    max_len = max(max_len, len(ex))
    except Exception:
        pass
    
    try:
        # UnifiedCorrector 包含多個子 corrector
        if hasattr(corrector, '_correctors'):
            for sub_corrector in corrector._correctors.values():
                sub_overlap = calculate_safe_overlap(sub_corrector, default=0, margin=0)
                max_len = max(max_len, sub_overlap)
    except Exception:
        pass
    
    # 計算最終值
    if max_len > 0:
        calculated = max_len + margin
        return max(calculated, MIN_OVERLAP_SIZE, default)
    
    return max(default, MIN_OVERLAP_SIZE)


@dataclass
class StreamingResult:
    """串流修正結果"""
    confirmed: str          # 已確認的修正文本（可安全輸出）
    pending: str            # 待確認的文本（可能還會變動）
    is_new_segment: bool    # 是否為新段落（快取被重置）
    raw_input: str          # 原始輸入（用於 debug）
    
    @property
    def display(self) -> str:
        """用於顯示的完整文本"""
        return self.confirmed + self.pending


class StreamingCorrector:
    """
    串流修正器 - 支援增量輸入的即時修正
    
    設計原理:
    1. 輸入累積：每次 feed() 傳入累積的完整文本
    2. 差異檢測：比對新輸入與快取，找出新增部分
    3. 重疊修正：重新修正「重疊區 + 新增區」確保不切斷詞彙
    4. 快取更新：將穩定部分移入已確認區
    5. 段落檢測：輸入不匹配時視為新段落
    
    Args:
        corrector: 修正器實例 (ChineseCorrector 或 UnifiedCorrector)
        overlap_size: 重疊區域大小（字符數），防止詞彙被切斷。
            設為 None 時自動根據 corrector 的 terms 計算安全值。
        min_confirm_size: 最小確認長度，累積超過此長度才開始確認
        auto_overlap: 是否自動計算 overlap（當 overlap_size=None 時預設 True）
        
    Example:
        >>> engine = ChineseEngine()
        >>> corrector = engine.create_corrector(["台北車站"])
        >>> streamer = StreamingCorrector(corrector)  # 自動計算 overlap
        >>> 
        >>> # 模擬 ASR 累積輸入
        >>> result = streamer.feed("我在胎北")
        >>> result = streamer.feed("我在胎北車站")  
        >>> result = streamer.feed("我在胎北車站等你")
        >>> print(result.confirmed)  # "我在台北車站"
        >>> print(result.pending)    # "等你"
    """
    
    def __init__(
        self,
        corrector: CorrectorProtocol,
        overlap_size: int | None = None,
        min_confirm_size: int | None = None,
        auto_overlap: bool = True,
    ):
        self.corrector = corrector
        self._logger = get_logger("streaming")
        
        # 動態計算或使用預設值
        if overlap_size is not None:
            self.overlap_size = overlap_size
        elif auto_overlap:
            self.overlap_size = calculate_safe_overlap(corrector)
            self._logger.debug(f"自動計算 overlap_size = {self.overlap_size}")
        else:
            self.overlap_size = DEFAULT_OVERLAP_SIZE
        
        self.min_confirm_size = min_confirm_size if min_confirm_size is not None else DEFAULT_MIN_CONFIRM_SIZE
        
        # 快取狀態
        self._last_input = ""           # 上次的原始輸入
        self._last_corrected = ""       # 上次的完整修正結果
        self._confirmed_input_len = 0   # 已確認的原始輸入長度
        self._confirmed_output = ""     # 已確認的修正輸出
        
    def feed(self, accumulated_text: str) -> StreamingResult:
        """
        餵入累積的文本，返回修正結果
        
        注意：每次應傳入**累積的完整文本**，而非增量 chunk。
        
        Args:
            accumulated_text: 累積的完整輸入文本
            
        Returns:
            StreamingResult: 包含已確認和待確認的修正結果
        """
        if not accumulated_text:
            return StreamingResult(
                confirmed=self._confirmed_output,
                pending="",
                is_new_segment=False,
                raw_input=""
            )
        
        # 檢查是否為新段落
        is_new_segment = self._is_new_segment(accumulated_text)
        
        if is_new_segment:
            self._logger.debug("偵測到新段落，重置快取")
            self._reset()
        
        # 完整修正當前輸入
        full_corrected = self.corrector.correct(accumulated_text)
        
        # 計算可以確認的長度（保留 overlap 區域不確認）
        safe_input_len = max(0, len(accumulated_text) - self.overlap_size)
        
        # 只有超過最小確認長度才開始確認
        if safe_input_len >= self.min_confirm_size:
            # 根據輸入長度比例，推算修正結果中可確認的位置
            if len(accumulated_text) > 0:
                ratio = safe_input_len / len(accumulated_text)
                safe_output_len = int(len(full_corrected) * ratio)
            else:
                safe_output_len = 0
            
            self._confirmed_output = full_corrected[:safe_output_len]
            self._confirmed_input_len = safe_input_len
        
        # 更新快取
        self._last_input = accumulated_text
        self._last_corrected = full_corrected
        
        # 計算待確認部分
        pending = full_corrected[len(self._confirmed_output):]
        
        return StreamingResult(
            confirmed=self._confirmed_output,
            pending=pending,
            is_new_segment=is_new_segment,
            raw_input=accumulated_text
        )
    
    def finalize(self) -> str:
        """
        結束串流，返回完整的修正結果
        
        Returns:
            str: 完整的修正後文本
        """
        if self._last_input:
            result = self.corrector.correct(self._last_input)
            self._reset()
            return result
        return ""
    
    def reset(self):
        """重置狀態，開始新的串流"""
        self._reset()
        
    def _is_new_segment(self, new_text: str) -> bool:
        """檢測是否為新段落"""
        if not self._last_input:
            return False
            
        cached = self._last_input
        
        # 檢查共同前綴長度
        common_len = 0
        for i in range(min(len(new_text), len(cached))):
            if new_text[i] == cached[i]:
                common_len += 1
            else:
                break
        
        # 如果共同前綴太短，視為新段落
        min_common = min(5, len(cached) * 0.5)
        if common_len < min_common:
            return True
            
        # 如果新文本比快取短很多，可能是新段落
        if len(new_text) < len(cached) * 0.3:
            return True
            
        return False
    
    def _reset(self):
        """重置快取狀態"""
        self._last_input = ""
        self._last_corrected = ""
        self._confirmed_input_len = 0
        self._confirmed_output = ""


class ChunkStreamingCorrector:
    """
    Chunk 模式串流修正器 - 接收增量 chunk
    
    與 StreamingCorrector 不同，此類接收增量的 chunk 而非累積文本。
    適用於 LLM Streaming 場景。
    
    Args:
        corrector: 修正器實例
        overlap_size: 重疊區域大小，設為 None 時自動計算
        min_confirm_size: 最小確認長度
        auto_overlap: 是否自動計算 overlap
    
    Example:
        >>> streamer = ChunkStreamingCorrector(corrector)
        >>> 
        >>> for chunk in llm_stream:
        >>>     result = streamer.feed_chunk(chunk)
        >>>     print(result.confirmed, end="", flush=True)
        >>> 
        >>> final = streamer.finalize()
    """
    
    def __init__(
        self,
        corrector: CorrectorProtocol,
        overlap_size: int | None = None,
        min_confirm_size: int | None = None,
        auto_overlap: bool = True,
    ):
        self._corrector = corrector
        self._logger = get_logger("streaming.chunk")
        
        # 動態計算或使用預設值
        if overlap_size is not None:
            self._overlap_size = overlap_size
        elif auto_overlap:
            self._overlap_size = calculate_safe_overlap(corrector)
            self._logger.debug(f"自動計算 overlap_size = {self._overlap_size}")
        else:
            self._overlap_size = DEFAULT_OVERLAP_SIZE
        
        self._min_confirm_size = min_confirm_size if min_confirm_size is not None else DEFAULT_MIN_CONFIRM_SIZE
        
        self._accumulated = ""          # 累積的原始輸入
        self._total_confirmed = ""      # 累計已確認的輸出
        self._last_full_corrected = ""  # 上次的完整修正結果
        
    def feed_chunk(self, chunk: str) -> StreamingResult:
        """
        餵入增量 chunk
        
        Args:
            chunk: 新增的文本片段
            
        Returns:
            StreamingResult: confirmed 只包含**新增**的已確認部分
        """
        self._accumulated += chunk
        
        # 完整修正累積文本
        full_corrected = self._corrector.correct(self._accumulated)
        
        # 計算可確認的長度
        safe_input_len = max(0, len(self._accumulated) - self._overlap_size)
        
        new_confirmed = ""
        pending = full_corrected
        
        if safe_input_len >= self._min_confirm_size:
            # 根據比例計算可確認的輸出長度
            ratio = safe_input_len / len(self._accumulated) if len(self._accumulated) > 0 else 0
            safe_output_len = int(len(full_corrected) * ratio)
            
            current_confirmed = full_corrected[:safe_output_len]
            
            # 計算新增的確認部分
            if len(current_confirmed) > len(self._total_confirmed):
                new_confirmed = current_confirmed[len(self._total_confirmed):]
                self._total_confirmed = current_confirmed
            
            pending = full_corrected[safe_output_len:]
        
        self._last_full_corrected = full_corrected
        
        return StreamingResult(
            confirmed=new_confirmed,
            pending=pending,
            is_new_segment=False,
            raw_input=chunk
        )
    
    def finalize(self) -> str:
        """結束串流，返回剩餘的待確認內容"""
        if self._accumulated:
            final = self._corrector.correct(self._accumulated)
            # 返回尚未確認輸出的部分
            remaining = final[len(self._total_confirmed):]
            self._reset()
            return remaining
        return ""
    
    def reset(self):
        """重置狀態"""
        self._reset()
        
    def _reset(self):
        self._accumulated = ""
        self._total_confirmed = ""
        self._last_full_corrected = ""
    
    @property
    def full_result(self) -> str:
        """取得目前的完整修正結果"""
        return self._last_full_corrected


# =============================================================================
# 便捷函數
# =============================================================================

def create_streaming_corrector(
    corrector: CorrectorProtocol,
    mode: str = "accumulated",
    **kwargs
) -> StreamingCorrector | ChunkStreamingCorrector:
    """
    建立串流修正器的便捷函數
    
    Args:
        corrector: 修正器實例
        mode: 
            - "accumulated": 每次傳入累積的完整文本 (適合 ASR)
            - "chunk": 每次傳入增量的 chunk (適合 LLM)
        **kwargs: 傳遞給修正器的其他參數
        
    Returns:
        StreamingCorrector 或 ChunkStreamingCorrector
    """
    if mode == "accumulated":
        return StreamingCorrector(corrector, **kwargs)
    elif mode == "chunk":
        return ChunkStreamingCorrector(corrector, **kwargs)
    else:
        raise ValueError(f"不支援的模式: {mode}，請使用 'accumulated' 或 'chunk'")
