"""Tabletop exercise mode: timed practice drills on a simulated clock.

A drill plays one of the built-in scenarios as a series of injects. At each
inject the team can assess reportability, record a reasonable belief, notify
the (simulated) NCUA, or log a note. A simulated clock moves forward with the
injects and, by default, also with real time: one real minute is one simulated
hour, so a team that debates for ten minutes spends ten hours of its 72.

Drills are kept apart from real incidents on purpose:
  * they live in their own folder (--drills, default ./drills), never --home;
  * their ids start with TT-, real incidents with CI-;
  * the first log entry is marked "exercise": true, and the real commands refuse
    to open, list or build an examiner packet from such a log.

The result is an after-action report (PDF, Markdown or HTML) with a score.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any, Callable

from .clock import fmt_duration, fmt_local, from_iso, parse_time, to_iso, utcnow
from .incident import Incident, load
from .log import EVENT_TYPES, IncidentLog, LogError
from .report import Block, render_html, render_markdown
from .rule import (
    DEADLINE_HOURS,
    NO,
    REPORTABLE,
    SOURCES,
    TESTS,
    UNDETERMINED,
    YES,
    determine,
    relevant_tests,
)
from .scenarios import SCENARIOS, Scenario, by_key

AAR_DISCLAIMER = (
    "This report is a training aid, not legal advice. The answer keys apply 12 CFR 748.1(c) and NCUA "
    "Letter 23-CU-07 to fictional facts; a facilitator may reasonably disagree with a call. Verify real "
    "determinations against the current rule and NCUA guidance, and consult counsel where needed."
)
EXERCISE_BANNER = "EXERCISE ONLY. This is a tabletop drill, not a real incident. Nothing here is reported to the NCUA."
DEFAULT_SPEED = 60.0  # simulated seconds per real second: 1 real minute = 1 simulated hour

Prompt = Callable[[str], str]
Out = Callable[[str], None]


class DrillLog(IncidentLog):
    """Same append-only, hash-chained log, with its own id prefix and event types."""

    PREFIX = "TT"
    TYPES = EVENT_TYPES + ("inject", "drill_end")


def is_exercise_id(incident_id: str) -> bool:
    return incident_id.upper().startswith(DrillLog.PREFIX + "-")


# ------------------------------------------------------------------ simulated clock

class SimClock:
    """Simulated time that steps forward at each inject and runs at `speed` x real time between them."""

    def __init__(self, start: datetime, speed: float, real_clock: Callable[[], float] = time.monotonic):
        if speed < 0:
            raise ValueError("speed can't be negative")
        self.speed = speed
        self._real = real_clock
        self._base = start
        self._real_base = real_clock()

    def now(self) -> datetime:
        return self._base + timedelta(seconds=(self._real() - self._real_base) * self.speed)

    def advance_to(self, at: datetime) -> datetime:
        """Jump to `at`, or stay later if the team already spent past it."""
        self._base = max(at, self.now())
        self._real_base = self._real()
        return self._base


def scenario_start(scn: Scenario, tz: tzinfo, now: datetime | None = None) -> datetime:
    """The most recent date on or before today that falls on the scenario's weekday, at its start time."""
    now = (now or utcnow()).astimezone(tz)
    day = now.date() - timedelta(days=(now.weekday() - scn.weekday) % 7)
    hh, mm = (int(x) for x in scn.start.split(":"))
    local = datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
    return parse_time(local.isoformat(), tz)


# ------------------------------------------------------------------ running a drill

ACTIONS = (
    ("continue", "next inject (or press Enter)"),
    ("assess", "walk the reportability tests"),
    ("belief", "record that the credit union now reasonably believes a reportable incident occurred"),
    ("notify", "notify the NCUA (simulated)"),
    ("log", "log a decision or note"),
    ("status", "show the simulated clock"),
    ("end", "end the drill now and score it"),
)


def _choose(prompt: Prompt, out: Out) -> str:
    menu = "  ".join(f"[{name[0]}]{name[1:]}" for name, _ in ACTIONS)
    while True:
        value = prompt(f"Action: {menu}\n> ").strip().lower()
        if not value:
            return "continue"
        for name, _ in ACTIONS:
            if name.startswith(value):
                return name
        out("  Type c, a, b, n, l, s or e.")


@dataclass
class Drill:
    scenario: Scenario
    log: DrillLog
    tz: tzinfo
    clock: SimClock
    actor: str
    out: Out = print
    ended_early: bool = False

    def state(self) -> Incident:
        return load(self.log)

    def append(self, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        data = dict(data)
        data.setdefault("real_at", to_iso(utcnow()))
        return self.log.append(kind, data, self.actor)

    def show_clock(self) -> None:
        now = self.clock.now()
        inc = self.state()
        self.out(f"   Simulated time: {fmt_local(now, self.tz)}")
        self.out(f"   Clock: {inc.clock(now).describe(self.tz)}")
        if inc.assessment:
            self.out(f"   Team's determination so far: {inc.outcome}")

    # -- actions
    def do_assess(self, prompt: Prompt | None, key_answers: bool = False) -> None:
        from .cli import _walk

        if key_answers:
            answers = {k: {"answer": v.answer, "rationale": "Walkthrough: answer key played."} for k, v in self.scenario.answer_key.items()}
        else:
            answers = _walk(prompt, self.out)  # type: ignore[arg-type]
        outcome, explanation = determine({k: v["answer"] for k, v in answers.items()})
        at = self.clock.now()
        self.append("assessment", {
            "answers": answers,
            "outcome": outcome,
            "explanation": explanation,
            "assessed_at": to_iso(at),
            "assessed_by": self.actor,
        })
        self.out(f"   Team determination: {outcome}. {explanation}")

    def do_belief(self, basis: str) -> None:
        self.append("belief", {"at": to_iso(self.clock.now()), "basis": basis})
        self.out(f"   {self.state().clock(self.clock.now()).describe(self.tz)}")

    def do_notify(self, method: str, reference: str) -> None:
        self.append("notified", {
            "at": to_iso(self.clock.now()),
            "method": method,
            "by": self.actor,
            "reference": ("SIMULATED, exercise only. " + reference).strip(),
        })
        self.out(f"   {self.state().clock(self.clock.now()).describe(self.tz)}")

    def do_note(self, text: str) -> None:
        self.append("note", {"at": to_iso(self.clock.now()), "text": text})

    # -- the loop
    def play(self, prompt: Prompt, walkthrough: bool = False) -> None:
        from .cli import _ask, _ask_choice

        scn = self.scenario
        start = scenario_start_from_log(self.state())
        for n, inj in enumerate(scn.injects, 1):
            at = self.clock.advance_to(start + timedelta(minutes=inj.minutes))
            self.append("inject", {"n": n, "at": to_iso(at), "headline": inj.headline, "text": inj.text})
            if inj.third_party:
                self.append("third_party_notice", {"at": to_iso(at), "party": inj.third_party, "summary": inj.headline})
            self.out("")
            self.out(f"=== INJECT {n} of {len(scn.injects)}  T+{fmt_duration(at - start)}  {fmt_local(at, self.tz)}  [EXERCISE]")
            self.out(f"    {inj.headline}")
            self.out(f"    {inj.text}")
            self.show_clock()
            if walkthrough:
                for action in scn.model_play.get(n, ()):
                    self._model_action(action, n)
                continue
            while True:
                action = _choose(prompt, self.out)
                if action == "continue":
                    break
                if action == "end":
                    self.ended_early = n < len(scn.injects)
                    return
                if action == "assess":
                    self.do_assess(prompt)
                elif action == "belief":
                    self.do_belief(_ask(prompt, "   What formed that belief"))
                elif action == "notify":
                    method = _ask_choice(prompt, "   Method", ("phone", "secure-email", "other"))
                    self.do_notify(method, _ask(prompt, "   Reference or what was said", required=False))
                elif action == "log":
                    self.do_note(_ask(prompt, "   Note"))
                elif action == "status":
                    self.show_clock()

    def _model_action(self, action: str, n: int) -> None:
        if action == "assess":
            self.out("   [walkthrough] Team walks the tests using the answer key.")
            self.do_assess(None, key_answers=True)
        elif action == "belief":
            self.out("   [walkthrough] Team records its reasonable belief.")
            self.do_belief(f"Facts in inject {n}: {self.scenario.injects[n - 1].headline}.")
        elif action == "notify":
            self.out("   [walkthrough] Team calls 1-833-CYBERCU (simulated).")
            self.do_notify("phone", "Incident commander gave name, charter, contact and a basic description.")
        elif action == "note":
            self.out("   [walkthrough] Team logs a decision.")
            self.do_note(f"Decision logged after inject {n}: {self.scenario.injects[n - 1].headline}.")


def scenario_start_from_log(inc: Incident) -> datetime:
    return from_iso(inc.profile["sim_start"])


def start_drill(
    scn: Scenario,
    drills_home: Path,
    tz: tzinfo,
    actor: str,
    speed: float = DEFAULT_SPEED,
    facilitator: str = "",
    participants: str = "",
    now: datetime | None = None,
    real_clock: Callable[[], float] = time.monotonic,
    out: Out = print,
) -> Drill:
    sim_start = scenario_start(scn, tz, now)
    log = DrillLog.create(Path(drills_home))
    profile = {
        "exercise": True,
        "scenario": scn.key,
        "scenario_title": scn.title,
        "title": f"EXERCISE: {scn.title}",
        "description": scn.description,
        "affected_functions": scn.affected_functions,
        "sensitive_data": "unknown",
        "discovered_at": to_iso(sim_start),
        "sim_start": to_iso(sim_start),
        "speed": speed,
        "facilitator": facilitator,
        "participants": participants,
        **_example_cu(),
    }
    log.append("opened", profile, actor)
    return Drill(scn, log, tz, SimClock(sim_start, speed, real_clock), actor, out)


def _example_cu() -> dict[str, str]:
    from .scenarios import EXAMPLE_CU

    return dict(EXAMPLE_CU)


def finish_drill(drill: Drill) -> "Score":
    inc = drill.state()
    end = drill.clock.now()
    sc = score(drill.scenario, inc, end, drill.tz)
    drill.append("drill_end", {
        "at": to_iso(end),
        "ended_early": drill.ended_early,
        "score": sc.total,
        "team_outcome": sc.team_outcome,
        "expected_outcome": drill.scenario.expected_outcome,
    })
    return sc


# ------------------------------------------------------------------ scoring

@dataclass
class Part:
    name: str
    points: int
    max: int
    detail: str


@dataclass
class Score:
    total: int
    parts: list[Part]
    findings: list[str]
    team_outcome: str
    expected_outcome: str
    true_start: datetime | None
    true_start_by: str | None
    deadline: datetime | None
    notified_at: datetime | None
    test_rows: list[list[str]] = field(default_factory=list)

    @property
    def rating(self) -> str:
        if self.total >= 90:
            return "Strong"
        if self.total >= 70:
            return "Solid, with gaps to work on"
        return "Needs work"


def _entries(inc: Incident, kind: str) -> list[dict[str, Any]]:
    return [e["data"] for e in inc.entries if e["type"] == kind]


def _inject_time(inc: Incident, n: int) -> datetime | None:
    for d in _entries(inc, "inject"):
        if d["n"] == n:
            return from_iso(d["at"])
    return None


def score(scn: Scenario, inc: Incident, end: datetime, tz: tzinfo) -> Score:
    findings: list[str] = []
    parts: list[Part] = []
    expected = scn.expected_outcome
    team = inc.assessment["outcome"] if inc.assessment else "NO ASSESSMENT"

    # 1. Determination (40)
    if team == expected:
        pts = 40
        findings.append(f"Strength: the team reached the right call, {expected}.")
    elif team == UNDETERMINED:
        pts = 15
        findings.append(
            "Gap: the team ended undetermined. That is defensible only if it then contacted the NCUA, as "
            "23-CU-07 advises when a credit union is unsure. Work on which facts would settle the open tests."
        )
    elif team == "NO ASSESSMENT":
        pts = 0
        findings.append("Gap: the team never walked the reportability tests, so there is no recorded decision for an examiner.")
    else:
        pts = 0
        findings.append(f"Gap: the team concluded {team}; the answer key says {expected}. Review the test-by-test table.")
    parts.append(Part("Reportability call", pts, 40, f"Team: {team}. Answer key: {expected}."))

    # 2. Individual tests (20)
    key_plain = {k: v.answer for k, v in scn.answer_key.items()}
    asked = relevant_tests(key_plain)
    team_answers = inc.assessment["answers"] if inc.assessment else {}
    matched = 0
    rows = []
    for t in TESTS:
        if t.key not in asked:
            continue
        k = scn.answer_key[t.key]
        mine = team_answers.get(t.key, {})
        ok = k.accepts(mine.get("answer"))
        matched += ok
        rows.append([
            t.title,
            _label(mine.get("answer")) + ("" if ok else "  (differs)"),
            mine.get("rationale", "") or "",
            _label(k.answer) + (f" (also fine: {', '.join(_label(a) for a in k.also_ok)})" if k.also_ok else ""),
            k.why,
        ])
    pts = round(20 * matched / len(asked)) if asked else 0
    parts.append(Part("Test-by-test answers", pts, 20, f"{matched} of {len(asked)} match the answer key."))
    if inc.assessment and matched < len(asked):
        diff = len(asked) - matched
        findings.append(f"Gap: {'one test answer differs' if diff == 1 else f'{diff} test answers differ'} from the answer key. The table below shows why.")

    # 3. Notification timing (30) and 4. clock start / belief (10)
    third = [from_iso(d["at"]) for d in _entries(inc, "third_party_notice")]
    belief_due = _inject_time(inc, scn.belief_inject)
    notified_at = inc.first_notified_at
    beliefs = [from_iso(d["at"]) for d in _entries(inc, "belief")]
    team_belief = min(beliefs) if beliefs else None

    true_start = true_by = deadline = None
    if expected == REPORTABLE:
        candidates = [(t, "third-party notice") for t in third]
        if belief_due:
            candidates.append((belief_due, f"facts in inject {scn.belief_inject}"))
        if candidates:
            true_start, true_by = min(candidates, key=lambda c: c[0])
            deadline = true_start + timedelta(hours=DEADLINE_HOURS)
        if notified_at and deadline and notified_at <= deadline:
            margin = notified_at - true_start
            msg = f"Notified {fmt_duration(margin)} after the clock started, {fmt_duration(deadline - notified_at)} before the deadline."
            if margin <= timedelta(hours=12):
                pts = 30
                findings.append("Strength: the NCUA was notified promptly, well inside the 72 hours.")
            elif margin <= timedelta(hours=24):
                pts = 25
                findings.append("Gap: the notice was on time, but the rule says as soon as possible, and it took most of a day. Ask what held it up.")
            else:
                pts = 20
                findings.append("Gap: the notice beat the deadline but came more than a day in. The rule says as soon as possible; find what held it up.")
        elif notified_at and deadline:
            pts = 0
            msg = f"Notified {fmt_duration(notified_at - deadline)} after the deadline."
            findings.append("Gap: the notice was late. Find where the time went and who could have made the call sooner.")
        else:
            pts = 0
            msg = "The NCUA was never notified during the drill."
            findings.append("Gap: no notice to the NCUA was made, though the incident was reportable.")
        parts.append(Part("NCUA notice within 72 hours", pts, 30, msg))

        if team_belief and belief_due and team_belief <= belief_due + timedelta(hours=2):
            pts, msg = 10, f"Recorded {fmt_local(team_belief, tz)}, in step with the facts."
        elif team_belief and belief_due and team_belief <= belief_due + timedelta(hours=12):
            pts, msg = 5, f"Recorded {fmt_duration(team_belief - belief_due)} after the facts supported it."
            findings.append("Gap: the team was slow to record its reasonable belief. Name who decides that, and when.")
        elif team_belief and belief_due:
            pts, msg = 0, f"Recorded {fmt_duration(team_belief - belief_due)} after the facts supported it."
            findings.append("Gap: the team recorded its reasonable belief very late.")
        else:
            pts, msg = 0, "No reasonable belief was recorded."
            findings.append("Gap: the team never recorded when it formed a reasonable belief, the point the rule turns on.")
        parts.append(Part("Reasonable belief recorded promptly", pts, 10, msg))
    else:
        if notified_at:
            msg = "The team contacted the NCUA. Not required by the answer key, and never wrong when unsure."
        else:
            msg = "No notice was needed, and none was made."
        parts.append(Part("NCUA notice decision", 30, 30, msg))
        if team_belief:
            pts, msg = 5, "The team recorded a reasonable belief that a reportable incident occurred, which the facts did not support."
            findings.append("Gap: only a reasonable belief that a *reportable* incident occurred starts the clock. Revisit the substantial test.")
        else:
            pts, msg = 10, "No clock was needed."
        parts.append(Part("Clock handled correctly", pts, 10, msg))

    if not _entries(inc, "note"):
        findings.append("Tip: log decisions as you go (the [l]og action). An examiner will ask why, not only what.")

    total = sum(p.points for p in parts)
    return Score(total, parts, findings, team, expected, true_start, true_by, deadline, notified_at, rows)


def _label(a: str | None) -> str:
    return {YES: "Yes", NO: "No", "unsure": "Unsure"}.get(a or "", "Not answered")


# ------------------------------------------------------------------ after-action report

def _drill_event_text(e: dict[str, Any], tz: tzinfo) -> str:
    from .report import _event_text

    t, d = e["type"], e["data"]
    if t == "opened":
        return f"Exercise started: {d.get('scenario_title', '')}."
    if t == "inject":
        return f"Inject {d['n']}: {d['headline']}. {d['text']}"
    if t == "assessment":
        return f"Team assessed reportability: {d['outcome']}. {d.get('explanation', '')}"
    if t == "notified":
        return f"Team notified the NCUA (simulated) by {d.get('method', '')}. {d.get('reference', '')}"
    if t == "drill_end":
        early = " (ended early by the team)" if d.get("ended_early") else ""
        return f"Exercise ended{early}. Score {d.get('score')} of 100."
    return _event_text(e, tz)


def _sim_time(e: dict[str, Any]) -> str | None:
    d = e["data"]
    if e["type"] == "opened":
        return d.get("sim_start")
    if e["type"] == "assessment":
        return d.get("assessed_at")
    return d.get("at")


def after_action_blocks(inc: Incident, tz: tzinfo) -> list[Block]:
    if not inc.profile.get("exercise"):
        raise ValueError(f"{inc.incident_id} is not a tabletop exercise")
    scn = by_key(inc.profile["scenario"])
    ends = _entries(inc, "drill_end")
    end = from_iso(ends[-1]["at"]) if ends else max(
        (from_iso(t) for t in (_sim_time(e) for e in inc.entries) if t), default=from_iso(inc.profile["sim_start"])
    )
    sc = score(scn, inc, end, tz)
    p = inc.profile
    speed = p.get("speed", DEFAULT_SPEED)
    pace = "frozen between injects" if not speed else f"{speed:g}x real time ({speed / 60:g} simulated hours per real minute)"
    first_real = from_iso(inc.entries[0]["recorded_at"]) if inc.entries else None

    b: list[Block] = []
    b.append(("h1", f"Tabletop Exercise After-Action Report: {inc.incident_id}"))
    b.append(("p", scn.title))
    b.append(("note", EXERCISE_BANNER + " " + AAR_DISCLAIMER))
    b.append(("kv", [
        ("Score", f"{sc.total} of 100: {sc.rating}"),
        ("Scenario", f"{scn.title} ({scn.key})"),
        ("Credit union", f"{p.get('cu_name', '')}"),
        ("Facilitator", p.get("facilitator") or "not recorded"),
        ("Participants", p.get("participants") or "not recorded"),
        ("Exercise run", fmt_local(first_real, tz) if first_real else "not recorded"),
        ("Simulated start", fmt_local(from_iso(p["sim_start"]), tz)),
        ("Simulated clock", pace),
        ("Status", "ended early by the team" if ends and ends[-1].get("ended_early") else ("complete" if ends else "not finished")),
    ]))

    b.append(("h2", "1. Score"))
    b.append(("table", ["Area", "Points", "Out of", "Detail"], [[x.name, str(x.points), str(x.max), x.detail] for x in sc.parts]))

    b.append(("h2", "2. Findings"))
    b.append(("list", sc.findings or ["No findings."]))

    b.append(("h2", "3. Reportability call"))
    b.append(("p", f"Team: {sc.team_outcome}. Answer key: {sc.expected_outcome}."))
    if sc.test_rows:
        b.append(("table", ["Test", "Team", "Team's reasoning", "Key", "Why"], sc.test_rows))

    b.append(("h2", "4. The 72-hour clock"))
    b.append(("p", scn.clock_note))
    clock = inc.clock(end)
    b.append(("kv", [
        ("Clock should have started", (fmt_local(sc.true_start, tz) + f" ({sc.true_start_by})") if sc.true_start else "no clock: not reportable"),
        ("Deadline", fmt_local(sc.deadline, tz) if sc.deadline else "none"),
        ("Team's clock", clock.describe(tz)),
        ("Team's reasonable belief", fmt_local(inc.belief_at, tz)),
        ("NCUA notified (simulated)", fmt_local(sc.notified_at, tz)),
    ]))

    b.append(("h2", "5. Debrief questions"))
    b.append(("list", list(scn.debrief)))

    b.append(("h2", "6. Exercise timeline"))
    rows = []
    for e in inc.entries:
        st = _sim_time(e)
        rows.append([str(e["seq"]), fmt_local(from_iso(st), tz) if st else "", _drill_event_text(e, tz)])
    b.append(("table", ["#", "Simulated time", "Entry"], rows))

    b.append(("h2", "7. Log integrity"))
    if inc.integrity and inc.integrity.ok:
        b.append(("p", f"Verified: {inc.integrity.entries} entries, hash chain intact. Final SHA-256: {inc.integrity.last_hash}"))
    elif inc.integrity:
        b.append(("p", f"VERIFICATION FAILED: {inc.integrity.problem}. The score may not reflect the drill as run."))

    b.append(("h2", "8. Sources"))
    b.append(("list", [f"{name}: {url}" for name, url in SOURCES.values()]))
    return b


def after_action_markdown(inc: Incident, tz: tzinfo) -> str:
    return render_markdown(after_action_blocks(inc, tz))


def after_action_html(inc: Incident, tz: tzinfo, author: str | None = None, extra_body: str = "") -> str:
    return render_html(after_action_blocks(inc, tz), f"Tabletop After-Action Report {inc.incident_id}", author=author, extra_body=extra_body)


def after_action_pdf(inc: Incident, tz: tzinfo, author: str | None = None) -> bytes:
    from .pdf import render_pdf

    footer = f"EXERCISE, NOT A REAL INCIDENT  |  {inc.incident_id}  |  Not legal advice."
    return render_pdf(
        after_action_blocks(inc, tz),
        f"Tabletop After-Action Report {inc.incident_id}",
        author,
        footer,
        subject="Tabletop exercise after-action report (exercise, not a real incident)",
    )


def load_drill(drills_home: Path, drill_id: str) -> Incident:
    if not is_exercise_id(drill_id):
        raise LogError(f"{drill_id} is not a drill id; drill ids start with TT-")
    inc = load(DrillLog.open(Path(drills_home), drill_id.upper()))
    if not inc.profile.get("exercise"):
        raise LogError(f"{drill_id} is not marked as an exercise")
    return inc


def scenario_list() -> list[Scenario]:
    return list(SCENARIOS)

