# Korean Dependency Install Matrix (Codex A-P1 Gate)

## 目的
KoreanPhonemizer 依賴 `ko-pron` + `python-mecab-ko`，Phase 5 動工前必須在三平台確認可裝可 import。

## 結果（2026-05-26 測）

| Platform | `ko-pron` | `python-mecab-ko` | Smoke test | Notes |
|----------|-----------|--------------------|------------|-------|
| mac arm64 (M-series) | ✅ v1.3 | ✅ v1.3.7 | ✅ | 需先 `brew install mecab-ko`（系統 lib），見下方細節 |
| linux x86_64 | TBD | TBD | TBD | Phase 5 day-0 補 |
| windows x86_64 | TBD | TBD | TBD | Phase 5 day-0 補 |

## mac arm64 實測細節

### 環境
- Python: 3.13 (venv `.venv`)
- uv: `/opt/homebrew/bin/uv`
- macOS: 25.5.0 arm64

### ko-pron

```
$ uv pip install ko-pron
Resolved 1 package in 406ms
Installed 1 package in 1ms
 + ko-pron==1.3
```
- wheel: 純 Python，預編譯 → 無 build step，exit 0
- 無額外依賴

**Smoke output:**
```python
>>> import ko_pron
>>> ko_pron.romanise("안녕하세요", "rr")
'annyeonghaseyo'
```
결果合理（Revised Romanization of Korean 標準）。

### python-mecab-ko

**第一次嘗試（無系統 mecab）→ 失敗**
```
RuntimeError: mecab-config not found
```
需要系統層 MeCab C 函式庫。

**修復：安裝系統依賴**
```
$ brew install mecab-ko
==> Pouring mecab-ko--0.996-ko-0.9.2.arm64_tahoe.bottle.1.tar.gz
/opt/homebrew/Cellar/mecab-ko/0.996-ko-0.9.2
```
- `mecab-ko-dic` 等 brew formula 不需要；`python-mecab-ko` 自帶 `python-mecab-ko-dic==2.1.1.post2`

**第二次嘗試（有 mecab-config）→ 成功**
```
$ uv pip install python-mecab-ko
   Building python-mecab-ko==1.3.7
Downloading python-mecab-ko-dic (32.9MiB)
Built python-mecab-ko==1.3.7
Installed 2 packages in 1ms
 + python-mecab-ko==1.3.7
 + python-mecab-ko-dic==2.1.1.post2
```
- **source build**（非預編譯 wheel），pybind11 + C++ extension 編譯，約 14s
- 自動拉取 `python-mecab-ko-dic==2.1.1.post2`（32.9MB 字典包）

**Smoke output:**
```python
>>> import mecab
>>> m = mecab.MeCab()
>>> m.parse("한국어 형태소 분석")
[
  Morpheme(span=Span(start=0, end=3), surface='한국어',
    feature=Feature(pos='NNG', reading='한국어', type='Compound',
      expression='한국/NNG/*+어/NNG/*')),
  Morpheme(span=Span(start=4, end=7), surface='형태소',
    feature=Feature(pos='NNG', reading='형태소', type='Compound',
      expression='형태/NNG/*+소/NNG/*')),
  Morpheme(span=Span(start=8, end=10), surface='분석',
    feature=Feature(pos='NNG', semantic='행위', reading='분석')),
]
```
形態素分析正常（名詞 NNG 切分正確）。

### 額外系統依賴清單

| 依賴 | 安裝方式 | 是否必需 |
|------|----------|----------|
| `mecab-ko` (C library) | `brew install mecab-ko` | **必需**，python-mecab-ko build 依賴 |
| `mecab-ko-dic` (brew) | 不需要 | pip 包自帶字典 |

## Gate Rule

- 三平台任一 install 失敗 → 該平台 KoreanPhonemizer 標 `unavailable` + 文件 fallback（使用 `ko-pron` 純字典拼音法）
- 若 mac arm64 失敗 → Phase 5 韓文整個延後 v0.4.1
- mac arm64 **有條件通過**：須預先 `brew install mecab-ko`，否則 `python-mecab-ko` build 失敗

## Phase 5 行動清單

1. `pyproject.toml` 加 `ko-pron>=1.3` + `python-mecab-ko>=1.3.7`（optional dep，group=`ko`）
2. CI/CD mac runner 補 `brew install mecab-ko` 步驟
3. Linux x86_64：確認 `apt install mecab libmecab-dev mecab-ipadic-utf8`（待測）
4. Windows：預期 python-mecab-ko build 困難，備選方案使用 `ko-pron` 字典模式降級

## 還原

測試後已 uninstall：
```
$ uv pip uninstall ko-pron python-mecab-ko python-mecab-ko-dic
Uninstalled 3 packages in 4ms
```
系統 `mecab-ko` (brew) 保留（非 venv 範疇，不影響 lockfile）。
