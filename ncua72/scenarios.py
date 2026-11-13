"""Built-in tabletop exercise scenarios.

Every credit union, person and company named here is fictional. The facts are
modeled on the kinds of events NCUA lists in Letter 23-CU-07, Appendix A
(likely reportable) and Appendix B (likely not reportable). The answer keys
apply 12 CFR 748.1(c) as this tool encodes it; they are teaching material, not
legal advice, and a facilitator may reasonably disagree with a call.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .rule import NO, NOT_REPORTABLE, REPORTABLE, UNSURE, YES


@dataclass(frozen=True)
class Inject:
    minutes: int  # simulated minutes after the scenario starts
    headline: str
    text: str
    third_party: str | None = None  # set when this inject is a third party's notice to the credit union


@dataclass(frozen=True)
class KeyAnswer:
    answer: str
    why: str
    also_ok: tuple[str, ...] = ()  # other answers a facilitator would accept

    def accepts(self, answer: str | None) -> bool:
        return answer == self.answer or answer in self.also_ok


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    summary: str
    weekday: int  # 0 = Monday
    start: str  # "HH:MM" local time the scenario opens
    description: str  # what the team knows at the start; becomes the drill's profile description
    affected_functions: str
    injects: tuple[Inject, ...]
    answer_key: dict[str, KeyAnswer]
    expected_outcome: str
    belief_inject: int  # 1-based inject by which the facts support a reasonable belief
    model_play: dict[int, tuple[str, ...]]  # inject number -> actions, for --walkthrough
    clock_note: str
    debrief: tuple[str, ...] = field(default_factory=tuple)

    @property
    def length_hours(self) -> float:
        return self.injects[-1].minutes / 60


EXAMPLE_CU = {
    "cu_name": "Example Federal Credit Union (fictional)",
    "charter": "00000",
    "reporter_name": "Drill Participant",
    "reporter_title": "Exercise role: incident commander",
    "reporter_phone": "(555) 010-0100",
    "reporter_email": "drill@example.org",
}

H = 60  # minutes per hour, for readable offsets

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="core-ransomware",
        title="Core provider ransomware on a Friday evening",
        summary="Your core processing provider calls about a 'security event' and takes your instance offline.",
        weekday=4,
        start="16:45",
        description=(
            "Late Friday afternoon, the core processing provider calls the on-call line about a security "
            "event in its hosting environment. Core, online banking and card authorizations are affected."
        ),
        affected_functions="Core processing, online and mobile banking, card authorizations",
        injects=(
            Inject(0, "Call from your core provider",
                   "The incident manager at Example Core Services, Inc. calls your on-call line. They are "
                   "investigating a security event in their hosting environment and have taken several client "
                   "instances offline as a precaution, including yours. Next update in about two hours.",
                   third_party="Example Core Services, Inc."),
            Inject(20, "Members can't get in",
                   "The contact center reports a spike in calls. Online banking and the mobile app show "
                   "'temporarily unavailable.' Card authorizations are falling back to stand-in limits."),
            Inject(2 * H, "Provider confirms ransomware",
                   "The provider confirms ransomware in its hosting environment. Servers running your instance "
                   "were encrypted. They are still investigating whether data was taken. Restoring from offline "
                   "backups will take 24 to 48 hours."),
            Inject(3 * H, "Pressure from the corner office",
                   "Your CEO asks whether anyone has to be told tonight or whether it can wait until Monday. "
                   "Your cyber insurer's hotline asks for the policy number and whether any regulator has been "
                   "notified."),
            Inject(18 * H, "Saturday morning",
                   "The provider restores core in read-only mode. Branches open with manual procedures and "
                   "withdrawal limits. Online banking is still down."),
            Inject(48 * H, "Leak site claim",
                   "A ransomware group posts a claim naming the provider on its leak site. It is not yet clear "
                   "whether your members' data was included."),
            Inject(73 * H, "Monday afternoon: your examiner calls",
                   "Your NCUA examiner calls and asks when the credit union notified the agency, and how the "
                   "credit union decided the incident was reportable."),
        ),
        answer_key={
            "cyber_incident": KeyAnswer(YES, "Ransomware encrypted the systems running the credit union's core. Availability, and possibly confidentiality, were actually jeopardized without lawful authority."),
            "good_faith_exclusion": KeyAnswer(NO, "Nobody requested or authorized this activity."),
            "substantial": KeyAnswer(YES, "Appendix A lists ransomware attacks impacting critical systems or data. Core and member channels went down."),
            "prong_a": KeyAnswer(YES, "Vital member services (online banking, cards) were disrupted, a substantial loss of availability."),
            "prong_b": KeyAnswer(YES, "Business operations and member systems were disrupted by a cyberattack."),
            "prong_c": KeyAnswer(YES, "The disruption was caused by a compromise of a third-party data hosting provider."),
        },
        expected_outcome=REPORTABLE,
        belief_inject=3,
        model_play={1: ("note",), 3: ("belief", "assess"), 4: ("notify",)},
        clock_note=(
            "For a third-party incident, the 72 hours run from the provider's notice or the credit union's own "
            "reasonable belief, whichever is sooner. Here that is the provider's Friday evening call, not the "
            "later confirmation and not Monday morning."
        ),
        debrief=(
            "Who on the team is authorized to call 1-833-CYBERCU after hours, and is that written down?",
            "When did the 72-hour clock start, and did everyone in the room agree?",
            "What does your cyber insurance policy require, and by when? Insurer notice windows are often shorter than 72 hours.",
            "If member data turns out to be in the leak, who decides on member notice under Part 748 Appendix B and any state breach laws?",
            "Does the core provider's contract require it to notify you promptly, and did it?",
        ),
    ),
    Scenario(
        key="bec-wire",
        title="Business email compromise and a fraudulent wire",
        summary="A member says they never asked for yesterday's wire. The request came in by email.",
        weekday=1,
        start="10:10",
        description=(
            "A member calls to dispute a $48,500 outgoing wire sent yesterday. The request came by email to a "
            "member service representative, who confirmed it by replying to the same email address."
        ),
        affected_functions="Wire transfers, employee email",
        injects=(
            Inject(0, "A member disputes a wire",
                   "A member says they never requested yesterday's $48,500 wire to an out-of-state bank. The "
                   "request came by email to a member service representative, who confirmed it by replying to "
                   "the same address instead of calling the member."),
            Inject(45, "Something is wrong in the mailbox",
                   "IT finds an inbox rule in the representative's mailbox that forwards any message containing "
                   "'wire' to an outside address and deletes the original. Sign-in logs show access from an "
                   "unfamiliar foreign IP address since the representative clicked a phishing link last week. "
                   "The mailbox holds member statements and loan documents."),
            Inject(90, "Recall requested",
                   "Your wire team sends a recall request to the receiving bank. No response yet."),
            Inject(4 * H, "Scope of access",
                   "Mail logs show the attacker read the mailbox for six days, including messages with full "
                   "account numbers for about 40 members."),
            Inject(24 * H, "Funds are gone",
                   "The receiving bank says the funds were withdrawn before the recall arrived. Your cyber "
                   "insurer asks whether the policy's social engineering coverage applies."),
            Inject(73 * H, "The board chair asks",
                   "The board chair asks whether the NCUA has been told and wants a briefing before the "
                   "supervisory committee meets."),
        ),
        answer_key={
            "cyber_incident": KeyAnswer(YES, "An attacker used stolen credentials to access an employee mailbox without lawful authority, jeopardizing the confidentiality and integrity of information on that system."),
            "good_faith_exclusion": KeyAnswer(NO, "Nobody authorized the access."),
            "substantial": KeyAnswer(YES, "Appendix A lists a social engineering attack leading to fraudulent wire transfers, and phishing that leads to compromise."),
            "prong_a": KeyAnswer(YES, "Unauthorized access to and exposure of sensitive member data, a substantial loss of confidentiality and integrity."),
            "prong_b": KeyAnswer(NO, "No system was made inoperable; the harm came through access, not disruption.", also_ok=(YES, UNSURE)),
            "prong_c": KeyAnswer(NO, "The compromise was of the credit union's own mailbox, not a CUSO, cloud provider or supply chain.", also_ok=(UNSURE,)),
        },
        expected_outcome=REPORTABLE,
        belief_inject=2,
        model_play={2: ("belief", "assess"), 3: ("notify",)},
        clock_note=(
            "There is no third-party notice here, so the clock starts when the credit union reasonably "
            "believes a reportable incident occurred. The mailbox findings at 45 minutes are the strongest "
            "point for that belief; the member's call alone could have been ordinary fraud."
        ),
        debrief=(
            "Would a call-back to a known phone number have stopped the wire? Is that rule written into the wire procedure?",
            "Who decides whether a Suspicious Activity Report is needed, and how does that clock relate to this one?",
            "Does the cyber insurance policy cover social engineering losses, and what notice does it require?",
            "Which members need to be told their account numbers were exposed, and who decides?",
            "Was multi-factor authentication on that mailbox, and why didn't it stop the sign-in?",
        ),
    ),
    Scenario(
        key="ddos-mitigated",
        title="Payday DDoS that the mitigation service absorbed",
        summary="Traffic to online banking spikes 40 times normal on a payday morning. Is it reportable?",
        weekday=0,
        start="08:30",
        description=(
            "On a payday Monday morning, traffic to online banking jumps to about 40 times normal and the "
            "contracted DDoS mitigation service engages automatically."
        ),
        affected_functions="Online banking (slow logins)",
        injects=(
            Inject(0, "Traffic alarm",
                   "Monitoring alerts on traffic to online banking at about 40 times normal. Your contracted "
                   "DDoS mitigation service engages automatically."),
            Inject(15, "Slow logins",
                   "Some members report slow logins, with pages taking five to eight seconds. Online banking "
                   "stays up."),
            Inject(50, "Attack absorbed",
                   "The mitigation provider reports the attack fully absorbed. Login success rates stayed normal "
                   "the whole time. There are no signs of intrusion, and firewall logs show no exploit attempts."),
            Inject(3 * H, "A claim on social media",
                   "An online group claims it 'took down' several credit unions, including yours. A local "
                   "reporter emails asking for comment."),
            Inject(24 * H, "Post-incident review",
                   "The review finds 22 minutes of degraded performance, no downtime, and no data accessed."),
        ),
        answer_key={
            "cyber_incident": KeyAnswer(YES, "A denial of service attack imminently jeopardized the availability of online banking.", also_ok=(UNSURE,)),
            "good_faith_exclusion": KeyAnswer(NO, "Nobody requested the traffic."),
            "substantial": KeyAnswer(NO, "Appendix B lists a denial of service attack with minimal impact on service availability. Service stayed up, slowed for 22 minutes, and no data was touched."),
        },
        expected_outcome=NOT_REPORTABLE,
        belief_inject=3,
        model_play={3: ("assess",), 4: ("note",)},
        clock_note=(
            "The 72-hour clock runs only from a reasonable belief that a reportable incident occurred. A "
            "well-documented decision that an incident is not reportable is the right result here, and "
            "23-CU-07 expects every incident to be documented."
        ),
        debrief=(
            "What would have made this reportable? Appendix A lists a DDoS causing significant downtime.",
            "Does a public claim of responsibility change the facts? Who answers the reporter, and with what?",
            "Is the decision and its reasoning recorded where an examiner can find it later?",
            "If the team was unsure, did it know that 23-CU-07 says to contact the NCUA as soon as possible?",
        ),
    ),
    Scenario(
        key="vendor-exposure",
        title="Member statements exposed by a print vendor",
        summary="Your statement print-and-mail vendor reports a publicly readable cloud storage bucket.",
        weekday=2,
        start="14:00",
        description=(
            "The credit union's statement print-and-mail vendor emails that a cloud storage bucket holding "
            "statement files was publicly readable."
        ),
        affected_functions="Member statement files held by a third-party vendor",
        injects=(
            Inject(0, "Email from the vendor's privacy office",
                   "Example Print & Mail Co. emails that a security researcher found one of its cloud storage "
                   "buckets publicly readable. It held statement files for several credit union clients, "
                   "including yours: about 12,400 members' names, mailing addresses, full account numbers and "
                   "balances. The vendor locked the bucket this morning.",
                   third_party="Example Print & Mail Co."),
            Inject(60, "What the contract says",
                   "Vendor management pulls the contract: the vendor must notify you within 48 hours of "
                   "discovery. The vendor's email says it learned of the problem five days ago."),
            Inject(4 * H, "Files confirmed",
                   "The vendor sends a file list. Your compliance officer confirms the files match last month's "
                   "statement run."),
            Inject(24 * H, "Someone else downloaded them",
                   "The vendor's forensic firm reports downloads from IP addresses other than the researcher's "
                   "during the exposure window."),
            Inject(48 * H, "Member notice questions",
                   "Counsel raises member notice under Part 748 Appendix B and state breach notification laws "
                   "for members in other states."),
            Inject(73 * H, "Your examiner calls",
                   "Your NCUA examiner calls about the vendor exposure and asks when the credit union notified "
                   "the agency."),
        ),
        answer_key={
            "cyber_incident": KeyAnswer(YES, "Sensitive member information on an information system was exposed without lawful authority."),
            "good_faith_exclusion": KeyAnswer(NO, "The researcher's finding does not make the exposure authorized activity requested by the system owner.", also_ok=(UNSURE,)),
            "substantial": KeyAnswer(YES, "Appendix A lists a misconfigured storage account exposing a substantial amount of sensitive member information, and a third party's notice of a breach of member information."),
            "prong_a": KeyAnswer(YES, "Exposure of sensitive member data is a substantial loss of confidentiality."),
            "prong_b": KeyAnswer(NO, "Nothing was disrupted.", also_ok=(UNSURE,)),
            "prong_c": KeyAnswer(YES, "The exposure came through a contracted third-party data host."),
        },
        expected_outcome=REPORTABLE,
        belief_inject=1,
        model_play={1: ("belief", "assess"), 3: ("notify",)},
        clock_note=(
            "The clock starts at the vendor's notice to the credit union, not at the vendor's own discovery "
            "five days earlier. The vendor's late notice is a contract issue to raise, not a reason to wait."
        ),
        debrief=(
            "When did the clock start: the vendor's email, or the file confirmation four hours later? Why?",
            "What will you do about the vendor missing its contractual notice window?",
            "Who owns the member notice decision, and what do state laws require for out-of-state members?",
            "Does your vendor due diligence cover how vendors store your data in the cloud?",
        ),
    ),
)


def by_key(key: str) -> Scenario:
    for s in SCENARIOS:
        if s.key == key:
            return s
    raise KeyError(key)


def keys() -> list[str]:
    return [s.key for s in SCENARIOS]

