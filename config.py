# config.py

# -----------------------------
# Audio analysis
# -----------------------------

SAMPLE_RATE = 16000

FRAME_LENGTH = 2048
HOP_LENGTH = 512

# librosa.effects.split()
# peak amplitude 기준으로 top_db 이하를 silence로 처리
TOP_DB = 35

# 너무 짧은 gap은 pause로 보지 않음
MIN_PAUSE_DURATION = 0.25


# -----------------------------
# Pitch / F0
# -----------------------------

F0_MIN = 70
F0_MAX = 350


# -----------------------------
# Filler candidate
# -----------------------------

# filler 후보로 분석할 voiced segment의 길이 범위
MIN_FILLER_DURATION = 0.20
MAX_FILLER_DURATION = 2.00

# 아직 실제 데이터로 확정하지 않은 threshold
# None이면 판정하지 않고 feature만 출력함
F0_STD_THRESHOLD = None
F0_SLOPE_THRESHOLD = None
FLATNESS_THRESHOLD = None