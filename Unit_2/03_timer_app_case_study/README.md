# Timer App (example)

This folder contains a local timer/alarm/reminder app implementation based on the requirements and architecture documents.

## Quick start

From this folder:

- Install in editable mode:
  - `python -m pip install -e .`

- Run help:
  - `python -m timer_app --help`

## Storage

By default the app stores data in `data/timer_app.json`.
You can override it with `--store path/to/file.json`.

## Smoke tests (minimal side effects)

To avoid mutating repo data under `data/`, run commands against a temporary store file. This exercises success paths for alarms/reminders/world/convert.

Note: This snippet intentionally avoids long-running commands like `run` (scheduler loop), `countdown`, and `pomodoro`.

```sh
set -eu

TMPDIR="$(mktemp -d -t timer-app-smoke.XXXXXX)"
STORE="$TMPDIR/state.json"
trap 'rm -rf -- "$TMPDIR"' 0

app() { python -m timer_app --store "$STORE" "$@"; }

ALARM_ID="$(app alarms add 07:30 --recurrence daily --label 'Smoke alarm' | awk '{print $3}')"
app alarms list | grep -q "$ALARM_ID"
app alarms disable "$ALARM_ID"
app alarms delete "$ALARM_ID"

REM_ID="$(app reminders add 2099-01-01 09:00 --tz Europe/Berlin --message 'Smoke reminder' | awk '{print $3}')"
app reminders list | grep -q "$REM_ID"

app world add Europe/Berlin
app world add America/New_York
app world now | grep -q 'Europe/Berlin:'

app convert tz 2026-02-23 12:00 Europe/Berlin America/New_York | grep -q '^UTC:'
app convert utc 2026-02-23 12:00 Europe/Berlin | grep -q 'UTC'

echo "Smoke tests passed."
```

## Examples

- Add an alarm (daily):
  - `python -m timer_app alarms add 07:30 --recurrence daily --label "Wake up"`

- List alarms:
  - `python -m timer_app alarms list`

- Add a reminder (local tz by default):
  - `python -m timer_app reminders add 2026-02-24 09:00 --message "Standup"`

- Run the scheduler (alarms/reminders fire while running):
  - `python -m timer_app run`

- World clock:
  - `python -m timer_app world add Europe/Berlin`
  - `python -m timer_app world add America/New_York`
  - `python -m timer_app world now`

- Convert date/time between time zones:
  - `python -m timer_app convert tz 2026-02-23 12:00 Europe/Berlin America/New_York`
