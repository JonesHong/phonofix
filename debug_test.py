from multi_language_corrector.languages.chinese.corrector import ChineseCorrector
from multi_language_corrector.languages.chinese.utils import PhoneticUtils
import Levenshtein

term_mapping = {
    '台北車站': [],
}
corrector = ChineseCorrector.from_terms(term_mapping)
utils = PhoneticUtils()

print('=== 詳細距離分析 ===')
window_text = '在北車用'
window_pinyin = utils.get_pinyin_string(window_text)

for item in corrector.search_index:
    target_pinyin = item['pinyin_str']
    dist = Levenshtein.distance(window_pinyin, target_pinyin)
    max_len = max(len(window_pinyin), len(target_pinyin))
    ratio = dist / max_len if max_len > 0 else 0
    
    if ratio <= 0.40:
        print(f"  匹配! {window_text}({window_pinyin}) vs {item['term']}({target_pinyin})")
        print(f"         距離={dist}, 長度={max_len}, 比率={ratio:.3f}")
        
print()
print('=== 聲母比較 ===')
import pypinyin
window_initials = pypinyin.lazy_pinyin(window_text, style=pypinyin.INITIALS, strict=False)
target_initials = pypinyin.lazy_pinyin('台北車站', style=pypinyin.INITIALS, strict=False)
print(f"  {window_text} 聲母: {window_initials}")
print(f"  台北車站 聲母: {target_initials}")
