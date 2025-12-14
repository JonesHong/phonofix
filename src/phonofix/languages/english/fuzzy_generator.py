"""
英文模糊變體生成器

設計原則（以中文為 reference）：
- phonetic matching 為核心（IPA 相似度比對）
- surface variants 只是「把可能的錯拼先列成別名」用來增加可命中的目標、提升召回與效率
- 變體在生成階段以 phonetic key（IPA）去重，避免膨脹

注意：
- 本模組不維護特定詞彙的錯拼字典；如需相容舊行為，可 opt-in legacy patterns。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from phonofix.backend import EnglishPhoneticBackend, get_english_backend
from phonofix.core.protocols.fuzzy import FuzzyGeneratorProtocol

from .config import EnglishPhoneticConfig


@dataclass(frozen=True)
class _Candidate:
    text: str
    cost: int


class EnglishFuzzyGenerator(FuzzyGeneratorProtocol):
    """
    英文模糊變體生成器（surface-only，可選）

    預設只產生「低風險、可泛化」的變體：
    - 大小寫
    - 符號/分隔（. _ -）的移除或空白化
    - CamelCase 分詞（TensorFlow -> Tensor Flow）
    - 短縮寫空白化（AWS -> A W S）

    進階（預設關閉）：
    - representative spelling（較 aggressive 的字母/數字混淆與簡單拼寫模式）
    - legacy ASR split patterns（詞彙表；不建議）
    """

    def __init__(
        self,
        config: Optional[type[EnglishPhoneticConfig]] = None,
        backend: Optional[EnglishPhoneticBackend] = None,
        *,
        enable_representative_variants: bool = False,
    ) -> None:
        self.config = config or EnglishPhoneticConfig
        self._backend = backend
        self.enable_representative_variants = enable_representative_variants

    def generate_variants(self, term: str, max_variants: int = 30) -> List[str]:
        if not term:
            return []

        max_variants = max(0, int(max_variants))
        if max_variants == 0:
            return []

        candidates: list[_Candidate] = []
        candidates.extend(self._generate_safe_surface_variants(term))

        if self.enable_representative_variants:
            candidates.extend(self._generate_representative_spelling_variants(term))

        # 移除原詞與空值，先做 surface 去重（保留最低成本）
        by_text: dict[str, int] = {}
        for cand in candidates:
            text = cand.text
            if not text or text == term:
                continue
            prev = by_text.get(text)
            if prev is None or cand.cost < prev:
                by_text[text] = cand.cost

        if not by_text:
            return []

        deduped = [_Candidate(text=t, cost=c) for t, c in by_text.items()]

        backend = self._backend or self._try_get_backend()
        if backend is None or not backend.is_initialized():
            ranked = sorted(deduped, key=lambda c: (c.cost, len(c.text), c.text))
            return [c.text for c in ranked][:max_variants]

        # 生成階段即以 IPA 去重：同 IPA 只保留成本最低的代表
        ipa_map = backend.to_phonetic_batch([c.text for c in deduped])
        by_ipa: dict[str, Tuple[str, int]] = {}
        for cand in deduped:
            ipa = (ipa_map.get(cand.text) or "").replace(" ", "")
            if not ipa:
                continue
            prev = by_ipa.get(ipa)
            if prev is None or cand.cost < prev[1] or (cand.cost == prev[1] and cand.text < prev[0]):
                by_ipa[ipa] = (cand.text, cand.cost)

        ranked = sorted(by_ipa.values(), key=lambda v: (v[1], len(v[0]), v[0]))
        return [t for (t, _) in ranked][:max_variants]

    def _try_get_backend(self) -> Optional[EnglishPhoneticBackend]:
        try:
            return get_english_backend()
        except Exception:
            return None

    def _generate_safe_surface_variants(self, term: str) -> list[_Candidate]:
        out: list[_Candidate] = []

        # 1) 大小寫
        out.append(_Candidate(term.lower(), 1))

        # 2) 符號/分隔：Vue.js / Node-js / foo_bar
        if re.search(r"[\\._\\-]", term):
            spaced = re.sub(r"[\\._\\-]+", " ", term).strip()
            compact = re.sub(r"[\\._\\-]+", "", term)
            if spaced and spaced != term:
                out.append(_Candidate(spaced, 1))
                out.append(_Candidate(spaced.lower(), 2))
            if compact and compact != term:
                out.append(_Candidate(compact, 1))
                out.append(_Candidate(compact.lower(), 2))

        # 3) CamelCase：TensorFlow -> Tensor Flow
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\\d|$)|[A-Z]?[a-z]+|\\d+", term)
        if len(parts) >= 2:
            spaced = " ".join(parts)
            out.append(_Candidate(spaced, 1))
            out.append(_Candidate(spaced.lower(), 2))

        # 4) 短縮寫：AWS -> A W S
        if term.isalpha() and term.isupper() and len(term) <= 6:
            letters = " ".join(list(term))
            out.append(_Candidate(letters, 1))
            out.append(_Candidate(letters.lower(), 2))
            out.append(_Candidate(".".join(list(term)) + ".", 2))

        return out

    def _generate_representative_spelling_variants(self, term: str) -> list[_Candidate]:
        out: list[_Candidate] = []
        lower = term.lower()

        # 1) 常見拼寫模式（偏 aggressive；只做單步替換避免爆炸）
        for pattern, replacement in self.config.SPELLING_PATTERNS:
            if re.search(pattern, lower):
                v = re.sub(pattern, replacement, lower, count=1)
                if v and v != lower:
                    out.append(_Candidate(v, 3))

        # 2) 字母/數字音似混淆：單一位置替換
        for i, ch in enumerate(term):
            repls = self.config.LETTER_NUMBER_CONFUSIONS.get(ch.upper()) or []
            for r in repls:
                v = term[:i] + r + term[i + 1 :]
                if v and v != term:
                    out.append(_Candidate(v, 4))

        return out


def generate_english_variants(term: str, max_variants: int = 20) -> List[str]:
    generator = EnglishFuzzyGenerator()
    return generator.generate_variants(term, max_variants)
