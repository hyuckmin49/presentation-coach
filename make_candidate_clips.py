import json
import os
import soundfile as sf
import librosa


AUDIO_PATH = "input/sample.wav"
SCORING_PATH = "output/scoring_result.json"
OUTPUT_DIR = "output/clips"

# 앞뒤로 조금 더 들을 수 있게 여유 시간
PADDING = 0.7


os.makedirs(OUTPUT_DIR, exist_ok=True)


# ------------------------------------------------------------
# scoring 결과 불러오기
# ------------------------------------------------------------

with open(
    SCORING_PATH,
    "r",
    encoding="utf-8"
) as f:
    scoring_result = json.load(f)


candidates = scoring_result[
    "coaching_candidates"
]


# ------------------------------------------------------------
# 원본 음성 불러오기
# ------------------------------------------------------------

y, sr = librosa.load(
    AUDIO_PATH,
    sr=None,
    mono=True
)

audio_duration = len(y) / sr


# ------------------------------------------------------------
# 후보 구간별 WAV 저장
# ------------------------------------------------------------

for i, candidate in enumerate(
    candidates,
    start=1
):

    start = max(
        0,
        candidate["start"] - PADDING
    )

    end = min(
        audio_duration,
        candidate["end"] + PADDING
    )

    start_sample = int(
        start * sr
    )

    end_sample = int(
        end * sr
    )

    clip = y[
        start_sample:end_sample
    ]

    output_path = os.path.join(
        OUTPUT_DIR,
        f"candidate_{i:02d}.wav"
    )

    sf.write(
        output_path,
        clip,
        sr
    )

    print(
        f"[{i}] "
        f"{start:.2f}s ~ {end:.2f}s"
    )

    print(
        f"발화: {candidate['text']}"
    )

    print(
        f"점수: {candidate['score']}"
    )

    print(
        f"근거: {', '.join(candidate['reasons'])}"
    )

    print(
        f"저장: {output_path}"
    )

    print("-" * 60)


print(
    "\n후보 구간 추출 완료"
)