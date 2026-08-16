import unittest

import numpy as np

from audio_analysis import detect_sustained_word_events_from_waveform


class SustainedWordDetectionTests(unittest.TestCase):

    def test_detects_stable_single_syllable_prolongation(self):
        sr = 16000
        duration = 1.0
        time = np.arange(int(sr * duration)) / sr
        waveform = 0.1 * np.sin(2 * np.pi * 120 * time)
        transcription = {
            "words": [{"word": "면", "start": 0.0, "end": duration}]
        }

        events = detect_sustained_word_events_from_waveform(
            waveform,
            sr,
            transcription,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["text"], "면")

    def test_detects_stable_window_inside_multi_syllable_word(self):
        sr = 16000
        duration = 1.6
        half = int(sr * duration / 2)
        prefix_time = np.arange(half) / sr
        suffix_time = np.arange(half) / sr
        prefix = 0.1 * np.sin(
            2 * np.pi * (100 * prefix_time + 80 * prefix_time ** 2)
        )
        suffix = 0.1 * np.sin(2 * np.pi * 120 * suffix_time)
        waveform = np.concatenate([prefix, suffix])
        transcription = {
            "words": [{"word": "이어가면", "start": 0.0, "end": duration}]
        }

        events = detect_sustained_word_events_from_waveform(
            waveform,
            sr,
            transcription,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["detection_method"], "word_internal_window")

    def test_ignores_normal_multi_syllable_pitch_change(self):
        sr = 16000
        duration = 1.0
        time = np.arange(int(sr * duration)) / sr
        waveform = 0.1 * np.sin(
            2 * np.pi * (100 * time + 80 * time ** 2)
        )
        transcription = {
            "words": [{"word": "이런", "start": 0.0, "end": duration}]
        }

        events = detect_sustained_word_events_from_waveform(
            waveform,
            sr,
            transcription,
        )

        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
