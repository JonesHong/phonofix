"""Default backend assignments for v0.4.0 (4 languages).

This module is a pure data table — no backend implementations here.
Phase 2 will consume these constants when wiring up the registry.

Gate note: "ko" entries are conditional on the KO dependency install
matrix gate passing (mac arm64 / linux x86_64 / win x86_64) before
Phase 5 KoreanPhonemizer is committed to scope.
"""

# Default G2P backend name per language.
# Values correspond to backend `name` attributes that will be registered
# in Phase 2.
DEFAULT_G2P: dict[str, str] = {
    "zh": "pypinyin",
    "ja": "cutlet",
    "en": "phonemizer-espeak",
    "ko": "ko-pron",  # Phase 1 install matrix gate 通過後才生效
}

# Default tokenizer per language: (mode, tokenizer_name | None).
# None means "built-in / no external lib required".
DEFAULT_TOKENIZER: dict[str, tuple[str, str | None]] = {
    "zh": ("char", None),
    "ja": ("char", "fugashi"),  # fugashi 提供 morpheme + char-level steps
    "en": ("word", "whitespace"),
    "ko": ("char", "mecab-ko"),  # gate 通過後
}
