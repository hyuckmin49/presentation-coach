# scoring.py

# ============================================================
# D. 통합 / Speech Event / Rule-based Scoring
# ============================================================

FILLER_TOKENS = {
    "어",
    "음",
    "아",
    "으",
}


# ------------------------------------------------------------
# 기본 유틸
# ------------------------------------------------------------

def overlaps(start1, end1, start2, end2):
    """
    두 시간 구간이 실제로 겹치는지 확인.
    단순히 경계값이 같은 경우는 겹침으로 보지 않음.
    """
    return max(start1, start2) < min(end1, end2)


def is_filler_word(word):
    """
    Whisper가 직접 전사한 filler 판정.

    exact token만 사용하여 과탐을 줄인다.
    예: '음과'는 filler로 세지 않음.
    """

    cleaned = word.strip(".,?! ")

    return cleaned in FILLER_TOKENS


# ------------------------------------------------------------
# B → filler events
# ------------------------------------------------------------

def extract_filler_events(transcription_result):
    """
    Whisper word timestamp에서 filler 추출.
    """

    events = []

    for word_info in transcription_result["words"]:

        if is_filler_word(word_info["word"]):

            events.append({
                "start": word_info["start"],
                "end": word_info["end"],
                "text": word_info["word"],
            })

    return events


def extract_repeated_weakener_events(language_result):
    """한 문장 안에서 두 번째 이후에 등장한 '약간'을 찾는다."""

    events = []
    for sentence in language_result.get("sentences", []):
        words = [
            word
            for chunk in sentence.get("chunks", [])
            for word in chunk.get("words", [])
        ]
        weakener_words = [
            word
            for word in words
            if word.get("word", "").strip(".,?! ") == "약간"
        ]
        for word in weakener_words[1:]:
            events.append({
                "start": word["start"],
                "end": word["end"],
                "text": word["word"],
                "sentence_id": sentence["sentence_id"],
            })
    return events


# ------------------------------------------------------------
# C → 모든 chunk 평탄화
# ------------------------------------------------------------

def flatten_chunks(language_result):
    """
    sentence 내부의 chunk들을 하나의 리스트로 평탄화.
    """

    chunks = []

    for sentence in language_result["sentences"]:

        sentence_id = sentence["sentence_id"]

        for chunk in sentence["chunks"]:

            chunks.append({
                "sentence_id": sentence_id,
                "chunk_id": chunk["chunk_id"],
                "start": chunk["start"],
                "end": chunk["end"],
                "text": chunk["text"],
            })

    return chunks


# ------------------------------------------------------------
# A → pause 추출
# ------------------------------------------------------------

def extract_pauses(audio_result):
    """
    A 결과에서 pause 목록 추출.

    audio_analysis.json의 구조가
    {"pauses": [...]} 라는 현재 설계를 기준으로 한다.
    """

    return audio_result.get("pauses", [])


# ------------------------------------------------------------
# pause 위치 판정
# ------------------------------------------------------------

def locate_pause(pause, chunks):
    """
    pause가

    WITHIN_CHUNK
    BETWEEN_CHUNKS
    BETWEEN_SENTENCES

    중 어디에 있는지 판정한다.
    """

    pause_start = pause["start"]
    pause_end = pause["end"]

    pause_mid = (pause_start + pause_end) / 2


    # 1. chunk 내부 pause
    for chunk in chunks:

        if (
            chunk["start"]
            < pause_mid
            < chunk["end"]
        ):
            return {
                "position": "WITHIN_CHUNK",
                "chunk": chunk,
            }


    # 2. 인접 chunk 사이
    for i in range(len(chunks) - 1):

        left = chunks[i]
        right = chunks[i + 1]

        if (
            left["end"]
            <= pause_mid
            <= right["start"]
        ):

            if left["sentence_id"] == right["sentence_id"]:

                return {
                    "position": "BETWEEN_CHUNKS",
                    "left_chunk": left,
                    "right_chunk": right,
                }

            else:

                return {
                    "position": "BETWEEN_SENTENCES",
                    "left_chunk": left,
                    "right_chunk": right,
                }


    return {
        "position": "OUTSIDE",
    }


# ------------------------------------------------------------
# Speech Event 생성
# ------------------------------------------------------------

def build_speech_events(
    audio_result,
    transcription_result,
    language_result
):
    """
    의미 chunk를 기본 Speech Event 단위로 사용한다.

    한 chunk 내부에서 발생한
    - internal pause
    - filler
    - repetition/restart

    를 하나의 event로 통합한다.

    chunk 사이에서 발생한 filler / repetition도
    transition event로 별도 생성한다.
    """

    pauses = extract_pauses(audio_result)

    fillers = extract_filler_events(
        transcription_result
    )

    repeated_weakener_events = extract_repeated_weakener_events(
        language_result
    )
    fillers.extend(repeated_weakener_events)

    repetitions = language_result.get(
        "repetition_restart_events",
        []
    )

    chunks = flatten_chunks(language_result)

    events = []


    # ========================================================
    # 1. 각 chunk 내부 Speech Event
    # ========================================================

    for chunk in chunks:

        internal_pauses = []

        for pause in pauses:

            location = locate_pause(
                pause,
                chunks
            )

            if (
                location["position"]
                == "WITHIN_CHUNK"
                and location["chunk"]["sentence_id"]
                == chunk["sentence_id"]
                and location["chunk"]["chunk_id"]
                == chunk["chunk_id"]
            ):
                internal_pauses.append(pause)


        # filler는 midpoint를 기준으로
        # 하나의 chunk에만 배정
        chunk_fillers = []

        for filler in fillers:

            filler_mid = (
                filler["start"]
                + filler["end"]
            ) / 2

            if (
                chunk["start"]
                <= filler_mid
                < chunk["end"]
            ):
                chunk_fillers.append(filler)


        # filler와 겹치는 pause는
        # 동일 발화 사건의 일부일 가능성이 있으므로
        # 별도 pause 신호로 중복 계산하지 않음
        filtered_internal_pauses = []

        for pause in internal_pauses:

            overlaps_filler = False

            for filler in chunk_fillers:

                if overlaps(
                    pause["start"],
                    pause["end"],
                    filler["start"],
                    filler["end"]
                ):
                    overlaps_filler = True
                    break

            if not overlaps_filler:
                filtered_internal_pauses.append(pause)

        internal_pauses = filtered_internal_pauses


        chunk_repetitions = [
            repetition
            for repetition in repetitions
            if overlaps(
                repetition["start"],
                repetition["end"],
                chunk["start"],
                chunk["end"]
            )
        ]

        chunk_repeated_weakeners = [
            event
            for event in repeated_weakener_events
            if overlaps(
                event["start"],
                event["end"],
                chunk["start"],
                chunk["end"]
            )
        ]


        signals = {
            "internal_pause":
                len(internal_pauses) > 0,

            "filler":
                len(chunk_fillers) > 0,

            "repetition_restart":
                len(chunk_repetitions) > 0,

            "repeated_weakener":
                len(chunk_repeated_weakeners) > 0,
        }


        events.append({
            "event_type": "CHUNK",

            "sentence_id":
                chunk["sentence_id"],

            "chunk_id":
                chunk["chunk_id"],

            "start":
                chunk["start"],

            "end":
                chunk["end"],

            "text":
                chunk["text"],

            "signals":
                signals,

            "details": {
                "internal_pauses":
                    internal_pauses,

                "fillers":
                    chunk_fillers,

                "repetition_restart":
                    chunk_repetitions,

                "repeated_weakener":
                    chunk_repeated_weakeners,
            }
        })


    # ========================================================
    # 2. chunk / sentence 사이 transition events
    # ========================================================

    for i in range(len(chunks) - 1):

        left = chunks[i]
        right = chunks[i + 1]

        transition_start = left["end"]
        transition_end = right["start"]

        # 시간 간격이 음수면 skip
        if transition_end < transition_start:
            continue


        # transition filler도 midpoint 기준
        transition_fillers = []

        for filler in fillers:

            filler_mid = (
                filler["start"]
                + filler["end"]
            ) / 2

            if (
                transition_start
                <= filler_mid
                < transition_end
            ):
                transition_fillers.append(
                    filler
                )


        transition_repetitions = [
            repetition
            for repetition in repetitions
            if overlaps(
                repetition["start"],
                repetition["end"],
                transition_start,
                transition_end
            )
        ]

        transition_repeated_weakeners = [
            event
            for event in repeated_weakener_events
            if overlaps(
                event["start"],
                event["end"],
                transition_start,
                transition_end
            )
        ]


        # pause는 boundary에서 단독 점수 없음
        boundary_pauses = []

        for pause in pauses:

            pause_mid = (
                pause["start"]
                + pause["end"]
            ) / 2

            if (
                transition_start
                <= pause_mid
                <= transition_end
            ):
                boundary_pauses.append(
                    pause
                )


        # filler / repetition이 전혀 없으면
        # transition event 생성하지 않음
        if (
            len(transition_fillers) == 0
            and len(transition_repetitions) == 0
        ):
            continue


        if (
            left["sentence_id"]
            == right["sentence_id"]
        ):
            position = "BETWEEN_CHUNKS"

        else:
            position = "BETWEEN_SENTENCES"


        events.append({
            "event_type":
                "TRANSITION",

            "position":
                position,

            "start":
                transition_start,

            "end":
                transition_end,

            "left_text":
                left["text"],

            "right_text":
                right["text"],

            "signals": {
                # 경계 pause는 점수에 포함하지 않음
                "internal_pause":
                    False,

                "filler":
                    len(transition_fillers) > 0,

                "repetition_restart":
                    len(transition_repetitions) > 0,

                "repeated_weakener":
                    len(transition_repeated_weakeners) > 0,
            },

            "details": {
                "boundary_pauses":
                    boundary_pauses,

                "fillers":
                    transition_fillers,

                "repetition_restart":
                    transition_repetitions,

                "repeated_weakener":
                    transition_repeated_weakeners,
            }
        })


    return events


# ------------------------------------------------------------
# 점수 계산
# ------------------------------------------------------------

def score_event(event):
    """
    사용자 설계 점수 규칙:

    signal 0개 → 0점
    signal 1개 → 1점
    signal 2개 → 3점
    signal 3개 → 5점
    """

    signals = event["signals"]

    signal_count = sum(
        1
        for value in signals.values()
        if value
    )


    if signal_count == 0:
        score = 0

    elif signal_count == 1:
        score = 1

    elif signal_count == 2:
        score = 3

    else:
        score = 5


    if score == 0:
        classification = "GENERAL"

    elif score <= 2:
        classification = "BORDERLINE"

    else:
        classification = "DISFLUENCY_CANDIDATE"


    reasons = []

    if signals["internal_pause"]:
        reasons.append(
            "의미 단위 내부에서 pause 발생"
        )

    if signals["filler"]:
        reasons.append(
            "간투사 사용"
        )

    if signals["repetition_restart"]:
        reasons.append(
            "반복 또는 재시작 발생"
        )

    if signals.get("repeated_weakener"):
        reasons.append(
            "한 문장 안에서 '약간' 반복 사용"
        )


    event["signal_count"] = signal_count
    event["score"] = score
    event["classification"] = classification
    event["reasons"] = reasons

    return event


# ------------------------------------------------------------
# 코칭 문구 생성
# ------------------------------------------------------------

def add_coaching_prompt(event):

    if (
        event["classification"]
        != "DISFLUENCY_CANDIDATE"
    ):
        event["coaching_prompt"] = None
        return event


    if event["event_type"] == "CHUNK":

        event["coaching_prompt"] = (
            "이 의미 단위에서 전달하려던 "
            "핵심 개념과 내용 간 관계를 다시 정리한 뒤, "
            "대본을 보지 않고 자신의 언어로 재발화해 보세요."
        )

    else:

        event["coaching_prompt"] = (
            "앞 내용과 다음 내용이 어떤 관계로 "
            "이어지는지 다시 정리한 뒤, "
            "두 의미 단위를 자연스럽게 연결하여 "
            "재발화해 보세요."
        )

    return event


# ------------------------------------------------------------
# D 전체 실행
# ------------------------------------------------------------

def analyze_scoring(
    audio_result,
    transcription_result,
    language_result
):

    print("\n[D1] Speech Event 생성")

    events = build_speech_events(
        audio_result,
        transcription_result,
        language_result
    )


    print(
        f"[D1] 생성된 event 수: "
        f"{len(events)}"
    )


    print("\n[D2] rule-based scoring")

    scored_events = []

    for event in events:

        event = score_event(event)
        event = add_coaching_prompt(event)

        scored_events.append(event)


    candidates = [
        event
        for event in scored_events
        if (
            event["classification"]
            == "DISFLUENCY_CANDIDATE"
        )
    ]


    print(
        f"[D2] 비유창성 후보: "
        f"{len(candidates)}"
    )


    return {
        "events": scored_events,
        "coaching_candidates": candidates,
    }
