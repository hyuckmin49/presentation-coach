import io
import wave


def get_wav_duration_seconds(audio_bytes):
    """WAV 바이트에서 재생 시간을 초 단위로 반환한다."""

    with wave.open(io.BytesIO(audio_bytes), "rb") as audio:
        frame_rate = audio.getframerate()
        if frame_rate <= 0:
            return 0.0
        return audio.getnframes() / frame_rate


def estimate_analysis_seconds(audio_duration_seconds):
    """실측 처리 비율을 바탕으로 예상 분석 시간을 10초 단위로 반환한다."""

    estimated_seconds = max(0.0, audio_duration_seconds) * 0.4
    return max(10, round(estimated_seconds / 10) * 10)


def analysis_time_label(audio_bytes):
    duration = get_wav_duration_seconds(audio_bytes)
    seconds = estimate_analysis_seconds(duration)
    if seconds < 60:
        return f"예상 소요 시간 약 {seconds}초"

    minutes, remaining_seconds = divmod(seconds, 60)
    if remaining_seconds == 0:
        return f"예상 소요 시간 약 {minutes}분"
    return f"예상 소요 시간 약 {minutes}분 {remaining_seconds}초"
