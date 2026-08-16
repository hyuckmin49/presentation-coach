import numpy as np
import librosa

from config import (
    SAMPLE_RATE,
    FRAME_LENGTH,
    HOP_LENGTH,
    TOP_DB,
    MIN_PAUSE_DURATION,
    F0_MIN,
    F0_MAX,
    MIN_FILLER_DURATION,
    MAX_FILLER_DURATION,
    F0_STD_THRESHOLD,
    F0_SLOPE_THRESHOLD,
    FLATNESS_THRESHOLD,
)


def load_audio(audio_path: str):
    """
    음성 파일을 mono waveform으로 불러온다.
    """
    y, sr = librosa.load(
        audio_path,
        sr=SAMPLE_RATE,
        mono=True
    )

    duration = librosa.get_duration(y=y, sr=sr)

    return y, sr, duration


def detect_speech_intervals(y, sr):
    """
    energy threshold 기반으로 비무음(speech-like) 구간을 탐지한다.

    반환:
    [
        {
            "start": float,
            "end": float,
            "duration": float
        }
    ]
    """

    intervals = librosa.effects.split(
        y,
        top_db=TOP_DB,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH
    )

    speech_intervals = []

    for start_sample, end_sample in intervals:

        start_time = start_sample / sr
        end_time = end_sample / sr

        speech_intervals.append({
            "start": round(start_time, 3),
            "end": round(end_time, 3),
            "duration": round(end_time - start_time, 3)
        })

    return speech_intervals


def detect_pauses(speech_intervals, audio_duration):
    """
    비무음 구간 사이의 gap을 pause로 변환한다.
    """

    pauses = []

    if not speech_intervals:
        return pauses

    # 첫 발화 이전의 silence는 발표 시작 전 정적일 가능성이 높으므로
    # 현재는 pause 분석에서 제외한다.

    for i in range(len(speech_intervals) - 1):

        current_end = speech_intervals[i]["end"]
        next_start = speech_intervals[i + 1]["start"]

        pause_duration = next_start - current_end

        if pause_duration >= MIN_PAUSE_DURATION:

            pauses.append({
                "start": round(current_end, 3),
                "end": round(next_start, 3),
                "duration": round(pause_duration, 3)
            })

    # 마지막 발화 이후 silence 역시 현재 pause 분석에서 제외

    return pauses


def analyze_pitch(segment, sr):
    """
    segment의 F0를 pYIN으로 분석한다.

    반환:
    {
        "f0_mean": ...,
        "f0_std": ...,
        "f0_slope": ...
    }
    """

    if len(segment) < FRAME_LENGTH:
        return {
            "f0_mean": None,
            "f0_std": None,
            "f0_slope": None
        }

    try:
        f0, voiced_flag, voiced_prob = librosa.pyin(
            segment,
            fmin=F0_MIN,
            fmax=F0_MAX,
            sr=sr,
            frame_length=FRAME_LENGTH,
            hop_length=HOP_LENGTH
        )

    except Exception:
        return {
            "f0_mean": None,
            "f0_std": None,
            "f0_slope": None
        }

    valid_f0 = f0[~np.isnan(f0)]

    if len(valid_f0) < 2:
        return {
            "f0_mean": None,
            "f0_std": None,
            "f0_slope": None
        }

    f0_mean = np.mean(valid_f0)
    f0_std = np.std(valid_f0)

    # F0 contour의 전체적인 변화율
    x = np.arange(len(valid_f0))

    slope = np.polyfit(
        x,
        valid_f0,
        1
    )[0]

    return {
        "f0_mean": round(float(f0_mean), 3),
        "f0_std": round(float(f0_std), 3),
        "f0_slope": round(float(slope), 3)
    }


def analyze_spectral_flatness(segment):
    """
    유성 구간의 spectral flatness를 계산한다.

    낮을수록 tonal/harmonic한 성격,
    높을수록 noise-like한 성격이 강하다.

    단, 이 값만으로 filler를 판정하지 않는다.
    """

    if len(segment) < FRAME_LENGTH:
        return None

    flatness = librosa.feature.spectral_flatness(
        y=segment,
        n_fft=FRAME_LENGTH,
        hop_length=HOP_LENGTH
    )

    mean_flatness = np.mean(flatness)

    return round(float(mean_flatness), 6)


def analyze_rms(segment):
    """
    segment의 평균 RMS energy.
    """

    if len(segment) < FRAME_LENGTH:
        return None

    rms = librosa.feature.rms(
        y=segment,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH
    )

    return round(float(np.mean(rms)), 6)


def classify_filler_candidate(
    duration,
    f0_std,
    f0_slope,
    flatness
):
    """
    filler 후보 여부를 판정한다.

    현재 threshold가 미정인 경우:
    None 반환.

    향후 데이터 분석 후 threshold를 config.py에 설정하면
    자동 판정하도록 설계.
    """

    if duration < MIN_FILLER_DURATION:
        return False

    if duration > MAX_FILLER_DURATION:
        return False

    thresholds = [
        F0_STD_THRESHOLD,
        F0_SLOPE_THRESHOLD,
        FLATNESS_THRESHOLD
    ]

    # 아직 threshold가 하나라도 미정이면
    # 실제 filler 판정은 보류
    if any(value is None for value in thresholds):
        return None

    if (
        f0_std is not None
        and f0_slope is not None
        and flatness is not None
        and f0_std <= F0_STD_THRESHOLD
        and abs(f0_slope) <= F0_SLOPE_THRESHOLD
        and flatness <= FLATNESS_THRESHOLD
    ):
        return True

    return False


def analyze_voiced_segments(y, sr, speech_intervals):
    """
    각각의 비무음 구간에 대해
    F0 / spectral flatness / RMS를 계산한다.

    filler candidate 분석용 feature table 역할.
    """

    results = []

    for i, interval in enumerate(speech_intervals):

        start = interval["start"]
        end = interval["end"]
        duration = interval["duration"]

        start_sample = int(start * sr)
        end_sample = int(end * sr)

        segment = y[start_sample:end_sample]

        pitch = analyze_pitch(segment, sr)

        flatness = analyze_spectral_flatness(segment)

        rms = analyze_rms(segment)

        filler_candidate = classify_filler_candidate(
            duration=duration,
            f0_std=pitch["f0_std"],
            f0_slope=pitch["f0_slope"],
            flatness=flatness
        )

        results.append({
            "segment_id": i,
            "start": start,
            "end": end,
            "duration": duration,

            "f0_mean": pitch["f0_mean"],
            "f0_std": pitch["f0_std"],
            "f0_slope": pitch["f0_slope"],

            "spectral_flatness": flatness,
            "rms_mean": rms,

            "filler_candidate": filler_candidate
        })

    return results


def analyze_audio(audio_path: str):
    """
    A 모듈 메인 함수.

    Input:
        audio file path

    Output:
        음향 분석 결과 dictionary
    """

    y, sr, duration = load_audio(audio_path)

    speech_intervals = detect_speech_intervals(
        y,
        sr
    )

    pauses = detect_pauses(
        speech_intervals,
        duration
    )

    result = {
        "audio_path": audio_path,
        "sample_rate": sr,
        "audio_duration": round(duration, 3),

        "speech_intervals": speech_intervals,

        "pauses": pauses,

        # 기존 구간별 pYIN 계산은 아직 최종 판정에 사용되지 않으면서
        # 분석 시간을 늘렸으므로 보류한다. 음 끌기 탐지 단계에서
        # 전체 파형을 한 번만 처리하는 방식으로 다시 연결할 예정이다.
        "acoustic_segments": []
    }

    return result
