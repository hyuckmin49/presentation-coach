import re
from html import escape


def candidate_fragments(candidate):
    if candidate.get("event_type") == "CHUNK":
        values = [candidate.get("text", "")]
    else:
        values = [
            candidate.get("left_text", ""),
            candidate.get("right_text", ""),
        ]
    return [value.strip() for value in values if value and value.strip()]


def split_highlighted_transcript(transcript, candidates):
    fragments = {
        fragment
        for candidate in candidates
        for fragment in candidate_fragments(candidate)
    }
    if not fragments:
        return [(transcript, False)]

    pattern = re.compile(
        "(" + "|".join(re.escape(value) for value in sorted(fragments, key=len, reverse=True)) + ")",
        flags=re.IGNORECASE,
    )
    return [
        (part, index % 2 == 1)
        for index, part in enumerate(pattern.split(transcript))
        if part
    ]


def highlight_transcript(transcript, candidates):
    """발표 전문에서 보완 후보와 일치하는 문구를 안전한 HTML로 강조한다."""

    highlighted = []
    for part, is_candidate in split_highlighted_transcript(transcript, candidates):
        safe_part = escape(part).replace("\n", "<br/>")
        if is_candidate:
            highlighted.append(
                '<mark style="background-color:#FFE08A; color:inherit; '
                'padding:0.08em 0.18em; border-radius:0.2em">'
                f"{safe_part}</mark>"
            )
        else:
            highlighted.append(safe_part)
    return "".join(highlighted)


def highlight_transcript_pdf(transcript, candidates):
    """ReportLab 문단에서 사용할 보완 후보 강조 마크업을 만든다."""

    highlighted = []
    for part, is_candidate in split_highlighted_transcript(transcript, candidates):
        safe_part = escape(part).replace("\n", "<br/>")
        if is_candidate:
            highlighted.append(
                f'<font backColor="#FFE08A">{safe_part}</font>'
            )
        else:
            highlighted.append(safe_part)
    return "".join(highlighted)
