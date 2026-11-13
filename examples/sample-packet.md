# Cyber Incident Record: CI-20261109-5A7C

Core processing provider ransomware

> This packet is a recordkeeping aid, not legal advice. It reflects the user's answers. Verify every determination against the current text of 12 CFR 748.1(c) and current NCUA guidance, and consult counsel where needed.

| Field | Value |
|---|---|
| Credit union | Example Federal Credit Union (charter 00000) |
| Determination | REPORTABLE |
| 72-hour clock | NOTIFIED ON TIME |
| Clock detail | NCUA notified Mon Nov 9, 2026 9:10 AM PST, 2d 21h 30m before the Thu Nov 12, 2026 6:40 AM PST deadline. |
| Prepared | Thu Nov 12, 2026 6:17 PM PST by pexample |

## 1. Incident profile

| Field | Value |
|---|---|
| Discovered | Mon Nov 9, 2026 6:52 AM PST |
| Description | Our core processing provider reported a ransomware attack on the environment that hosts our core. Core, online banking and card authorizations were unavailable. |
| Affected functions | Core processing, online and mobile banking, bill pay, card authorizations |
| Sensitive information compromised | Unknown at this time |
| Reporting individual | Pat Example, Chief Information Security Officer |
| Contact | (555) 010-0100 / pat.example@example.org |

## 2. Reportability determination

Outcome: REPORTABLE. A substantial cyber incident that meets Prongs A, B and C.

Assessed Thu Nov 12, 2026 6:17 PM PST by pexample.

| Test | Answer | Rationale | Citation |
|---|---|---|---|
| Is it a cyber incident? | Yes | Ransomware encrypted the core processing environment our provider hosts for us. Member account data and core availability were actually jeopardized without lawful authority. | 12 CFR 748.1(c)(2) (definition of cyber incident) |
| Is it excluded as authorized, good-faith activity? | No | No testing or other authorized activity was under way. The provider confirmed a criminal intrusion. | 12 CFR 748.1(c)(1)(ii) |
| Is the cyber incident substantial? | Yes | Core, online banking and card authorizations were unavailable for more than four hours. NCUA's Appendix A lists ransomware on critical systems as an example that likely qualifies. | 12 CFR 748.1(c)(1)(i); 23-CU-07 Appendices A and B |
| Prong A: substantial loss of confidentiality, integrity or availability | Yes | Vital member services (online banking, bill pay, shared branching) were disrupted. Exposure of member data is still being investigated. | 12 CFR 748.1(c)(1)(i)(A) |
| Prong B: disruption from a cyberattack or exploited vulnerability | Yes | The disruption resulted from a cyberattack (ransomware). | 12 CFR 748.1(c)(1)(i)(B) |
| Prong C: third-party or supply chain compromise | Yes | The disruption was caused by a compromise of our third-party core processing and data hosting provider. | 12 CFR 748.1(c)(1)(i)(C); 23-CU-07 |

## 3. Notification clock

| Field | Value |
|---|---|
| Reasonable belief formed | Mon Nov 9, 2026 7:30 AM PST |
| Basis for belief | Provider confirmed our instance was encrypted; members unable to log in. |
| Third-party notice received | Mon Nov 9, 2026 6:40 AM PST from Example Core Services, Inc. |
| Clock started by | third-party notice |
| Deadline (72 hours) | Thu Nov 12, 2026 6:40 AM PST |
| Status | NCUA notified Mon Nov 9, 2026 9:10 AM PST, 2d 21h 30m before the Thu Nov 12, 2026 6:40 AM PST deadline. |

## 4. NCUA notification record

| When | Method | By | Reference |
|---|---|---|---|
| Mon Nov 9, 2026 9:10 AM PST | phone | Pat Example | Voicemail left at 1-833-CYBERCU with name, charter, contact and basic description |

Notification summary prepared for NCUA:

```text
NCUA CYBER INCIDENT NOTIFICATION (initial)

Credit union: Example Federal Credit Union
Charter number: 00000
Reporting individual: Pat Example, Chief Information Security Officer
Telephone: (555) 010-0100
Email: pat.example@example.org
Reasonable belief formed: Mon Nov 9, 2026 7:30 AM PST
Third-party notice received: Mon Nov 9, 2026 6:40 AM PST (Example Core Services, Inc.)
Description: Our core processing provider reported a ransomware attack on the environment that hosts our core. Core, online banking and card authorizations were unavailable.
Affected functions: Core processing, online and mobile banking, bill pay, card authorizations
Sensitive information compromised: Unknown at this time

-- For the person reporting (not part of the notice) --
Deadline: Thu Nov 12, 2026 6:40 AM PST
How to notify:
  - Phone: 1-833-CYBERCU (1-833-292-3728); leave a voicemail if no one answers.
  - Secure email to cybercu@ncua.gov, sent through the NCUA Secure Email Message Center.
  - Other similar methods the NCUA may prescribe (12 CFR 748.1(c)).
Leave out of the initial notice: sensitive personally identifiable information, indicators of compromise, specific vulnerabilities, email attachments.
```

## 5. Timeline (append-only log)

| # | Recorded | By | Entry |
|---|---|---|---|
| 1 | Thu Nov 12, 2026 6:17 PM PST | pexample | Incident opened: Core processing provider ransomware. Discovered Mon Nov 9, 2026 6:52 AM PST. |
| 2 | Thu Nov 12, 2026 6:17 PM PST | pexample | Notice from third party Example Core Services, Inc. received Mon Nov 9, 2026 6:40 AM PST. Provider called the on-call line: ransomware in its hosting environment; our instance affected. |
| 3 | Thu Nov 12, 2026 6:17 PM PST | pexample | Note (as of Mon Nov 9, 2026 7:15 AM PST): Incident response plan activated. IR retainer firm and cyber insurer notified. |
| 4 | Thu Nov 12, 2026 6:17 PM PST | pexample | Reportability assessed: REPORTABLE. A substantial cyber incident that meets Prongs A, B and C. |
| 5 | Thu Nov 12, 2026 6:17 PM PST | pexample | Reasonable belief recorded as of Mon Nov 9, 2026 7:30 AM PST. Basis: Provider confirmed our instance was encrypted; members unable to log in. |
| 6 | Thu Nov 12, 2026 6:17 PM PST | pexample | NCUA notified by phone at Mon Nov 9, 2026 9:10 AM PST by Pat Example, reference Voicemail left at 1-833-CYBERCU with name, charter, contact and basic description. |
| 7 | Thu Nov 12, 2026 6:17 PM PST | pexample | Note (as of Mon Nov 9, 2026 3:45 PM PST): Provider restored core from clean backups. Services back for members. |
| 8 | Thu Nov 12, 2026 6:17 PM PST | pexample | Incident closed: Services restored. Data exposure review continues under the IR firm; member notice decision tracked separately. |

## 6. Log integrity

Verified: 8 entries, hash chain intact. Final SHA-256: 4b32ca632434643e9cfb17b3390b81eb69394d271b638e56f3a907452c78f6ac

Each log entry stores the SHA-256 of the entry before it. Editing, deleting or reordering any entry breaks the chain.

Closed: Services restored. Data exposure review continues under the IR firm; member notice decision tracked separately. (Tue Nov 10, 2026 5:00 PM PST).

## 7. Sources

- 12 CFR 748.1(c), Cyber incident notification requirements: https://www.ecfr.gov/current/title-12/chapter-VII/subchapter-A/part-748
- NCUA Letter to Credit Unions 23-CU-07, Cyber Incident Notification Requirements (Aug. 2023): https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements
- 23-CU-07 Appendix A, examples that likely would qualify: https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-a
- 23-CU-07 Appendix B, examples that likely would not qualify: https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-b
