# ncua72: the 72-hour cyber incident clock for credit unions

A small, dependency-free Python tool that helps a federally insured credit union decide whether a cyber incident is reportable to the NCUA, track the 72-hour notification deadline, keep a tamper-evident incident log, and hand an examiner a clean record of what was decided and when.

> **Not legal advice.** This tool records your answers and applies the rule as written in the sources below. It does not make the decision for you. Verify every determination against the current text of 12 CFR 748.1(c) and current NCUA guidance, and involve counsel where needed.

## The problem

Since September 1, 2023, every federally insured credit union must notify the NCUA "as soon as possible but no later than 72 hours" after it "reasonably believes" it has experienced a reportable cyber incident (12 CFR 748.1(c)). When the incident comes through a CUSO, cloud provider or other third-party data host, the clock starts when the third party notifies the credit union or when the credit union forms its own reasonable belief, whichever is sooner (NCUA Letter 23-CU-07).

In practice, the hard part is not the phone call. It is what happens in the hours before and the months after:

- **The determination is made under pressure.** At 2 a.m. during a ransomware event, someone has to work through the definition of a cyber incident, the good-faith exclusion, whether it is "substantial," and three separate prongs. That reasoning is rarely written down at the time.
- **The clock start is ambiguous.** "Reasonable belief" is a judgment, and a vendor's call may start the clock earlier. Teams lose track of which time controls.
- **Examiners ask later.** At the next exam, the credit union needs to show what it knew, when it knew it, why it decided what it decided, and when it notified, for reportable and non-reportable incidents alike. NCUA's letter also expects credit unions to document all incidents.

Many teams handle this with a spreadsheet and memory, and general incident response tools do not usually encode NCUA's specific tests. This tool fills that gap with something a small IT or security team can run on a laptop in minutes.

## What it does

- **Walks you through the reportability tests** from 12 CFR 748.1(c), one at a time, with the rule's own language and citation. Every answer (yes, no or unsure) requires a written rationale, which goes into the record.
- **Starts the 72-hour clock** from the earlier of the reasonable-belief time or a third-party notice, and shows the deadline and time left in your local time zone (daylight saving time handled).
- **Keeps an append-only, hash-chained log** (one JSON Lines file per incident). Each entry carries the SHA-256 of the entry before it, so any later edit, deletion or reordering is detectable with `ncua72 verify`. Corrections are new entries, never edits.
- **Prints the initial notification summary** with the items NCUA's letter asks credit unions to be ready to provide, and reminds you what to leave out of the first notice.
- **Builds an examiner packet** as a PDF, Markdown or printable HTML: profile, determination with each test's answer and rationale, clock, notification record, full timeline and an integrity check.
- **Shows a local dashboard** (`ncua72 serve`) with a live countdown for every open incident and a PDF download for each packet. It is read-only and listens on 127.0.0.1 only.

No third-party packages, except one optional library ([reportlab](https://pypi.org/project/reportlab/)) for PDF export. No network calls. Your incident data stays in a folder you choose.

## Quick start

Requires Python 3.10 or later.

```sh
git clone https://github.com/justingburns/ncua-cyber-incident-72hr.git
cd ncua-cyber-incident-72hr
pip install ".[pdf]"     # adds the ncua72 command, with PDF export
# Without PDF export: pip install .
```

Set your time zone once (or pass `--tz` each time):

```sh
export NCUA72_TZ=America/Los_Angeles
export NCUA72_HOME=/secure/share/incidents    # where the logs live; default ./incidents
```

Open an incident and walk through the tests:

```sh
ncua72 new                      # prompts for the profile when run in a terminal
ncua72 assess CI-20261109-5A7C  # walks the tests; asks when reasonable belief formed
ncua72 status                   # deadline and time left for every incident
```

Record what happens as you go:

```sh
ncua72 third-party CI-20261109-5A7C --at "2026-11-09 06:40" --party "Example Core Services, Inc."
ncua72 believe     CI-20261109-5A7C --at "2026-11-09 07:30" --basis "Provider confirmed our instance was encrypted"
ncua72 note        CI-20261109-5A7C "IR firm engaged" --at "2026-11-09 07:15"
ncua72 summary     CI-20261109-5A7C            # text to read or send at initial notification
ncua72 notified    CI-20261109-5A7C --at "2026-11-09 09:10" --method phone --reference "Voicemail left"
ncua72 packet      CI-20261109-5A7C --format pdf                 # writes CI-20261109-5A7C.pdf
ncua72 packet      CI-20261109-5A7C --format html --out packet.html
ncua72 verify                                   # check every log's hash chain
ncua72 serve                                    # dashboard at http://127.0.0.1:8072/
```

### On Windows

Windows has no built-in time zone database, so install `tzdata` too. These steps run the tool straight from the downloaded folder with `py -m ncua72`, with no install. If `py` isn't found, use `python`.

PowerShell:

```powershell
git clone https://github.com/justingburns/ncua-cyber-incident-72hr.git
cd ncua-cyber-incident-72hr
py -m pip install tzdata reportlab
$env:NCUA72_TZ = "America/Los_Angeles"
py -m ncua72 --home examples\incidents status
py -m ncua72 --home examples\incidents packet CI-20261109-5A7C --format pdf --out sample.pdf
start sample.pdf
py -m ncua72 new
py -m ncua72 serve
```

Command Prompt:

```bat
git clone https://github.com/justingburns/ncua-cyber-incident-72hr.git
cd ncua-cyber-incident-72hr
py -m pip install tzdata reportlab
set NCUA72_TZ=America/Los_Angeles
py -m ncua72 --home examples\incidents status
py -m ncua72 --home examples\incidents packet CI-20261109-5A7C --format pdf --out sample.pdf
start sample.pdf
py -m ncua72 new
py -m ncua72 serve
```

The time zone setting lasts for that window only. No git? Use **Code > Download ZIP** on the repository page, unzip it, and `cd` into the folder.

### PDF export

`--format pdf` needs `reportlab`. Without it, the tool says how to install it and every other command still works. The PDF's Author is the incident's reporting individual unless you pass `--author`. Creator and Producer are left blank, so the file names no software in its properties.

Times you type are read in your time zone. Use `now`, `YYYY-MM-DD HH:MM` (24-hour) or full ISO 8601. Every entry also records when it was actually written, so a backdated "as of" time and the real recording time are both kept.

For scripted use, `ncua72 assess ID --answers answers.json` takes the answers from a file. See [examples/answers-core-provider-ransomware.json](examples/answers-core-provider-ransomware.json).

## The tests it walks

| # | Test | Source |
|---|---|---|
| 1 | Is it a cyber incident: an occurrence that actually or imminently jeopardizes, without lawful authority, information on an information system or the system itself? | 12 CFR 748.1(c)(2) |
| 2 | Is it excluded: performed in good faith at the system owner's or operator's specific request (for example, a contracted penetration test)? | 12 CFR 748.1(c)(1)(ii) |
| 3 | Is it a *substantial* cyber incident? NCUA's Appendices A and B give examples on each side. | 12 CFR 748.1(c)(1)(i); 23-CU-07 |
| 4 | Prong A: substantial loss of confidentiality, integrity or availability from unauthorized access to or exposure of sensitive data, disruption of vital member services, or a serious impact on operational systems? | 12 CFR 748.1(c)(1)(i)(A) |
| 5 | Prong B: disruption of business operations, vital member services or a member information system from a cyberattack or exploited vulnerability? | 12 CFR 748.1(c)(1)(i)(B) |
| 6 | Prong C: disruption or unauthorized access to sensitive data through a compromised CUSO, cloud provider, other third-party data host, or the supply chain? | 12 CFR 748.1(c)(1)(i)(C) |

**Outcome.** Reportable when tests 1 to 3 clear and any one prong is met. Not reportable when it is not a cyber incident, is excluded, is not substantial, or meets no prong. **Undetermined** when an answer is "unsure." NCUA's letter says a credit union that is unsure should contact the NCUA as soon as possible, and the tool says so.

## Example output

`ncua72 status`:

```text
CI-20261109-5A7C  Core processing provider ransomware  [closed]
   Determination: REPORTABLE
   NCUA notified Mon Nov 9, 2026 9:10 AM PST, 2d 21h 30m before the Thu Nov 12, 2026 6:40 AM PST deadline.
```

`ncua72 summary CI-20261109-5A7C`:

```text
NCUA CYBER INCIDENT NOTIFICATION (initial)

Credit union: Example Federal Credit Union
Charter number: 00000
Reporting individual: Pat Example, Chief Information Security Officer
Telephone: (555) 010-0100
Email: pat.example@example.org
Reasonable belief formed: Mon Nov 9, 2026 7:30 AM PST
Third-party notice received: Mon Nov 9, 2026 6:40 AM PST (Example Core Services, Inc.)
Description: Our core processing provider reported a ransomware attack on the environment that hosts our core. ...
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

The full examiner packet for this fictional incident is in [examples/sample-packet.pdf](examples/sample-packet.pdf), with Markdown and HTML versions in [examples/sample-packet.md](examples/sample-packet.md) and [examples/sample-packet.html](examples/sample-packet.html). Rebuild them with `sh examples/run-sample.sh`. The sample was entered after the fact, so its "Recorded" times are later than the events; in real use you log as things happen.

## Where the data lives, and how to protect it

Each incident is one file, `<NCUA72_HOME>/<incident id>.jsonl`. Keep that folder on storage with access controls and backups that match your incident response records policy. The hash chain shows tampering; it does not prevent it, and it does not encrypt anything. For stronger assurance, copy the final hash from `ncua72 verify` into your ticket or IR report at key moments. The `.gitignore` keeps `incidents/` out of version control. Do not commit real incident data.

## Sources

Read for this version (November 2026):

- 12 CFR 748.1(c), Cyber incident notification requirements (eCFR; amended by 88 FR 12816, Mar. 1, 2023): https://www.ecfr.gov/current/title-12/chapter-VII/subchapter-A/part-748
- NCUA Letter to Credit Unions 23-CU-07, *Cyber Incident Notification Requirements* (August 2023): https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements
- 23-CU-07 Appendix A, incidents that likely would qualify: https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-a
- 23-CU-07 Appendix B, incidents that likely would not qualify: https://ncua.gov/regulation-supervision/letters-credit-unions-other-guidance/cyber-incident-notification-requirements/appendix-b

Phone numbers, email addresses and portals change. Confirm the current notification channels on ncua.gov before you rely on the ones this tool prints.

## Development

```sh
pip install reportlab tzdata   # PDF tests are skipped without reportlab
python -m unittest discover -s tests -v
```

The code is small on purpose:

| File | Purpose |
|---|---|
| `ncua72/rule.py` | The tests, citations and decision logic |
| `ncua72/clock.py` | Time parsing, zones and the 72-hour clock |
| `ncua72/log.py` | Append-only, hash-chained log |
| `ncua72/incident.py` | Rebuilds an incident's state from its log |
| `ncua72/report.py` | Notification summary and examiner packet (Markdown, HTML) |
| `ncua72/pdf.py` | PDF version of the packet (optional reportlab) |
| `ncua72/cli.py` | The `ncua72` command |
| `ncua72/web.py` | Read-only local dashboard |

Issues and pull requests are welcome, especially from credit union security and compliance teams who see a test or a workflow that should work differently.

## License

MIT. See [LICENSE](LICENSE).
