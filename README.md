# PGAI Voice Tester

An automated patient that phones a medical practice's AI receptionist, holds a real
conversation with it, and writes down what went wrong.

It places outbound calls to `+1-805-439-8008`, plays one of twelve patient personas
over the phone via OpenAI's Realtime API, records both sides, and drafts a bug
report from the transcripts.

- **How it works and why:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **What it found:** [BUGS.md](BUGS.md)
- **The calls:** [`calls/`](calls/) — one directory each, with `transcript.txt`,
  `transcript.json`, `recording.mp3`, `meta.json` and the raw `events.jsonl`

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill it in
```

`.env` needs an `OPENAI_API_KEY`, your Twilio SID/token, and the one Twilio number
you'll call from. Two things that will otherwise cost you an hour:

- **A Twilio trial account cannot do this.** Trial accounts only dial numbers
  you've verified as your own, and you can't verify someone else's line. Upgrade
  first.
- **Twilio needs a public URL** to stream audio to. Install `cloudflared`
  (`brew install cloudflared`, no account needed) and the tool opens the tunnel
  itself, or set `PUBLIC_WSS_URL` in `.env` to your own.

## Run

One command — starts the bridge, opens the tunnel, places every call in sequence:

```bash
python run_calls.py --all
python collect.py               # download recording.mp3 for each call
python analyze.py               # draft candidate bugs -> BUGS_draft.md
```

```bash
python run_calls.py --scenario refill closed_weekend   # just these
python run_calls.py --all --dry-run                    # print TwiML, spend nothing
```

## Testing without a phone bill

`tests/loopback.py` runs a full call with no telephony. It stands up the real
bridge, speaks Twilio's WebSocket protocol at it, and puts a second Realtime
session on the far end playing a clinic receptionist:

```bash
python tests/loopback.py refill
pytest tests/test_units.py -q
```

Four of the six bugs in this project were caught here, for cents, before any
Twilio minutes were spent. The fake receptionist has one deliberate flaw — it
books weekend appointments without checking the calendar — so `analyze.py` gets
verified end to end too.

## The scenarios

| Scenario | What it probes |
| --- | --- |
| `book_new` | Baseline: new patient books a physical |
| `reschedule` | Moves an appointment — is the old slot released? |
| `cancel` | Plain cancellation, no rebook |
| `refill` | Drug, dose and pharmacy captured correctly? |
| `hours_location` | Factual accuracy on hours, offices, parking |
| `insurance` | Does it claim network status or quote prices it can't know? |
| `closed_weekend` | Will it book a Sunday when the office is shut? |
| `barge_in` | Interruptions — does it stop talking and keep state? |
| `vague` | Caller who can't say what's wrong |
| `topic_switch` | Books, detours into billing — does the booking survive? |
| `spelling` | Hard-to-spell name, accented speech, "say that again?" |
| `medical_advice` | Asks for a dosing change — must refuse and escalate |

Twelve for a ten-call minimum, so a dropped call doesn't put the submission under
the bar.

## Cost

About **$0.40–$0.70 per call** — Twilio outbound is ~$0.014/min, the rest is
Realtime audio tokens. Twelve calls is under $10. Every scenario has a hard
duration cap and the watchdog hangs up on dead air, so a stuck call can't run up a
bill.

## What to do when this finishes running

Plain English, no developer knowledge assumed.

1. **Open the `calls/` folder.** One folder per phone call.
2. **Read `transcript.txt`** — the conversation, timestamped, labelled `AGENT`
   (theirs) and `PATIENT` (ours). If it reads like two people talking, it worked.
3. **Play `recording.mp3`.** Reviewers listen to this before reading any code, so
   it's the thing that actually decides the outcome.
4. **Count the folders.** You need ten or more with both a transcript and an MP3.
   Re-run any that failed with `python run_calls.py --scenario <name>`.
5. **Read `BUGS.md`.** Findings, each with the call and timestamp to hear it at.
6. **Record the two Loom videos.** Webcam on, your own voice — one walkthrough
   (under 3 min), one of you debugging with AI.
7. **Push to a public GitHub repo and submit the form.** Include the Twilio number
   you called from in `+1XXXXXXXXXX` form; they can't grade the calls without it.
