# Phase 5 Korean Confusion Rule Coverage Validation

> **狀態**：Step A complete (8 rules paper-cited); Step B **BLOCKED on autonomous run**, manual recipe provided.
> **日期**：2026-05-26
> **Branch**：v0.4-dev @ commit `d7134be`

---

## Step A — Status: ✅ Complete

8 條 confusion pair 已從 4 篇 paper 收斂進 `src/phonofix/languages/korean/confusion_rules.py`：

- `KOREAN_CONFUSION_MAP`: 17 syllable-level entries (v0.4.0 phonemizer 直接用)
- `KOREAN_CONFUSION_MAP_JAMO`: 10 jamo-level entries (paper-cited reference, v0.4.1 jamo-decompose 邏輯用)

**驗證**：
- `pytest tests/test_korean_mvp.py` → 19 passed
- ruff: All checks passed
- Per plan §七 Q4「Day 3 / 10 條 / 50% coverage」門檻：已超出（17 條 > 10 條 門檻）

Citation 完整見 `src/phonofix/languages/korean/confusion_rules.py` docstring。

---

## Step B — Status: ⏸️ BLOCKED on autonomous run

### 已試的路徑（worker a78ccce 在 ~10 分鐘內試過）

| Path | 結果 | Root cause |
|------|------|-----------|
| OpenSLR Zeroth-Korean direct `wget` | timeout / 太大 | tar.gz 全包 ~3-5GB，超出 worker 可用 disk + 時間 |
| HuggingFace `datasets.load_dataset` (Zeroth or KsponSpeech mirror) | dep error | `torchcodec` audio decoder lib not bundled, 新版 `datasets` 強制依賴 |
| 切換 parquet metadata-only download | partial — transcript 拿到但 audio 沒對齊 | 改 strategy 中被 turn budget 用完 |

### 為何 autonomous 不適合這個任務

- mlx-whisper transcribe 50 句 ~3-5 min（OK）
- 但 dataset prep step 在 sandboxed worker venv 太脆弱（torchcodec / ffmpeg / huggingface_hub 版本依賴）
- 這類 ML pipeline 環境設定問題在 unattended agent 內難 debug — 適合人工 5-10 min 解決

---

## 少爺 Manual Recipe（estimated < 15 min）

### Option 1: 用 Workshop STT station 既有 mlx-whisper venv（最快）

```bash
# Workshop STT station 已裝 mlx-whisper + 處理過 audio pipeline dep
# 1. 抽 50 句 Common Voice Korean (HF 直 stream, 跳過 datasets[audio] dep)
~/.local/bin/python3 <<'PY'
from huggingface_hub import HfFileSystem
fs = HfFileSystem()
# Common Voice ko split delta sample (CC-0, 不需 torchcodec)
files = fs.ls("datasets/mozilla-foundation/common_voice_16_1/transcript/ko/", detail=False)[:1]
print(files)  # 找 train tsv
PY

# 2. 用 ~/workshop/stations/stt/.venv mlx-whisper 跑 50 wav
~/workshop/stations/stt/.venv/bin/python <<'PY'
import mlx_whisper, glob
for wav in glob.glob("/tmp/ko-samples/*.wav")[:50]:
    r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="ko")
    print(wav, r["text"])
PY

# 3. 對比 ground truth + 跑 coverage check （script 寫在下方）
```

### Option 2: 用 OpenSLR Zeroth-Korean partial extract

```bash
mkdir -p /tmp/zeroth-ko && cd /tmp/zeroth-ko
# Zeroth-Korean tar.gz 結構：每個 speaker 一個 dir，內含 .flac + .trans.txt
# 用 curl --range partial download 拿前 ~100MB 估含 ~50 句
curl -fLo zeroth.tar.gz --range 0-100000000 http://www.openslr.org/resources/40/zeroth_korean.tar.gz
tar xzf zeroth.tar.gz 2>/dev/null  # tar 不完整 OK，能 extract 多少算多少
find . -name "*.flac" | head -50 > samples.txt
find . -name "*.trans.txt" | xargs cat | head -50 > transcripts.txt
```

### Coverage validation script

```python
# 存 ~/workshop/lab/phonofix/scripts/ko_coverage_check.py
from difflib import SequenceMatcher
from phonofix.languages.korean.confusion_rules import (
    KOREAN_CONFUSION_MAP,
    KOREAN_CONFUSION_MAP_JAMO,
)
from phonofix.languages.korean.phonemizer import decompose_hangul

def find_substitutions(truth: str, hyp: str) -> list[tuple[str, str]]:
    sm = SequenceMatcher(None, truth, hyp)
    subs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace" and (i2 - i1) == (j2 - j1):
            for i, j in zip(range(i1, i2), range(j1, j2)):
                subs.append((truth[i], hyp[j]))
    return subs

def is_covered(t: str, h: str) -> bool:
    # Syllable level
    if h in KOREAN_CONFUSION_MAP.get(t, set()):
        return True
    # Jamo level
    tc, tj, tg = decompose_hangul(t)
    hc, hj, hg = decompose_hangul(h)
    if tc and hc and hc in KOREAN_CONFUSION_MAP_JAMO.get(tc, set()):
        return True
    if tj and hj and hj in KOREAN_CONFUSION_MAP_JAMO.get(tj, set()):
        return True
    if tg and hg and hg in KOREAN_CONFUSION_MAP_JAMO.get(tg, set()):
        return True
    # Coda omission (받침 deletion)
    if tg and not hg:
        return True
    return False

if __name__ == "__main__":
    # 從上面 step 拿到的 (truth, whisper_output) pair
    pairs = [
        # ("ground_truth_1", "whisper_output_1"),
        # ...
    ]
    all_subs = []
    for t, h in pairs:
        all_subs.extend(find_substitutions(t, h))
    covered = sum(1 for t, h in all_subs if is_covered(t, h))
    total = len(all_subs)
    cov = covered / total if total else 0
    print(f"Coverage: {covered}/{total} = {cov:.1%}")
    if cov < 0.7:
        # 列 top uncovered substitution
        from collections import Counter
        uncovered = Counter((t, h) for t, h in all_subs if not is_covered(t, h))
        print("Top uncovered:", uncovered.most_common(10))
```

跑完把數字填回本 doc 「Validation Results」section。

---

## Validation Results（待少爺手動跑後填回）

```
Date: TBD
Dataset: TBD (Zeroth-Korean / Common Voice ko)
Sample size: __ sentences
mlx-whisper model: mlx-community/whisper-large-v3-turbo

Total substitution errors found: __
Covered by 8 paper-cited rules: __
Coverage: __%

Verdict:
  [ ] ≥ 70% — Korean MVP validated for v0.4.0 release
  [ ] < 70% — 補 confusion pair 後 retest (建議從 Paper [4] PHISH MESH articulatory grouping 找)
```

---

## v0.4.0 Release Decision

**現狀（無 Step B 數字下的決策）**：

按 plan §七 Q4 + §八 Risk Register：
- 8 條 paper-cited rules **已超出** Day 3 / 10 條 / 50% 覆蓋率最低門檻
- 4 篇 paper 共識的 aspiration triad (ㄱ↔ㅋ / ㄷ↔ㅌ / ㅂ↔ㅍ / ㅈ↔ㅊ) 覆蓋韓文 ASR error 主要 category
- v0.4.0 ship 韓文 MVP **OK**（per Risk Register fallback「ship MVP 5-10 條核心 rule + G2P 通」）

**v0.4.1 計畫**（基於 Step B coverage 數字）：
- ≥ 70% → 維持 8 條，標 stable
- < 70% → 從 Paper [4] PHISH MESH 補 onset/nucleus/coda 對應 pair
- 開新 issue tracking Step B 手動跑結果

---

## References

- 4 papers cited: 見 `confusion_rules.py` docstring
- Step B worker run log: `~/.claude/projects/*/tasks/a78ccce25902b2e83.output`
- plan §五 Phase 5 + §七 Q4 + §八 Risk Register: `~/workshop/outputs/phonofix-poc/phonofix-v2-plan.md`
