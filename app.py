# app.py

import os
import tempfile
import streamlit as st

from audio_analysis import analyze_audio
from transcription import WhisperTranscriber
from language_analysis import analyze_language
from scoring import analyze_scoring


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="발표 코칭 프로그램",
    page_icon="🎤",
    layout="centered"
)

st.title("🎤 발표 코칭 프로그램")

st.write(
    "발표 음성을 분석하여 발화 흐름이 흔들린 "
    "후보 구간을 찾고, 다시 연습할 지점을 제시합니다."
)


# ============================================================
# Whisper 모델 캐시
# ============================================================

@st.cache_resource
def load_transcriber():
    return WhisperTranscriber(
        model_name="small"
    )


transcriber = load_transcriber()


# ============================================================
# 공통 분석 함수
# ============================================================

def run_analysis(audio_file, transcriber):
    """
    Streamlit의 녹음/업로드 파일을 받아
    A → B → C → D 분석을 수행한다.
    """

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".wav"
    ) as tmp:

        tmp.write(
            audio_file.getvalue()
        )

        audio_path = tmp.name

    try:

        audio_result = analyze_audio(
            audio_path
        )

        transcription_result = (
            transcriber.transcribe(
                audio_path
            )
        )

        language_result = (
            analyze_language(
                transcription_result
            )
        )

        scoring_result = (
            analyze_scoring(
                audio_result,
                transcription_result,
                language_result
            )
        )

        return {
            "audio_result":
                audio_result,

            "transcription_result":
                transcription_result,

            "language_result":
                language_result,

            "scoring_result":
                scoring_result,
        }

    finally:

        if os.path.exists(
            audio_path
        ):
            os.remove(
                audio_path
            )


# ============================================================
# 1. 1차 발표 입력
# ============================================================

st.header("1. 1차 발표")

st.write(
    "분석할 발표를 웹에서 바로 녹음하거나, "
    "미리 녹음한 WAV 파일을 업로드하세요."
)


first_input_method = st.radio(
    "1차 발표 입력 방법",
    [
        "웹에서 바로 녹음",
        "녹음 파일 업로드"
    ],
    horizontal=True,
    key="first_input_method"
)


first_audio = None


# ------------------------------------------------------------
# 웹 직접 녹음
# ------------------------------------------------------------

if first_input_method == "웹에서 바로 녹음":

    first_audio = st.audio_input(
        "1차 발표를 녹음하세요.",
        sample_rate=16000,
        key="first_recording"
    )


# ------------------------------------------------------------
# 파일 업로드
# ------------------------------------------------------------

else:

    first_audio = st.file_uploader(
        "1차 발표 WAV 파일을 업로드하세요.",
        type=["wav"],
        key="first_upload"
    )


# ------------------------------------------------------------
# 음성 확인
# ------------------------------------------------------------

if first_audio is not None:

    st.markdown(
        "**입력한 1차 발표 음성 확인**"
    )

    st.audio(
        first_audio,
        format="audio/wav"
    )


    # ========================================================
    # 2. 1차 분석 실행
    # ========================================================

    if st.button(
        "1차 발표 분석 시작",
        type="primary"
    ):

        with st.status(
            "1차 발표를 분석하고 있습니다...",
            expanded=True
        ) as status:

            st.write(
                "A. 음성 신호 분석"
            )

            st.write(
                "B. 음성 → 텍스트 변환"
            )

            st.write(
                "C. 언어 구조 분석"
            )

            st.write(
                "D. 비유창성 후보 통합 판단"
            )


            first_result = run_analysis(
                first_audio,
                transcriber
            )


            status.update(
                label="1차 발표 분석 완료",
                state="complete",
                expanded=False
            )


        st.session_state[
            "first_audio_bytes"
        ] = first_audio.getvalue()

        st.session_state[
            "first_result"
        ] = first_result


# ============================================================
# 3. 1차 분석 결과
# ============================================================

if (
    "first_result"
    in st.session_state
):

    first_result = st.session_state[
        "first_result"
    ]

    transcription_result = (
        first_result[
            "transcription_result"
        ]
    )

    scoring_result = (
        first_result[
            "scoring_result"
        ]
    )

    candidates = (
        scoring_result[
            "coaching_candidates"
        ]
    )


    st.divider()

    st.header(
        "2. 1차 발표 분석 결과"
    )


    # --------------------------------------------------------
    # 전체 발표문
    # --------------------------------------------------------

    with st.expander(
        "전체 발표 내용 보기"
    ):

        st.write(
            transcription_result[
                "text"
            ]
        )


    # --------------------------------------------------------
    # 후보 개수
    # --------------------------------------------------------

    if len(candidates) == 0:

        st.success(
            "우선 코칭이 필요한 "
            "비유창성 후보 구간이 탐지되지 않았습니다."
        )

    else:

        st.warning(
            f"우선 점검이 필요한 "
            f"발화 구간이 "
            f"{len(candidates)}개 탐지되었습니다."
        )


        # ====================================================
        # 후보별 출력
        # ====================================================

        for i, candidate in enumerate(
            candidates,
            start=1
        ):

            st.subheader(
                f"후보 {i}"
            )


            # -----------------------------------------------
            # 시간 / 점수
            # -----------------------------------------------

            col1, col2 = st.columns(
                2
            )

            with col1:

                st.metric(
                    "발화 구간",
                    (
                        f"{candidate['start']:.2f}s "
                        f"~ "
                        f"{candidate['end']:.2f}s"
                    )
                )

            with col2:

                st.metric(
                    "비유창성 점수",
                    candidate[
                        "score"
                    ]
                )


            # -----------------------------------------------
            # 해당 발화
            # -----------------------------------------------

            st.markdown(
                "**해당 발화**"
            )

            st.info(
                candidate[
                    "text"
                ]
            )


            # -----------------------------------------------
            # 탐지 근거
            # -----------------------------------------------

            st.markdown(
                "**탐지 근거**"
            )

            for reason in candidate[
                "reasons"
            ]:

                st.write(
                    f"- {reason}"
                )


            # -----------------------------------------------
            # 코칭 제안
            # -----------------------------------------------

            st.markdown(
                "**코칭 제안**"
            )

            st.success(
                candidate[
                    "coaching_prompt"
                ]
            )


            # -----------------------------------------------
            # 원본 발표 재생
            # -----------------------------------------------

            st.markdown(
                "**원본 발표에서 확인하기**"
            )

            st.audio(
                st.session_state[
                    "first_audio_bytes"
                ],
                format="audio/wav",
                start_time=
                    candidate[
                        "start"
                    ]
            )


            # -----------------------------------------------
            # 사용자 회고
            # -----------------------------------------------

            st.text_area(
                (
                    "이 구간에서 전달하려던 "
                    "핵심 내용과 내용 간 관계를 "
                    "간단히 정리해 보세요."
                ),
                key=f"reflection_{i}",
                placeholder=(
                    "예: 현재 작업 "
                    "→ 알고리즘 제작 "
                    "→ 학습 데이터 구축"
                )
            )


            st.divider()


    # ========================================================
    # 4. 코칭 후 재발화
    # ========================================================

    st.header(
        "3. 코칭 후 다시 발표하기"
    )

    st.write(
        "위에서 확인한 코칭 내용을 바탕으로 "
        "핵심 내용과 내용 간 관계를 다시 정리한 뒤, "
        "같은 내용을 자신의 언어로 다시 말해 보세요."
    )

    st.info(
        "문장을 그대로 암기하기보다 "
        "핵심 개념과 내용의 관계를 떠올리며 "
        "재발화해 보세요."
    )


    retry_input_method = st.radio(
        "2차 발표 입력 방법",
        [
            "웹에서 바로 녹음",
            "녹음 파일 업로드"
        ],
        horizontal=True,
        key="retry_input_method"
    )


    retry_audio = None


    # --------------------------------------------------------
    # 웹 직접 녹음
    # --------------------------------------------------------

    if (
        retry_input_method
        == "웹에서 바로 녹음"
    ):

        retry_audio = st.audio_input(
            "2차 발표를 녹음하세요.",
            sample_rate=16000,
            key="retry_recording"
        )


    # --------------------------------------------------------
    # 파일 업로드
    # --------------------------------------------------------

    else:

        retry_audio = st.file_uploader(
            "2차 발표 WAV 파일을 업로드하세요.",
            type=["wav"],
            key="retry_upload"
        )


    # --------------------------------------------------------
    # 2차 음성 확인
    # --------------------------------------------------------

    if retry_audio is not None:

        st.markdown(
            "**입력한 2차 발표 음성 확인**"
        )

        st.audio(
            retry_audio,
            format="audio/wav"
        )


        # ====================================================
        # 5. 2차 분석
        # ====================================================

        if st.button(
            "2차 발표 분석 시작",
            type="primary"
        ):

            with st.status(
                "2차 발표를 분석하고 있습니다...",
                expanded=True
            ) as status:

                st.write(
                    "A. 음성 신호 분석"
                )

                st.write(
                    "B. 음성 → 텍스트 변환"
                )

                st.write(
                    "C. 언어 구조 분석"
                )

                st.write(
                    "D. 비유창성 후보 통합 판단"
                )


                retry_result = run_analysis(
                    retry_audio,
                    transcriber
                )


                status.update(
                    label="2차 발표 분석 완료",
                    state="complete",
                    expanded=False
                )


            st.session_state[
                "retry_audio_bytes"
            ] = retry_audio.getvalue()

            st.session_state[
                "retry_result"
            ] = retry_result


# ============================================================
# 6. 코칭 전후 비교
# ============================================================

if (
    "first_result"
    in st.session_state
    and
    "retry_result"
    in st.session_state
):

    first_result = st.session_state[
        "first_result"
    ]

    retry_result = st.session_state[
        "retry_result"
    ]


    first_candidates = (
        first_result[
            "scoring_result"
        ][
            "coaching_candidates"
        ]
    )

    retry_candidates = (
        retry_result[
            "scoring_result"
        ][
            "coaching_candidates"
        ]
    )


    st.divider()

    st.header(
        "4. 코칭 전후 비교"
    )


    # --------------------------------------------------------
    # 후보 수 비교
    # --------------------------------------------------------

    col1, col2 = st.columns(
        2
    )


    with col1:

        st.metric(
            "1차 발표 코칭 후보",
            len(
                first_candidates
            )
        )


    with col2:

        difference = (
            len(retry_candidates)
            - len(first_candidates)
        )

        st.metric(
            "2차 발표 코칭 후보",
            len(
                retry_candidates
            ),
            delta=difference,
            delta_color="inverse"
        )


    # --------------------------------------------------------
    # 결과 해석
    # --------------------------------------------------------

    if (
        len(retry_candidates)
        < len(first_candidates)
    ):

        st.success(
            "2차 발표에서 우선 코칭 후보 구간이 감소했습니다. "
            "코칭 전후 어떤 발화 신호가 달라졌는지 "
            "세부 결과를 확인해 보세요."
        )

    elif (
        len(retry_candidates)
        == len(first_candidates)
    ):

        st.info(
            "1차와 2차 발표에서 탐지된 후보 수가 같습니다. "
            "후보가 나타난 위치와 탐지 근거의 변화를 "
            "함께 확인해 보세요."
        )

    else:

        st.warning(
            "2차 발표에서 탐지된 후보 수가 증가했습니다. "
            "새롭게 발화가 흔들린 의미 단위가 있는지 "
            "확인해 보세요."
        )


    # --------------------------------------------------------
    # 1차 전체 transcript
    # --------------------------------------------------------

    with st.expander(
        "1차 발표 내용 보기"
    ):

        st.write(
            first_result[
                "transcription_result"
            ][
                "text"
            ]
        )


    # --------------------------------------------------------
    # 2차 전체 transcript
    # --------------------------------------------------------

    with st.expander(
        "2차 발표 내용 보기"
    ):

        st.write(
            retry_result[
                "transcription_result"
            ][
                "text"
            ]
        )


    # --------------------------------------------------------
    # 2차 후보 세부 결과
    # --------------------------------------------------------

    st.subheader(
        "2차 발표 세부 분석"
    )


    if len(retry_candidates) == 0:

        st.success(
            "2차 발표에서는 "
            "우선 코칭 후보 구간이 탐지되지 않았습니다."
        )

    else:

        for i, candidate in enumerate(
            retry_candidates,
            start=1
        ):

            st.markdown(
                f"### 후보 {i}"
            )


            st.write(
                (
                    f"발화 구간: "
                    f"{candidate['start']:.2f}s "
                    f"~ "
                    f"{candidate['end']:.2f}s"
                )
            )


            st.info(
                candidate[
                    "text"
                ]
            )


            st.write(
                "점수:",
                candidate[
                    "score"
                ]
            )


            st.write(
                "탐지 근거:"
            )

            for reason in candidate[
                "reasons"
            ]:

                st.write(
                    f"- {reason}"
                )


            st.audio(
                st.session_state[
                    "retry_audio_bytes"
                ],
                format="audio/wav",
                start_time=
                    candidate[
                        "start"
                    ]
            )


            st.divider()