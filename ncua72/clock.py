"""Time handling and the 72-hour notification clock."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo

from .rule import DEADLINE_HOURS

DUE_SOON_HOURS = 12

NO_CLOCK = "NO CLOCK"
RUNNING = "RUNNING"
DUE_SOON = "DUE SOON"
OVERDUE = "OVERDUE"
NOTIFIED_ON_TIME = "NOTIFIED ON TIME"
NOTIFIED_LATE = "NOTIFIED LATE"


def get_tz(name: str | None = None) -> tzinfo:
    """Return a tzinfo for an IANA zone name such as "America/Los_Angeles".

    With no name, use $NCUA72_TZ, then $TZ, then the system zone. Windows has no
    built-in zone database, so naming a zone there needs `pip install tzdata`.
    """
    import os
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    name = name or os.environ.get("NCUA72_TZ") or os.environ.get("TZ")
    if not name:
        try:
            link = os.path.realpath("/etc/localtime")
            if "zoneinfo/" in link:
                name = link.split("zoneinfo/", 1)[1]
        except OSError:
            name = None
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(
                f"unknown time zone {name!r}; on Windows run `pip install tzdata`"
            ) from exc
    # Last resort: the current fixed offset. DST changes are not tracked.
    local = datetime.now().astimezone().tzinfo
    assert local is not None
    return local


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(text: str | None, tz: tzinfo, now: datetime | None = None) -> datetime:
    """Parse a user-entered time. Accepts "now", ISO 8601, or "YYYY-MM-DD HH:MM".

    A time without an offset is read in the given zone. Returns an aware UTC datetime.
    """
    now = now or utcnow()
    if text is None or text.strip().lower() in ("", "now"):
        return now.astimezone(timezone.utc)
    s = text.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    s = re.sub(r"\s+", " ", s)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(
            f"could not read time {text!r}; use 'now' or 'YYYY-MM-DD HH:MM' (24-hour)"
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def from_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def fmt_local(dt: datetime | None, tz: tzinfo) -> str:
    if dt is None:
        return "not recorded"
    local = dt.astimezone(tz)
    hour = local.hour % 12 or 12
    ampm = "AM" if local.hour < 12 else "PM"
    return f"{local:%a %b} {local.day}, {local.year} {hour}:{local:%M} {ampm} {local.tzname()}"


def fmt_duration(delta: timedelta) -> str:
    total = int(abs(delta.total_seconds()))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours}h")
    parts.append(f"{minutes:02d}m")
    return " ".join(parts)


@dataclass(frozen=True)
class ClockState:
    status: str
    started_at: datetime | None
    started_by: str | None  # "reasonable belief" or "third-party notice"
    deadline: datetime | None
    remaining: timedelta | None
    notified_at: datetime | None

    def describe(self, tz: tzinfo) -> str:
        if self.status == NO_CLOCK:
            return "Clock not started: no reasonable belief or third-party notice recorded."
        due = fmt_local(self.deadline, tz)
        if self.status in (NOTIFIED_ON_TIME, NOTIFIED_LATE):
            margin = (self.deadline - self.notified_at) if self.deadline and self.notified_at else None
            when = fmt_local(self.notified_at, tz)
            if self.status == NOTIFIED_ON_TIME:
                return f"NCUA notified {when}, {fmt_duration(margin)} before the {due} deadline."
            return f"NCUA notified {when}, {fmt_duration(margin)} after the {due} deadline."
        assert self.remaining is not None
        if self.status == OVERDUE:
            return f"OVERDUE by {fmt_duration(self.remaining)}. Deadline was {due}."
        return f"{fmt_duration(self.remaining)} left. Notify NCUA by {due}."


def compute_clock(
    belief_at: datetime | None,
    third_party_at: datetime | None,
    notified_at: datetime | None,
    now: datetime | None = None,
) -> ClockState:
    """The deadline is 72 hours from the earlier of reasonable belief or third-party notice.

    12 CFR 748.1(c) and 23-CU-07: for a third-party incident the clock starts when the
    third party notifies the credit union or when the credit union forms a reasonable
    belief, whichever is sooner.
    """
    now = now or utcnow()
    candidates = []
    if belief_at is not None:
        candidates.append((belief_at, "reasonable belief"))
    if third_party_at is not None:
        candidates.append((third_party_at, "third-party notice"))
    if not candidates:
        return ClockState(NO_CLOCK, None, None, None, None, notified_at)
    started_at, started_by = min(candidates, key=lambda c: c[0])
    deadline = started_at + timedelta(hours=DEADLINE_HOURS)
    if notified_at is not None:
        status = NOTIFIED_ON_TIME if notified_at <= deadline else NOTIFIED_LATE
        return ClockState(status, started_at, started_by, deadline, None, notified_at)
    remaining = deadline - now
    if remaining <= timedelta(0):
        status = OVERDUE
    elif remaining <= timedelta(hours=DUE_SOON_HOURS):
        status = DUE_SOON
    else:
        status = RUNNING
    return ClockState(status, started_at, started_by, deadline, remaining, None)
