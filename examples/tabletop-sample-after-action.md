# Tabletop Exercise After-Action Report: TT-20261113-79E1

Core provider ransomware on a Friday evening

> EXERCISE ONLY. This is a tabletop drill, not a real incident. Nothing here is reported to the NCUA. This report is a training aid, not legal advice. The answer keys apply 12 CFR 748.1(c) and NCUA Letter 23-CU-07 to fictional facts; a facilitator may reasonably disagree with a call. Verify real determinations against the current rule and NCUA guidance, and consult counsel where needed.

| Field | Value |
|---|---|
| Score | 92 of 100: Strong |
| Scenario | Core provider ransomware on a Friday evening (core-ransomware) |
| Credit union | Example Federal Credit Union (fictional) |
| Facilitator | Pat Example |
| Participants | CEO, CISO, COO, Compliance Officer, Marketing |
| Exercise run | Fri Nov 13, 2026 11:48 AM PST |
| Simulated start | Fri Nov 13, 2026 4:45 PM PST |
| Simulated clock | frozen between injects |
| Status | complete |

## 1. Score

| Area | Points | Out of | Detail |
|---|---|---|---|
| Reportability call | 40 | 40 | Team: REPORTABLE. Answer key: REPORTABLE. |
| Test-by-test answers | 17 | 20 | 5 of 6 match the answer key. |
| NCUA notice within 72 hours | 25 | 30 | Notified 18h 00m after the clock started, 2d 6h 00m before the deadline. |
| Reasonable belief recorded promptly | 10 | 10 | Recorded Fri Nov 13, 2026 7:45 PM PST, in step with the facts. |

## 2. Findings

- Strength: the team reached the right call, REPORTABLE.
- Gap: one test answer differs from the answer key. The table below shows why.
- Gap: the notice was on time, but the rule says as soon as possible, and it took most of a day. Ask what held it up.

## 3. Reportability call

Team: REPORTABLE. Answer key: REPORTABLE.

| Test | Team | Team's reasoning | Key | Why |
|---|---|---|---|---|
| Is it a cyber incident? | Yes | Ransomware at the core provider. | Yes | Ransomware encrypted the systems running the credit union's core. Availability, and possibly confidentiality, were actually jeopardized without lawful authority. |
| Is it excluded as authorized, good-faith activity? | No | Not authorized. | No | Nobody requested or authorized this activity. |
| Is the cyber incident substantial? | Yes | Core and cards down. | Yes | Appendix A lists ransomware attacks impacting critical systems or data. Core and member channels went down. |
| Prong A: substantial loss of confidentiality, integrity or availability | Yes | Member services disrupted. | Yes | Vital member services (online banking, cards) were disrupted, a substantial loss of availability. |
| Prong B: disruption from a cyberattack or exploited vulnerability | Unsure  (differs) | Not sure an outage at the provider counts as our disruption. | Yes | Business operations and member systems were disrupted by a cyberattack. |
| Prong C: third-party or supply chain compromise | Yes | Through the core provider. | Yes | The disruption was caused by a compromise of a third-party data hosting provider. |

## 4. The 72-hour clock

For a third-party incident, the 72 hours run from the provider's notice or the credit union's own reasonable belief, whichever is sooner. Here that is the provider's Friday evening call, not the later confirmation and not Monday morning.

| Field | Value |
|---|---|
| Clock should have started | Fri Nov 13, 2026 4:45 PM PST (third-party notice) |
| Deadline | Mon Nov 16, 2026 4:45 PM PST |
| Team's clock | NCUA notified Sat Nov 14, 2026 10:45 AM PST, 2d 6h 00m before the Mon Nov 16, 2026 4:45 PM PST deadline. |
| Team's reasonable belief | Fri Nov 13, 2026 7:45 PM PST |
| NCUA notified (simulated) | Sat Nov 14, 2026 10:45 AM PST |

## 5. Debrief questions

- Who on the team is authorized to call 1-833-CYBERCU after hours, and is that written down?
- When did the 72-hour clock start, and did everyone in the room agree?
- What does your cyber insurance policy require, and by when? Insurer notice windows are often shorter than 72 hours.
- If member data turns out to be in the leak, who decides on member notice under Part 748 Appendix B and any state breach laws?
- Does the core provider's contract require it to notify you promptly, and did it?

## 6. Exercise timeline

| # | Simulated time | Entry |
|---|---|---|
| 1 | Fri Nov 13, 2026 4:45 PM PST | Exercise started: Core provider ransomware on a Friday evening. |
| 2 | Fri Nov 13, 2026 4:45 PM PST | Inject 1: Call from your core provider. The incident manager at Example Core Services, Inc. calls your on-call line. They are investigating a security event in their hosting environment and have taken several client instances offline as a precaution, including yours. Next update in about two hours. |
| 3 | Fri Nov 13, 2026 4:45 PM PST | Notice from third party Example Core Services, Inc. received Fri Nov 13, 2026 4:45 PM PST. Call from your core provider |
| 4 | Fri Nov 13, 2026 5:05 PM PST | Inject 2: Members can't get in. The contact center reports a spike in calls. Online banking and the mobile app show 'temporarily unavailable.' Card authorizations are falling back to stand-in limits. |
| 5 | Fri Nov 13, 2026 6:45 PM PST | Inject 3: Provider confirms ransomware. The provider confirms ransomware in its hosting environment. Servers running your instance were encrypted. They are still investigating whether data was taken. Restoring from offline backups will take 24 to 48 hours. |
| 6 | Fri Nov 13, 2026 6:45 PM PST | Note (as of Fri Nov 13, 2026 6:45 PM PST): Waiting for the provider's next update before deciding. |
| 7 | Fri Nov 13, 2026 7:45 PM PST | Inject 4: Pressure from the corner office. Your CEO asks whether anyone has to be told tonight or whether it can wait until Monday. Your cyber insurer's hotline asks for the policy number and whether any regulator has been notified. |
| 8 | Fri Nov 13, 2026 7:45 PM PST | Reasonable belief recorded as of Fri Nov 13, 2026 7:45 PM PST. Basis: CEO asked; provider confirmation at 6:45 PM was enough. |
| 9 | Fri Nov 13, 2026 7:45 PM PST | Team assessed reportability: REPORTABLE. A substantial cyber incident that meets Prongs A and C. |
| 10 | Sat Nov 14, 2026 10:45 AM PST | Inject 5: Saturday morning. The provider restores core in read-only mode. Branches open with manual procedures and withdrawal limits. Online banking is still down. |
| 11 | Sat Nov 14, 2026 10:45 AM PST | Team notified the NCUA (simulated) by phone. SIMULATED, exercise only. Voicemail at 1-833-CYBERCU with name, charter, contact and description. |
| 12 | Sun Nov 15, 2026 4:45 PM PST | Inject 6: Leak site claim. A ransomware group posts a claim naming the provider on its leak site. It is not yet clear whether your members' data was included. |
| 13 | Mon Nov 16, 2026 5:45 PM PST | Inject 7: Monday afternoon: your examiner calls. Your NCUA examiner calls and asks when the credit union notified the agency, and how the credit union decided the incident was reportable. |
| 14 | Mon Nov 16, 2026 5:45 PM PST | Exercise ended. Score 92 of 100. |

## 7. Log integrity

Verified: 14 entries, hash chain intact. Final SHA-256: 99e874fe802e3cd64975e965f6e85d52fcff31f7c1f2bc4cf4345fdecfe1d312

## 8. Sources

- 12 CFR 748.1(c), Cyber incident notification requirements: https://www.ecfr.gov/current/title-12/chapter-VII/subchapter-A/part-748
- NCUA Letter to Credit Unions 23-CU-07, Cyber Incident Notification Requirements (Aug. 2023): https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements
- 23-CU-07 Appendix A, examples that likely would qualify: https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-a
- 23-CU-07 Appendix B, examples that likely would not qualify: https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-b
