"""
修正器協議定義 (Corrector Protocol)

定義所有修正器必須實作的介面，使用 Python Protocol (Structural Subtyping)。
這讓組合型和裝飾型修正器可以接受任何符合協議的修正器。

設計原則：
- 使用 Protocol 而非 ABC（符合 Python 鴨子類型精神）
- runtime_checkable 讓我們可以用 isinstance() 檢查
- 最小介面原則：只定義必要的方法

使用方式:
    from phonofix.correction import CorrectorProtocol
    
    # 任何實作 correct() 方法的類別都自動符合協議
    class MyCorrector:
        def correct(self, text: str) -> str:
            return text.upper()
    
    # 可以與 StreamingCorrector 等組合使用
    streamer = StreamingCorrector(MyCorrector())
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class CorrectorProtocol(Protocol):
    """
    修正器協議 (Corrector Protocol)
    
    所有修正器（包含語言修正器、組合修正器、裝飾修正器）
    都應該實作此協議。
    
    最小介面：
    - correct(text) -> str: 修正文本
    
    符合此協議的類別：
    - ChineseCorrector
    - EnglishCorrector  
    - UnifiedCorrector
    - StreamingCorrector（透過內部 corrector）
    
    Example:
        def process_with_any_corrector(corrector: CorrectorProtocol):
            result = corrector.correct("some text")
            return result
    """
    
    def correct(self, text: str) -> str:
        """
        修正文本中的錯誤
        
        Args:
            text: 原始文本
            
        Returns:
            str: 修正後的文本
        """
        ...


@runtime_checkable
class ContextAwareCorrectorProtocol(Protocol):
    """
    上下文感知修正器協議
    
    擴充的協議，支援傳入完整上下文以進行更準確的修正。
    主要用於英文修正器在混合語言環境中的 keyword/exclude_when 判斷。
    
    Example:
        # 當處理混合語言時，傳入完整文本作為上下文
        segment_result = corrector.correct(segment, full_context=full_text)
    """
    
    def correct(self, text: str, full_context: str = "") -> str:
        """
        修正文本中的錯誤
        
        Args:
            text: 要修正的文本片段
            full_context: 完整的原始文本（用於上下文判斷）
            
        Returns:
            str: 修正後的文本
        """
        ...
