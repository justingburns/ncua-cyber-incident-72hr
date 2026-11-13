import unittest

from ncua72.rule import (
    NOT_REPORTABLE,
    REPORTABLE,
    UNDETERMINED,
    determine,
    relevant_tests,
)

BASE = {"cyber_incident": "yes", "good_faith_exclusion": "no", "substantial": "yes"}


def with_prongs(a="no", b="no", c="no", **overrides):
    d = dict(BASE, prong_a=a, prong_b=b, prong_c=c)
    d.update(overrides)
    return d


class DetermineTests(unittest.TestCase):
    def test_any_one_prong_is_reportable(self):
        for prong in ("a", "b", "c"):
            outcome, why = determine(with_prongs(**{prong: "yes"}))
            self.assertEqual(outcome, REPORTABLE, prong)
            self.assertIn(f"Prong {prong.upper()}", why)

    def test_multiple_prongs_named(self):
        _, why = determine(with_prongs(a="yes", c="yes"))
        self.assertIn("Prongs A and C", why)

    def test_no_prong_is_not_reportable(self):
        self.assertEqual(determine(with_prongs())[0], NOT_REPORTABLE)

    def test_not_a_cyber_incident(self):
        self.assertEqual(determine({"cyber_incident": "no"})[0], NOT_REPORTABLE)

    def test_good_faith_exclusion(self):
        outcome, why = determine({"cyber_incident": "yes", "good_faith_exclusion": "yes"})
        self.assertEqual(outcome, NOT_REPORTABLE)
        self.assertIn("good-faith", why)

    def test_not_substantial(self):
        outcome = determine({"cyber_incident": "yes", "good_faith_exclusion": "no", "substantial": "no"})[0]
        self.assertEqual(outcome, NOT_REPORTABLE)

    def test_unsure_prong_is_undetermined(self):
        outcome, why = determine(with_prongs(b="unsure"))
        self.assertEqual(outcome, UNDETERMINED)
        self.assertIn("contact the NCUA", why)

    def test_unsure_threshold_with_prong_met_is_undetermined(self):
        self.assertEqual(determine(with_prongs(a="yes", substantial="unsure"))[0], UNDETERMINED)

    def test_missing_answers_undetermined(self):
        self.assertEqual(determine(BASE)[0], UNDETERMINED)

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            determine({"cyber_incident": "maybe"})
        with self.assertRaises(ValueError):
            determine({"made_up": "yes"})


class WalkTests(unittest.TestCase):
    def test_walk_stops_when_not_a_cyber_incident(self):
        self.assertEqual(relevant_tests({"cyber_incident": "no"}), ["cyber_incident"])

    def test_walk_stops_on_exclusion(self):
        self.assertEqual(
            relevant_tests({"cyber_incident": "yes", "good_faith_exclusion": "yes"}),
            ["cyber_incident", "good_faith_exclusion"],
        )

    def test_walk_continues_when_unsure(self):
        keys = relevant_tests({"cyber_incident": "unsure", "good_faith_exclusion": "no", "substantial": "unsure"})
        self.assertIn("prong_c", keys)


if __name__ == "__main__":
    unittest.main()
