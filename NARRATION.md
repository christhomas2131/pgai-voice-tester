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

**2:15 · What it found** — *show `BUGS.md`*
- Eleven of twelve calls never got the caller what they rang for.
- Your transfer to patient support hangs up on people — 9 of 12 calls. It says "please stay on the line," then the line says goodbye.
- It greets strangers by a previous caller's name: *"Am I speaking with Daniel?"* — off caller ID alone, before any authentication.
- A patient asked whether to double his metformin. No advice, no refusal, no human, no note.
- The only call that worked was the only one that never needed a patient record.

**2:50 · Close**
- Transcripts, MP3s and the full write-up are all in the repo.
