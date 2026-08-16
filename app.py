import os
import tempfile
import time

import streamlit as st

from audio_analysis import analyze_audio
from feedback_report import build_feedback_pdf, feedback_pdf_filename
from language_analysis import analyze_language
from scoring import analyze_scoring
from transcription import WhisperTranscriber
from transcript_highlight import highlight_transcript


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
    st.session_state.setdefault("onboarding_step", 1)
    st.session_state.setdefault("student_info_confirmed", False)


def result_key(round_number):
    return f"round_{round_number}_result"


def audio_key(round_number):
    return f"round_{round_number}_audio_bytes"


def reflection_key(round_number, candidate_index):
    return f"round_{round_number}_reflection_{candidate_index}"


def structure_note_key(round_number):
    return f"round_{round_number}_structure_note"


def run_analysis(audio_file, transcriber, on_stage=None):
    """Streamlit 입력 음성에 A → B → C → D 분석을 수행한다."""

    def announce(label):
        if on_stage is not None:
            on_stage(label)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_file.getvalue())
        audio_path = tmp.name

    try:
        processing_seconds = {}

        announce("A. 음성 신호 분석")
        started_at = time.perf_counter()
        audio_result = analyze_audio(audio_path)
        processing_seconds["A"] = round(time.perf_counter() - started_at, 3)

        announce("B. 음성을 텍스트로 변환")
        started_at = time.perf_counter()
        transcription_result = transcriber.transcribe(audio_path)
        processing_seconds["B"] = round(time.perf_counter() - started_at, 3)

        announce("C. 발화 구조 분석")
        started_at = time.perf_counter()
        language_result = analyze_language(transcription_result)
        processing_seconds["C"] = round(time.perf_counter() - started_at, 3)

        announce("D. 비유창성 후보 통합 판단")
        started_at = time.perf_counter()
        scoring_result = analyze_scoring(
            audio_result,
            transcription_result,
            language_result,
        )
        processing_seconds["D"] = round(time.perf_counter() - started_at, 3)
        return {
            "audio_result": audio_result,
            "transcription_result": transcription_result,
            "language_result": language_result,
            "scoring_result": scoring_result,
            "processing_seconds": processing_seconds,
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
        st.session_state.pop(structure_note_key(target_round), None)
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
    for key in (
        "student_id",
        "student_name",
        "student_id_input",
        "student_name_input",
    ):
        st.session_state.pop(key, None)
    st.session_state.student_info_confirmed = False
    st.session_state.onboarding_step = 1
    st.session_state.current_step = 1


def go_to_step(step):
    st.session_state.current_step = step


def render_program_introduction():
    st.header("발표를 외우는 대신 구조화하는 연습")
    st.write(
        "이 프로그램은 발표의 정답이나 내용 수준을 평가하지 않습니다. "
        "멈춤, 간투사, 반복·재시작처럼 발화 흐름이 흔들린 구간을 찾아 "
        "발표자가 다시 생각해 볼 지점을 제안합니다."
    )
    with st.container(border=True):
        st.subheader("어디를 코칭하나요?")
        st.write("발표 중 의미 단위 내부에서 머뭇거리거나 흐름이 끊긴 구간을 살펴봅니다.")
        st.caption(
            "탐지 결과는 잘못된 구간에 대한 판정이 아니라, "
            "스스로 점검할 보완 후보입니다."
        )
    st.info(
        "프로그램이 사람의 모든 문제점을 발견할 수는 없습니다. "
        "발표 전문을 직접 읽고 스스로 점검하는 과정이 필요합니다."
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "사용 방법 보기",
            type="primary",
            icon=":material/arrow_forward:",
        ):
            st.session_state.onboarding_step = 2
            st.rerun()


def render_usage_guide():
    st.header("세 번의 발표로 내용을 구조화합니다")
    st.write(
        "목표는 문장을 외워 매끄럽게 말하는 것이 아닙니다. "
        "핵심 개념과 내용의 관계를 머릿속에 구조화한 뒤, "
        "같은 내용을 자신의 언어로 다시 발표하는 것입니다."
    )
    for title, description in (
        ("1. 발표하고 확인하기", "음성을 분석해 보완 후보와 발표 전문을 확인합니다."),
        ("2. 부분부터 점검하기", "각 보완 후보에서 전달하려던 내용의 관계를 정리합니다."),
        ("3. 전체로 확장하기", "부분 점검을 바탕으로 발표 전체의 구조를 다시 메모합니다."),
        ("4. 다시 발표하기", "구조를 떠올리며 자신의 언어로 총 3차례 발표합니다."),
    ):
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.write(description)
    st.warning(
        "머릿속에 내용을 구조화해 보는 적극적인 시도가 필요합니다. "
        "부분 구조 메모와 전체 구조 메모를 작성해야 다음 회차로 넘어갈 수 있습니다."
    )
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if st.button("이전", icon=":material/arrow_back:"):
            st.session_state.onboarding_step = 1
            st.rerun()
        if st.button(
            "시작해 보기",
            type="primary",
            icon=":material/play_arrow:",
        ):
            st.session_state.onboarding_step = 3
            st.rerun()


def render_student_entry():
    st.header("연습 정보")
    st.write(
        "최종 피드백 PDF의 파일명과 표지에 사용할 학번과 이름을 입력하세요. "
        "입력한 정보는 현재 브라우저 세션에서만 사용됩니다."
    )
    with st.form("student_info_form"):
        st.text_input(
            "학번",
            key="student_id_input",
            max_chars=30,
            placeholder="예: 20315",
        )
        st.text_input(
            "이름",
            key="student_name_input",
            max_chars=30,
            placeholder="예: 홍길동",
        )
        submitted = st.form_submit_button(
            "연습 시작",
            type="primary",
            icon=":material/play_arrow:",
        )

    if submitted:
        student_id = st.session_state.student_id_input.strip()
        student_name = st.session_state.student_name_input.strip()
        if not student_id or not student_name:
            st.error("학번과 이름을 모두 입력하세요.")
            return
        st.session_state.student_id = student_id
        st.session_state.student_name = student_name
        st.session_state.student_info_confirmed = True
        st.rerun()


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
            "부분 구조 메모 (필수)",
            key=reflection_key(round_number, candidate_index),
            placeholder="예: 현재 작업 → 알고리즘 제작 → 학습 데이터 구축",
            help=(
                "이 구간에서 전달하려던 핵심 내용과 "
                "내용 간 관계를 간단히 정리하세요."
            ),
            persist_state="session",
        )


def render_structure_note(round_number):
    st.divider()
    st.subheader("발표 전체 구조 메모")
    st.write(
        "부분 점검을 바탕으로 발표 전체에서 전달하려는 핵심 개념과 "
        "내용의 관계를 다시 구조화해 보세요."
    )
    st.text_area(
        "전체 구조 메모 (필수)",
        key=structure_note_key(round_number),
        placeholder=(
            "예: 문제 상황 → 기존 방식의 한계 → 분석 원리 "
            "→ 적용 결과 → 탐구의 한계"
        ),
        height=150,
        persist_state="session",
    )


def render_round_result(round_number, result, audio_bytes):
    candidates = get_candidates(result)
    st.divider()
    st.header(f"{round_number}차 발표 분석 결과")

    with st.expander("발표 전문 보기", expanded=True):
        st.caption("노란색 부분은 보완 후보로 탐지된 발화입니다.")
        st.markdown(
            highlight_transcript(
                result["transcription_result"]["text"],
                candidates,
            ),
            unsafe_allow_html=True,
        )

    if not candidates:
        st.success("우선 코칭이 필요한 비유창성 후보 구간이 탐지되지 않았습니다.")
        st.caption(
            "자동 탐지 결과가 없더라도 발표 전문을 직접 점검한 뒤 "
            "전체 구조 메모를 작성하세요."
        )
    else:
        st.warning(f"우선 점검할 발화 구간이 {len(candidates)}개 탐지되었습니다.")
        for index, candidate in enumerate(candidates, start=1):
            render_candidate(
                candidate,
                index,
                round_number,
                audio_bytes,
            )

    render_structure_note(round_number)


def render_analysis_status(audio_file, transcriber):
    with st.status("발표를 분석하고 있습니다...", expanded=True) as status:
        active_slot = None
        active_label = None

        def show_stage(label):
            nonlocal active_slot, active_label
            if active_slot is not None:
                active_slot.write(f"✓ {active_label}")
            active_slot = st.empty()
            active_label = label
            active_slot.write(f"진행 중 · {label}")

        result = run_analysis(audio_file, transcriber, on_stage=show_stage)
        if active_slot is not None:
            active_slot.write(f"✓ {active_label}")
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


def missing_required_notes(round_number, result):
    missing = []
    for index, _candidate in enumerate(get_candidates(result), start=1):
        if not st.session_state.get(reflection_key(round_number, index), "").strip():
            missing.append(f"보완 후보 {index}의 부분 구조 메모")
    if not st.session_state.get(structure_note_key(round_number), "").strip():
        missing.append("발표 전체 구조 메모")
    return missing


def render_round_navigation(round_number, result):
    st.divider()
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if round_number > 1 and st.button(
            "이전 단계",
            icon=":material/arrow_back:",
            key=f"round_{round_number}_previous",
        ):
            go_to_step(round_number - 1)
            st.rerun()

        if result is not None:
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
                missing = missing_required_notes(round_number, result)
                if missing:
                    st.error("다음 항목을 작성해야 계속할 수 있습니다: " + ", ".join(missing))
                else:
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

    render_round_navigation(round_number, stored_result)


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
            st.markdown("**발표 전문**")
            st.caption("노란색 부분은 보완 후보로 탐지된 발화입니다.")
            st.markdown(
                highlight_transcript(
                    result["transcription_result"]["text"],
                    candidates,
                ),
                unsafe_allow_html=True,
            )
            if not candidates:
                st.success("보완 후보가 탐지되지 않았습니다.")
            for index, candidate in enumerate(candidates, start=1):
                render_comparison_candidate(
                    round_number,
                    candidate,
                    index,
                    st.session_state[audio_key(round_number)],
                )

    reflections = {}
    structure_notes = {}
    for round_number, result in enumerate(results, start=1):
        for index, _candidate in enumerate(get_candidates(result), start=1):
            reflections[(round_number, index)] = st.session_state.get(
                reflection_key(round_number, index),
                "",
            )
        structure_notes[round_number] = st.session_state.get(
            structure_note_key(round_number),
            "",
        )

    pdf_bytes = build_feedback_pdf(
        st.session_state.student_id,
        st.session_state.student_name,
        results,
        reflections,
        structure_notes,
    )
    st.subheader("최종 피드백 문서")
    st.write(
        "세 차례 발표 결과와 작성한 회고가 포함된 PDF를 개인 기기에 저장하세요."
    )
    st.download_button(
        "최종 피드백 PDF 다운로드",
        data=pdf_bytes,
        file_name=feedback_pdf_filename(
            st.session_state.student_id,
            st.session_state.student_name,
        ),
        mime="application/pdf",
        type="primary",
        icon=":material/download:",
        on_click="ignore",
        width="stretch",
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

st.title("🎤 발표 코칭 프로그램")
st.write(
    "발표 음성을 분석하여 발화 흐름이 흔들린 구간을 찾고, "
    "세 번의 연습 결과를 비교합니다."
)

if st.session_state.onboarding_step == 1:
    render_program_introduction()
    st.stop()

if st.session_state.onboarding_step == 2:
    render_usage_guide()
    st.stop()

if not st.session_state.student_info_confirmed:
    render_student_entry()
    st.stop()

st.caption(
    f"{st.session_state.student_id} · {st.session_state.student_name}"
)
transcriber = load_transcriber()
render_progress()
st.divider()

if st.session_state.current_step <= TOTAL_ROUNDS:
    render_round_page(st.session_state.current_step, transcriber)
else:
    render_comparison_page()
