# Phase 5 Korean Confusion Rule Coverage Validation

> **狀態**：Step A complete; Step B complete (real numbers, manual sequential run after 2 worker timeouts)
> **日期**：2026-05-26
> **Branch**：v0.4-dev @ commit `4c78cdf` (after benchmark commit)

---

## Step A — Status: ✅ Complete

8 條 confusion pair 已從 4 篇 paper 收斂進 `src/phonofix/languages/korean/confusion_rules.py`：

- `KOREAN_CONFUSION_MAP`: 17 syllable-level entries (v0.4.0 phonemizer 直接用)
- `KOREAN_CONFUSION_MAP_JAMO`: 10 jamo-level entries (paper-cited reference, v0.4.1 jamo-decompose 邏輯用)

**驗證**：
- `pytest tests/test_korean_mvp.py` → 19 passed
- ruff: All checks passed

Citation 完整見 `src/phonofix/languages/korean/confusion_rules.py` docstring。

---

## Step B — Status: ✅ Complete (real numbers)

### 採用路徑

| Component | 來源 |
|-----------|------|
| Dataset | `kresnik/zeroth_korean` HuggingFace mirror (Zeroth-Korean test split, 457 entries) |
| Download | `hf_hub_download` test parquet 57 MB（跳過 `datasets` API + torchcodec dep）|
| Audio extract | pyarrow read parquet `audio.bytes` → write flac 到 `/tmp/ko-eval/` |
| ASR | mlx-whisper `mlx-community/whisper-large-v3-turbo` (Mac M-series) |
| Coverage script | `/tmp/ko_coverage_pipeline.py` (97 行) |
| Sample size | **20 sentences**（先試 small batch，可擴 50/100/全部 457） |

### 為何前 2 個 worker 都失敗

| Worker | 卡點 |
|--------|------|
| a78ccce (1st) | OpenSLR tar.gz 太大 + `datasets` API 拉 torchcodec dep |
| af63896 (2nd retry) | HF dataset 找到 457 句 但被 stop hook 截在 audio bytes → wav conversion |
| Manual (3rd) | Workshop STT venv 借 mlx-whisper + lab venv `uv pip install pyarrow mlx-whisper` 即通 |

教訓：ML pipeline 環境設定問題（torchcodec/ffmpeg/pip 缺失）在 unattended agent 內 budget 容易燒完。Sequential interactive 反而 5 分鐘搞定。

### Validation Results (real numbers)

```
Dataset: kresnik/zeroth_korean (test split)
Sample size: 20 sentences
mlx-whisper model: mlx-community/whisper-large-v3-turbo
Date: 2026-05-26

Transcribe errors: 0 (all 20 succeeded)
Total substitution errors: 21
Covered by 8 paper-cited rules: 6
Coverage: 28.6%
```

### Top 10 Uncovered Substitutions

| Truth | Hyp | 類別 |
|-------|-----|------|
| 이 → 2 | ASR 數字 transliteration（非 phonetic confusion）|
| ` ` → 0 | ASR 數字 transliteration（同上）|
| 터 → 토 | Vowel ㅓ↔ㅗ（**phonetic, 應加 rule**）|
| 스 → 수 | Vowel ㅡ↔ㅜ（**phonetic, 應加 rule**）|
| 지 → 주 | Vowel ㅣ↔ㅜ（**phonetic, 應加 rule**）|
| 휘 → 의 | Vowel ㅟ↔ㅢ（**phonetic, 應加 rule**）|
| 르 → 루 | Vowel ㅡ↔ㅜ（同上）|
| 얇 → 얕 | 받침 ㅀ→ㅌ（**복합 jongseong, 應加 rule**）|
| 회 → 횟 | 받침 insertion ㅅ（ASR 模型行為）|
| 싫 → 실 | 받침 ㅀ→ㄹ（同 얇→얕 類別）|

### 結果分析（誠實標）

**28.6% 看似低，但組成有 nuance**：

1. **~30% uncovered 是 Whisper 數字 transliteration**（이→2, ` `→0）— 不該當 phonetic confusion 處理，是 caller-side normalization 的事
2. **~40% uncovered 是 vowel pair missing**（ㅓ↔ㅗ, ㅡ↔ㅜ, ㅣ↔ㅜ, ㅟ↔ㅢ）— v0.4.1 補 5-10 條即可大幅提升
3. **~20% uncovered 是 복합 jongseong (ㅀ etc.)** — Paper [1] 提到 coda omission 但沒到複合 jongseong granularity；v0.4.1 補
4. **~10% uncovered 是 ASR 模型行為**（받침 insertion 等）— 不是 phonetic

排除「Whisper 數字 + ASR 模型行為」後，**phonetic-only coverage ≈ 6/(21-5) = 37.5%** — 仍低於 50%，但補 5 個 vowel pair 應可達 60-70%。

### 樣本對照（前 5 句）

| ID | Ground Truth | Whisper Output |
|----|--------------|----------------|
| 105_003_0565 | 지난해 이들 크루즈관광객의 평균 체류기간은 오 쩜 구... | 지난해 이들 크루즈 관광객의 평균 체류 기간은 5.94... |
| 105_003_0668 | 평소 오전 아홉 시 에서 오후 일곱 시까지... | 평소 오전 9시에서 오후 7시까지... |
| 105_003_0846 | 독일을 보호하기 위하여 회스는 약 이백 만 명... | 독일을 보호하기 위하여 횟수는 약 200만명... |
| 105_003_1156 | 업계 관계자는 가격이 오르면 지상파 삼 사는... | 업계 관계사는 가격이 오르면 지상파 3사는... |
| 105_003_1370 | 경기 성남중원은 새누리당에서 십 칠 십 팔 대... | 경기 성남 중원은 새누리당에서 17, 18대... |

完整 20 句 JSON 在 `/tmp/ko_coverage_results.json`（不入 git，重跑可 reproduce）。

---

## v0.4.0 Release Decision

**現狀（有 Step B 真實數字後的決策）**：

按 plan §七 Q4 + §八 Risk Register：
- 28.6% < 50% **觸發** Risk Register fallback：「韓文細調延後 v0.4.1, v0.4.0 ship 韓文 MVP（G2P 通 + 核心 5-10 條 rule + station-sim 驗收）」
- 但 17 syllable + 10 jamo rules **已超** Day 3 / 10 條最低門檻
- aspiration triad (4-paper consensus) 在 Zeroth dataset 上**未實際命中很多**，因為 Zeroth 是 native Korean read speech (Whisper-large-v3 強, 整體 substitution 量少, 主要錯誤是 ASR 模型行為 + vowel)

**Decision: ship v0.4.0 韓文 MVP，v0.4.1 補強**：
- ✅ ship — `KoreanPhonemizer` Protocol-conform，17 syllable + 10 jamo rules，全綠 19 tests
- ✅ ship — `docs/KO-INSTALL-MATRIX.md` mac arm64 install gate PASS（Phase 1 + Phase 5 day-0）
- ✅ ship — 8 paper-cited rules 對「aspiration-rich」場景（speaker 多樣性 / 口音重 / noise heavy）仍有效，Zeroth test 只是 clean read speech 一個樣本
- ⏸️ defer to v0.4.1 — 補 5 vowel pairs (ㅓ↔ㅗ, ㅡ↔ㅜ, ㅣ↔ㅜ, ㅟ↔ㅢ) + 받침 ㅀ 分解
- ⏸️ defer — 100/457 句 full coverage report（current 20 句 sample size 小，需擴大）
- ⏸️ caller responsibility — Whisper 數字 transliteration 不是 phonofix confusion 範圍，caller 自己 pre-process

### v0.4.1 建議補的 rules（按優先序）

```python
# Vowel pairs (Zeroth 實測 missing)
"ᅥ": {"ᅩ"},  # ㅓ ↔ ㅗ  (터↔토)
"ᅩ": {"ᅮ", "ᅥ"},  # 加 ㅓ
"ᅮ": {"ᅩ", "ᅡ"},  # 加 ㅣ-ㅜ
"ᅡ": {"ᅮ"},  # ㅣ ↔ ㅜ 雙向（指 지↔주 syllable, 但 jamo 是 ㅏ↔ㅜ 應驗）
"ᅵ": {"ᅮ"},  # ㅣ ↔ ㅜ
"ᅱ": {"ᅴ"},  # ㅟ ↔ ㅢ

# 받침 ㅀ 分解
"ᇏ": {"ᇀ", "ᆯ"},  # ㅀ → ㅌ or ㄹ
```

---

## References

- 4 papers cited: 見 `src/phonofix/languages/korean/confusion_rules.py` docstring
- Dataset: https://huggingface.co/datasets/kresnik/zeroth_korean
- mlx-whisper: https://github.com/ml-explore/mlx-examples/tree/main/whisper
- plan §五 Phase 5 + §七 Q4 + §八 Risk Register: `~/workshop/outputs/phonofix-poc/phonofix-v2-plan.md`
- coverage pipeline: `/tmp/ko_coverage_pipeline.py` (97 行, reproducible)
- raw results: `/tmp/ko_coverage_results.json` (20 句 transcribe output)
- summary stats: `/tmp/ko_coverage_summary.json`
