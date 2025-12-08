## 日文（Japanese）

- **遺失原始的漢字 / SJIS 表層形式**：`generate_variants` 會把詞轉成平假名/羅馬字，並在原詞存在時把它移除（`src/phonofix/languages/japanese/fuzzy_generator.py` 第 181–214 行）。因此像「東京」這種字典條目永遠不會回傳漢字本身或「漢字層級」的混淆變體——只剩假名/羅馬字。這會讓你很難抓到漢字打錯字，或在使用者介面上顯示同腳本（漢字）變體。

- **對假名輸入的長音 / 促音不會在語音 key 中被正規化**：`_get_phonetic_key` 只會縮短羅馬字（第 133–164 行），所以「おう」vs「おお」或「っ」等變體會保留不同的 key，`filter_homophones` 因而無法把它們合併。這會削弱「以語音維度去重」的目標。

- **長音符號「ー」與其他片假名特有的長音情境沒有處理**：在 `_kata_to_hira` 或 `_apply_kana_phrase_rules`（第 90–105 行）中都沒有觸及，導致常見 ASR 輸出如「スーパー → すーぱー」不會被正規化。

- **變體搜尋空間被任意裁切**：程式在沒有按「可能性」排序的情況下做裁切（`i > 50`、只取前 10 個假名→羅馬字；第 188–208 行），重要變體可能會被不可預期地丟掉。另外 `_romaji_reverse_map` 有建立但完全沒用到（第 24–29 行），暗示雙向映射邏輯可能未完成。


## 中文（Chinese）

- **`_generate_char_combinations` / `generate_variants` 的笛卡兒積沒有上限**（`src/phonofix/languages/chinese/fuzzy_generator.py` 第 259–270 行）：長詞加上豐富的模糊集合時，組合會指數爆炸、甚至卡死。日文/英文有做上限控制，中文沒有。

- **`_get_char_variations` 會用 Pinyin2Hanzi 用一個任意「代表」漢字去替換模糊拼音**（第 145–157 行）：這可能產生與原詞無關的字，把你帶離使用者提供的專有名詞。又因為只回傳文字（拼音被丟棄），下游在「語音維度」匹配時失去真正的拼音 key，增加誤匹配與 UX 噪音風險。

- **延遲匯入保護 `_imports_checked` 沒有在 `_get_pinyin2hanzi` 中被設為 true**（第 28–43 行）：因此每次呼叫都會重新 import，匯入失敗也會無限重試；`hanziconv` 會設 flag，但前提是 `_get_hanziconv` 先被執行過。

- **仍不支援中文姓名的拉丁字母 ASR 輸出**：例如「Taibei」「zhongguo」。產生器只回傳漢字字串，因此無法匹配那些已經被羅馬化的 ASR/LLM 輸出。


## 英文（English）

- **實作與 docstring 不一致（宣稱 “IPA phonetic back-off”）**：實際上只有啟發式字串改寫，沒有使用 phonemizer / IPA（`src/phonofix/languages/english/fuzzy_generator.py` 第 1–73 行）。這違背「統一到語音維度」的設計，也會漏掉口音/音素驅動的混淆。

- **`_filter_similar_variants` 幾乎不會過濾噪音**：它保留所有編輯距離 ≥ 1 的結果（第 190–214 行），除了完全相同的重複外幾乎都會保留。由於變體來自 set、順序不穩定，再加上切到 `max_variants`，輸出會在不同執行間呈現非決定性。

- **預先定義 pattern 影響過大且缺少可能性排序**：沒有依「可信度/機率」做 scoring/ranking，因此當你截斷結果時，稀有/噪音改寫（例如多重 split patterns）可能把更合理的變體擠掉。


## 工程建議（跨語系）

- **回傳結構化輸出**：在 surface text 之外，同時攜帶 phonetic key（平假名/羅馬字/拼音/IPA）；用 key 做去重與匹配，並保留使用者原始輸入文字用於 UX 顯示。

- **限制並排序搜尋空間**：以 token 與 term 為單位設定上限，並用有序策略（例如對拼音/羅馬字做 beam search、依頻率或規則權重排序）取代「硬切 50/10」或「無上限笛卡兒積」。

- **系統化正規化長音/促音/撥音**：在「生成」與「語音 key」兩個層面都做一致處理（包含片假名長音「ー」、おう/えい 等長音變體、促音等）。

- **中文方向**：考慮直接回傳拼音拼寫（必要時漢字僅作展示 alias），而非「憑空造新漢字」；並補上羅馬化 ASR 覆蓋。

- **英文方向**：接上現有 phonemizer/IPA 映射，並依音素編輯距離做排序，以符合「語音維度」策略；在截斷前先把順序穩定化（deterministic ordering）。

- 若你需要，我也可以草擬一份（按語言分開的）具體重構計畫，並加上一些針對性的測試。
