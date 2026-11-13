import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

from ncua72.cli import main
from ncua72.incident import load
from ncua72.log import IncidentLog, LogError
from ncua72.report import packet_html, packet_markdown
from ncua72.web import make_handler

LA = ZoneInfo("America/Los_Angeles")
IID = "CI-20261112-AB12"

ANSWERS = {
    "cyber_incident": {"answer": "yes", "rationale": "Ransomware encrypted the hosted core."},
    "good_faith_exclusion": {"answer": "no", "rationale": "Not contracted testing."},
    "substantial": {"answer": "yes", "rationale": "Core and online banking unavailable."},
    "prong_a": {"answer": "yes", "rationale": "Vital member services disrupted."},
    "prong_b": {"answer": "yes", "rationale": "Disruption caused by a cyberattack."},
    "prong_c": {"answer": "yes", "rationale": "Caused by compromise of the core provider."},
}


def run(home, *argv, prompt=None):
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(["--home", str(home), "--tz", "America/Los_Angeles", "--actor", "tester", *argv],
                    prompt=prompt or (lambda _: ""), interactive=prompt is not None)
    return code, out.getvalue()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        code, _ = run(self.home, "new", "--id", IID, "--title", "Core provider ransomware",
                      "--cu-name", "Example Federal Credit Union", "--charter", "99999",
                      "--reporter-name", "Pat Example", "--reporter-title", "CISO",
                      "--reporter-phone", "555-0100", "--reporter-email", "pat@example.org",
                      "--description", "Core provider reports ransomware.", "--sensitive", "unknown",
                      "--discovered", "2026-11-12 08:15")
        self.assertEqual(code, 0)

    def tearDown(self):
        self.tmp.cleanup()


class LogTests(Fixture):
    def test_chain_verifies(self):
        run(self.home, "note", IID, "Engaged IR firm.")
        r = IncidentLog.open(self.home, IID).verify()
        self.assertTrue(r.ok)
        self.assertEqual(r.entries, 2)

    def test_tamper_is_detected(self):
        run(self.home, "note", IID, "Engaged IR firm.")
        path = self.home / f"{IID}.jsonl"
        lines = path.read_text().splitlines()
        e = json.loads(lines[1])
        e["data"]["text"] = "Edited later."
        lines[1] = json.dumps(e, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")
        log = IncidentLog.open(self.home, IID)
        self.assertFalse(log.verify().ok)
        self.assertIn("changed", log.verify().problem)
        with self.assertRaises(LogError):
            log.append("note", {"text": "x"}, "tester")
        code, out = run(self.home, "verify", IID)
        self.assertEqual(code, 1)
        self.assertIn("FAILED", out)

    def test_deleted_entry_is_detected(self):
        run(self.home, "note", IID, "one")
        run(self.home, "note", IID, "two")
        path = self.home / f"{IID}.jsonl"
        lines = path.read_text().splitlines()
        path.write_text("\n".join([lines[0], lines[2]]) + "\n")
        self.assertFalse(IncidentLog.open(self.home, IID).verify().ok)

    def test_cannot_open_twice(self):
        with self.assertRaises(LogError):
            IncidentLog.open(self.home, IID).append("opened", {}, "tester")


class CLITests(Fixture):
    def assess(self):
        f = self.home / "answers.json"
        f.write_text(json.dumps(ANSWERS))
        return run(self.home, "assess", IID, "--answers", str(f))

    def test_full_flow(self):
        code, out = self.assess()
        self.assertEqual(code, 0)
        self.assertIn("REPORTABLE", out)
        run(self.home, "third-party", IID, "--at", "2026-11-12 07:40", "--party", "Example Core Co.")
        run(self.home, "believe", IID, "--at", "2026-11-12 09:30", "--basis", "Provider confirmed by phone.")
        inc = load(IncidentLog.open(self.home, IID))
        self.assertEqual(inc.clock().started_by, "third-party notice")
        code, out = run(self.home, "notified", IID, "--at", "2026-11-12 11:05", "--method", "phone",
                        "--reference", "Voicemail left")
        self.assertIn("before", out)
        code, out = run(self.home, "summary", IID)
        for needed in ("Example Federal Credit Union", "99999", "Pat Example", "CISO", "555-0100",
                       "pat@example.org", "Reasonable belief formed", "Description"):
            self.assertIn(needed, out)
        md = packet_markdown(load(IncidentLog.open(self.home, IID)), LA)
        self.assertIn("NOTIFIED ON TIME", md)
        self.assertIn("hash chain intact", md)
        self.assertIn("not legal advice", md)

    def test_interactive_walk(self):
        replies = iter(["yes", "it is", "no", "not testing", "yes", "big", "no", "x", "yes", "attack", "no", "y",
                        "2026-11-12 09:30", "SOC confirmed"])
        code, out = run(self.home, "assess", IID, prompt=lambda _: next(replies))
        self.assertEqual(code, 0)
        self.assertIn("Prong B", out)
        inc = load(IncidentLog.open(self.home, IID))
        self.assertIsNotNone(inc.belief_at)

    def test_rationale_required(self):
        f = self.home / "answers.json"
        f.write_text(json.dumps({"cyber_incident": "no"}))
        code, _ = run(self.home, "assess", IID, "--answers", str(f))
        self.assertEqual(code, 2)

    def test_html_has_no_tool_metadata(self):
        self.assess()
        page = packet_html(load(IncidentLog.open(self.home, IID)), LA, author="Jane Author")
        self.assertIn('<meta name="author" content="Jane Author">', page)
        self.assertNotIn("generator", page.lower())
        self.assertNotIn("generated by", page.lower())

    def test_status_lists(self):
        code, out = run(self.home, "status")
        self.assertIn(IID, out)
        self.assertIn("Clock not started", out)


class WebTests(Fixture):
    def test_dashboard_and_packet(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.home, LA))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            page = urllib.request.urlopen(base + "/").read().decode()
            self.assertIn(IID, page)
            page = urllib.request.urlopen(f"{base}/incident/{IID}").read().decode()
            self.assertIn("Cyber Incident Record", page)
            md = urllib.request.urlopen(f"{base}/incident/{IID}/packet.md").read().decode()
            self.assertTrue(md.startswith("# Cyber Incident Record"))
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(f"{base}/incident/../../etc/passwd")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
