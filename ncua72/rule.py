"""The NCUA cyber incident notification rule, encoded as a decision walk-through.

Source text: 12 CFR 748.1(c) (eCFR, as amended by 88 FR 12816, Mar. 1, 2023)
and NCUA Letter to Credit Unions 23-CU-07, "Cyber Incident Notification
Requirements" (August 2023) with its Appendices A and B.

This module paraphrases and briefly quotes the rule so a user can apply it.
It is not legal advice. Always check the current rule text and NCUA guidance.
"""

from __future__ import annotations

from dataclasses import dataclass

YES, NO, UNSURE = "yes", "no", "unsure"
ANSWERS = (YES, NO, UNSURE)

REPORTABLE = "REPORTABLE"
NOT_REPORTABLE = "NOT REPORTABLE"
UNDETERMINED = "UNDETERMINED"

DEADLINE_HOURS = 72

SOURCES = {
    "rule": (
        "12 CFR 748.1(c), Cyber incident notification requirements",
        "https://www.ecfr.gov/current/title-12/chapter-VII/subchapter-A/part-748",
    ),
    "letter": (
        "NCUA Letter to Credit Unions 23-CU-07, Cyber Incident Notification Requirements (Aug. 2023)",
        "https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements",
    ),
    "appendix_a": (
        "23-CU-07 Appendix A, examples that likely would qualify",
        "https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-a",
    ),
    "appendix_b": (
        "23-CU-07 Appendix B, examples that likely would not qualify",
        "https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-b",
    ),
}

# How notice is given, per 23-CU-07. Verify before relying on these.
NOTICE_CHANNELS = (
    "Phone: 1-833-CYBERCU (1-833-292-3728); leave a voicemail if no one answers.",
    "Secure email to cybercu@ncua.gov, sent through the NCUA Secure Email Message Center.",
    "Other similar methods the NCUA may prescribe (12 CFR 748.1(c)).",
)

# Per 23-CU-07, leave these out of the initial notification.
DO_NOT_SEND = (
    "sensitive personally identifiable information",
    "indicators of compromise",
    "specific vulnerabilities",
    "email attachments",
)


@dataclass(frozen=True)
class Test:
    key: str
    title: str
    question: str
    help: str
    cite: str


TESTS: tuple[Test, ...] = (
    Test(
        key="cyber_incident",
        title="Is it a cyber incident?",
        question=(
            "Did an occurrence actually or imminently jeopardize, without lawful authority, "
            "the integrity, confidentiality, or availability of information on an information "
            "system, or an information system itself?"
        ),
        help=(
            "This is the rule's definition of a cyber incident. If nothing was actually or "
            "imminently put at risk, the event is not a cyber incident."
        ),
        cite="12 CFR 748.1(c)(2) (definition of cyber incident)",
    ),
    Test(
        key="good_faith_exclusion",
        title="Is it excluded as authorized, good-faith activity?",
        question=(
            "Was the activity performed in good faith by an entity in response to a specific "
            "request by the owner or operator of the system (for example, a penetration test "
            "the credit union contracted for)?"
        ),
        help="If yes, the rule says it is not a reportable cyber incident.",
        cite="12 CFR 748.1(c)(1)(ii)",
    ),
    Test(
        key="substantial",
        title="Is the cyber incident substantial?",
        question=(
            "Is this a substantial cyber incident, not a routine event that controls handled "
            "(a blocked phish, failed logins, malware removed by antivirus without harm)?"
        ),
        help=(
            "The rule covers 'any substantial cyber incident.' NCUA's Appendix A lists events "
            "that likely qualify (ransomware on critical systems, DDoS with significant downtime, "
            "compromised online banking). Appendix B lists events that likely do not."
        ),
        cite="12 CFR 748.1(c)(1)(i); 23-CU-07 Appendices A and B",
    ),
    Test(
        key="prong_a",
        title="Prong A: substantial loss of confidentiality, integrity or availability",
        question=(
            "Did it lead to a substantial loss of confidentiality, integrity, or availability of a "
            "network or member information system that results from unauthorized access to or "
            "exposure of sensitive data, disrupts vital member services, or has a serious impact "
            "on the safety and resiliency of operational systems and processes?"
        ),
        help="Think: data exposed, member services down, or core operations seriously affected.",
        cite="12 CFR 748.1(c)(1)(i)(A)",
    ),
    Test(
        key="prong_b",
        title="Prong B: disruption from a cyberattack or exploited vulnerability",
        question=(
            "Did it lead to a disruption of business operations, vital member services, or a "
            "member information system resulting from a cyberattack or exploitation of "
            "vulnerabilities?"
        ),
        help=(
            "The rule defines disruption as an unplanned event that causes an information system "
            "to be inoperable for a length of time. Planned maintenance is routine."
        ),
        cite="12 CFR 748.1(c)(1)(i)(B)",
    ),
    Test(
        key="prong_c",
        title="Prong C: third-party or supply chain compromise",
        question=(
            "Did it lead to a disruption of business operations or unauthorized access to "
            "sensitive data facilitated through, or caused by, a compromise of a CUSO, cloud "
            "service provider, or other third-party data hosting provider, or by a supply chain "
            "compromise?"
        ),
        help=(
            "For this prong the 72-hour clock starts when the third party notifies the credit "
            "union or when the credit union forms a reasonable belief, whichever is sooner."
        ),
        cite="12 CFR 748.1(c)(1)(i)(C); 23-CU-07",
    ),
)

TEST_KEYS = tuple(t.key for t in TESTS)
PRONGS = ("prong_a", "prong_b", "prong_c")


def test_by_key(key: str) -> Test:
    for t in TESTS:
        if t.key == key:
            return t
    raise KeyError(key)


def relevant_tests(answers: dict[str, str]) -> list[str]:
    """Return the test keys still worth asking, given answers so far.

    A clear "no" to cyber_incident, or a clear "yes" to the exclusion, ends the walk.
    """
    keys = ["cyber_incident"]
    if answers.get("cyber_incident") == NO:
        return keys
    keys.append("good_faith_exclusion")
    if answers.get("good_faith_exclusion") == YES:
        return keys
    keys.append("substantial")
    if answers.get("substantial") == NO:
        return keys
    keys.extend(PRONGS)
    return keys


def determine(answers: dict[str, str]) -> tuple[str, str]:
    """Apply the rule to a dict of {test key: yes/no/unsure}.

    Returns (outcome, explanation).
    """
    for key, value in answers.items():
        if key not in TEST_KEYS:
            raise ValueError(f"unknown test: {key}")
        if value not in ANSWERS:
            raise ValueError(f"answer for {key} must be one of {ANSWERS}, got {value!r}")

    def ans(key: str) -> str | None:
        return answers.get(key)

    if ans("cyber_incident") == NO:
        return NOT_REPORTABLE, "The event does not meet the rule's definition of a cyber incident."
    if ans("good_faith_exclusion") == YES:
        return NOT_REPORTABLE, "Excluded: good-faith activity at the system owner's specific request."
    if ans("substantial") == NO:
        return NOT_REPORTABLE, "The cyber incident is not substantial."

    gate = [ans("cyber_incident"), ans("good_faith_exclusion"), ans("substantial")]
    prongs = [ans(p) for p in PRONGS]
    gate_clear = gate[0] == YES and gate[1] == NO and gate[2] == YES

    met = [p for p in PRONGS if ans(p) == YES]
    if gate_clear and met:
        letters = [p[-1].upper() for p in met]
        if len(letters) == 1:
            names = f"Prong {letters[0]}"
        else:
            names = "Prongs " + ", ".join(letters[:-1]) + " and " + letters[-1]
        return REPORTABLE, f"A substantial cyber incident that meets {names}."

    if None in gate or None in prongs:
        missing = [k for k in TEST_KEYS if ans(k) is None]
        return UNDETERMINED, "Not every test is answered yet: " + ", ".join(missing) + "."

    if UNSURE in gate or UNSURE in prongs:
        if met:
            return UNDETERMINED, (
                "At least one prong is met but a threshold test is unsure. NCUA's 23-CU-07 says a "
                "credit union unsure whether an incident is reportable should contact the NCUA as "
                "soon as possible."
            )
        return UNDETERMINED, (
            "Some answers are unsure. NCUA's 23-CU-07 says a credit union unsure whether an "
            "incident is reportable should contact the NCUA as soon as possible."
        )

    return NOT_REPORTABLE, "A substantial cyber incident, but none of the three prongs is met."

DISCLAIMER_SHORT = (
    "Not legal advice. Verify every determination against the current 12 CFR 748.1(c) "
    "and current NCUA guidance."
)
