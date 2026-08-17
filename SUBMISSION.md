# Submission checklist

Everything the brief asks for, and what's still on you.

## Ready

| Deliverable | Where |
| --- | --- |
| Working code, Python | `bridge.py`, `scenarios.py`, `run_calls.py`, `collect.py`, `analyze.py` |
| README, single command to run | [README.md](README.md) — `python run_calls.py --all` |
| Architecture doc + reasoning | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Bug report | [BUGS.md](BUGS.md) — 8 findings, 2 critical |
| 12 transcripts, both sides | `calls/call-NN-*/transcript.txt` (+ `.json`) |
| 12 recordings, MP3, dual-channel | `calls/call-NN-*/recording.mp3` |
| `.env.example`, no secrets committed | [.env.example](.env.example) |
| Tests | `pytest tests/test_units.py -q` — 27 passing |

**Call number to put on the form (E.164):** `+16018716381`

All 12 calls were placed from that one number. Getting this wrong means they can't
grade the audio.

**Call summary:** 12 calls, 1:33–3:03 each, 8–19 turns each. 11 of 12 ended with the
bot saying goodbye and hanging up on its own; one hit the duration cap.

## Still yours

- [ ] **Loom video 1** — project walkthrough, under 3 minutes, webcam on, your voice.
      Script: [LOOM1-WALKTHROUGH.md](LOOM1-WALKTHROUGH.md)
- [ ] **Loom video 2** — you prompting AI to debug and fix the code.
      Script: [LOOM2-DEBUGGING.md](LOOM2-DEBUGGING.md), which also explains how to
      reproduce the bug live on camera in 20 seconds without placing a call.
- [ ] **Both Looms set to public.**
- [ ] **Push to a public GitHub repo.** Confirm `.env` is not in it:
      `git ls-files | grep -c '^\.env$'` should print `0`.
- [ ] **Rotate your credentials.** The OpenAI key and Twilio auth token were pasted
      into a chat transcript that's on disk.
- [ ] **Submit the form** with the repo link, both Loom links, and `+16018716381`.
- [ ] **Expense receipts** — Twilio and OpenAI. They reimburse up to $20.

## Cost

Roughly $8: about $0.35 of Twilio call minutes across 12 calls plus Realtime API
audio, on top of the $20 Twilio account upgrade (which is the reimbursable part).
