# Submission checklist

Everything the brief asks for, and what's still on you.

## Ready

| Deliverable | Where |
| --- | --- |
| Working code, Python | `bridge.py`, `scenarios.py`, `run_calls.py`, `collect.py`, `analyze.py` |
| README, single command to run | [README.md](README.md) — `python run_calls.py --all` |
| Architecture doc + reasoning | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Bug report | [BUGS.md](BUGS.md) — 9 findings (1 critical, 2 high) |
| 18 transcripts, both sides | `calls/call-NN-*/transcript.txt` (+ `.json`) |
| 18 recordings, MP3, dual-channel | `calls/call-NN-*/recording.mp3` |
| `.env.example`, no secrets committed | [.env.example](.env.example) |
| Tests | `pytest tests/test_units.py -q` — 28 passing |

**Call number to put on the form (E.164):** `+16018716381`

All 12 calls were placed from that one number. Getting this wrong means they can't
grade the audio.

**Call summary:** 18 calls, 1:33–3:03 each, 8–19 turns each. 16 ended with the bot
saying goodbye and hanging up on its own; two hit the duration cap.

Calls 1–12 are the first pass, one persona each. Calls 13–18 re-run the
booking-flow scenarios under the identity the practice actually holds, to remove a
confound in the first pass — see the top of [BUGS.md](BUGS.md). Both sets are kept:
the comparison between them is what isolated the critical finding.

## Still yours

- [ ] **Loom video 1** — project walkthrough, under 3 minutes, webcam on, your voice.
      Script: [LOOM-SCRIPTS-PLAIN.md](LOOM-SCRIPTS-PLAIN.md) (plain English, no
      timings) or [LOOM1-WALKTHROUGH.md](LOOM1-WALKTHROUGH.md) (timed beats)
- [ ] **Loom video 2** — you prompting AI to debug and fix the code.
      Script: [LOOM-SCRIPTS-PLAIN.md](LOOM-SCRIPTS-PLAIN.md) or
      [LOOM2-DEBUGGING.md](LOOM2-DEBUGGING.md). Both explain how to reproduce the bug
      live on camera in 20 seconds without placing a call.
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
