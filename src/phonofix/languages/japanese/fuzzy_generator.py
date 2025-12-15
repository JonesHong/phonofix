"""
日文模糊變體生成器（JapaneseFuzzyGenerator）

設計原則（以中文為 reference）：
- phonetic matching 為核心（以讀音/羅馬拼音維度做比對）
- surface variants 只是輔助：用來涵蓋不同書寫系統（漢字/假名/romaji）或常見輸入差異
- 變體生成階段就以 phonetic key 去重，控制膨脹，並保持輸出穩定可預期
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import List, Optional

from phonofix.core.protocols.fuzzy import FuzzyGeneratorProtocol
from phonofix.backend import JapanesePhoneticBackend, get_japanese_backend

from .config import JapanesePhoneticConfig


@dataclass(frozen=True)
class _Candidate:
    """
    內部候選資料結構（用於 variants 去重與排序）。

    欄位：
    - text: 候選變體文字
    - cost: 生成成本（越低越接近原詞、優先保留）
    - key: phonetic key（正規化 romaji），用於去重
    """

    text: str
    cost: int
    key: str


def _kata_to_hira(text: str) -> str:
    """
    將片假名轉為平假名（僅轉換假名字元，其他字元保持不變）。

    用途：
    - fugashi 的 reading 可能回傳片假名
    - 我們希望把 reading 先統一成平假名，降低後續變體生成的分支
    """
    hira = []
    for ch in text:
        if "\u30a1" <= ch <= "\u30f6":
            hira.append(chr(ord(ch) - 0x60))
        else:
            hira.append(ch)
    return "".join(hira)


def _hira_to_kata(text: str) -> str:
    """
    將平假名轉為片假名（僅轉換假名字元，其他字元保持不變）。

    用途：
    - 產生「書寫系統差異」的 surface variants（平/片 假名）
    """
    kata = []
    for ch in text:
        if "\u3041" <= ch <= "\u3096":
            kata.append(chr(ord(ch) + 0x60))
        else:
            kata.append(ch)
    return "".join(kata)


def _has_japanese_script(text: str) -> bool:
    """
    粗略判斷文字是否包含日文書寫系統（假名或常用漢字區段）。

    用途：
    - 決定 term 是「需要轉讀音/romaji」的日文文本，或已是 romaji/mixed
    """
    return any(
        ("\u3040" <= ch <= "\u30ff") or ("\u4e00" <= ch <= "\u9fff") for ch in text
    )


def _normalize_romaji(romaji: str, config: type[JapanesePhoneticConfig]) -> str:
    """
    正規化 romaji，產生穩定的 phonetic key。

    目標：
    - 將不同羅馬字標準（hepburn/kunrei）對齊
    - 長音/促音/鼻音做規則化，提升 fuzzy matching 的召回率
    - 回傳值用於 variants 去重（同一讀音只保留成本最低的候選）
    """
    normalized = romaji.lower().strip().replace(" ", "")

    # 1) 羅馬字變體標準化
    for variant, standard in config.ROMANIZATION_VARIANTS.items():
        normalized = normalized.replace(variant, standard)

    # 2) 長音縮短
    for long_vowel, short_vowel in config.FUZZY_LONG_VOWELS.items():
        normalized = normalized.replace(long_vowel, short_vowel)

    # 3) 促音簡化
    for geminated, single in config.FUZZY_GEMINATION.items():
        normalized = normalized.replace(geminated, single)

    # 4) 鼻音標準化
    for nasal_variant, standard in config.FUZZY_NASALS.items():
        normalized = normalized.replace(nasal_variant, standard)

    return normalized


def _romaji_variants(base: str, config: type[JapanesePhoneticConfig], *, max_states: int) -> list[tuple[str, int]]:
    """
    以 romaji 維度做有限展開（避免爆炸）
    回傳 (variant, cost)
    """
    base = base.lower().strip()
    states: dict[str, int] = {base: 0}

    # 使用「一次替換」的方式展開，並限制狀態數量，確保 deterministic
    rules: list[tuple[dict[str, str], int, bool]] = [
        (config.ROMANIZATION_VARIANTS, 1, True),  # 雙向（kunrei/hepburn）
        (config.FUZZY_LONG_VOWELS, 1, False),     # 長音->短音（單向）
        (config.FUZZY_GEMINATION, 1, False),      # 促音->單子音（單向）
        (config.FUZZY_NASALS, 1, True),           # 撥音 m/n（雙向）
    ]

    for mapping, cost, bidirectional in rules:
        next_states = dict(states)
        for s, c in states.items():
            for a, b in mapping.items():
                if a in s:
                    v = s.replace(a, b)
                    if v != s:
                        next_states[v] = min(next_states.get(v, 10**9), c + cost)
                if bidirectional and b in s:
                    v = s.replace(b, a)
                    if v != s:
                        next_states[v] = min(next_states.get(v, 10**9), c + cost)

        if len(next_states) > max_states:
            ranked = sorted(next_states.items(), key=lambda kv: (kv[1], len(kv[0]), kv[0]))
            next_states = dict(ranked[:max_states])
        states = next_states

    ranked = sorted(states.items(), key=lambda kv: (kv[1], len(kv[0]), kv[0]))
    return ranked


class JapaneseFuzzyGenerator(FuzzyGeneratorProtocol):
    """
    日文模糊變體生成器（surface-only，可選）

    預設行為（低風險、可泛化）：
    - 產生讀音（平假名）與 romaji（連續字串）
    - 針對 romaji 套用「常見規則」做少量變體（hepburn/kunrei、長音、促音、撥音）
    - 以 phonetic key（正規化 romaji）去重

    representative_kana（預設關閉）：
    - 產生假名層級混淆（清濁音/半濁音/助詞/近音）
    - 會帶來更多 surface 字符變體（類似中文的代表字功能）
    """

    def __init__(
        self,
        config: Optional[JapanesePhoneticConfig] = None,
        backend: JapanesePhoneticBackend | None = None,
        *,
        enable_representative_variants: bool = False,
        max_phonetic_states: int = 400,
    ) -> None:
        """
        初始化日文模糊變體生成器。

        Args:
            config: 日文語音設定（未提供則使用預設 JapanesePhoneticConfig）
            backend: 可選 backend（未提供則取得日文 backend 單例）
            enable_representative_variants: 是否啟用假名層級混淆（較昂貴，預設關閉）
            max_phonetic_states: 展開狀態上限，用於控制變體爆炸
        """
        self.config = config or JapanesePhoneticConfig()
        self._backend = backend or get_japanese_backend()
        self.enable_representative_variants = enable_representative_variants
        self.max_phonetic_states = max(50, int(max_phonetic_states))

    def generate_variants(self, term: str, max_variants: int = 30) -> List[str]:
        """
        為輸入詞彙生成日文模糊變體（surface variants）。

        產物用途：
        - 讓 corrector 能涵蓋不同書寫系統（漢字/假名/romaji）與常見輸入差異

        注意：
        - 這裡生成的是「表面字串」變體，最終仍以 phonetic key 去重與比對
        - 變體數量受 `max_variants` 與 `max_phonetic_states` 控制，避免膨脹
        """
        if not term:
            return []

        max_variants = max(0, int(max_variants))
        if max_variants == 0:
            return []

        candidates: list[tuple[str, int]] = []

        if _has_japanese_script(term):
            hira = self._to_hiragana_reading(term)
            if hira and hira != term:
                candidates.append((hira, 1))
            kata = _hira_to_kata(hira) if hira else ""
            if kata and kata != term:
                candidates.append((kata, 2))

            romaji = self._to_romaji(hira if hira else term)
            if romaji and romaji != term:
                candidates.append((romaji, 1))

            # romaji 常見規則變體
            candidates.extend(self._romaji_rule_variants(romaji))

            if self.enable_representative_variants and hira:
                candidates.extend(self._kana_confusion_variants(hira))
        else:
            # term 本身就是 romaji / mixed
            base = term.lower().strip()
            candidates.append((base.replace(" ", ""), 1))
            candidates.extend(self._romaji_rule_variants(base))

        # 生成階段就以 phonetic key 去重
        best_by_key: dict[str, _Candidate] = {}
        for text, cost in candidates:
            if not text or text == term:
                continue
            key = self._phonetic_key(text)
            if not key:
                continue
            cand = _Candidate(text=text, cost=cost, key=key)
            prev = best_by_key.get(key)
            if prev is None or cand.cost < prev.cost or (cand.cost == prev.cost and cand.text < prev.text):
                best_by_key[key] = cand

        ranked = sorted(best_by_key.values(), key=lambda c: (c.cost, len(c.text), c.text))
        return [c.text for c in ranked][:max_variants]

    def _to_hiragana_reading(self, text: str) -> str:
        """
        將日文文本轉為平假名讀音字串。

        實作：
        - 使用 fugashi 斷詞後取 reading（kana），若讀不到則回退為 surface
        - 全部統一成平假名（避免片假名造成額外分支）
        """
        tagger = self._backend.get_tagger()
        parts: list[str] = []
        for word in tagger(text):
            try:
                reading = word.feature.kana or word.surface
            except AttributeError:
                reading = word.surface
            parts.append(_kata_to_hira(reading))
        return "".join(parts)

    def _to_romaji(self, text: str) -> str:
        """
        將（假名/漢字）日文文本轉為 romaji。

        注意：
        - 轉換與 macrons 移除交由 backend 處理（共享快取、避免重複初始化）
        - 回傳值用於後續 phonetic key 正規化與規則展開（因此要維持穩定的 ASCII key）
        """
        if not text:
            return ""
        return self._backend.to_phonetic(text)

    def _phonetic_key(self, text: str) -> str:
        """
        取得候選文字的 phonetic key（正規化 romaji）。

        - 若 text 含日文字元，先轉 romaji
        - 再套用 `_normalize_romaji()` 做規則化
        """
        if _has_japanese_script(text):
            romaji = self._to_romaji(text)
        else:
            romaji = text
        return _normalize_romaji(romaji, JapanesePhoneticConfig)

    def _romaji_rule_variants(self, romaji: str) -> list[tuple[str, int]]:
        """
        針對 romaji 產生少量規則變體（hepburn/kunrei、長音、促音、鼻音）。

        回傳：
        - (variant, cost)；cost 用於排序（越小越優先）
        """
        if not romaji:
            return []
        ranked = _romaji_variants(romaji, JapanesePhoneticConfig, max_states=self.max_phonetic_states)
        # 排除 base 本身
        return [(v, c + 1) for v, c in ranked if v and v != romaji]

    def _kana_confusion_variants(self, hira: str) -> list[tuple[str, int]]:
        """
        產生假名層級的混淆變體（較昂貴，可選）。

        範例：
        - 清濁音互換
        - 半濁音互換
        - 常見近音混淆
        - 助詞混淆

        注意：
        - 會做有限 product 並裁剪，避免爆炸
        """
        # 每字最多 2-3 個候選，使用有限 product 並裁剪
        def options(ch: str) -> list[str]:
            """取得單一假名的可替代選項集合（含原字）。"""
            out = {ch}
            out.update((JapanesePhoneticConfig.PARTICLE_CONFUSIONS.get(ch) or ""))
            voiced = JapanesePhoneticConfig.VOICED_CONSONANT_MAP.get(ch)
            if voiced:
                out.add(voiced)
            for k, v in JapanesePhoneticConfig.VOICED_CONSONANT_MAP.items():
                if v == ch:
                    out.add(k)
            semi = JapanesePhoneticConfig.SEMI_VOICED_MAP.get(ch)
            if semi:
                out.add(semi)
            for k, v in JapanesePhoneticConfig.SEMI_VOICED_MAP.items():
                if v == ch:
                    out.add(k)
            for v in JapanesePhoneticConfig.SIMILAR_SOUND_CONFUSIONS.get(ch, []):
                out.add(v)
            out.discard("")
            return sorted(out)

        char_options = [options(ch) for ch in hira]
        # 限制組合數，避免爆炸（以 phonetic_states 控制）
        max_combos = min(self.max_phonetic_states, 300)

        variants: list[tuple[str, int]] = []
        for i, combo in enumerate(itertools.product(*char_options)):
            if i >= max_combos:
                break
            text = "".join(combo)
            if text != hira:
                variants.append((text, 5))
        return variants
