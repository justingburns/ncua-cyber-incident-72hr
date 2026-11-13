"""Notification summary and examiner packet, rendered as Markdown or printable HTML."""

from __future__ import annotations

import html
from datetime import datetime, tzinfo
from typing import Any, Iterable

from .clock import fmt_local, from_iso, utcnow
from .incident import Incident
from .rule import DO_NOT_SEND, NOTICE_CHANNELS, SOURCES, TESTS

DISCLAIMER = (
    "This packet is a recordkeeping aid, not legal advice. It reflects the user's answers. "
    "Verify every determination against the current text of 12 CFR 748.1(c) and current NCUA "
    "guidance, and consult counsel where needed."
)

SENSITIVE_LABELS = {"yes": "Yes", "no": "No", "unknown": "Unknown at this time"}

# ---------------------------------------------------------------- blocks
# A packet is a list of simple blocks so the same content renders to Markdown and HTML.
#   ("h1"|"h2"|"h3", text) ("p", text) ("note", text) ("list", [items])
#   ("table", headers, rows) ("kv", [(label, value), ...]) ("pre", text)

Block = tuple


def notification_summary(inc: Incident, tz: tzinfo) -> str:
    """The short text to read or send at initial notification (23-CU-07's list)."""
    p = inc.profile
    clock = inc.clock()
    lines = [
        "NCUA CYBER INCIDENT NOTIFICATION (initial)",
        "",
        f"Credit union: {p.get('cu_name', '')}",
        f"Charter number: {p.get('charter', '')}",
        f"Reporting individual: {p.get('reporter_name', '')}, {p.get('reporter_title', '')}",
        f"Telephone: {p.get('reporter_phone', '')}",
        f"Email: {p.get('reporter_email', '')}",
        f"Reasonable belief formed: {fmt_local(inc.belief_at, tz)}",
    ]
    if inc.third_party_at:
        lines.append(
            f"Third-party notice received: {fmt_local(inc.third_party_at, tz)}"
            f" ({inc.third_party.get('party', '') if inc.third_party else ''})"
        )
    lines += [
        f"Description: {p.get('description', '')}",
        f"Affected functions: {p.get('affected_functions') or 'Under assessment'}",
        f"Sensitive information compromised: {SENSITIVE_LABELS.get(p.get('sensitive_data', 'unknown'), 'Unknown at this time')}",
        "",
        "-- For the person reporting (not part of the notice) --",
        f"Deadline: {fmt_local(clock.deadline, tz)}" if clock.deadline else "Deadline: clock not started",
        "How to notify:",
        *[f"  - {c}" for c in NOTICE_CHANNELS],
        "Leave out of the initial notice: " + ", ".join(DO_NOT_SEND) + ".",
    ]
    return "\n".join(lines)


def _answer_label(a: str) -> str:
    return {"yes": "Yes", "no": "No", "unsure": "Unsure"}.get(a, a)


def _event_text(e: dict[str, Any], tz: tzinfo) -> str:
    t, d = e["type"], e["data"]
    if t == "opened":
        return f"Incident opened: {d.get('title', '')}. Discovered {fmt_local(from_iso(d['discovered_at']), tz) if d.get('discovered_at') else 'time not recorded'}."
    if t == "assessment":
        return f"Reportability assessed: {d['outcome']}. {d.get('explanation', '')}"
    if t == "belief":
        return f"Reasonable belief recorded as of {fmt_local(from_iso(d['at']), tz)}. Basis: {d.get('basis', '')}"
    if t == "third_party_notice":
        return f"Notice from third party {d.get('party', '')} received {fmt_local(from_iso(d['at']), tz)}. {d.get('summary', '')}"
    if t == "note":
        when = f" (as of {fmt_local(from_iso(d['at']), tz)})" if d.get("at") else ""
        return f"Note{when}: {d.get('text', '')}"
    if t == "notified":
        ref = f", reference {d['reference']}" if d.get("reference") else ""
        return f"NCUA notified by {d.get('method', '')} at {fmt_local(from_iso(d['at']), tz)} by {d.get('by', '')}{ref}."
    if t == "closed":
        return f"Incident closed: {d.get('reason', '')}"
    return t


def packet_blocks(inc: Incident, tz: tzinfo, now: datetime | None = None, prepared_by: str | None = None) -> list[Block]:
    now = now or utcnow()
    p = inc.profile
    clock = inc.clock(now)
    integrity = inc.integrity
    b: list[Block] = []

    b.append(("h1", f"Cyber Incident Record: {inc.incident_id}"))
    b.append(("p", p.get("title", "")))
    b.append(("note", DISCLAIMER))
    b.append(("kv", [
        ("Credit union", f"{p.get('cu_name', '')} (charter {p.get('charter', '')})"),
        ("Determination", inc.outcome),
        ("72-hour clock", clock.status),
        ("Clock detail", clock.describe(tz)),
        ("Prepared", fmt_local(now, tz) + (f" by {prepared_by}" if prepared_by else "")),
    ]))

    b.append(("h2", "1. Incident profile"))
    b.append(("kv", [
        ("Discovered", fmt_local(from_iso(p["discovered_at"]), tz) if p.get("discovered_at") else "not recorded"),
        ("Description", p.get("description", "")),
        ("Affected functions", p.get("affected_functions") or "Under assessment"),
        ("Sensitive information compromised", SENSITIVE_LABELS.get(p.get("sensitive_data", "unknown"), "Unknown")),
        ("Reporting individual", f"{p.get('reporter_name', '')}, {p.get('reporter_title', '')}"),
        ("Contact", f"{p.get('reporter_phone', '')} / {p.get('reporter_email', '')}"),
    ]))

    b.append(("h2", "2. Reportability determination"))
    if not inc.assessment:
        b.append(("p", "No assessment recorded yet."))
    else:
        a = inc.assessment
        b.append(("p", f"Outcome: {a['outcome']}. {a.get('explanation', '')}"))
        b.append(("p", f"Assessed {fmt_local(from_iso(a['assessed_at']), tz)} by {a.get('assessed_by', '')}."))
        rows = []
        for t in TESTS:
            ans = a["answers"].get(t.key)
            if ans is None:
                continue
            rows.append([t.title, _answer_label(ans["answer"]), ans.get("rationale", ""), t.cite])
        b.append(("table", ["Test", "Answer", "Rationale", "Citation"], rows))
        if len(inc.assessments) > 1:
            b.append(("p", f"This incident was assessed {len(inc.assessments)} times. The latest assessment is shown; earlier ones are in the timeline."))

    b.append(("h2", "3. Notification clock"))
    b.append(("kv", [
        ("Reasonable belief formed", fmt_local(inc.belief_at, tz)),
        ("Basis for belief", inc.belief_basis or "not recorded"),
        ("Third-party notice received", fmt_local(inc.third_party_at, tz) + (f" from {inc.third_party.get('party')}" if inc.third_party else "")),
        ("Clock started by", clock.started_by or "not started"),
        ("Deadline (72 hours)", fmt_local(clock.deadline, tz)),
        ("Status", clock.describe(tz)),
    ]))

    b.append(("h2", "4. NCUA notification record"))
    if inc.notifications:
        rows = [[fmt_local(from_iso(n["at"]), tz), n.get("method", ""), n.get("by", ""), n.get("reference", "")] for n in inc.notifications]
        b.append(("table", ["When", "Method", "By", "Reference"], rows))
    else:
        b.append(("p", "No notification to NCUA recorded."))
    b.append(("p", "Notification summary prepared for NCUA:"))
    b.append(("pre", notification_summary(inc, tz)))

    b.append(("h2", "5. Timeline (append-only log)"))
    rows = [[str(e["seq"]), fmt_local(from_iso(e["recorded_at"]), tz), e.get("actor", ""), _event_text(e, tz)] for e in inc.entries]
    b.append(("table", ["#", "Recorded", "By", "Entry"], rows))

    b.append(("h2", "6. Log integrity"))
    if integrity and integrity.ok:
        b.append(("p", f"Verified: {integrity.entries} entries, hash chain intact. Final SHA-256: {integrity.last_hash}"))
    elif integrity:
        b.append(("p", f"VERIFICATION FAILED: {integrity.problem}. Do not rely on this record without review."))
    b.append(("p", "Each log entry stores the SHA-256 of the entry before it. Editing, deleting or reordering any entry breaks the chain."))
    if inc.closed:
        b.append(("p", f"Closed: {inc.closed.get('reason', '')} ({fmt_local(from_iso(inc.closed['at']), tz)})."))

    b.append(("h2", "7. Sources"))
    b.append(("list", [f"{name}: {url}" for name, url in SOURCES.values()]))
    return b


# ---------------------------------------------------------------- Markdown

def _md_cell(s: Any) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_markdown(blocks: Iterable[Block]) -> str:
    out: list[str] = []
    for blk in blocks:
        kind = blk[0]
        if kind in ("h1", "h2", "h3"):
            out.append("#" * int(kind[1]) + " " + blk[1])
        elif kind == "p":
            out.append(blk[1])
        elif kind == "note":
            out.append("> " + blk[1])
        elif kind == "list":
            out.append("\n".join(f"- {i}" for i in blk[1]))
        elif kind == "pre":
            out.append("```text\n" + blk[1] + "\n```")
        elif kind == "kv":
            rows = "\n".join(f"| {_md_cell(k)} | {_md_cell(v)} |" for k, v in blk[1])
            out.append("| Field | Value |\n|---|---|\n" + rows)
        elif kind == "table":
            headers, rows = blk[1], blk[2]
            lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
            lines += ["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows]
            out.append("\n".join(lines))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- HTML

CSS = """
:root { --ink:#1b2430; --muted:#5a6573; --line:#d7dce2; --accent:#0b4f8a; --warn:#8a1c0b; --bg:#ffffff; --panel:#f4f6f8; }
@media (prefers-color-scheme: dark) { :root { --ink:#e6e9ee; --muted:#a3adba; --line:#3a4350; --accent:#7db7ef; --warn:#ff8f7a; --bg:#14181d; --panel:#1d232a; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.6rem; margin: 0 0 4px; color: var(--accent); }
h2 { font-size: 1.15rem; margin: 28px 0 8px; padding-bottom: 4px; border-bottom: 2px solid var(--line); }
table { width:100%; border-collapse: collapse; margin: 8px 0; display:block; overflow-x:auto; }
th, td { text-align:left; vertical-align: top; padding: 6px 8px; border: 1px solid var(--line); }
th { background: var(--panel); }
table.kv td:first-child { width: 30%; color: var(--muted); }
.note { background: var(--panel); border-left: 4px solid var(--warn); padding: 8px 12px; color: var(--muted); }
pre { background: var(--panel); padding: 12px; white-space: pre-wrap; border: 1px solid var(--line); }
@media print { body { font-size: 11pt; background:#fff; color:#000; } main { max-width:none; padding:0; } h2 { break-after: avoid; } tr { break-inside: avoid; } }
"""


def render_html(blocks: Iterable[Block], title: str, author: str | None = None, extra_head: str = "", extra_body: str = "") -> str:
    e = html.escape
    parts: list[str] = []
    for blk in blocks:
        kind = blk[0]
        if kind in ("h1", "h2", "h3"):
            parts.append(f"<{kind}>{e(blk[1])}</{kind}>")
        elif kind == "p":
            parts.append(f"<p>{e(blk[1])}</p>")
        elif kind == "note":
            parts.append(f'<p class="note">{e(blk[1])}</p>')
        elif kind == "list":
            parts.append("<ul>" + "".join(f"<li>{e(i)}</li>" for i in blk[1]) + "</ul>")
        elif kind == "pre":
            parts.append(f"<pre>{e(blk[1])}</pre>")
        elif kind == "kv":
            rows = "".join(f"<tr><td>{e(str(k))}</td><td>{e(str(v))}</td></tr>" for k, v in blk[1])
            parts.append(f'<table class="kv"><tbody>{rows}</tbody></table>')
        elif kind == "table":
            head = "".join(f"<th>{e(h)}</th>" for h in blk[1])
            rows = "".join("<tr>" + "".join(f"<td>{e(str(c))}</td>" for c in r) + "</tr>" for r in blk[2])
            parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>")
    author_meta = f'<meta name="author" content="{e(author)}">' if author else ""
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{author_meta}<title>{e(title)}</title><style>{CSS}</style>{extra_head}</head>"
        f"<body><main>{extra_body}{''.join(parts)}</main></body></html>\n"
    )


def packet_markdown(inc: Incident, tz: tzinfo, now: datetime | None = None, prepared_by: str | None = None) -> str:
    return render_markdown(packet_blocks(inc, tz, now, prepared_by))


def packet_html(inc: Incident, tz: tzinfo, now: datetime | None = None, prepared_by: str | None = None, author: str | None = None) -> str:
    return render_html(packet_blocks(inc, tz, now, prepared_by), f"Cyber Incident Record {inc.incident_id}", author=author)


