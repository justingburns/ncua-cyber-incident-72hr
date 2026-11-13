import io
import json
import re
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

from ncua72 import pdf
from ncua72.cli import main
from ncua72.incident import load
from ncua72.log import IncidentLog
from ncua72.report import packet_blocks
from ncua72.rule import NOT_REPORTABLE, REPORTABLE, determine
from ncua72.scenarios import SCENARIOS, by_key
from ncua72.tabletop import (
    DrillLog,
    SimClock,
    after_action_markdown,
    after_action_pdf,
    finish_drill,
    load_drill,
    scenario_start,
    start_drill,
)
from ncua72.web import make_handler

LA = ZoneInfo("America/Los_Angeles")
NOW = datetime(2026, 11, 13, 19, 0, tzinfo=timezone.utc)  # Fri Nov 13, 2026 11:00 AM PST


def run(home, drills, *argv, prompt=None):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(["--home", str(home), "--drills", str(drills), "--tz", "America/Los_Angeles",
                     "--actor", "tester", *argv],
                    prompt=prompt or (lambda _: ""), interactive=prompt is not None)
    return code, out.getvalue(), err.getvalue()


class Script:
    """Feeds replies to prompts. Each reply also moves a fake real-time clock forward."""

    def __init__(self, replies, seconds_per_reply=0.0):
        self.replies = iter(replies)
        self.step = seconds_per_reply
        self.t = 0.0

    def __call__(self, _label):
        self.t += self.step
        return next(self.replies)

    def clock(self):
        return self.t


def walk(*pairs):
    """Replies for the reportability walk: answer, rationale, answer, rationale..."""
    out = []
    for a in pairs:
        out += [a, f"Because {a}."]
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home, self.drills = root / "incidents", root / "drills"

    def tearDown(self):
        self.tmp.cleanup()

    def drill(self, key, script, speed=0.0):
        d = start_drill(by_key(key), self.drills, LA, "tester", speed=speed, facilitator="Fac Ilitator",
                        participants="CEO, CISO, Compliance", now=NOW, real_clock=script.clock,
                        out=lambda _: None)
        d.play(script)
        return d, finish_drill(d)


class ScenarioTests(unittest.TestCase):
    def test_answer_keys_reach_the_expected_outcome(self):
        for s in SCENARIOS:
            outcome, _ = determine({k: v.answer for k, v in s.answer_key.items()})
            self.assertEqual(outcome, s.expected_outcome, s.key)
            self.assertTrue(1 <= s.belief_inject <= len(s.injects), s.key)
            minutes = [i.minutes for i in s.injects]
            self.assertEqual(minutes, sorted(minutes), s.key)
            played = {a for acts in s.model_play.values() for a in acts}
            self.assertIn("assess", played, s.key)
            if s.expected_outcome == REPORTABLE:
                self.assertIn("notify", played, s.key)

    def test_no_real_institutions(self):
        for s in SCENARIOS:
            for inj in s.injects:
                if inj.third_party:
                    self.assertTrue(inj.third_party.startswith("Example "), inj.third_party)

    def test_scenario_starts_on_its_weekday(self):
        for s in SCENARIOS:
            start = scenario_start(s, LA, NOW).astimezone(LA)
            self.assertEqual(start.weekday(), s.weekday)
            self.assertEqual(f"{start:%H:%M}", s.start)
            self.assertLessEqual(start.date(), NOW.astimezone(LA).date())


class SimClockTests(unittest.TestCase):
    def test_runs_at_speed_and_never_goes_back(self):
        t = [0.0]
        start = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)
        c = SimClock(start, 60, real_clock=lambda: t[0])
        t[0] = 120  # two real minutes
        self.assertEqual(c.now(), start + timedelta(hours=2))
        # The team spent past the next inject's scheduled time, so it arrives late.
        self.assertEqual(c.advance_to(start + timedelta(hours=1)), start + timedelta(hours=2))
        self.assertEqual(c.advance_to(start + timedelta(hours=5)), start + timedelta(hours=5))

    def test_negative_speed_refused(self):
        with self.assertRaises(ValueError):
            SimClock(datetime.now(timezone.utc), -1)


class DrillTests(Base):
    def test_walkthrough_scores_full_marks(self):
        for s in SCENARIOS:
            code, out, _ = run(self.home, self.drills, "tabletop", "run", s.key, "--walkthrough",
                               "--format", "md", "--out", str(self.drills.parent / f"{s.key}.md"))
            self.assertEqual(code, 0, out)
            self.assertIn("Score: 100 of 100", out)
        code, out, _ = run(self.home, self.drills, "tabletop", "history")
        self.assertEqual(out.count("score 100/100"), len(SCENARIOS))

    def test_good_interactive_drill(self):
        replies = ["c", "c",                       # injects 1 and 2
                   "b", "Provider confirmed encryption.",
                   "a", *walk("yes", "no", "yes", "yes", "yes", "yes"),
                   "n", "phone", "Voicemail at 1-833-CYBERCU",
                   "l", "CEO briefed; insurer called.",
                   "c",                            # end of inject 3
                   "", "", "", ""]                 # Enter through the rest
        d, sc = self.drill("core-ransomware", Script(replies))
        self.assertEqual(sc.total, 100)
        inc = load(d.log)
        self.assertEqual(inc.notifications[0]["reference"][:9], "SIMULATED")
        md = after_action_markdown(load_drill(self.drills, d.log.incident_id), LA)
        self.assertIn("EXERCISE ONLY", md)
        self.assertIn("Fac Ilitator", md)
        self.assertIn("CEO briefed", md)
        self.assertIn("hash chain intact", md)
        self.assertIn("not legal advice", md)

    def test_team_that_never_notifies(self):
        d, sc = self.drill("core-ransomware", Script(["", "", "", "", "", "", ""]))
        self.assertEqual(sc.team_outcome, "NO ASSESSMENT")
        self.assertEqual(sc.total, 0)
        self.assertTrue(any("never notified" in p.detail for p in sc.parts))

    def test_dithering_costs_simulated_time(self):
        # Speed 60: every reply takes 30 real seconds, so 30 simulated minutes.
        # The team waits until the last inject (T+73h), past the deadline that started at T+0.
        replies = ["c"] * 6 + ["b", "Finally sure.", "a", *walk("yes", "no", "yes", "yes", "yes", "yes"),
                              "n", "phone", "", "c"]
        d, sc = self.drill("core-ransomware", Script(replies, seconds_per_reply=30), speed=60)
        timing = next(p for p in sc.parts if p.name.startswith("NCUA notice"))
        self.assertEqual(timing.points, 0)
        self.assertIn("after the deadline", timing.detail)
        self.assertEqual(sc.true_start_by, "third-party notice")
        inject_times = [e["data"]["at"] for e in load(d.log).entries if e["type"] == "inject"]
        self.assertEqual(inject_times, sorted(inject_times))

    def test_wrong_call_on_not_reportable_scenario(self):
        replies = ["c", "c", "b", "Seems bad.", "a", *walk("yes", "no", "yes", "yes", "yes", "no"),
                   "n", "phone", "", "c", "c", "c"]
        d, sc = self.drill("ddos-mitigated", Script(replies))
        self.assertEqual(sc.expected_outcome, NOT_REPORTABLE)
        self.assertEqual(sc.team_outcome, REPORTABLE)
        self.assertLess(sc.total, 70)
        self.assertTrue(any("substantial" in f for f in sc.findings))

    def test_undetermined_gets_partial_credit(self):
        replies = ["b", "Vendor notice.", "a", *walk("yes", "no", "unsure", "yes", "no", "yes"),
                   "e"]
        d, sc = self.drill("vendor-exposure", Script(replies))
        self.assertEqual(sc.team_outcome, "UNDETERMINED")
        self.assertEqual(sc.parts[0].points, 15)
        self.assertTrue(d.ended_early)

    def test_bad_scenario_and_speed(self):
        code, _, err = run(self.home, self.drills, "tabletop", "run", "nope")
        self.assertEqual(code, 2)
        self.assertIn("core-ransomware", err)
        code, _, err = run(self.home, self.drills, "tabletop", "run", "bec-wire", "--speed", "-5")
        self.assertEqual(code, 2)

    def test_cli_interactive_run(self):
        replies = ["Fac Ilitator", "CEO, CISO",
                   "c", "b", "Mailbox rule and foreign sign-ins.",
                   "a", *walk("yes", "no", "yes", "yes", "no", "no"),
                   "notify", "secure-email", "Sent via Secure Email Message Center", "",
                   "", "", "", ""]
        out_file = self.drills.parent / "cli.md"
        code, out, err = run(self.home, self.drills, "tabletop", "run", "bec-wire", "--speed", "0",
                             "--format", "md", "--out", str(out_file), prompt=Script(replies))
        self.assertEqual(code, 0, err)
        self.assertIn("EXERCISE ONLY", out)
        self.assertIn("Score: 100 of 100", out)
        self.assertIn("Fac Ilitator", out_file.read_text())

    def test_list(self):
        code, out, _ = run(self.home, self.drills, "tabletop", "list")
        for s in SCENARIOS:
            self.assertIn(s.key, out)


class SeparationTests(Base):
    def setUp(self):
        super().setUp()
        code, out, _ = run(self.home, self.drills, "tabletop", "run", "bec-wire", "--walkthrough", "--format", "md",
                           "--out", str(self.drills.parent / "aar.md"))
        self.assertEqual(code, 0)
        self.tid = re.search(r"Drill (TT-\d{8}-[0-9A-F]{4})", out).group(1)

    def test_drills_never_show_as_incidents(self):
        self.assertTrue((self.drills / f"{self.tid}.jsonl").exists())
        self.assertEqual(IncidentLog.list_ids(self.drills), [])
        code, out, _ = run(self.home, self.drills, "status")
        self.assertNotIn(self.tid, out)
        self.assertIn("No incidents", out)

    def test_real_commands_refuse_drills(self):
        for argv in (("packet", self.tid), ("summary", self.tid), ("note", self.tid, "x"), ("status", self.tid),
                     ("verify", self.tid)):
            code, _, err = run(self.home, self.drills, *argv)
            self.assertEqual(code, 2, argv)
            self.assertIn("tabletop", err)

    def test_reserved_prefix(self):
        code, _, err = run(self.home, self.drills, "new", "--id", "TT-20261113-0000", "--title", "x",
                           "--cu-name", "y", "--description", "z")
        self.assertEqual(code, 2)
        self.assertIn("reserved", err)

    def test_same_folder_refused(self):
        code, _, err = run(self.drills, self.drills, "tabletop", "history")
        self.assertEqual(code, 2)
        self.assertIn("separate", err)

    def test_copied_drill_log_cannot_pass_as_real(self):
        self.home.mkdir(parents=True, exist_ok=True)
        fake = "CI-20261113-AAAA"
        shutil.copy(self.drills / f"{self.tid}.jsonl", self.home / f"{fake}.jsonl")
        code, out, _ = run(self.home, self.drills, "status")
        self.assertIn("skipped", out)
        code, _, err = run(self.home, self.drills, "packet", fake)
        self.assertEqual(code, 2)
        self.assertFalse(IncidentLog.open(self.home, fake).verify().ok)
        with self.assertRaises(ValueError):
            packet_blocks(load(IncidentLog.open(self.home, fake)), LA)

    def test_tampered_drill_is_flagged(self):
        path = self.drills / f"{self.tid}.jsonl"
        lines = path.read_text().splitlines()
        e = json.loads(lines[-1])
        e["data"]["score"] = 1000
        lines[-1] = json.dumps(e, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")
        code, out, _ = run(self.home, self.drills, "tabletop", "history")
        self.assertIn("FAILED VERIFICATION", out)
        md = after_action_markdown(load_drill(self.drills, self.tid), LA)
        self.assertIn("VERIFICATION FAILED", md)

    def test_dashboard_lists_drills_apart(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.home, LA, self.drills))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            page = urllib.request.urlopen(base + "/").read().decode()
            self.assertIn("Tabletop drills", page)
            self.assertIn(self.tid, page)
            page = urllib.request.urlopen(f"{base}/drill/{self.tid}").read().decode()
            self.assertIn("After-Action Report", page)
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(f"{base}/incident/{self.tid}")
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(f"{base}/drill/../../etc/passwd")
        finally:
            server.shutdown()
            server.server_close()


@unittest.skipUnless(pdf.available(), "reportlab not installed")
class ReportPDFTests(Base):
    def test_pdf_metadata_names_no_software(self):
        out = self.drills.parent / "aar.pdf"
        code, _, _ = run(self.home, self.drills, "tabletop", "run", "vendor-exposure", "--walkthrough",
                         "--format", "pdf", "--author", "Justin Burns, MBA", "--out", str(out))
        self.assertEqual(code, 0)
        data = out.read_bytes()
        self.assertTrue(data.startswith(b"%PDF-"))
        ref = re.search(rb"/Info (\d+) 0 R", data).group(1)
        obj = re.search(rb"\n" + ref + rb" 0 obj\s*<<(.*?)>>\s*endobj", data, re.S).group(1)
        meta = {k.decode(): v.decode("latin-1") for k, v in re.findall(rb"/(\w+)\s*\(([^)]*)\)", obj)}
        self.assertEqual(meta["Author"], "Justin Burns, MBA")
        self.assertEqual(meta["Creator"], "")
        self.assertEqual(meta["Producer"], "")
        self.assertIn("Tabletop", meta["Title"])
        for word in (b"reportlab", b"generated by", b"python", b"ncua72"):
            self.assertNotIn(word, data.lower())

    def test_report_rebuilds(self):
        d, _ = Base.drill(self, "bec-wire", Script(["e"]))
        data = after_action_pdf(load_drill(self.drills, d.log.incident_id), LA, author="Fac Ilitator")
        self.assertTrue(data.startswith(b"%PDF-"))
        out = self.drills.parent / "again.pdf"
        code, _, _ = run(self.home, self.drills, "tabletop", "report", d.log.incident_id, "--format", "pdf",
                         "--out", str(out))
        self.assertEqual(code, 0)
        self.assertTrue(out.read_bytes().startswith(b"%PDF-"))


class DrillLogTests(Base):
    def test_ids_and_types(self):
        log = DrillLog.create(self.drills)
        self.assertTrue(log.incident_id.startswith("TT-"))
        log.append("opened", {"exercise": True}, "t")
        log.append("inject", {"n": 1}, "t")
        with self.assertRaises(Exception):
            IncidentLog.create(self.home, "CI-20261113-0001").append("inject", {}, "t")


if __name__ == "__main__":
    unittest.main()
