import io
import unittest

from pypdf import PdfReader

from feedback_report import build_feedback_pdf, feedback_pdf_filename


def sample_result(candidate_count=1):
    candidates = []
    if candidate_count:
        candidates.append(
            {
                "event_type": "CHUNK",
                "start": 1.2,
                "end": 3.4,
                "text": "음 발표의 핵심은",
                "score": 3,
                "reasons": ["간투사 사용", "반복 또는 재시작 발생"],
                "coaching_prompt": "핵심 개념을 정리한 뒤 다시 말해 보세요.",
            }
        )
    return {
        "transcription_result": {"text": "한국어 발표 전사문입니다."},
        "scoring_result": {"coaching_candidates": candidates},
    }


class FeedbackReportTests(unittest.TestCase):

    def test_builds_readable_three_round_pdf(self):
        pdf_bytes = build_feedback_pdf(
            "20315",
            "홍길동",
            [sample_result(), sample_result(0), sample_result()],
            {(1, 1): "핵심 내용을 먼저 말하겠습니다."},
            {
                1: "문제 상황에서 분석 원리로 이어집니다.",
                2: "분석 결과와 적용 방법을 연결합니다.",
                3: "탐구의 한계와 개선 방향으로 마무리합니다.",
            },
        )

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        io_stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(io_stream)
        self.assertGreaterEqual(len(reader.pages), 4)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("발표 코칭 최종 피드백", text)
        self.assertIn("홍길동", text)
        self.assertIn("3차 발표", text)
        self.assertIn("발표 전체 구조 메모", text)
        self.assertIn("탐구의 한계와 개선 방향", text)
        io_stream.close()

    def test_sanitizes_download_filename(self):
        self.assertEqual(
            feedback_pdf_filename("20/315", "홍 길동"),
            "20_315_홍_길동_발표피드백.pdf",
        )

    def test_requires_exactly_three_results(self):
        with self.assertRaises(ValueError):
            build_feedback_pdf("1", "학생", [sample_result()], {})


if __name__ == "__main__":
    unittest.main()
