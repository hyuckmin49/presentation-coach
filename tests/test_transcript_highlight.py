import unittest

from transcript_highlight import highlight_transcript, highlight_transcript_pdf


class TranscriptHighlightTests(unittest.TestCase):

    def test_highlights_chunk_in_full_transcript(self):
        result = highlight_transcript(
            "오늘은 speech signal 분석을 설명합니다.",
            [{"event_type": "CHUNK", "text": "speech signal 분석"}],
        )

        self.assertIn("<mark", result)
        self.assertIn("speech signal 분석</mark>", result)

    def test_highlights_both_sides_of_transition(self):
        result = highlight_transcript(
            "핵심 개념을 설명하고 사례를 제시합니다.",
            [
                {
                    "event_type": "TRANSITION",
                    "left_text": "핵심 개념을 설명하고",
                    "right_text": "사례를 제시합니다",
                }
            ],
        )

        self.assertEqual(result.count("<mark"), 2)

    def test_escapes_untrusted_transcript(self):
        result = highlight_transcript("<script>alert(1)</script>", [])

        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_builds_reportlab_highlight_markup(self):
        result = highlight_transcript_pdf(
            "발표에서 멈춤이 발생했습니다.",
            [{"event_type": "CHUNK", "text": "멈춤이 발생했습니다"}],
        )

        self.assertIn('<font backColor="#FFE08A">', result)
        self.assertIn("멈춤이 발생했습니다</font>", result)


if __name__ == "__main__":
    unittest.main()
