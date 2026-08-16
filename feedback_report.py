import io
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from transcript_highlight import highlight_transcript_pdf


FONT_NAME = "PresentationCoachKorean"
FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    Path("C:/Windows/Fonts/malgun.ttf"),
)


def register_korean_font():
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return FONT_NAME

    for font_path in FONT_CANDIDATES:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))
            return FONT_NAME

    raise RuntimeError(
        "한국어 PDF 글꼴을 찾을 수 없습니다. "
        "Windows에서는 맑은 고딕, Linux에서는 fonts-nanum이 필요합니다."
    )


def sanitize_filename_part(value):
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", value.strip())
    return cleaned.strip("_") or "미입력"


def feedback_pdf_filename(student_id, student_name):
    safe_id = sanitize_filename_part(student_id)
    safe_name = sanitize_filename_part(student_name)
    return f"{safe_id}_{safe_name}_발표피드백.pdf"


def candidate_text(candidate):
    if candidate.get("event_type") == "CHUNK":
        return candidate.get("text", "")
    return (
        f"{candidate.get('left_text', '')} "
        f"→ {candidate.get('right_text', '')}"
    ).strip()


def paragraph_text(value):
    return escape(str(value or "")).replace("\n", "<br/>")


def build_styles(font_name):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "KoreanTitle",
            parent=base["Title"],
            fontName=font_name,
            fontSize=20,
            leading=27,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1F3A5F"),
            spaceAfter=8 * mm,
        ),
        "heading": ParagraphStyle(
            "KoreanHeading",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=14,
            leading=20,
            textColor=colors.HexColor("#1F3A5F"),
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
        ),
        "subheading": ParagraphStyle(
            "KoreanSubheading",
            parent=base["Heading3"],
            fontName=font_name,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#334E68"),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "KoreanBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=15,
            wordWrap="CJK",
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "KoreanSmall",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=12,
            wordWrap="CJK",
            textColor=colors.HexColor("#52606D"),
        ),
    }


def add_page_number(canvas, document):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#7B8794"))
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f"{document.page}쪽")
    canvas.restoreState()


def build_feedback_pdf(
    student_id,
    student_name,
    results,
    reflections,
    structure_notes=None,
):
    """세 차례 발표 분석 결과를 하나의 한국어 PDF 바이트로 만든다."""

    if len(results) != 3:
        raise ValueError("PDF 생성에는 정확히 3회의 발표 결과가 필요합니다.")

    structure_notes = structure_notes or {}
    font_name = register_korean_font()
    styles = build_styles(font_name)
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="발표 코칭 최종 피드백",
        author="발표 코칭 프로그램",
    )
    story = []

    story.append(Paragraph("발표 코칭 최종 피드백", styles["title"]))
    info_table = Table(
        [
            ["학번", Paragraph(paragraph_text(student_id), styles["body"])],
            ["이름", Paragraph(paragraph_text(student_name), styles["body"])],
        ],
        colWidths=[32 * mm, 120 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF2F8")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1F3A5F")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BCCCDC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 7 * mm))

    counts = [
        len(result["scoring_result"]["coaching_candidates"])
        for result in results
    ]
    summary_table = Table(
        [
            ["1차 보완 후보", "2차 보완 후보", "3차 보완 후보"],
            [str(counts[0]), str(counts[1]), str(counts[2])],
        ],
        colWidths=[52 * mm, 52 * mm, 52 * mm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F7FA")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BCCCDC")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 4 * mm))

    difference = counts[2] - counts[0]
    if difference < 0:
        summary = f"3차 발표의 보완 후보가 1차보다 {abs(difference)}개 감소했습니다."
    elif difference > 0:
        summary = f"3차 발표의 보완 후보가 1차보다 {difference}개 늘었습니다."
    else:
        summary = "1차와 3차 발표의 보완 후보 수가 같습니다."
    story.append(Paragraph(paragraph_text(summary), styles["body"]))
    story.append(
        Paragraph(
            "이 문서는 멈춤, 간투사, 반복·재시작을 바탕으로 한 규칙 기반 "
            "음성 분석 결과입니다. 발표 내용의 논리성과 완성도 평가는 포함하지 않습니다.",
            styles["small"],
        )
    )
    story.append(
        Paragraph(
            "각 회차에는 발표 전문, 보완 후보로 거론된 발화, "
            "사용자가 직접 정리한 내용이 함께 수록됩니다.",
            styles["small"],
        )
    )

    for round_number, result in enumerate(results, start=1):
        story.append(PageBreak())
        candidates = result["scoring_result"]["coaching_candidates"]
        transcript = result["transcription_result"].get("text", "")

        story.append(Paragraph(f"{round_number}차 발표", styles["heading"]))
        story.append(
            Paragraph(
                f"보완 후보: {len(candidates)}개",
                styles["subheading"],
            )
        )
        story.append(Paragraph("발표 전문", styles["subheading"]))
        if candidates:
            story.append(
                Paragraph(
                    "노란색 부분은 보완 후보로 탐지된 발화입니다.",
                    styles["small"],
                )
            )
        story.append(
            Paragraph(
                highlight_transcript_pdf(transcript, candidates),
                styles["body"],
            )
        )

        if not candidates:
            story.append(
                Paragraph(
                    "우선 코칭이 필요한 비유창성 후보 구간이 탐지되지 않았습니다.",
                    styles["body"],
                )
            )
        for candidate_index, candidate in enumerate(candidates, start=1):
            story.append(
                Paragraph(f"보완 후보 {candidate_index}", styles["subheading"])
            )
            story.append(
                Paragraph(
                    f"구간: {candidate['start']:.2f}s - {candidate['end']:.2f}s "
                    f"/ 점수: {candidate['score']}점",
                    styles["body"],
                )
            )
            story.append(
                Paragraph(
                    "보완 후보로 거론된 부분: "
                    f"{paragraph_text(candidate_text(candidate))}",
                    styles["body"],
                )
            )
            reasons = ", ".join(candidate.get("reasons", [])) or "없음"
            story.append(
                Paragraph(f"탐지 근거: {paragraph_text(reasons)}", styles["body"])
            )
            for event in candidate.get("details", {}).get("sustained_vowel", []):
                story.append(
                    Paragraph(
                        "음 끌기 세부 구간: "
                        f"{event['start']:.2f}s - {event['end']:.2f}s "
                        f"/ 전사 단어: {paragraph_text(event['text'])}",
                        styles["body"],
                    )
                )
            if candidate.get("coaching_prompt"):
                story.append(
                    Paragraph(
                        f"코칭 제안: {paragraph_text(candidate['coaching_prompt'])}",
                        styles["body"],
                    )
                )
            reflection = reflections.get((round_number, candidate_index), "").strip()
            story.append(
                Paragraph(
                    "부분 구조 메모: "
                    + paragraph_text(reflection or "작성하지 않음"),
                    styles["body"],
                )
            )
            story.append(Spacer(1, 2 * mm))

        story.append(Paragraph("발표 전체 구조 메모", styles["subheading"]))
        story.append(
            Paragraph(
                paragraph_text(
                    structure_notes.get(round_number, "").strip()
                    or "작성하지 않음"
                ),
                styles["body"],
            )
        )

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )
    return buffer.getvalue()
