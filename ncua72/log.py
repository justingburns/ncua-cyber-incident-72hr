"""Append-only, hash-chained incident log.

Each incident is one JSON Lines file. Every entry carries the SHA-256 of the entry
before it, so any edit, deletion or reordering after the fact breaks the chain and
`ncua72 verify` reports where. Corrections are made by appending a new entry, never
by editing an old one.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .clock import to_iso, utcnow

GENESIS = "0" * 64

EVENT_TYPES = (
    "opened",
    "assessment",
    "belief",
    "third_party_notice",
    "note",
    "notified",
    "closed",
)


class LogError(Exception):
    pass


def _canonical(entry: dict[str, Any]) -> bytes:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def entry_hash(entry: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(entry)).hexdigest()


@dataclass
class VerifyResult:
    ok: bool
    entries: int
    last_hash: str
    problem: str | None = None


def default_home() -> Path:
    return Path(os.environ.get("NCUA72_HOME", "incidents"))


def default_drills() -> Path:
    return Path(os.environ.get("NCUA72_DRILLS", "drills"))


def new_incident_id(now: datetime | None = None, prefix: str = "CI") -> str:
    now = now or utcnow()
    return f"{prefix}-{now:%Y%m%d}-{secrets.token_hex(2).upper()}"


class IncidentLog:
    # Real incidents are CI-...; tabletop drills use a subclass with their own prefix
    # and folder, so the two never share a listing.
    PREFIX = "CI"
    TYPES: tuple[str, ...] = EVENT_TYPES

    def __init__(self, home: Path, incident_id: str):
        self.home = Path(home)
        self.incident_id = incident_id
        self.path = self.home / f"{incident_id}.jsonl"

    @classmethod
    def create(cls, home: Path, incident_id: str | None = None) -> "IncidentLog":
        home = Path(home)
        home.mkdir(parents=True, exist_ok=True)
        incident_id = incident_id or new_incident_id(prefix=cls.PREFIX)
        log = cls(home, incident_id)
        if log.path.exists():
            raise LogError(f"incident {incident_id} already exists")
        return log

    @classmethod
    def open(cls, home: Path, incident_id: str) -> "IncidentLog":
        log = cls(home, incident_id)
        if not log.path.exists():
            raise LogError(f"no incident {incident_id} in {home}")
        return log

    @classmethod
    def list_ids(cls, home: Path) -> list[str]:
        home = Path(home)
        if not home.is_dir():
            return []
        return sorted(p.stem for p in home.glob(f"{cls.PREFIX}-*.jsonl"))

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        with self.path.open("r", encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise LogError(f"{self.path}: line {n} is not valid JSON") from exc
        return out

    def verify(self) -> VerifyResult:
        prev = GENESIS
        entries = self.entries()
        for i, e in enumerate(entries):
            if e.get("seq") != i + 1:
                return VerifyResult(False, len(entries), prev, f"entry {i + 1}: sequence number is {e.get('seq')}")
            if e.get("prev") != prev:
                return VerifyResult(False, len(entries), prev, f"entry {i + 1}: does not link to entry {i}")
            if e.get("hash") != entry_hash(e):
                return VerifyResult(False, len(entries), prev, f"entry {i + 1}: contents changed after it was written")
            if e.get("incident_id") != self.incident_id:
                return VerifyResult(False, len(entries), prev, f"entry {i + 1}: belongs to another incident")
            prev = e["hash"]
        return VerifyResult(True, len(entries), prev)

    def append(self, event_type: str, data: dict[str, Any], actor: str) -> dict[str, Any]:
        if event_type not in self.TYPES:
            raise LogError(f"unknown event type {event_type}")
        check = self.verify()
        if not check.ok:
            raise LogError(f"refusing to append: log failed verification ({check.problem})")
        if check.entries == 0 and event_type != "opened":
            raise LogError("the first entry must open the incident")
        if check.entries > 0 and event_type == "opened":
            raise LogError("incident is already open")
        entry = {
            "seq": check.entries + 1,
            "incident_id": self.incident_id,
            "recorded_at": to_iso(utcnow()),
            "actor": actor,
            "type": event_type,
            "data": data,
            "prev": check.last_hash,
        }
        entry["hash"] = entry_hash(entry)
        line = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        # "a" mode: the file is only ever appended to.
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry
