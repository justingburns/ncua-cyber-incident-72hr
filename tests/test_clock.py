import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ncua72.clock import (
    DUE_SOON,
    NO_CLOCK,
    NOTIFIED_LATE,
    NOTIFIED_ON_TIME,
    OVERDUE,
    RUNNING,
    compute_clock,
    fmt_duration,
    fmt_local,
    parse_time,
)

LA = ZoneInfo("America/Los_Angeles")
UTC = timezone.utc


def t(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


class ParseTests(unittest.TestCase):
    def test_naive_is_read_in_given_zone(self):
        self.assertEqual(parse_time("2026-11-12 09:30", LA), t("2026-11-12T17:30:00"))

    def test_offset_and_z(self):
        self.assertEqual(parse_time("2026-11-12T09:30:00-08:00", LA), t("2026-11-12T17:30:00"))
        self.assertEqual(parse_time("2026-11-12T17:30:00Z", LA), t("2026-11-12T17:30:00"))

    def test_now(self):
        now = t("2026-01-01T00:00:00")
        self.assertEqual(parse_time("now", LA, now=now), now)
        self.assertEqual(parse_time(None, LA, now=now), now)

    def test_garbage(self):
        with self.assertRaises(ValueError):
            parse_time("next tuesday", LA)


class ClockTests(unittest.TestCase):
    def test_no_clock(self):
        self.assertEqual(compute_clock(None, None, None).status, NO_CLOCK)

    def test_deadline_is_72_hours(self):
        belief = t("2026-11-12T17:30:00")
        c = compute_clock(belief, None, None, now=belief + timedelta(hours=1))
        self.assertEqual(c.deadline, belief + timedelta(hours=72))
        self.assertEqual(c.status, RUNNING)
        self.assertEqual(c.remaining, timedelta(hours=71))

    def test_third_party_notice_earlier_wins(self):
        belief = t("2026-11-12T17:30:00")
        notice = t("2026-11-12T15:40:00")
        c = compute_clock(belief, notice, None, now=belief)
        self.assertEqual(c.started_by, "third-party notice")
        self.assertEqual(c.deadline, notice + timedelta(hours=72))

    def test_belief_earlier_wins(self):
        belief = t("2026-11-12T10:00:00")
        notice = t("2026-11-12T15:40:00")
        self.assertEqual(compute_clock(belief, notice, None, now=belief).started_by, "reasonable belief")

    def test_due_soon_and_overdue(self):
        belief = t("2026-11-12T00:00:00")
        self.assertEqual(compute_clock(belief, None, None, now=belief + timedelta(hours=61)).status, DUE_SOON)
        self.assertEqual(compute_clock(belief, None, None, now=belief + timedelta(hours=72)).status, OVERDUE)

    def test_notified(self):
        belief = t("2026-11-12T00:00:00")
        on_time = compute_clock(belief, None, belief + timedelta(hours=70))
        late = compute_clock(belief, None, belief + timedelta(hours=73))
        self.assertEqual(on_time.status, NOTIFIED_ON_TIME)
        self.assertEqual(late.status, NOTIFIED_LATE)
        self.assertIn("before", on_time.describe(LA))
        self.assertIn("after", late.describe(LA))

    def test_deadline_across_dst_end(self):
        # Fall back on Nov 1, 2026: 72 real hours from 9:00 AM PDT Oct 31 is 8:00 AM PST Nov 3.
        belief = parse_time("2026-10-31 09:00", LA)
        c = compute_clock(belief, None, None, now=belief)
        self.assertEqual(fmt_local(c.deadline, LA), "Tue Nov 3, 2026 8:00 AM PST")


class FormatTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(fmt_duration(timedelta(hours=49, minutes=5)), "2d 1h 05m")
        self.assertEqual(fmt_duration(timedelta(minutes=-90)), "1h 30m")

    def test_local_format(self):
        self.assertEqual(fmt_local(t("2026-11-12T17:05:00"), LA), "Thu Nov 12, 2026 9:05 AM PST")
        self.assertEqual(fmt_local(None, LA), "not recorded")


if __name__ == "__main__":
    unittest.main()
