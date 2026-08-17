# Architecture

## How it works

`run_calls.py` starts the bridge in-process, opens a tunnel, and asks Twilio to
place an outbound call with inline TwiML: `<Connect><Stream url="wss://…/ws">`.
When the practice's agent answers, Twilio opens a bidirectional WebSocket to
`bridge.py` and streams the call as base64 G.711 μ-law at 8 kHz. The bridge opens a
second WebSocket to the OpenAI Realtime API, configures `audio/pcmu` in **both**
directions plus a patient persona from `scenarios.py`, and then moves frames
between the two sockets. Because both legs speak the same codec, the audio path is
a base64 string copied from one socket to the other — no resampling, no
transcoding, no audio library anywhere in the hot path. Three tasks run per call:
phone→model, model→phone, and a watchdog. Transcripts fall out of the Realtime
event stream for free (the practice's speech from the input-transcription events,
ours from the output-transcript events), so the transcript is a byproduct of the
call rather than a second pass over the audio. Twilio records the call
independently; `collect.py` downloads it as MP3, `analyze.py` drafts candidate bugs.

Two AI agents on a phone line fail in ways a human caller never would: they wait
politely for each other forever, they never hang up, and they talk over each other
when latency stacks. So the bot never speaks first — the practice answers the
phone, so there is deliberately no opening `response.create`. A barge-in handler
flushes Twilio's playback buffer and cancels the in-flight response the moment
their agent starts talking, so two voices never overlap. Every scenario carries an
explicit goal and a `hang_up` tool, with a mark-based drain handshake so the
goodbye finishes playing before the line drops. A watchdog nudges after 28s of
mutual silence, gives up at 50s, and hard-caps every call — which is also the cost
control.

## Key decisions

**Speech-to-speech, not a cascaded pipeline.** The alternative was Deepgram → GPT →
ElevenLabs wired together by hand. A cascade adds a serial STT hop before the model
can start thinking, and every hop is another 100–300 ms; against an agent with its
own latency budget that compounds into exactly the awkward pauses this assessment
scores down. It also means owning VAD, interruption and endpointing myself. What
made Realtime the *simple* choice and not just the good one: it accepts
`audio/pcmu`, which is what Twilio already sends, so choosing it deleted the entire
audio-conversion layer.

**Raw Twilio + Realtime, not Pipecat.** Pipecat would have cut the bridge to ~80
lines of configuration. I passed because the interesting behaviour here *is* the
bridge — barge-in, the drain handshake, the silence watchdog — and burying it in a
framework's callbacks means explaining someone else's turn-taking model instead of
my own. At this size the framework saves less than it hides.

**Not a managed platform.** Vapi or Retell would have made this thirty lines: POST a
prompt and a number, receive a transcript. Genuinely the fastest path to ten calls.
I didn't, because the platform would own every decision worth discussing — codec,
VAD tuning, interruption policy, when to hang up — and those are the decisions that
determine whether the calls sound like a person.

**`<Parameter>`, not a query string.** Twilio discards the query string on the
`<Stream>` url. The first live call connected and was instantly refused because the
bridge never learned which scenario to play, which from Twilio's side is
indistinguishable from the server crashing. Scenario and output directory now ride
on `<Parameter>` children and arrive in the `start` frame.

## What the loopback harness bought

`tests/loopback.py` runs a complete call with no telephony: the real bridge, a fake
Twilio client speaking the exact WebSocket protocol, and a second Realtime session
on the far end playing a clinic receptionist — with audio paced at 20 ms / 160-byte
frames the way Twilio paces it. This is the piece I'd build first again. Four of six
bugs were found here for cents:

| Bug | Why it mattered |
| --- | --- |
| Relay sent nothing while idle | A real line carries silence frames, and VAD needs to *hear* silence to close a turn. Without it `speech_started` fired, `speech_stopped` never did, and no transcript was ever produced. |
| `silence_duration_ms` at 500 | Chopped one agent turn into four, so the patient replied to half a sentence then talked over the rest. Now 900 ms, and sweepable. |
| Silence measured from `response.done` | That's when the model stops generating, not when the audio stops playing — the watchdog nudged while the bot was still audibly talking. Now driven by a Twilio drain mark. |
| Fake receptionist had no barge-in | It queued a reply per interruption and backed the paced relay up by 66 seconds, which looked exactly like catastrophic latency. |

The two that only real calls could surface: Twilio dropping the query string, and
transcripts stamped at transcription time rather than speech time — which produced
a call where the caller answers at 01:08 a question the agent asks at 01:09. Turns
are now stamped when audio begins and sorted before writing.

The third only surfaced after the calls were done, in my own test design: twelve
personas down one phone number, against a system that keys records to caller ID.
Setting `IDENTITY=on_file` swaps a scenario's persona for the identity the practice
actually holds while leaving its task untouched, which is what the six re-runs use.
Comparing the two sets is what isolated the critical finding — the flaw was hiding a
sharper bug than the one it caused. Worth designing for next time: a test harness
needs to control the state on the *other* side of the call, not just its own.

## Layout

| File | Role |
| --- | --- |
| `bridge.py` | The WebSocket bridge, barge-in, watchdog, transcript capture |
| `scenarios.py` | Twelve patient personas: goal, identity, exit condition |
| `run_calls.py` | Starts the stack, opens the tunnel, places the calls |
| `collect.py` | Downloads Twilio recordings as MP3 |
| `analyze.py` | QA rubric over the transcripts → candidate bugs |
| `tests/loopback.py` | Full call against a fake receptionist, no telephony |
| `tests/test_units.py` | Config shape, transcript ordering, framing, dial-number guard |

## Known limits

- Realtime's function-call events have moved between API versions, so the `hang_up`
  handler accepts both event shapes rather than betting on one.
- I expected `<Connect><Stream>` to defeat Twilio's dual-channel recording, since
  dual-channel splits a *parent and child* call and a streamed call has one leg. It
  doesn't: all 12 recordings came back genuinely dual-channel, so the MP3s carry
  speaker separation as well as the transcripts. `collect.py` reports the layout
  per call rather than assuming it.
- Whisper occasionally mangles the practice's speech, which is why every candidate
  from `analyze.py` is checked against the recording before it reaches `BUGS.md`.
