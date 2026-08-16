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


# -----------------------------
# Sustained vowel candidate
# -----------------------------

MIN_SUSTAINED_DURATION = 0.75
MAX_SUSTAINED_DURATION = 3.00
MIN_DURATION_PER_SYLLABLE = 0.75
MIN_WINDOWED_DURATION_PER_SYLLABLE = 0.35
SUSTAINED_WINDOW_STEP = 0.10
MIN_SUSTAINED_VOICED_RATIO = 0.80
MAX_SUSTAINED_F0_STD_SEMITONE = 2.00
MAX_SUSTAINED_FLATNESS = 0.02
MIN_SUSTAINED_RMS = 0.01

# 여러 음절 단어 내부를 탐색할 때는 정상 발화를 잘못 잡지 않도록
# 한 음절 단어보다 엄격한 음향 기준을 사용한다.
MIN_WINDOWED_SUSTAINED_VOICED_RATIO = 0.90
MAX_WINDOWED_SUSTAINED_F0_STD_SEMITONE = 0.50
MAX_WINDOWED_SUSTAINED_FLATNESS = 0.01
