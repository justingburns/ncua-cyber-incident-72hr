"""Rebuild an incident's current state by replaying its log."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .clock import ClockState, compute_clock, from_iso
from .log import IncidentLog, VerifyResult
from .rule import UNDETERMINED


@dataclass
class Incident:
    incident_id: str
    profile: dict[str, Any] = field(default_factory=dict)
    assessment: dict[str, Any] | None = None
    assessments: list[dict[str, Any]] = field(default_factory=list)
    belief_at: datetime | None = None
    belief_basis: str | None = None
    third_party: dict[str, Any] | None = None
    third_party_at: datetime | None = None
    notifications: list[dict[str, Any]] = field(default_factory=list)
    closed: dict[str, Any] | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)
    integrity: VerifyResult | None = None

    @property
    def title(self) -> str:
        return self.profile.get("title", "(untitled)")

    @property
    def outcome(self) -> str:
        return self.assessment["outcome"] if self.assessment else UNDETERMINED

    @property
    def first_notified_at(self) -> datetime | None:
        times = [from_iso(n["at"]) for n in self.notifications]
        return min(times) if times else None

    def clock(self, now: datetime | None = None) -> ClockState:
        return compute_clock(self.belief_at, self.third_party_at, self.first_notified_at, now)


def load(log: IncidentLog) -> Incident:
    inc = Incident(log.incident_id)
    inc.integrity = log.verify()
    inc.entries = log.entries()
    for e in inc.entries:
        t, d = e["type"], e["data"]
        if t == "opened":
            inc.profile = dict(d)
        elif t == "assessment":
            inc.assessment = d
            inc.assessments.append(d)
        elif t == "belief":
            # A later belief entry is a correction; the log keeps both.
            inc.belief_at = from_iso(d["at"])
            inc.belief_basis = d.get("basis")
        elif t == "third_party_notice":
            at = from_iso(d["at"])
            if inc.third_party_at is None or at < inc.third_party_at:
                inc.third_party_at = at
                inc.third_party = d
        elif t == "notified":
            inc.notifications.append(d)
        elif t == "closed":
            inc.closed = d
    return inc
