# Loom 1 — Walkthrough script (3 min)

Beats, not a script. Say it your way — reading aloud sounds like reading aloud.

**0:00 · What I built**
- A bot that phones your test line and behaves like a patient. Twelve personas.
- It records both sides, transcribes them, and writes a bug report.
- Twelve calls, one command.

**0:25 · How it works** — *show `bridge.py`*
- Twilio dials your number and streams the live call to my server over a WebSocket.
- My server bridges that straight into OpenAI's Realtime API, which plays the patient.
- The trick: both legs speak G.711 μ-law at 8 kHz. So audio is a base64 string copied from one socket to the other — no resampling, no audio library anywhere.
- Realtime's voice-activity detection gives me turn-taking and barge-in for free.

**1:05 · Why I chose that** — *the part that matters*
- **Not a cascade** (speech-to-text → GPT → text-to-speech): every hop adds 100–300 ms, and your agent has its own latency budget. Stacked, that's exactly the awkward pauses you score down.
- **Not Pipecat**: the interesting code here *is* the bridge — barge-in, the hang-up handshake, the silence watchdog. A framework hides the thing I want to show you.
- **Not Vapi or Retell**: thirty lines and I'd be done, but then the platform owns every decision worth discussing — codec, VAD tuning, when to hang up.

**1:45 · How I kept it cheap** — *show `tests/loopback.py`*
- I built a loopback harness first: the real bridge, a fake Twilio client, and a second Realtime session playing a receptionist. A full call, no telephony.
- Four of six bugs were caught there for pennies. Best one: my relay sent nothing during silence — but a real phone line always sends silence frames, and the VAD has to *hear* them to know a turn ended. Without that, no transcripts at all.

**2:05 · What it found** — *show the table at the top of `BUGS.md`*
- The headline: **entering your phone-number verification step is fatal. Twelve of eighteen calls hit it. None of the twelve ever reached what the caller rang for.**
- The six that skipped it — caller ID recognised, date of birth only — five completed the task. Same agent, same data, opposite outcome. It's the code path, not the caller.
- The shape is always identical: verification succeeds, agent confirms the details out loud, then "I can't proceed further right now," then transfer.

**2:35 · Why there are eighteen calls, not twelve** — *the part I'd want to hear*
- My first twelve used twelve identities from one number. Your agent keys records to caller ID, so ten of them couldn't be found — I'd built a test that guaranteed failure and written it up as your bug.
- So I re-ran six with the identity actually on file. That's what isolated it: same identity, phone path still fails, short path still works. The confound was hiding a sharper bug than the one I thought I had.

**2:55 · Close**
- Eighteen transcripts and recordings in the repo — including the report I got wrong first.
