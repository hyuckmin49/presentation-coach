import json

from language_analysis import analyze_language


with open(
    "output/transcription.json",
    "r",
    encoding="utf-8"
) as f:
    transcription_result = json.load(f)


language_result = analyze_language(
    transcription_result
)


with open(
    "output/language_analysis.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        language_result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\nC 분석 완료")
print("output/language_analysis.json")