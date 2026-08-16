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
    MIN_SUSTAINED_DURATION,
    MAX_SUSTAINED_DURATION,
    MIN_DURATION_PER_SYLLABLE,
    MIN_WINDOWED_DURATION_PER_SYLLABLE,
    SUSTAINED_WINDOW_STEP,
    MIN_SUSTAINED_VOICED_RATIO,
    MAX_SUSTAINED_F0_STD_SEMITONE,
    MAX_SUSTAINED_FLATNESS,
    MIN_SUSTAINED_RMS,
    MIN_WINDOWED_SUSTAINED_VOICED_RATIO,
    MAX_WINDOWED_SUSTAINED_F0_STD_SEMITONE,
    MAX_WINDOWED_SUSTAINED_FLATNESS,
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


def count_korean_syllables(text):
    return sum(1 for character in text if "가" <= character <= "힣")


def analyze_sustained_segment(segment, sr):
    if len(segment) < FRAME_LENGTH:
        return None

    try:
        f0, voiced_flag, _voiced_prob = librosa.pyin(
            segment,
            fmin=F0_MIN,
            fmax=F0_MAX,
            sr=sr,
            frame_length=FRAME_LENGTH,
            hop_length=HOP_LENGTH,
        )
    except Exception:
        return None

    valid_f0 = f0[~np.isnan(f0)]
    if len(valid_f0) < 2:
        return None

    median_f0 = np.median(valid_f0)
    semitone_offsets = 12 * np.log2(valid_f0 / median_f0)
    return {
        "voiced_ratio": float(np.mean(voiced_flag)),
        "f0_std_semitone": float(np.std(semitone_offsets)),
        "spectral_flatness": analyze_spectral_flatness(segment),
        "rms_mean": analyze_rms(segment),
    }


def is_sustained_features(features, *, windowed=False):
    if features is None:
        return False

    if windowed:
        min_voiced_ratio = MIN_WINDOWED_SUSTAINED_VOICED_RATIO
        max_f0_std = MAX_WINDOWED_SUSTAINED_F0_STD_SEMITONE
        max_flatness = MAX_WINDOWED_SUSTAINED_FLATNESS
    else:
        min_voiced_ratio = MIN_SUSTAINED_VOICED_RATIO
        max_f0_std = MAX_SUSTAINED_F0_STD_SEMITONE
        max_flatness = MAX_SUSTAINED_FLATNESS

    return (
        features["voiced_ratio"] >= min_voiced_ratio
        and features["f0_std_semitone"] <= max_f0_std
        and features["spectral_flatness"] is not None
        and features["spectral_flatness"] <= max_flatness
        and features["rms_mean"] is not None
        and features["rms_mean"] >= MIN_SUSTAINED_RMS
    )


def detect_sustained_word_events_from_waveform(y, sr, transcription_result):
    """Whisper 단어 전체와 여러 음절 단어 내부의 지속 유성음을 찾는다."""

    events = []
    for word_info in transcription_result.get("words", []):
        text = word_info.get("word", "").strip(".,?! ")
        syllable_count = count_korean_syllables(text)
        if syllable_count == 0:
            continue

        start = float(word_info["start"])
        end = float(word_info["end"])
        duration = end - start
        duration_per_syllable = duration / syllable_count
        if not MIN_SUSTAINED_DURATION <= duration <= MAX_SUSTAINED_DURATION:
            continue

        event_start = start
        event_end = end
        features = None
        detection_method = "whole_word"

        if syllable_count == 1 and duration_per_syllable >= MIN_DURATION_PER_SYLLABLE:
            segment = y[int(start * sr):int(end * sr)]
            features = analyze_sustained_segment(segment, sr)
            detected = is_sustained_features(features)
        elif duration_per_syllable >= MIN_WINDOWED_DURATION_PER_SYLLABLE:
            detected = False
            detection_method = "word_internal_window"
            latest_window_start = end - MIN_SUSTAINED_DURATION
            for window_start in np.arange(
                start,
                latest_window_start + 0.001,
                SUSTAINED_WINDOW_STEP,
            ):
                window_end = window_start + MIN_SUSTAINED_DURATION
                segment = y[int(window_start * sr):int(window_end * sr)]
                window_features = analyze_sustained_segment(segment, sr)
                if is_sustained_features(window_features, windowed=True):
                    event_start = float(window_start)
                    event_end = float(window_end)
                    features = window_features
                    detected = True
                    break
        else:
            detected = False

        if detected:
            # Whisper가 한 지속음을 맞닿은 두 단어에 걸쳐 배정할 수 있다.
            # 이미 잡힌 구간과 바로 이어지는 내부 창은 중복 후보로 추가하지 않는다.
            if (
                detection_method == "word_internal_window"
                and events
                and event_start <= events[-1]["end"] + SUSTAINED_WINDOW_STEP
            ):
                continue

            events.append({
                "start": round(event_start, 3),
                "end": round(event_end, 3),
                "duration": round(event_end - event_start, 3),
                "duration_per_syllable": round(duration_per_syllable, 3),
                "text": text,
                "detection_method": detection_method,
                "voiced_ratio": round(features["voiced_ratio"], 3),
                "f0_std_semitone": round(features["f0_std_semitone"], 3),
                "spectral_flatness": features["spectral_flatness"],
                "rms_mean": features["rms_mean"],
            })

    return events


def detect_sustained_word_events(audio_path, transcription_result):
    y, sr, _duration = load_audio(audio_path)
    return detect_sustained_word_events_from_waveform(
        y,
        sr,
        transcription_result,
    )


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
