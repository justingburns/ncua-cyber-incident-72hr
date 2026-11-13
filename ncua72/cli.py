"""Command line interface: ncua72 <command> ..."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .clock import get_tz, parse_time, to_iso, utcnow
from .incident import load
from .log import IncidentLog, LogError, default_home
from .report import notification_summary, packet_html, packet_markdown
from .rule import (
    ANSWERS,
    DISCLAIMER_SHORT,
    REPORTABLE,
    TEST_KEYS,
    UNDETERMINED,
    determine,
    relevant_tests,
    test_by_key,
)

Prompt = Callable[[str], str]


class CLIError(Exception):
    pass


def _actor(args: argparse.Namespace) -> str:
    if args.actor:
        return args.actor
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def _ask(prompt: Prompt, label: str, default: str | None = None, required: bool = True) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = prompt(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if value or not required:
            return value
        print("  A value is required.")


def _ask_choice(prompt: Prompt, label: str, choices: tuple[str, ...]) -> str:
    while True:
        value = prompt(f"{label} ({'/'.join(choices)}): ").strip().lower()
        for c in choices:
            if value == c or (value and c.startswith(value)):
                return c
        print(f"  Please answer {', '.join(choices)}.")


def _open(args: argparse.Namespace) -> IncidentLog:
    return IncidentLog.open(Path(args.home), args.incident)


# ------------------------------------------------------------------ commands

PROFILE_FIELDS = (
    ("title", "Short title"),
    ("cu_name", "Credit union name"),
    ("charter", "Charter number"),
    ("reporter_name", "Reporting individual's name"),
    ("reporter_title", "Reporting individual's title"),
    ("reporter_phone", "Telephone"),
    ("reporter_email", "Email"),
    ("description", "Basic description of the incident"),
    ("affected_functions", "Affected functions (if known)"),
)


def cmd_new(args, tz, prompt: Prompt) -> int:
    data: dict[str, Any] = {}
    for key, label in PROFILE_FIELDS:
        value = getattr(args, key)
        if value is None and args.interactive:
            value = _ask(prompt, label, required=key not in ("affected_functions",))
        data[key] = value or ""
    missing = [k for k in ("title", "cu_name", "description") if not data[k]]
    if missing:
        raise CLIError("missing required fields: " + ", ".join("--" + m.replace("_", "-") for m in missing))
    sensitive = args.sensitive
    if sensitive is None:
        sensitive = _ask_choice(prompt, "Sensitive information compromised", ("yes", "no", "unknown")) if args.interactive else "unknown"
    data["sensitive_data"] = sensitive
    discovered = args.discovered
    if discovered is None and args.interactive:
        discovered = _ask(prompt, "When was it discovered (YYYY-MM-DD HH:MM, local)", default="now")
    data["discovered_at"] = to_iso(parse_time(discovered, tz))
    log = IncidentLog.create(Path(args.home), args.id)
    log.append("opened", data, _actor(args))
    print(f"Opened {log.incident_id}: {data['title']}")
    print(f"Next: ncua72 assess {log.incident_id}")
    return 0


def _walk(prompt: Prompt) -> dict[str, dict[str, str]]:
    answers: dict[str, dict[str, str]] = {}
    plain: dict[str, str] = {}
    print("\nAnswer each test yes, no or unsure, and give your reason. Your reasons go in the record.\n")
    while True:
        pending = [k for k in relevant_tests(plain) if k not in plain]
        if not pending:
            break
        t = test_by_key(pending[0])
        print(f"== {t.title}  [{t.cite}]")
        print(f"   {t.question}")
        print(f"   ({t.help})")
        a = _ask_choice(prompt, "   Answer", ANSWERS)
        r = _ask(prompt, "   Rationale")
        answers[t.key] = {"answer": a, "rationale": r}
        plain[t.key] = a
        print()
    return answers


def _load_answers(path: str) -> dict[str, dict[str, str]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for key, value in raw.items():
        if key not in TEST_KEYS:
            raise CLIError(f"unknown test {key!r} in {path}; tests are {', '.join(TEST_KEYS)}")
        if isinstance(value, str):
            value = {"answer": value, "rationale": ""}
        if not value.get("rationale"):
            raise CLIError(f"{key}: a rationale is required for every answer")
        out[key] = {"answer": value["answer"].lower(), "rationale": value["rationale"]}
    return out


def cmd_assess(args, tz, prompt: Prompt) -> int:
    log = _open(args)
    answers = _load_answers(args.answers) if args.answers else _walk(prompt)
    outcome, explanation = determine({k: v["answer"] for k, v in answers.items()})
    data = {
        "answers": answers,
        "outcome": outcome,
        "explanation": explanation,
        "assessed_at": to_iso(utcnow()),
        "assessed_by": _actor(args),
    }
    log.append("assessment", data, _actor(args))
    print(f"Determination: {outcome}. {explanation}")
    inc = load(log)
    if outcome in (REPORTABLE, UNDETERMINED) and inc.belief_at is None:
        if args.interactive and not args.answers:
            when = _ask(prompt, "When did the credit union form a reasonable belief (YYYY-MM-DD HH:MM, local)", default="now")
            basis = _ask(prompt, "What formed that belief")
            log.append("belief", {"at": to_iso(parse_time(when, tz)), "basis": basis}, _actor(args))
            inc = load(log)
        else:
            print(f"Record when the reasonable belief formed: ncua72 believe {log.incident_id} --at '...' --basis '...'")
    if outcome == UNDETERMINED:
        print("NCUA's 23-CU-07: if unsure whether an incident is reportable, contact the NCUA as soon as possible.")
    print(inc.clock().describe(tz))
    return 0


def cmd_believe(args, tz, prompt: Prompt) -> int:
    log = _open(args)
    log.append("belief", {"at": to_iso(parse_time(args.at, tz)), "basis": args.basis}, _actor(args))
    print(load(log).clock().describe(tz))
    return 0


def cmd_third_party(args, tz, prompt: Prompt) -> int:
    log = _open(args)
    data = {"at": to_iso(parse_time(args.at, tz)), "party": args.party, "summary": args.summary or ""}
    log.append("third_party_notice", data, _actor(args))
    print(load(log).clock().describe(tz))
    return 0


def cmd_note(args, tz, prompt: Prompt) -> int:
    log = _open(args)
    data: dict[str, Any] = {"text": args.text}
    if args.at:
        data["at"] = to_iso(parse_time(args.at, tz))
    entry = log.append("note", data, _actor(args))
    print(f"Logged entry {entry['seq']}.")
    return 0


def cmd_notified(args, tz, prompt: Prompt) -> int:
    log = _open(args)
    data = {
        "at": to_iso(parse_time(args.at, tz)),
        "method": args.method,
        "by": args.by or _actor(args),
        "reference": args.reference or "",
    }
    log.append("notified", data, _actor(args))
    print(load(log).clock().describe(tz))
    return 0


def cmd_close(args, tz, prompt: Prompt) -> int:
    log = _open(args)
    log.append("closed", {"at": to_iso(parse_time(args.at, tz)), "reason": args.reason}, _actor(args))
    print(f"Closed {log.incident_id}.")
    return 0


def cmd_status(args, tz, prompt: Prompt) -> int:
    home = Path(args.home)
    ids = [args.incident] if args.incident else IncidentLog.list_ids(home)
    if not ids:
        print(f"No incidents in {home}.")
        return 0
    for iid in ids:
        inc = load(IncidentLog.open(home, iid))
        flag = "" if inc.integrity and inc.integrity.ok else "  [LOG FAILED VERIFICATION]"
        closed = "  [closed]" if inc.closed else ""
        print(f"{iid}  {inc.title}{closed}{flag}")
        print(f"   Determination: {inc.outcome}")
        print(f"   {inc.clock().describe(tz)}")
    return 0


def cmd_summary(args, tz, prompt: Prompt) -> int:
    inc = load(_open(args))
    print(notification_summary(inc, tz))
    return 0


def cmd_packet(args, tz, prompt: Prompt) -> int:
    inc = load(_open(args))
    author = args.author or inc.profile.get("reporter_name") or None
    if args.format == "pdf":
        from .pdf import PDFUnavailable, packet_pdf

        try:
            data = packet_pdf(inc, tz, prepared_by=_actor(args), author=author)
        except PDFUnavailable as exc:
            raise CLIError(str(exc)) from exc
        out = args.out or f"{inc.incident_id}.pdf"
        Path(out).write_bytes(data)
        print(f"Wrote {out}")
        return 0
    if args.format == "html":
        text = packet_html(inc, tz, prepared_by=_actor(args), author=author)
    else:
        text = packet_markdown(inc, tz, prepared_by=_actor(args))
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_verify(args, tz, prompt: Prompt) -> int:
    home = Path(args.home)
    ids = [args.incident] if args.incident else IncidentLog.list_ids(home)
    bad = 0
    for iid in ids:
        r = IncidentLog.open(home, iid).verify()
        if r.ok:
            print(f"{iid}: OK, {r.entries} entries, final hash {r.last_hash}")
        else:
            bad += 1
            print(f"{iid}: FAILED, {r.problem}")
    return 1 if bad else 0


def cmd_serve(args, tz, prompt: Prompt) -> int:
    from .web import serve

    serve(Path(args.home), tz, host=args.host, port=args.port)
    return 0


# ------------------------------------------------------------------ parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="ncua72",
        description="Triage, clock and document cyber incidents under NCUA's 72-hour notification rule (12 CFR 748.1(c)).",
        epilog=DISCLAIMER_SHORT,
    )
    ap.add_argument("--version", action="version", version=f"ncua72 {__version__}")
    ap.add_argument("--home", default=str(default_home()), help="folder holding incident logs (default: ./incidents or $NCUA72_HOME)")
    ap.add_argument("--tz", help="IANA time zone for display and input, e.g. America/Los_Angeles (default: $NCUA72_TZ or system)")
    ap.add_argument("--actor", help="name recorded on log entries (default: your login name)")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="open a new incident")
    for key, label in PROFILE_FIELDS:
        p.add_argument("--" + key.replace("_", "-"), dest=key, help=label)
    p.add_argument("--sensitive", choices=("yes", "no", "unknown"), help="sensitive information compromised?")
    p.add_argument("--discovered", help="when discovered: 'now' or 'YYYY-MM-DD HH:MM'")
    p.add_argument("--id", help="use this incident id instead of a generated one")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("assess", help="walk through the reportability tests")
    p.add_argument("incident")
    p.add_argument("--answers", help="JSON file of {test: {answer, rationale}} instead of prompts")
    p.set_defaults(func=cmd_assess)

    p = sub.add_parser("believe", help="record when a reasonable belief formed (starts the clock)")
    p.add_argument("incident")
    p.add_argument("--at", default="now")
    p.add_argument("--basis", required=True, help="what formed the belief")
    p.set_defaults(func=cmd_believe)

    p = sub.add_parser("third-party", help="record a notice from a CUSO, cloud or other third-party provider")
    p.add_argument("incident")
    p.add_argument("--at", default="now")
    p.add_argument("--party", required=True)
    p.add_argument("--summary")
    p.set_defaults(func=cmd_third_party)

    p = sub.add_parser("note", help="append a timestamped note")
    p.add_argument("incident")
    p.add_argument("text")
    p.add_argument("--at", help="when the noted event happened, if not now")
    p.set_defaults(func=cmd_note)

    p = sub.add_parser("notified", help="record that NCUA was notified")
    p.add_argument("incident")
    p.add_argument("--at", default="now")
    p.add_argument("--method", required=True, choices=("phone", "secure-email", "other"))
    p.add_argument("--by", help="who made the notification")
    p.add_argument("--reference", help="voicemail time, email subject or other reference")
    p.set_defaults(func=cmd_notified)

    p = sub.add_parser("close", help="close the incident")
    p.add_argument("incident")
    p.add_argument("--at", default="now")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("status", help="show the clock for one or all incidents")
    p.add_argument("incident", nargs="?")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("summary", help="print the initial notification summary")
    p.add_argument("incident")
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("packet", help="write the examiner packet")
    p.add_argument("incident")
    p.add_argument("--format", choices=("md", "html", "pdf"), default="md", help="pdf needs the reportlab package")
    p.add_argument("--out", help="file to write (default: print; for pdf, <incident id>.pdf)")
    p.add_argument("--author", help="author in the document's metadata (default: the reporting individual)")
    p.set_defaults(func=cmd_packet)

    p = sub.add_parser("verify", help="check the hash chain of one or all incident logs")
    p.add_argument("incident", nargs="?")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("serve", help="local, read-only dashboard in your browser")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8072)
    p.set_defaults(func=cmd_serve)
    return ap


def main(argv: list[str] | None = None, prompt: Prompt = input, interactive: bool | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.interactive = sys.stdin.isatty() if interactive is None else interactive
    try:
        tz = get_tz(args.tz)
        return args.func(args, tz, prompt)
    except (CLIError, LogError, ValueError) as exc:
        print(f"ncua72: error: {exc}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nStopped. Nothing further was written.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
