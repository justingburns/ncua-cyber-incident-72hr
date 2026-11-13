"""PDF rendering of the examiner packet.

Optional: needs the reportlab package (`pip install reportlab`). Everything else
in ncua72 uses only the standard library.

The PDF's Author is whatever the caller passes. Creator and Producer are left
blank, and the library's own header comment is blanked out, so the file names
no software in its metadata.
"""

from __future__ import annotations

import io
import re
from datetime import datetime, tzinfo
from typing import Iterable
from xml.sax.saxutils import escape

from .incident import Incident
from .report import DISCLAIMER, Block, packet_blocks

INSTALL_HINT = "PDF export needs the reportlab package. Install it with: py -m pip install reportlab  (or: pip install reportlab)"


class PDFUnavailable(Exception):
    pass


def available() -> bool:
    try:
        import reportlab  # noqa: F401
    except ImportError:
        return False
    return True


# The library writes comment lines naming itself: one after %PDF-x.y and one in
# the trailer. They are comments, so blanking them byte-for-byte with spaces
# keeps every xref offset valid.
_TOOL_COMMENT = re.compile(rb"(?m)^(%[\x80-\xff]{0,4}) ?ReportLab[^\n]*$", re.IGNORECASE)


def _scrub_comments(data: bytes) -> bytes:
    def blank(m: re.Match) -> bytes:
        return m.group(1) + b" " * (len(m.group(0)) - len(m.group(1)))

    return _TOOL_COMMENT.sub(blank, data)


def _col_widths(headers: list[str], rows: list[list[str]], total: float, measure) -> list[float]:
    """Give each column room for its longest word, then share the rest by content length.

    measure(text, bold) returns the printed width of text in points.
    """
    pad = 10.0
    minimum, weight = [], []
    for i, h in enumerate(headers):
        cells = [str(r[i]) for r in rows]
        word = max([measure(w, True) for w in str(h).split()] + [measure(w, False) for c in cells for w in c.split()] + [0])
        minimum.append(word + pad)
        weight.append(min(max(len(c) for c in cells + [str(h)]), 70))
    floor = sum(minimum)
    if floor >= total:
        return [total * m / floor for m in minimum]
    extra = total - floor
    wsum = sum(weight) or 1
    return [m + extra * w / wsum for m, w in zip(minimum, weight)]


def render_pdf(blocks: Iterable[Block], title: str, author: str | None, footer: str) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise PDFUnavailable(INSTALL_HINT) from exc

    ink = colors.HexColor("#1b2430")
    accent = colors.HexColor("#0b4f8a")
    line = colors.HexColor("#c9d0d8")
    panel = colors.HexColor("#f1f4f7")
    warn = colors.HexColor("#8a1c0b")

    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=12.5, textColor=ink, alignment=TA_LEFT)
    cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=10.5, spaceBefore=0, spaceAfter=0)
    cell_head = ParagraphStyle("cellhead", parent=cell, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=accent, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=ink, spaceBefore=12, spaceAfter=4, keepWithNext=1)
    note = ParagraphStyle("note", parent=body, fontSize=8.5, leading=11, textColor=warn, backColor=panel, borderPadding=(5, 6, 5, 6), spaceBefore=4, spaceAfter=8)
    mono = ParagraphStyle("mono", parent=body, fontName="Courier", fontSize=8, leading=10, backColor=panel, borderPadding=6, spaceBefore=4, spaceAfter=8)

    page_w, page_h = LETTER
    margin = 0.7 * inch
    width = page_w - 2 * margin

    def measure(text: str, bold: bool) -> float:
        return stringWidth(text, "Helvetica-Bold" if bold else "Helvetica", cell.fontSize)

    def p(text: str, style) -> Paragraph:
        return Paragraph(escape(str(text)), style)

    grid = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, line),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])

    story = []
    for blk in blocks:
        kind = blk[0]
        if kind == "h1":
            story.append(p(blk[1], h1))
        elif kind in ("h2", "h3"):
            story.append(p(blk[1], h2))
        elif kind == "p":
            story.append(p(blk[1], body))
        elif kind == "note":
            story.append(p(blk[1], note))
        elif kind == "list":
            for item in blk[1]:
                story.append(Paragraph("&bull; " + escape(str(item)), body))
        elif kind == "pre":
            story.append(Paragraph(escape(blk[1]).replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;"), mono))
        elif kind == "kv":
            data = [[p(k, cell_head), p(v, cell)] for k, v in blk[1]]
            t = Table(data, colWidths=[1.9 * inch, width - 1.9 * inch])
            t.setStyle(grid)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), panel)]))
            story.append(t)
            story.append(Spacer(1, 4))
        elif kind == "table":
            headers, rows = blk[1], blk[2]
            data = [[p(h, cell_head) for h in headers]] + [[p(c, cell) for c in r] for r in rows]
            t = Table(data, colWidths=_col_widths(headers, rows, width, measure), repeatRows=1)
            t.setStyle(grid)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), panel)]))
            story.append(t)
            story.append(Spacer(1, 4))

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#5a6573"))
        canvas.drawString(margin, 0.45 * inch, footer)
        canvas.drawRightString(page_w - margin, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0.7 * inch,
        bottomMargin=0.75 * inch,
        title=title,
        author=author or "",
        subject="NCUA cyber incident notification record",
        creator="",
        producer="",
        keywords="",
    )
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return _scrub_comments(buf.getvalue())


def packet_pdf(
    inc: Incident,
    tz: tzinfo,
    now: datetime | None = None,
    prepared_by: str | None = None,
    author: str | None = None,
) -> bytes:
    footer = f"{inc.incident_id}  |  {DISCLAIMER.split('.')[0]}. Verify against current NCUA guidance."
    return render_pdf(
        packet_blocks(inc, tz, now, prepared_by),
        f"Cyber Incident Record {inc.incident_id}",
        author,
        footer,
    )
