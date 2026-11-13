"""A local, read-only dashboard: every incident's 72-hour clock, plus each packet.

Runs on the standard library's http.server and binds to 127.0.0.1 by default.
It never writes to the logs; use the CLI for that.
"""

from __future__ import annotations

import html
import re
from datetime import tzinfo
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .clock import DUE_SOON, NOTIFIED_LATE, OVERDUE, fmt_local
from .incident import load
from .log import IncidentLog, LogError
from .report import CSS, packet_blocks, packet_markdown, render_html

ID_RE = re.compile(r"^CI-\d{8}-[0-9A-F]{4}$")

COUNTDOWN_JS = """
<script>
(function () {
  function fmt(ms) {
    var neg = ms < 0; ms = Math.abs(ms);
    var m = Math.floor(ms / 60000), d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60);
    var s = (d ? d + "d " : "") + h + "h " + String(m % 60).padStart(2, "0") + "m";
    return neg ? "overdue by " + s : s + " left";
  }
  function tick() {
    document.querySelectorAll("[data-deadline]").forEach(function (el) {
      el.textContent = fmt(Number(el.dataset.deadline) - Date.now());
    });
  }
  tick(); setInterval(tick, 30000);
})();
</script>
"""

DASH_CSS = """
.status { font-weight: 600; white-space: nowrap; }
.status.bad { color: var(--warn); }
a { color: var(--accent); }
"""


def dashboard_html(home: Path, tz: tzinfo) -> str:
    e = html.escape
    rows = []
    for iid in IncidentLog.list_ids(home):
        inc = load(IncidentLog.open(home, iid))
        clock = inc.clock()
        bad = clock.status in (OVERDUE, DUE_SOON, NOTIFIED_LATE) or not (inc.integrity and inc.integrity.ok)
        if clock.deadline and clock.remaining is not None:
            left = f'<span data-deadline="{int(clock.deadline.timestamp() * 1000)}">{e(clock.describe(tz))}</span>'
        else:
            left = e(clock.describe(tz))
        rows.append(
            "<tr>"
            f'<td><a href="/incident/{e(iid)}">{e(iid)}</a></td>'
            f"<td>{e(inc.title)}{' (closed)' if inc.closed else ''}</td>"
            f"<td>{e(inc.outcome)}</td>"
            f'<td class="status{" bad" if bad else ""}">{e(clock.status)}</td>'
            f"<td>{e(fmt_local(clock.deadline, tz)) if clock.deadline else ''}</td>"
            f"<td>{left}</td>"
            "</tr>"
        )
    body = (
        "<h1>NCUA 72-hour cyber incident clock</h1>"
        f"<p>Logs in {e(str(home.resolve()))}. Times in {e(str(getattr(tz, 'key', tz)))}. Read-only; use the ncua72 command to add entries.</p>"
        '<p class="note">Not legal advice. Verify against the current 12 CFR 748.1(c) and NCUA guidance.</p>'
    )
    if rows:
        body += (
            "<table><thead><tr><th>Incident</th><th>Title</th><th>Determination</th>"
            "<th>Clock</th><th>Deadline</th><th>Time left</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )
    else:
        body += "<p>No incidents yet. Open one with <code>ncua72 new</code>.</p>"
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="refresh" content="300">'
        f"<title>Incident clock</title><style>{CSS}{DASH_CSS}</style></head>"
        f"<body><main>{body}</main>{COUNTDOWN_JS}</body></html>\n"
    )


def make_handler(home: Path, tz: tzinfo):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            try:
                if path == "/":
                    return self._send(200, dashboard_html(home, tz))
                m = re.match(r"^/incident/([^/]+)(/packet\.md)?$", path)
                if m and ID_RE.match(m.group(1)):
                    inc = load(IncidentLog.open(home, m.group(1)))
                    if m.group(2):
                        return self._send(200, packet_markdown(inc, tz), "text/markdown; charset=utf-8")
                    back = f'<p><a href="/">All incidents</a> · <a href="/incident/{inc.incident_id}/packet.md">Markdown</a> · print this page to save a PDF</p>'
                    return self._send(200, render_html(packet_blocks(inc, tz), f"Cyber Incident Record {inc.incident_id}", extra_body=back))
                return self._send(404, "<p>Not found</p>")
            except LogError:
                return self._send(404, "<p>No such incident</p>")

        def log_message(self, fmt: str, *args) -> None:
            pass

    return Handler


def serve(home: Path, tz: tzinfo, host: str = "127.0.0.1", port: int = 8072) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(home, tz))
    print(f"Dashboard at http://{host}:{port}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
