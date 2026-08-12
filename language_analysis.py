# language_analysis.py

import re
from difflib import SequenceMatcher

FILLER_TOKENS = {
    "어",
    "음",
    "아",
    "으",
}


def is_filler_phrase(text: str):
    tokens = normalize_text(text).split()

    if not tokens:
        return False

    return all(
        token in FILLER_TOKENS
        for token in tokens
    )


# ============================================================
# C1. 문장 분리
# ============================================================

def split_sentences_from_whisper(transcription_result: dict):
    """
    Whisper word timestamp를 이용해 문장 단위로 분리한다.
    . ? ! 를 문장 경계로 사용한다.
    """

    words = transcription_result["words"]

    sentences = []
    current_words = []
    sentence_id = 0

    for word_info in words:
        current_words.append(word_info)

        word = word_info["word"]

        if word.endswith((".", "?", "!")):

            sentence_text = " ".join(
                w["word"] for w in current_words
            ).strip()

            sentences.append({
                "sentence_id": sentence_id,
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "text": sentence_text,
                "words": current_words.copy()
            })

            sentence_id += 1
            current_words = []

    # 문장부호 없이 끝난 마지막 부분
    if current_words:
        sentence_text = " ".join(
            w["word"] for w in current_words
        ).strip()

        sentences.append({
            "sentence_id": sentence_id,
            "start": current_words[0]["start"],
            "end": current_words[-1]["end"],
            "text": sentence_text,
            "words": current_words.copy()
        })

    return sentences


# ============================================================
# C2. 규칙 기반 의미 chunking
# ============================================================

# 의미 관계가 전환될 가능성이 높은 연결 표현
CONNECTIVE_WORDS = {
    "하지만",
    "그러나",
    "그런데",
    "따라서",
    "그러므로",
    "그래서",
    "때문에",
    "반면",
    "즉",
    "또한",
    "그리고",
    "다만",
    "결국",
    "이후",
    "먼저",
    "반대로",
}

# 한국어 연결 어미
CONNECTIVE_ENDINGS = (
    "지만",
    "는데",
    "으며",
    "면서",
    "므로",
    "기에",
    "어서",
    "아서",
    "때문에",
    "고",
)


def is_chunk_boundary(word: str):
    """
    현재 단어 뒤에서 의미 chunk를 끊을지 판단한다.

    True:
        해당 단어까지 하나의 chunk로 보고 경계를 생성.
    """

    cleaned = word.strip()

    # 쉼표가 붙어 있으면 강한 후보
    if cleaned.endswith(","):
        return True

    # 연결 표현 자체
    plain = cleaned.rstrip(".,?!")

    if plain in CONNECTIVE_WORDS:
        return True

    # 연결 어미
    for ending in CONNECTIVE_ENDINGS:
        if plain.endswith(ending):
            return True

    return False


def semantic_chunk_sentence(sentence: dict):
    """
    하나의 문장을 규칙 기반 의미 chunk로 분해한다.

    핵심 원칙:
    - 너무 짧은 chunk 생성 방지
    - 연결어/연결어미를 의미 관계 경계 후보로 사용
    - timestamp는 Whisper word 정보에서 직접 유지
    """

    words = sentence["words"]

    chunks = []
    current_words = []

    chunk_id = 0

    # 너무 작은 chunk 방지
    MIN_WORDS_PER_CHUNK = 2

    for word_info in words:

        current_words.append(word_info)

        word = word_info["word"]

        boundary = is_chunk_boundary(word)

        if boundary and len(current_words) >= MIN_WORDS_PER_CHUNK:

            chunk_text = " ".join(
                w["word"] for w in current_words
            ).strip()

            chunks.append({
                "chunk_id": chunk_id,
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "text": chunk_text,
                "words": current_words.copy()
            })

            chunk_id += 1
            current_words = []

    # 남은 부분
    if current_words:

        # 마지막 조각이 너무 짧으면 이전 chunk에 병합
        if (
            len(current_words) < MIN_WORDS_PER_CHUNK
            and len(chunks) > 0
        ):
            chunks[-1]["words"].extend(current_words)
            chunks[-1]["end"] = current_words[-1]["end"]

            chunks[-1]["text"] = " ".join(
                w["word"] for w in chunks[-1]["words"]
            ).strip()

        else:
            chunk_text = " ".join(
                w["word"] for w in current_words
            ).strip()

            chunks.append({
                "chunk_id": chunk_id,
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "text": chunk_text,
                "words": current_words.copy()
            })

    return chunks


def build_semantic_structure(sentences: list):
    """
    모든 문장을 의미 chunk로 분해한다.
    """

    results = []

    for sentence in sentences:

        print(
            f"[C2] 의미 청킹 중: "
            f"Sentence {sentence['sentence_id']}"
        )

        chunks = semantic_chunk_sentence(sentence)

        results.append({
            "sentence_id": sentence["sentence_id"],
            "start": sentence["start"],
            "end": sentence["end"],
            "text": sentence["text"],
            "chunks": chunks
        })

    return results


# ============================================================
# C3. repetition / restart 탐지
# ============================================================

def normalize_text(text: str):
    """
    반복 탐지를 위해 문장부호 제거.
    """
    text = re.sub(r"[.,?!]", "", text)
    return text.strip()


def text_similarity(a: str, b: str):
    """
    문자열 유사도 0~1.
    """

    return SequenceMatcher(
        None,
        normalize_text(a),
        normalize_text(b)
    ).ratio()


def detect_repetition_restart(
    words: list,
    similarity_threshold=0.75
):
    """
    인접한 1~3단어 표현의 반복/재시작 탐지.

    예:
    이를 바탕 → 이를 바탕으로
    이 모델 → 이 모델은
    """

    events = []
    max_ngram = 3

    for n in range(1, max_ngram + 1):

        for i in range(len(words) - 2 * n + 1):

            first = words[i:i+n]
            second = words[i+n:i+2*n]

            first_text = " ".join(
                w["word"] for w in first
            )

            second_text = " ".join(
                w["word"] for w in second
            )

            similarity = text_similarity(
                first_text,
                second_text
            )


            # filler 자체의 반복은 repetition/restart로 세지 않음
            if (
                  is_filler_phrase(first_text)
                   and is_filler_phrase(second_text)
            ):
                 continue
            
            if similarity >= similarity_threshold:

                events.append({
                    "start": first[0]["start"],
                    "end": second[-1]["end"],
                    "first_text": first_text,
                    "second_text": second_text,
                    "similarity": round(similarity, 3),
                    "repetition_or_restart": True
                })

    return events


# ============================================================
# C 전체 실행
# ============================================================

def analyze_language(transcription_result: dict):

    print("\n[C1] 문장 분리 시작")

    sentences = split_sentences_from_whisper(
        transcription_result
    )

    print(
        f"[C1] 문장 수: {len(sentences)}"
    )

    print("\n[C2] 규칙 기반 의미 구조 분석 시작")

    semantic_structure = build_semantic_structure(
        sentences
    )

    print("\n[C3] 반복/재시작 탐지 시작")

    repetitions = detect_repetition_restart(
        transcription_result["words"]
    )

    return {
        "sentences": semantic_structure,
        "repetition_restart_events": repetitions
    }