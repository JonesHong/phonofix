"""Korean confusion rules — 8 paper-cited jamo pairs + syllable-level expansion.

依據：4 篇 Korean ASR error pattern 學術論文收斂（Paper [1]–[4]，2026-05 retrieved）。
非「從音韻學教科書硬抄」（plan §四.3 + Codex P1-1 警示）。

Paper [1] Comparison of L2 Korean Pronunciation Error Patterns from Five L1 Backgrounds (SNU, 2023)
  - https://arxiv.org/html/2306.10821
  - ASR: Wav2Vec2 XLS-R-300m, PER 3.88%
  - 提供：aspiration triad (ㄱ↔ㅋ / ㄷ↔ㅌ / ㅂ↔ㅍ) + diphthong→monophthong + coda deletion

Paper [2] ASR for Diagnosis of Speech Sound Disorders in Korean Children (2024)
  - https://arxiv.org/html/2403.08187v1
  - ASR: Fine-tuned Wav2Vec2.0-XLS-R, consonant F1 0.812
  - 提供：ㄷ ↔ ㅈ (alveolar) + ㄴ → ㅇ (coda)

Paper [3] Error Propagation in Korean Spoken QA with ASR-LLM Cascades (2026-05)
  - https://arxiv.org/html/2605.17443
  - ASR: Whisper-large-v3
  - 提供：single-character errors 在韓文 syllable=morpheme 特性下 12.5% 變語意失敗

Paper [4] PHISH in MESH — Korean Adversarial Phonetic Substitution (2025)
  - https://arxiv.org/html/2505.21380
  - 提供：onset / nucleus / coda 各按 articulatory features 分組 confusion

收斂的 8 條 jamo confusion pair（4 篇 paper 共識）：
  1. ㄱ ↔ ㅋ, ㄲ      [1][4]   aspiration triad
  2. ㄷ ↔ ㅌ, ㄸ      [1][4]   aspiration triad
  3. ㅂ ↔ ㅍ, ㅃ      [1][4]   aspiration triad
  4. ㅈ ↔ ㅊ, ㅉ      [1][4]   aspiration triad
  5. ㄷ ↔ ㅈ           [2]      alveolar articulation
  6. ㅐ ↔ ㅔ           [1]      vowel formant proximity
  7. ㄴ ↔ ㅇ (받침)    [2]      coda position
  8. 받침 omission     [1]      syllable-final deletion

⚠️ MVP scope: syllable-level expansion 涵蓋常見 syllable; 完整 jamo decompose+swap 邏輯留 v0.4.1
   (per plan §五 Phase 5 + §七 Q4)。

⚠️ 覆蓋率驗證：Phase 5 day-0 task — Zeroth-Korean 50 句 mlx-whisper transcribe →
   對比 8 rules 命中率 (target > 70%)。Coverage report 在 docs/PHASE5-KO-CONFUSION-COVERAGE.md.
"""

# ---------------------------------------------------------------------------
# Jamo-level reference (paper 直引，供 v0.4.1 jamo-decompose phonemizer 用)
# ---------------------------------------------------------------------------

KOREAN_CONFUSION_MAP_JAMO: dict[str, set[str]] = {
    # Aspiration triad — Paper [1][4] 4-paper consensus, highest confidence
    "ᄀ": {"ᄏ", "ᄁ"},  # ㄱ ↔ ㅋ, ㄲ
    "ᄃ": {"ᄐ", "ᄄ", "ᄌ"},  # ㄷ ↔ ㅌ, ㄸ + alveolar ㅈ (Paper [2])
    "ᄇ": {"ᄑ", "ᄈ"},  # ㅂ ↔ ㅍ, ㅃ
    "ᄌ": {"ᄎ", "ᄍ", "ᄃ"},  # ㅈ ↔ ㅊ, ㅉ + alveolar reverse
    # Vowel formant — Paper [1] + Zeroth real-data 補 (v0.4.0-rc2, 2026-05-26)
    "ᅢ": {"ᅦ"},  # ㅐ ↔ ㅔ
    "ᅦ": {"ᅢ"},
    "ᅩ": {"ᅮ", "ᅥ"},  # ㅗ ↔ ㅜ, ㅓ (Zeroth: 터↔토)
    "ᅮ": {"ᅩ", "ᅳ", "ᅵ"},  # ㅜ ↔ ㅗ, ㅡ, ㅣ (Zeroth: 스↔수, 르↔루, 지↔주)
    "ᅥ": {"ᅩ"},  # ㅓ ↔ ㅗ (Zeroth real)
    "ᅳ": {"ᅮ"},  # ㅡ ↔ ㅜ (Zeroth real)
    "ᅵ": {"ᅮ"},  # ㅣ ↔ ㅜ (Zeroth real)
    "ᅱ": {"ᅴ"},  # ㅟ ↔ ㅢ (Zeroth: 휘↔의)
    "ᅴ": {"ᅱ"},
    # Coda nasal — Paper [2]
    "ᆫ": {"ᆼ"},  # ㄴ ↔ ㅇ (받침)
    "ᆼ": {"ᆫ"},
    # 複합 jongseong simplification (v0.4.0-rc2 Zeroth real-data)
    "ᆲ": {"ᇀ", "ᆯ"},  # ㄼ → ㅌ or ㄹ (얇↔얕)
    "ᆶ": {"ᆯ", "ᇀ"},  # ㅀ → ㄹ or ㅌ (싫↔실)
}

# ---------------------------------------------------------------------------
# Syllable-level expansion (v0.4.0 MVP — phonemizer 直接 lookup)
# 12 條常見 syllable，從上述 8 條 jamo pair 展開
# ---------------------------------------------------------------------------

KOREAN_CONFUSION_MAP: dict[str, set[str]] = {
    # ── Aspiration triad expansion (Paper [1][4]) ──
    "가": {"카", "까"},  # ㄱ → ㅋ, ㄲ (vowel ㅏ)
    "고": {"코", "꼬"},  # ㄱ → ㅋ, ㄲ (vowel ㅗ)
    "기": {"키", "끼"},  # ㄱ → ㅋ, ㄲ (vowel ㅣ)
    "다": {"타", "따", "자"},  # ㄷ → ㅌ, ㄸ + alveolar ㅈ (Paper [2])
    "도": {"토", "또", "조"},
    "바": {"파", "빠"},  # ㅂ → ㅍ, ㅃ
    "보": {"포", "뽀"},
    "자": {"차", "짜", "다"},  # ㅈ → ㅊ, ㅉ + alveolar reverse
    "지": {"치", "찌"},
    "사": {"싸"},  # 既有 MVP
    # ── Vowel formant (Paper [1]) ──
    "애": {"에"},  # ㅐ ↔ ㅔ
    "에": {"애"},  # 雙向
    "오": {"우"},  # ㅗ ↔ ㅜ
    "우": {"오"},
    # ── Coda omission (Paper [1]) + nasal swap (Paper [2]) ──
    "인": {"이", "잉"},  # ㄴ omission + ㄴ↔ㅇ
    "안": {"아", "앙"},
    "운": {"우", "웅"},
}
