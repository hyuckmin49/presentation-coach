import sys
import types
import unittest
from unittest.mock import Mock, patch


# 로컬 환경에 openai-whisper가 없어도 전사 로직을 단위 테스트한다.
sys.modules.setdefault(
    "whisper",
    types.SimpleNamespace(load_model=Mock())
)

from transcription import WhisperTranscriber


class WhisperTranscriberTests(unittest.TestCase):

    @patch("transcription.whisper.load_model")
    def test_uses_korean_language_and_preserves_mixed_result(
        self,
        load_model
    ):
        model = Mock()
        load_model.return_value = model
        model.transcribe.return_value = {
            "language": "ko",
            "text": "Whisper로 speech signal을 분석합니다.",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.3456,
                    "text": " Whisper로 speech signal을 분석합니다. ",
                    "words": [
                        {
                            "word": " Whisper로",
                            "start": 0.0,
                            "end": 0.6,
                        },
                        {
                            "word": " speech signal을",
                            "start": 0.6,
                            "end": 1.4,
                        },
                    ],
                }
            ],
        }

        transcriber = WhisperTranscriber(model_name="small")
        result = transcriber.transcribe("mixed.wav")

        model.transcribe.assert_called_once_with(
            "mixed.wav",
            language="ko",
            task="transcribe",
            word_timestamps=True,
            verbose=False,
            fp16=False,
        )
        self.assertEqual(
            result["text"],
            "Whisper로 speech signal을 분석합니다."
        )
        self.assertEqual(result["segments"][0]["end"], 2.346)
        self.assertEqual(result["words"][1]["word"], "speech signal을")

    @patch("transcription.whisper.load_model")
    def test_allows_empty_segments(
        self,
        load_model
    ):
        model = Mock()
        load_model.return_value = model
        model.transcribe.return_value = {
            "text": "전사 결과",
            "segments": [],
        }

        transcriber = WhisperTranscriber()
        result = transcriber.transcribe("audio.wav")

        self.assertEqual(result["text"], "전사 결과")


if __name__ == "__main__":
    unittest.main()
