# Loom 2 — AI debugging walkthrough (~4 min)

No time limit on this one — the 3-minute cap is on the walkthrough. Timings are
measured at a normal speaking pace.

Show the loop: symptom → hypothesis → evidence → fix → *then fix whatever should
have caught it*. One bug shown properly beats three summarised. Use the first live
call: it died in one second and the error message blamed the wrong component.

## Reproduce it live on camera, for free

No phone call needed — the loopback harness reproduces the same class of failure in
about 20 seconds. In `tests/loopback.py`, delete the `customParameters` block from
the `start` frame, then:

```bash
python tests/loopback.py refill
```

The bridge prints `refusing stream: unknown scenario ''` and drops the connection —
the same failure Twilio hit. Put the block back afterwards.

## Beats

**0:00 · The symptom**
- Placed my first real call. Twilio said `completed`. Duration: one second.
- No transcript, no event log, nothing on disk. The bridge never wrote a byte.

**0:25 · Ask the tool for the error, not for a guess** — *show the prompt*
> "The call completed in 1s and the bridge wrote nothing. Pull the Twilio alerts for that call SID and tell me what the error code actually means."
- Error 31921. Twilio's docs: *"Twilio established a WebSocket connection to your
  server and your server then closed that connection."*
- So it blamed my code. That framing is what cost me the most time.

**1:00 · Test the accusation before accepting it**
> "Before I change anything — connect to the bridge through the public tunnel the way Twilio does, and tell me whether the handshake actually succeeds."
- It did. Handshake fine, full call log written. The bridge was innocent.
- The error was true but misleading: my server *did* close the connection — on purpose.

**1:40 · Stop guessing, add evidence**
- I'd been theorising: DNS, tunnel timing, recording flags. All plausible, all
  unverifiable from what I had.
> "I'm guessing. The bridge rejects a stream in three places and all three are silent. Make each one log why, then I'll call again."
- One line of logging. Next call printed: `refusing stream: unknown scenario ''`.
- Twilio discards the query string on `<Stream url>`. Custom data has to travel as
  `<Parameter>` children and arrives in the `start` frame. Fifteen-line fix.

**2:30 · Then fix the thing that should have caught it** — *the part I'd want to see*
- My loopback harness passed the scenario as a query string too. It was faithful to
  my assumption, not to Twilio. That's why it passed while production failed.
> "Change the harness to send customParameters like Twilio does, and add a test asserting the Stream url has no query string."
- Harness now mirrors Twilio exactly. Test fails if anyone reintroduces it.

**3:10 · Same move, on my own conclusions** — *show the table at the top of `BUGS.md`*
- I'd finished the bug report. Eight findings, two critical. Then I asked the same question I'd asked about the Twilio error: what if the framing is wrong?
> "Re-read the transcripts and tell me whether my critical findings could be artifacts of my own test design."
- They were. Twelve identities down one phone number, against a system that keys records to caller ID — I'd guaranteed the failures I was reporting.
- So I re-ran six calls with the identity held constant. That isolated the real bug: it's the phone-verification code path that dead-ends, not the lookup. Twelve of eighteen calls hit it, none completed.
- Worth saying plainly: the confound was hiding a sharper bug than the one it caused.

**3:45 · The habit, in one line**
- Every wrong turn came from trusting a framing — Twilio's, then my own. Every fix
  came from making the system say what it was actually doing, and re-running.

## Reference — other bugs the loop caught (not narrated)

- **Silence frames:** harness went silent. Event log showed `speech_started` with no
  `speech_stopped` — a real line always sends silence frames and VAD must *hear*
  them to close a turn.
- **Playback vs. generation:** silence was timed from `response.done`, which is when
  the model stops generating, not when audio stops playing. The bot got interrupted
  by its own watchdog mid-sentence.
- **Transcript ordering:** a call where the caller answers at 01:08 a question asked
  at 01:09. Turns were stamped when transcription resolved, not when speech happened.
