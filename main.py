# main.py

import json
import os

from audio_analysis import analyze_audio
from transcription import WhisperTranscriber
from language_analysis import analyze_language
from scoring import analyze_scoring


# ============================================================
# 기본 경로 설정
# ============================================================

AUDIO_PATH = "input/sample.wav"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# A. Speech Signal Analysis
# ============================================================

print("\n=== A. SPEECH SIGNAL ANALYSIS ===")

audio_result = analyze_audio(
    AUDIO_PATH
)

with open(
    os.path.join(
        OUTPUT_DIR,
        "audio_analysis.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        audio_result,
        f,
        ensure_ascii=False,
        indent=2
    )

print(
    "A 완료 → "
    "output/audio_analysis.json"
)


# ============================================================
# B. Whisper Transcription
# ============================================================

print("\n=== B. TRANSCRIPTION ===")

transcriber = WhisperTranscriber(
    model_name="small"
)

transcription_result = transcriber.transcribe(
    AUDIO_PATH
)

with open(
    os.path.join(
        OUTPUT_DIR,
        "transcription.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        transcription_result,
        f,
        ensure_ascii=False,
        indent=2
    )

print(
    "B 완료 → "
    "output/transcription.json"
)


# ============================================================
# C. Language Structure Analysis
# ============================================================

print("\n=== C. LANGUAGE ANALYSIS ===")

language_result = analyze_language(
    transcription_result
)

with open(
    os.path.join(
        OUTPUT_DIR,
        "language_analysis.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        language_result,
        f,
        ensure_ascii=False,
        indent=2
    )

print(
    "C 완료 → "
    "output/language_analysis.json"
)


# ============================================================
# D. Integration / Rule-based Scoring
# ============================================================

print("\n=== D. SCORING ===")

scoring_result = analyze_scoring(
    audio_result,
    transcription_result,
    language_result
)

with open(
    os.path.join(
        OUTPUT_DIR,
        "scoring_result.json"
    ),
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        scoring_result,
        f,
        ensure_ascii=False,
        indent=2
    )

print(
    "D 완료 → "
    "output/scoring_result.json"
)


# ============================================================
# 최종 요약
# ============================================================

candidates = scoring_result[
    "coaching_candidates"
]

print("\n================================")
print("발표 코칭 분석 완료")
print("================================")

print(
    f"비유창성 코칭 후보: "
    f"{len(candidates)}개"
)

for i, candidate in enumerate(
    candidates,
    start=1
):

    print(
        f"\n[{i}] "
        f"{candidate['start']:.2f}s"
        f" ~ "
        f"{candidate['end']:.2f}s"
    )

    if candidate["event_type"] == "CHUNK":

        print(
            "구간:",
            candidate["text"]
        )

    else:

        print(
            "이전:",
            candidate["left_text"]
        )

        print(
            "다음:",
            candidate["right_text"]
        )

    print(
        "점수:",
        candidate["score"]
    )

    print(
        "근거:",
        ", ".join(
            candidate["reasons"]
        )
    )

    print(
        "코칭:",
        candidate[
            "coaching_prompt"
        ]
    )