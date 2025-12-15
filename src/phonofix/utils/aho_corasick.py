"""
Aho-Corasick 多模式字串匹配（無第三方依賴）

用途：
- 只針對 surface alias 做 exact-match 搜尋，快速找出候選區間
- 再把候選區間交給 phonetic fuzzy scoring，減少整體比對次數
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Generic, Iterator, List, Tuple, TypeVar

T = TypeVar("T")


@dataclass
class _Node(Generic[T]):
    """
    Aho-Corasick trie 節點（內部使用）。

    欄位：
    - next: 字元 -> 節點索引（用 list 模擬指標，減少物件開銷）
    - fail: 失敗指標（fallback state index）
    - out: 此狀態可輸出的命中（word, value）列表
    """
    next: Dict[str, int] = field(default_factory=dict)
    fail: int = 0
    out: List[Tuple[str, T]] = field(default_factory=list)


class AhoCorasick(Generic[T]):
    """
    Aho-Corasick 多模式字串匹配器。

    典型用途：
    - 對大量 alias 做 exact-match 搜尋，快速找出所有命中 span
    - 將命中 span 交給後續的 phonetic fuzzy scoring 做精準排序

    使用方式：
        matcher = AhoCorasick[str]()
        matcher.add("foo", "foo")
        matcher.build()
        for start, end, word, value in matcher.iter_matches("..."):
            ...
    """

    def __init__(self) -> None:
        """建立 matcher。呼叫 `add()` 後需 `build()` 才能開始匹配（或讓 iter_matches 自動 build）。"""
        self._nodes: List[_Node[T]] = [_Node()]
        self._built = False

    def add(self, word: str, value: T) -> None:
        """
        加入一個 pattern。

        Args:
            word: 要匹配的字串（空字串會被忽略）
            value: 命中時要回傳的 payload

        Raises:
            RuntimeError: 若已呼叫 build()，為了保持一致性不允許再新增
        """
        if self._built:
            raise RuntimeError("AhoCorasick 已 build()，不可再 add()")
        if not word:
            return

        node = 0
        for ch in word:
            nxt = self._nodes[node].next.get(ch)
            if nxt is None:
                nxt = len(self._nodes)
                self._nodes[node].next[ch] = nxt
                self._nodes.append(_Node())
            node = nxt
        self._nodes[node].out.append((word, value))

    def build(self) -> None:
        """
        建立 fail links（將 trie 轉為可線性掃描的 automaton）。

        - 多次呼叫是安全的（built 後會直接 return）
        - build 後即可用 `iter_matches()` 在 O(n + matches) 時間內掃描整段文字
        """
        if self._built:
            return

        queue: deque[int] = deque()
        for ch, nxt in self._nodes[0].next.items():
            self._nodes[nxt].fail = 0
            queue.append(nxt)

        while queue:
            r = queue.popleft()
            for ch, u in self._nodes[r].next.items():
                queue.append(u)

                v = self._nodes[r].fail
                while v != 0 and ch not in self._nodes[v].next:
                    v = self._nodes[v].fail
                self._nodes[u].fail = self._nodes[v].next.get(ch, 0)

                # fail link 的輸出也屬於這個狀態
                self._nodes[u].out.extend(self._nodes[self._nodes[u].fail].out)

        self._built = True

    def iter_matches(self, text: str) -> Iterator[Tuple[int, int, str, T]]:
        """
        逐一輸出 matches

        Yields:
            (start, end, word, value)
            - start: match 起始 index（含）
            - end: match 結束 index（不含）
        """
        if not self._built:
            self.build()

        state = 0
        for i, ch in enumerate(text):
            while state != 0 and ch not in self._nodes[state].next:
                state = self._nodes[state].fail
            state = self._nodes[state].next.get(ch, 0)

            if not self._nodes[state].out:
                continue

            for word, value in self._nodes[state].out:
                start = i - len(word) + 1
                end = i + 1
                if start >= 0:
                    yield start, end, word, value
