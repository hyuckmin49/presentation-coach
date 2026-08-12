# transcription.py

import whisper


class WhisperTranscriber:

    def __init__(self, model_name="small"):
        """
        Whisper 모델 로드.

        처음에는 small 추천.
        너무 느리면 base로 낮춰도 됨.
        """

        print(f"[B] Whisper 모델 로딩 중: {model_name}")

        self.model = whisper.load_model(
            model_name
        )

        print("[B] Whisper 모델 로딩 완료")


    def transcribe(self, audio_path: str):
        """
        음성을 한국어 텍스트로 변환하고
        segment-level / word-level timestamp를 반환한다.
        """

        print(f"[B] 음성 변환 시작: {audio_path}")

        result = self.model.transcribe(
            audio_path,
            language="ko",
            task="transcribe",
            word_timestamps=True,
            verbose=False,
            fp16=False
        )


        # ====================================================
        # segment-level 결과
        # ====================================================

        segments = []

        for segment in result.get(
            "segments",
            []
        ):

            segment_text = (
                segment.get("text", "")
                .strip()
            )

            segments.append({
                "start": round(
                    float(segment["start"]),
                    3
                ),
                "end": round(
                    float(segment["end"]),
                    3
                ),
                "text": segment_text
            })


        # ====================================================
        # word-level 결과
        # ====================================================

        words = []

        for segment in result.get(
            "segments",
            []
        ):

            for word_info in segment.get(
                "words",
                []
            ):

                word = (
                    word_info
                    .get("word", "")
                    .strip()
                )

                if not word:
                    continue

                words.append({
                    "word": word,

                    "start": round(
                        float(
                            word_info["start"]
                        ),
                        3
                    ),

                    "end": round(
                        float(
                            word_info["end"]
                        ),
                        3
                    )
                })


        # ====================================================
        # 최종 출력
        # ====================================================

        output = {
            "text":
                result.get(
                    "text",
                    ""
                ).strip(),

            "segments":
                segments,

            "words":
                words
        }


        print("[B] 음성 변환 완료")

        return output