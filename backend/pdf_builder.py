"""
Branded one-page PDF for a single team's ZenoFest event-data submission.
Mirrors the DOCX branding (purple/cyan) using ReportLab, which runs
anywhere (Render free tier) with no external converter.

Layout: event name as the title; an invisible (line-free) two-column
table holds Team ID|Team Name, Project Title|Leader Name, Email|College;
remaining submission fields print full-width below.
"""
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

PURPLE = HexColor("#6A0DAD")
PURPLE_LIGHT = HexColor("#8A2BE2")
CYAN = HexColor("#0091EA")
DARK = HexColor("#333333")
MUTED = HexColor("#777777")


def _styles():
    return {
        "brand": ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=14,
                                leading=16, textColor=PURPLE, alignment=TA_CENTER),
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=22,
                                leading=26, textColor=DARK, alignment=TA_CENTER),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=12,
                                  leading=16, textColor=PURPLE_LIGHT, spaceBefore=10),
        "cell_label": ParagraphStyle("cell_label", fontName="Helvetica-Bold",
                                     fontSize=10, textColor=PURPLE, leading=14),
        "cell_value": ParagraphStyle("cell_value", fontName="Helvetica",
                                     fontSize=10.5, textColor=DARK, leading=14),
        "field_label": ParagraphStyle("field_label", fontName="Helvetica-Bold",
                                      fontSize=10, textColor=CYAN, leading=14),
        "field_value": ParagraphStyle("field_value", fontName="Helvetica",
                                      fontSize=10.5, textColor=DARK, leading=14),
        "footer": ParagraphStyle("footer", fontName="Helvetica-Oblique", fontSize=8,
                                 textColor=MUTED, alignment=TA_CENTER),
    }


def _cell(label, value, st):
    """One cell of the invisible table = 'Label: value'."""
    return Paragraph(
        f'<font color="#6A0DAD"><b>{label}</b></font>:&nbsp;'
        f'<font color="#333333">{value}</font>',
        st["cell_value"])


def build_submission_pdf(submission):
    """Return PDF bytes for one team's submission.
    `submission` keys: team_id, team_name, tech_event, leader_name, college,
                      email, submitted_at, form_data, field_labels"""
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="ZenoFest 2K26 - Event Submission",
    )

    event = submission.get("tech_event") or ""
    labels = submission.get("field_labels") or {}
    form_data = submission.get("form_data") or {}
    project_title = str(form_data.get("project_title") or form_data.get("title") or "")

    story = [
        Paragraph("ZENOFEST 2K26", st["brand"]),
        Paragraph((event + " SUBMISSION").upper(), st["title"]),
        HRFlowable(width="100%", thickness=2, color=PURPLE, spaceBefore=6, spaceAfter=12),
    ]

    # Invisible two-column table (no borders, no shading).
    pair = lambda left, right: [
        _cell(left[0], left[1], st),
        _cell(right[0], right[1], st),
    ]
    table_data = [
        pair(("Team ID", submission.get("team_id", "")),
             ("Team Name", submission.get("team_name", ""))),
        pair(("Project Title", project_title),
             ("Leader Name", submission.get("leader_name", ""))),
        pair(("Email", submission.get("email", "")),
             ("College", submission.get("college", ""))),
    ]
    table = Table(table_data, colWidths=[79 * mm, 79 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    story.append(Spacer(1, 4))

    story.append(Paragraph("SUBMISSION DATA", st["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=CYAN, spaceBefore=0, spaceAfter=6))

    already_shown = {"project_title", "title"}
    for key, value in form_data.items():
        if key in already_shown:
            continue
        label = labels.get(key, key.replace("_", " ").title())
        story.append(Paragraph(f'<b><font color="#0091EA">{label}</font>:</b>&nbsp;'
                               f'<font color="#333333">{value}</font>',
                               st["field_value"]))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MUTED, spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        "This is an official record of your ZenoFest 2K26 event-data submission. "
        "Keep this document safe and show it at the fest if required.",
        st["footer"]))

    doc.build(story)
    return buf.getvalue()


def pdf_filename(team_id, tech_event):
    safe = "".join(ch for ch in (tech_event or "") if ch.isalnum() or ch in " _-")
    team = (team_id or "team").replace("/", "-")
    stamp = datetime.now().strftime("%Y%m%d")
    return f"ZenoFest_{safe}_{team}_{stamp}.pdf"