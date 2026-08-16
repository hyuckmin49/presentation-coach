import io
import unittest
import wave

from analysis_time import (
    analysis_time_label,
    estimate_analysis_seconds,
    get_wav_duration_seconds,
)


def silent_wav(duration_seconds, sample_rate=16000):
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\x00\x00" * int(duration_seconds * sample_rate))
    return output.getvalue()


class AnalysisTimeTests(unittest.TestCase):

    def test_reads_wav_duration(self):
        duration = get_wav_duration_seconds(silent_wav(74))
        self.assertAlmostEqual(duration, 74.0, places=2)

    def test_estimates_single_value_from_audio_length(self):
        self.assertEqual(estimate_analysis_seconds(40), 20)
        self.assertEqual(estimate_analysis_seconds(74), 30)
        self.assertEqual(estimate_analysis_seconds(120), 50)

    def test_builds_single_line_status_label(self):
        label = analysis_time_label(silent_wav(74))
        self.assertEqual(label, "예상 소요 시간 약 30초")
        self.assertNotIn("\n", label)

    def test_formats_estimate_over_one_minute(self):
        label = analysis_time_label(silent_wav(180))
        self.assertEqual(label, "예상 소요 시간 약 1분 10초")


if __name__ == "__main__":
    unittest.main()
