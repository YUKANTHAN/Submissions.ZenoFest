"""
Branded one-page PDF for a single team's ZenoFest event-data submission.
Mirrors the DOCX branding (purple/cyan) using ReportLab, which runs
anywhere (Render free tier) with no external converter.

Layout: event name as the title; an invisible (line-free) two-column
table holds Team ID|Team Name, Project Title|Leader Name, Email|College;
remaining submission fields print full-width below.
Additional Links are rendered as a table.
"""
import io
import json
from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape

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


def _esc(v):
    """Escape a value for safe inclusion in ReportLab Paragraph markup."""
    return _xml_escape(str(v))


def _cell(label, value, st):
    """One cell of the invisible table = 'Label: value'."""
    return Paragraph(
        f'<font color="#6A0DAD"><b>{_esc(label)}</b></font>:&nbsp;'
        f'<font color="#333333">{_esc(value)}</font>',
        st["cell_value"])


def _parse_links(value):
    """Parse links field which may be JSON array of {label, url} or plain string."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [(item.get("label", ""), item.get("url", "")) for item in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: treat as single URL
    return [("", str(value))]


def _build_links_table(links, st):
    """Build a table for additional links with Label and URL columns."""
    if not links:
        return None
    table_data = [[Paragraph('<b><font color="#0091EA">Label</font></b>', st["cell_value"]),
                   Paragraph('<b><font color="#0091EA">URL</font></b>', st["cell_value"])]]
    for label, url in links:
        esc_url = _esc(url)
        table_data.append([
            Paragraph(f'<font color="#333333">{_esc(label)}</font>', st["cell_value"]),
            Paragraph(f'<font color="#0091EA"><a href="{esc_url}">{esc_url}</a></font>', st["cell_value"]),
        ])
    table = Table(table_data, colWidths=[55 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.5, MUTED),
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f0f0f0")),
    ]))
    return table


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
        # Handle additional_links as a table
        if key == "additional_links" and value:
            links = _parse_links(value)
            if links:
                link_table = _build_links_table(links, st)
                if link_table:
                    story.append(Paragraph(f'<b><font color="#0091EA">{_esc(label)}</font>:</b>', st["field_value"]))
                    story.append(Spacer(1, 3))
                    story.append(link_table)
                    story.append(Spacer(1, 6))
                    continue
        story.append(Paragraph(f'<b><font color="#0091EA">{_esc(label)}</font>:</b>&nbsp;'
                               f'<font color="#333333">{_esc(value)}</font>',
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