import json

from scoring import analyze_scoring


# A
with open(
    "output/audio_analysis.json",
    "r",
    encoding="utf-8"
) as f:
    audio_result = json.load(f)


# B
with open(
    "output/transcription.json",
    "r",
    encoding="utf-8"
) as f:
    transcription_result = json.load(f)


# C
with open(
    "output/language_analysis.json",
    "r",
    encoding="utf-8"
) as f:
    language_result = json.load(f)


# D
scoring_result = analyze_scoring(
    audio_result,
    transcription_result,
    language_result
)


with open(
    "output/scoring_result.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        scoring_result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\nD 분석 완료")
print("output/scoring_result.json")