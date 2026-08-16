import unittest

from scoring import analyze_scoring, extract_repeated_weakener_events


def word(text, start, end):
    return {"word": text, "start": start, "end": end}


def language_result(words):
    return {
        "sentences": [
            {
                "sentence_id": 0,
                "start": words[0]["start"],
                "end": words[-1]["end"],
                "text": " ".join(item["word"] for item in words),
                "chunks": [
                    {
                        "chunk_id": 0,
                        "start": words[0]["start"],
                        "end": words[-1]["end"],
                        "text": " ".join(item["word"] for item in words),
                        "words": words,
                    }
                ],
            }
        ],
        "repetition_restart_events": [],
    }


class RepeatedWeakenerTests(unittest.TestCase):

    def test_single_use_is_not_a_weakener_event(self):
        words = [word("약간", 0.0, 0.4), word("증가했습니다.", 0.4, 1.0)]

        self.assertEqual(extract_repeated_weakener_events(language_result(words)), [])

    def test_marks_only_second_and_later_use_in_sentence(self):
        words = [
            word("약간", 0.0, 0.4),
            word("흐름을", 0.4, 0.8),
            word("약간", 0.8, 1.2),
            word("바꿉니다.", 1.2, 1.8),
        ]

        events = extract_repeated_weakener_events(language_result(words))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["start"], 0.8)

    def test_repeated_use_becomes_coaching_candidate(self):
        words = [
            word("약간", 0.0, 0.4),
            word("흐름을", 0.4, 0.8),
            word("약간", 0.8, 1.2),
            word("바꿉니다.", 1.2, 1.8),
        ]
        transcription = {"words": words, "text": "약간 흐름을 약간 바꿉니다."}
        result = analyze_scoring(
            {"pauses": []},
            transcription,
            language_result(words),
        )

        self.assertEqual(len(result["coaching_candidates"]), 1)
        candidate = result["coaching_candidates"][0]
        self.assertEqual(candidate["score"], 3)
        self.assertIn("한 문장 안에서 '약간' 반복 사용", candidate["reasons"])


if __name__ == "__main__":
    unittest.main()
