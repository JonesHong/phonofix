"""Korean confusion rules MVP (5-10 條 hand-coded).

⚠️ This is MVP only — real ground truth pending 50-sentence KsponSpeech ASR analysis
   (Phase 5 day-0 manual task by owner).
⚠️ Per plan §五 Phase 5 + §七 Q4: if confusion rule coverage < 50% after Day 3 /
   10 rules → 韓文細調延後 v0.4.1.
"""

# Format: syllable_jamo_str → set of confusable syllable_jamo_str
# Based on common Korean ASR error patterns (initial consonant confusions, 받침 omission)
KOREAN_CONFUSION_MAP: dict[str, set[str]] = {
    # 平音 / 激音 / 硬音 (常見 ASR 混淆)
    "가": {"카", "까"},  # 가 / 카 / 까
    "다": {"타", "따"},  # 다 / 타 / 따
    "바": {"파", "빠"},  # 바 / 파 / 빠
    "자": {"차", "짜"},  # 자 / 차 / 짜
    "사": {"싸"},  # 사 / 싸
    # 韻母混淆
    "애": {"에"},  # 애 / 에
    "오": {"우"},  # 오 / 우
    # 받침 omission (常見口語)
    "인": {"이"},  # 인 / 이 (받침 ㄴ 消失)
}
