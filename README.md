# PGAI Voice Tester

An automated patient that phones a medical practice's AI receptionist, holds a
real conversation with it, and writes down what went wrong.

It places outbound calls to the assessment line (`+1-805-439-8008`), plays one of
twelve patient personas over the phone via OpenAI's Realtime API, records both
sides, and drafts a bug report from the transcripts.

- **How it works and why it's built this way:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **What it found:** [BUGS.md](BUGS.md)
- **The calls:** [`calls/`](calls/) — one directory per call, each with
  `transcript.txt`, `transcript.json`, `recording.mp3`, `meta.json`, and the raw
  `events.jsonl`

---

## Setup

**1. Install**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure**

```bash
cp .env.example .env
```

Then fill in `.env`. You need three things:

| What | Where to get it |
| --- | --- |
| `OPENAI_API_KEY` | platform.openai.com → API keys. Billing must be enabled. |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Twilio Console home page. |
| `TWILIO_FROM_NUMBER` | Buy one US number in the Twilio Console. Use the same one for every call. |

**A Twilio trial account will not work.** Trial accounts can only dial numbers
you've verified as your own, and you can't verify someone else's line. The account
has to be upgraded before the first call will connect.

**3. Expose the bridge**

Twilio needs a public URL to stream audio to. Either install
[ngrok](https://ngrok.com/download) and let the tool open the tunnel for you, or
put your own public `wss://` URL in `.env` as `PUBLIC_WSS_URL`.

---

## Run

One command. It starts the bridge, opens the tunnel, and places every call in
sequence:

```bash
python run_calls.py --all
```

Then pull the audio down and analyse it:

```bash
python collect.py     # downloads recording.mp3 for each call
python analyze.py     # drafts candidate bugs -> findings.json, BUGS_draft.md
```

Other useful invocations:

```bash
python run_calls.py --scenario refill closed_weekend   # just these two
python run_calls.py --all --dry-run                    # print TwiML, spend nothing
```

---

## Testing without a phone bill

`tests/loopback.py` runs a complete call with no telephony at all. It stands up
the real bridge, speaks Twilio's WebSocket protocol at it, and puts a second
Realtime session on the far end playing a clinic receptionist. Same code path as a
live call, no Twilio account needed, a few cents per run:

```bash
python tests/loopback.py refill
python tests/loopback.py closed_weekend
```

This is how turn-taking, barge-in, transcription and the hang-up handshake were
debugged before any real money went through Twilio. The fake receptionist has one
deliberate flaw — it books weekend appointments without checking the calendar — so
`analyze.py` can be verified end to end too.

The pieces that don't need audio have ordinary tests:

```bash
pytest tests/test_units.py -q
```

---

## The scenarios

| Scenario | What it's probing |
| --- | --- |
| `book_new` | Baseline: new patient books a physical |
| `reschedule` | Moves an existing appointment; is the old slot released? |
| `cancel` | Plain cancellation with no rebook |
| `refill` | Drug, dose and pharmacy captured correctly? |
| `hours_location` | Factual accuracy on hours, offices, parking |
| `insurance` | Does it claim network status or quote prices it can't know? |
| `closed_weekend` | Will it book a Sunday when the office is shut? |
| `barge_in` | Interruptions — does it stop talking and keep state? |
| `vague` | Caller who can't say what's wrong |
| `topic_switch` | Books, detours into billing, does the booking survive? |
| `spelling` | Hard-to-spell name, accented speech, "say that again?" |
| `medical_advice` | Asks for a dosing change — must refuse and escalate |

Twelve scenarios for a ten-call minimum, so a dropped call doesn't put the
submission under the bar.

---

## Cost

Roughly **$0.40–$0.70 per call**: Twilio outbound is about $0.014/min, the rest is
Realtime API audio tokens. Twelve calls comes to well under $10. Every scenario has
a hard `max_seconds` ceiling and the watchdog hangs up on dead air, so a stuck call
can't quietly run up a bill.

---

## What to do when this finishes running

Plain English, no developer knowledge assumed.

1. **Look in the `calls/` folder.** There's one folder per phone call, named like
   `call-01-book_new`. Open any of them.
2. **Read `transcript.txt`.** It's the conversation, with timestamps, labelled
   `AGENT` (the practice's bot) and `PATIENT` (ours). If this reads like two people
   talking, the run worked.
3. **Play `recording.mp3`.** Double-click it. This is what the reviewers listen to
   first, and it's the thing the whole submission is graded on — if the audio is
   awkward, nothing else matters.
4. **Count the folders.** You need at least ten with both a transcript and an MP3.
   If some calls failed, run `python run_calls.py --scenario <name>` again for just
   those.
5. **Read `BUGS_draft.md`.** These are candidate bugs the analyser found. They are
   drafts — check each one against the actual audio before trusting it, then write
   the real ones up in `BUGS.md`.
6. **Then record the two Loom videos.** Webcam on, your own voice. One walking
   through the project (under 3 minutes), one showing you debugging with AI.
7. **Push to a public GitHub repo** and submit the form. Include the Twilio number
   you called from, in `+1XXXXXXXXXX` format, and make sure it's the number in your
   `.env` — they can't grade the call quality without it.
