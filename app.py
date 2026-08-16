import os
import tempfile

import streamlit as st

from audio_analysis import analyze_audio
from language_analysis import analyze_language
from scoring import analyze_scoring
from transcription import WhisperTranscriber


TOTAL_ROUNDS = 3
FINAL_STEP = TOTAL_ROUNDS + 1
STEP_LABELS = {
    1: "1차 발표",
    2: "2차 발표",
    3: "3차 발표",
    4: "최종 비교",
}

st.set_page_config(
    page_title="발표 코칭 프로그램",
    page_icon="🎤",
    layout="centered",
)


@st.cache_resource
def load_transcriber():
    return WhisperTranscriber(model_name="small")


def initialize_session_state():
    st.session_state.setdefault("current_step", 1)


def result_key(round_number):
    return f"round_{round_number}_result"


def audio_key(round_number):
    return f"round_{round_number}_audio_bytes"


def reflection_key(round_number, candidate_index):
    return f"round_{round_number}_reflection_{candidate_index}"


def run_analysis(audio_file, transcriber):
    """Streamlit 입력 음성에 A → B → C → D 분석을 수행한다."""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_file.getvalue())
        audio_path = tmp.name

    try:
        audio_result = analyze_audio(audio_path)
        transcription_result = transcriber.transcribe(audio_path)
        language_result = analyze_language(transcription_result)
        scoring_result = analyze_scoring(
            audio_result,
            transcription_result,
            language_result,
        )
        return {
            "audio_result": audio_result,
            "transcription_result": transcription_result,
            "language_result": language_result,
            "scoring_result": scoring_result,
        }
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def get_candidates(result):
    return result["scoring_result"]["coaching_candidates"]


def get_candidate_text(candidate):
    if candidate["event_type"] == "CHUNK":
        return candidate["text"]
    return (
        f"{candidate.get('left_text', '')} "
        f"→ {candidate.get('right_text', '')}"
    ).strip()


def clear_from_round(round_number):
    """현재 회차부터 이후의 분석과 회고를 모두 초기화한다."""

    for target_round in range(round_number, TOTAL_ROUNDS + 1):
        st.session_state.pop(result_key(target_round), None)
        st.session_state.pop(audio_key(target_round), None)
        prefix = f"round_{target_round}_reflection_"
        for key in list(st.session_state):
            if key.startswith(prefix):
                del st.session_state[key]
    st.session_state.current_step = round_number


def reset_practice():
    clear_from_round(1)
    for key in list(st.session_state):
        if key.startswith("round_"):
            del st.session_state[key]
    st.session_state.current_step = 1


def go_to_step(step):
    st.session_state.current_step = step


def render_progress():
    current_step = st.session_state.current_step
    st.progress(
        current_step / FINAL_STEP,
        text=f"{current_step}/{FINAL_STEP} · {STEP_LABELS[current_step]}",
    )
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        for step, label in STEP_LABELS.items():
            if step < current_step:
                st.caption(f"✓ {label}")
            elif step == current_step:
                st.markdown(f"**{label}**")
            else:
                st.caption(label)


def render_candidate(
    candidate,
    candidate_index,
    round_number,
    audio_bytes,
):
    with st.container(border=True):
        st.subheader(f"보완 후보 {candidate_index}")
        columns = st.columns(2)
        columns[0].metric(
            "발화 구간",
            f"{candidate['start']:.2f}s ~ {candidate['end']:.2f}s",
        )
        columns[1].metric("비유창성 점수", candidate["score"])

        st.markdown("**해당 발화**")
        st.info(get_candidate_text(candidate))
        st.markdown("**탐지 근거**")
        for reason in candidate["reasons"]:
            st.write(f"- {reason}")

        if candidate.get("coaching_prompt"):
            st.markdown("**코칭 제안**")
            st.success(candidate["coaching_prompt"])

        st.markdown("**원본 발표에서 확인하기**")
        st.audio(
            audio_bytes,
            format="audio/wav",
            start_time=candidate["start"],
        )

        st.text_area(
            "이 구간에서 전달하려던 핵심 내용과 내용 간 관계를 "
            "간단히 정리해 보세요.",
            key=reflection_key(round_number, candidate_index),
            placeholder="예: 현재 작업 → 알고리즘 제작 → 학습 데이터 구축",
        )


def render_round_result(round_number, result, audio_bytes):
    candidates = get_candidates(result)
    st.divider()
    st.header(f"{round_number}차 발표 분석 결과")

    with st.expander("전체 발표 내용 보기"):
        st.write(result["transcription_result"]["text"])

    if not candidates:
        st.success("우선 코칭이 필요한 비유창성 후보 구간이 탐지되지 않았습니다.")
        return

    st.warning(f"우선 점검할 발화 구간이 {len(candidates)}개 탐지되었습니다.")
    for index, candidate in enumerate(candidates, start=1):
        render_candidate(
            candidate,
            index,
            round_number,
            audio_bytes,
        )


def render_analysis_status(audio_file, transcriber):
    with st.status("발표를 분석하고 있습니다...", expanded=True) as status:
        st.write("A. 음성 신호 분석")
        st.write("B. 음성을 텍스트로 변환")
        st.write("C. 발화 구조 분석")
        st.write("D. 비유창성 후보 통합 판단")
        result = run_analysis(audio_file, transcriber)
        status.update(
            label="발표 분석 완료",
            state="complete",
            expanded=False,
        )
    return result


def render_audio_input(round_number):
    input_method = st.segmented_control(
        f"{round_number}차 발표 입력 방법",
        ["웹에서 바로 녹음", "녹음 파일 업로드"],
        default="웹에서 바로 녹음",
        key=f"round_{round_number}_input_method",
        width="stretch",
    )

    if input_method == "웹에서 바로 녹음":
        return st.audio_input(
            f"{round_number}차 발표를 녹음하세요.",
            sample_rate=16000,
            key=f"round_{round_number}_recording",
        )

    return st.file_uploader(
        f"{round_number}차 발표 WAV 파일을 업로드하세요.",
        type=["wav"],
        key=f"round_{round_number}_upload",
    )


def render_round_navigation(round_number, has_result):
    st.divider()
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if round_number > 1 and st.button(
            "이전 단계",
            icon=":material/arrow_back:",
            key=f"round_{round_number}_previous",
        ):
            go_to_step(round_number - 1)
            st.rerun()

        if has_result:
            next_label = (
                "최종 비교 보기"
                if round_number == TOTAL_ROUNDS
                else f"{round_number + 1}차 발표로"
            )
            if st.button(
                next_label,
                type="primary",
                icon=":material/arrow_forward:",
                key=f"round_{round_number}_next",
            ):
                go_to_step(round_number + 1)
                st.rerun()


def render_round_page(round_number, transcriber):
    st.header(f"{round_number}차 발표")
    if round_number == 1:
        st.write("현재 발표를 녹음하고 첫 분석 결과를 확인하세요.")
    else:
        st.write(
            "이전 회차의 코칭 내용을 바탕으로 핵심 내용을 다시 정리한 뒤, "
            "같은 내용을 자신의 언어로 다시 발표하세요."
        )
        st.info(
            "문장을 암기하기보다 핵심 개념과 내용의 관계를 떠올리며 "
            "재발화해 보세요."
        )

    stored_result = st.session_state.get(result_key(round_number))
    if stored_result is None:
        audio_file = render_audio_input(round_number)
        if audio_file is not None:
            st.audio(audio_file, format="audio/wav")
            if st.button(
                f"{round_number}차 발표 분석 시작",
                type="primary",
                icon=":material/analytics:",
                key=f"round_{round_number}_analyze",
            ):
                result = render_analysis_status(audio_file, transcriber)
                st.session_state[result_key(round_number)] = result
                st.session_state[audio_key(round_number)] = audio_file.getvalue()
                st.rerun()
    else:
        render_round_result(
            round_number,
            stored_result,
            st.session_state[audio_key(round_number)],
        )
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button(
                "이 회차부터 다시 녹음",
                icon=":material/replay:",
                key=f"round_{round_number}_retry",
            ):
                clear_from_round(round_number)
                st.rerun()

    render_round_navigation(round_number, stored_result is not None)


def render_comparison_candidate(round_number, candidate, index, audio_bytes):
    with st.container(border=True):
        st.markdown(f"**{round_number}차 보완 후보 {index}**")
        st.write(
            f"{candidate['start']:.2f}s ~ {candidate['end']:.2f}s · "
            f"{candidate['score']}점"
        )
        st.info(get_candidate_text(candidate))
        st.write("탐지 근거: " + ", ".join(candidate["reasons"]))
        st.audio(
            audio_bytes,
            format="audio/wav",
            start_time=candidate["start"],
        )


def render_comparison_page():
    if not all(
        result_key(round_number) in st.session_state
        for round_number in range(1, TOTAL_ROUNDS + 1)
    ):
        st.warning("3차 발표 분석까지 완료해야 최종 비교를 볼 수 있습니다.")
        if st.button("미완료 단계로 돌아가기"):
            for round_number in range(1, TOTAL_ROUNDS + 1):
                if result_key(round_number) not in st.session_state:
                    go_to_step(round_number)
                    st.rerun()
        return

    results = [
        st.session_state[result_key(round_number)]
        for round_number in range(1, TOTAL_ROUNDS + 1)
    ]
    counts = [len(get_candidates(result)) for result in results]

    st.header("최종 비교")
    st.write("1차부터 3차까지 발화 흐름이 어떻게 변했는지 확인하세요.")
    columns = st.columns(3)
    for index, count in enumerate(counts):
        delta = None if index == 0 else count - counts[index - 1]
        columns[index].metric(
            f"{index + 1}차 보완 후보",
            count,
            delta=delta,
            delta_color="inverse",
        )

    if counts[-1] < counts[0]:
        st.success(
            f"3차 발표의 보완 후보가 1차보다 "
            f"{counts[0] - counts[-1]}개 감소했습니다."
        )
    elif counts[-1] == counts[0]:
        st.info(
            "1차와 3차의 보완 후보 수가 같습니다. "
            "구간과 탐지 근거의 변화를 함께 확인하세요."
        )
    else:
        st.warning(
            f"3차 발표의 보완 후보가 1차보다 "
            f"{counts[-1] - counts[0]}개 늘었습니다."
        )

    for round_number, result in enumerate(results, start=1):
        candidates = get_candidates(result)
        with st.expander(
            f"{round_number}차 세부 결과 · 보완 후보 {len(candidates)}개"
        ):
            st.markdown("**전체 발표 내용**")
            st.write(result["transcription_result"]["text"])
            if not candidates:
                st.success("보완 후보가 탐지되지 않았습니다.")
            for index, candidate in enumerate(candidates, start=1):
                render_comparison_candidate(
                    round_number,
                    candidate,
                    index,
                    st.session_state[audio_key(round_number)],
                )

    st.divider()
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if st.button("이전 단계", icon=":material/arrow_back:"):
            go_to_step(TOTAL_ROUNDS)
            st.rerun()
        if st.button(
            "새 연습 시작",
            type="primary",
            icon=":material/restart_alt:",
        ):
            reset_practice()
            st.rerun()


initialize_session_state()
transcriber = load_transcriber()

st.title("🎤 발표 코칭 프로그램")
st.write(
    "발표 음성을 분석하여 발화 흐름이 흔들린 구간을 찾고, "
    "세 번의 연습 결과를 비교합니다."
)
render_progress()
st.divider()

if st.session_state.current_step <= TOTAL_ROUNDS:
    render_round_page(st.session_state.current_step, transcriber)
else:
    render_comparison_page()
