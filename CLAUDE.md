# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A test harness that phones a medical practice's AI receptionist, plays a scripted
patient over the phone, records and transcribes both sides, and reports bugs found in
the *other* system. The deliverable is the call evidence and the bug report, not a
service — nothing here runs as a daemon.

The target is the assessment line `+18054398008`, hardcoded as `run_calls.TARGET` and
guarded by a test. **Do not parameterise it.** A typo dials a stranger.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python -m pytest tests/test_units.py -q          # all unit tests
.venv/bin/python -m pytest tests/test_units.py -q -k vad   # a single test/group

.venv/bin/python tests/loopback.py refill        # full call, no telephony (~$0.02)
.venv/bin/python run_calls.py --all --dry-run    # print TwiML, spend nothing
.venv/bin/python run_calls.py --all              # live calls, ~$0.50 each
.venv/bin/python run_calls.py --scenario refill closed_weekend
IDENTITY=on_file .venv/bin/python run_calls.py --scenario closed_weekend

.venv/bin/python collect.py                      # Twilio recordings -> MP3
.venv/bin/python analyze.py                      # transcripts -> BUGS_draft.md

.venv/bin/python tools/make_docx.py                        # Markdown -> .docx
.venv/bin/python tools/make_docx.py LOOM1-WALKTHROUGH.md --compact
```

`tests/loopback.py` is the development loop. It needs only `OPENAI_API_KEY`, exercises
the real bridge end to end, and costs cents. Reach for it before any live call.

## Architecture

Four processes, one flow:

1. **`run_calls.py`** starts `bridge.py` in-process via uvicorn, brings up a public
   tunnel, and asks Twilio to dial with inline TwiML — `<Connect><Stream>` plus
   `<Parameter>` children. No webhook endpoint exists; the server is one WebSocket route.
2. **`bridge.py`** is the whole system. Twilio streams the live call in as base64 G.711
   μ-law; the bridge relays it to the OpenAI Realtime API configured with `audio/pcmu`
   in both directions, and relays the model's audio back. **Both legs use the same
   codec, so audio is a base64 string copied between sockets — there is no resampling
   or audio library, and adding one is almost certainly a mistake.**
3. **`collect.py`** downloads the Twilio recordings as MP3 (they arrive a few seconds
   after a call ends, so it polls).
4. **`analyze.py`** runs a QA rubric over the transcripts to draft candidates into
   `BUGS_draft.md`. Output is a draft: findings are verified by hand before reaching
   `BUGS.md`.

`bridge.py` runs three concurrent tasks per call — phone→model, model→phone, and a
watchdog — and the first to return decides `ended_reason`. Per-call artifacts land in
`calls/call-NN-<scenario>/`: `transcript.txt`, `transcript.json`, `meta.json`,
`recording.mp3`, and `events.jsonl` (the full Realtime event firehose, audio payloads
elided — this is the first place to look when a call misbehaves).

`scenarios.py` holds the personas. A `Scenario` is a frozen dataclass of persona plus
goal plus exit condition; `instructions()` renders the system prompt. `ORDER` drives
`--all` (the 12 primary scenarios); `ROUND2` is a further 20 probes that are written
but were never run.

## Constraints that cost real time to learn

**Twilio discards the query string on `<Stream url>`.** Scenario and output directory
travel as `<Parameter>` children and arrive in the `start` frame, which is why
`media_stream` waits for `start` before deciding anything. A stream that connects and
is instantly refused looks identical, from Twilio's side, to the server crashing.

**A phone line is never silent — it carries silence frames**, and server VAD needs to
*hear* that silence to close a turn. `tests/loopback.py`'s `PacedRelay` emits μ-law
silence when idle for exactly this reason. Send nothing and `speech_started` fires,
`speech_stopped` never does, and no transcript is ever produced.

**`response.done` means the model stopped generating, not that audio stopped playing.**
Silence is measured from a Twilio drain mark echoing back, otherwise the watchdog
interrupts the bot mid-sentence.

**Transcripts resolve after the audio they describe.** Turns are stamped with speech
start time (`State.agent_turn_at` / `bot_turn_at`) and sorted in `CallLog.close`. Stamp
them on event arrival and you get transcripts where the caller answers a question
before it was asked.

**`silence_duration_ms` below ~800 chops one agent turn into several**, so the bot
replies to half a sentence and then talks over the rest. 900 ms is the floor, enforced
by a test. Tune via `VAD_SILENCE_MS` / `VAD_TYPE`.

**The Realtime API nests audio config** under `session.audio.input|output` with
`{"type": "audio/pcmu"}` — not the older flat `input_audio_format`. Voices `fable`,
`onyx` and `nova` are reported to produce distorted audio over μ-law; a test pins the
allowed set. Function-call events have moved between API versions, so the `hang_up`
handler accepts both `response.function_call_arguments.done` and
`response.output_item.done` shapes.

**Tunnels lie about being ready.** cloudflared prints its hostname several seconds
before registering at the edge, and probing before the DNS record exists makes macOS
cache the NXDOMAIN so every retry then fails from cache. `establish_tunnel` waits for
"Registered tunnel connection", delays the first probe, verifies `/health` through the
public hostname, and falls through cloudflared → ngrok. cloudflared is preferred
because quick tunnels need no account.

**A Twilio trial account cannot run this** — trial accounts only dial numbers you have
verified as your own.

**`IDENTITY=on_file` exists because of a test-design flaw worth understanding.** The
practice keys demo records to caller ID. Running twelve personas down one phone number
meant ten could never be found, and the resulting failures were initially written up as
a lookup bug. Setting `IDENTITY=on_file` swaps a scenario's persona for the identity the
practice actually holds and leaves its task intact. Calls 1–12 are the confounded first
pass; 13–18 are the controlled re-run. **Keep both — the comparison between them is what
isolated the critical finding.** See the top of `BUGS.md`.

## Cost control

Every scenario carries `max_seconds`; the watchdog nudges once after 28 s of mutual
silence and hangs up at 50 s. Live calls run sequentially with a gap. Roughly
$0.40–0.70 per call, dominated by Realtime audio tokens rather than Twilio minutes.

## The .docx deliverables

`tools/make_docx.py` renders the Markdown deliverables to Word. Markdown is the source
of truth — GitHub renders it and the graders read the repo — and the `.docx` files are
generated copies for sharing. Regenerate them after editing any `.md`.

Two traps in that converter, both already fixed and both easy to reintroduce: a
fixed-layout Word table measures `w:tblGrid`, **not** cell widths, and page counts
cannot be estimated from line counts. Measure by rendering:

```bash
soffice --headless --convert-to pdf --outdir /tmp *.docx
```

`--compact` is for the one-page narration sheets. Verify they still fit after editing.
