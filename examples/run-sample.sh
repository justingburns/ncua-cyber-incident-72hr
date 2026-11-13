#!/usr/bin/env sh
# Rebuilds the sample incident in examples/incidents and the sample packets.
# Fictional credit union, people and provider. Run from the repository root.
set -e
export NCUA72_HOME=examples/incidents NCUA72_TZ=America/Los_Angeles
ID=CI-20261109-5A7C
rm -f "$NCUA72_HOME/$ID.jsonl"

python3 -m ncua72 --actor pexample new --id "$ID" \
  --title "Core processing provider ransomware" \
  --cu-name "Example Federal Credit Union" --charter "00000" \
  --reporter-name "Pat Example" --reporter-title "Chief Information Security Officer" \
  --reporter-phone "(555) 010-0100" --reporter-email "pat.example@example.org" \
  --description "Our core processing provider reported a ransomware attack on the environment that hosts our core. Core, online banking and card authorizations were unavailable." \
  --affected-functions "Core processing, online and mobile banking, bill pay, card authorizations" \
  --sensitive unknown --discovered "2026-11-09 06:52"
python3 -m ncua72 --actor pexample third-party "$ID" --at "2026-11-09 06:40" \
  --party "Example Core Services, Inc." --summary "Provider called the on-call line: ransomware in its hosting environment; our instance affected."
python3 -m ncua72 --actor pexample note "$ID" "Incident response plan activated. IR retainer firm and cyber insurer notified." --at "2026-11-09 07:15"
python3 -m ncua72 --actor pexample assess "$ID" --answers examples/answers-core-provider-ransomware.json
python3 -m ncua72 --actor pexample believe "$ID" --at "2026-11-09 07:30" --basis "Provider confirmed our instance was encrypted; members unable to log in."
python3 -m ncua72 --actor pexample notified "$ID" --at "2026-11-09 09:10" --method phone --by "Pat Example" \
  --reference "Voicemail left at 1-833-CYBERCU with name, charter, contact and basic description"
python3 -m ncua72 --actor pexample note "$ID" "Provider restored core from clean backups. Services back for members." --at "2026-11-09 15:45"
python3 -m ncua72 --actor pexample close "$ID" --at "2026-11-10 17:00" --reason "Services restored. Data exposure review continues under the IR firm; member notice decision tracked separately."

python3 -m ncua72 --actor pexample summary "$ID" > examples/sample-notification-summary.txt
python3 -m ncua72 --actor pexample packet "$ID" --format md --out examples/sample-packet.md
python3 -m ncua72 --actor pexample packet "$ID" --format html --author "Justin Burns, MBA" --out examples/sample-packet.html
python3 -m ncua72 --actor pexample packet "$ID" --format pdf --author "Justin Burns, MBA" --out examples/sample-packet.pdf
python3 -m ncua72 verify "$ID"
