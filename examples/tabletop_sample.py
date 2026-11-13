"""Rebuild the sample tabletop after-action report in examples/.

Plays the core-ransomware scenario as a team that is a little slow: it records
its reasonable belief and assesses only after the CEO's question (inject 4) and
calls the NCUA on Saturday morning (inject 5). It is unsure about Prong B. Run from the repository root:

    python examples/tabletop_sample.py
"""

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ncua72.scenarios import by_key  # noqa: E402
from ncua72.tabletop import after_action_markdown, after_action_pdf, finish_drill, load_drill, start_drill  # noqa: E402

TZ = ZoneInfo("America/Los_Angeles")
OUT = Path("examples")
DRILLS = OUT / "drills"

ANSWERS = ["yes", "Ransomware at the core provider.", "no", "Not authorized.", "yes", "Core and cards down.",
           "yes", "Member services disrupted.", "unsure", "Not sure an outage at the provider counts as our disruption.", "yes", "Through the core provider."]
REPLIES = iter(
    ["c", "c", "l", "Waiting for the provider's next update before deciding.", "c",
     "b", "CEO asked; provider confirmation at 6:45 PM was enough.", "a", *ANSWERS, "c",
     "n", "phone", "Voicemail at 1-833-CYBERCU with name, charter, contact and description.", "c",
     "c", "c"]
)

shutil.rmtree(DRILLS, ignore_errors=True)
drill = start_drill(by_key("core-ransomware"), DRILLS, TZ, "pexample", speed=0, facilitator="Pat Example",
                    participants="CEO, CISO, COO, Compliance Officer, Marketing",
                    now=datetime(2026, 11, 13, 19, 0, tzinfo=timezone.utc), out=lambda _: None)
drill.play(lambda _: next(REPLIES))
sc = finish_drill(drill)
inc = load_drill(DRILLS, drill.log.incident_id)
(OUT / "tabletop-sample-after-action.md").write_text(after_action_markdown(inc, TZ), encoding="utf-8")
(OUT / "tabletop-sample-after-action.pdf").write_bytes(after_action_pdf(inc, TZ, author="Justin Burns, MBA"))
shutil.rmtree(DRILLS)
print(f"Score {sc.total} of 100. Wrote examples/tabletop-sample-after-action.md and .pdf")
