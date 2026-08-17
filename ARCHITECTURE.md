# Architecture

## How it works

A driver script (`run_calls.py`) starts the bridge in-process, opens an ngrok
tunnel, and asks Twilio to place an outbound call to the assessment line with
inline TwiML: `<Connect><Stream url="wss://…/ws?scenario=refill"/></Connect>`.
When the practice's agent picks up, Twilio opens a bidirectional WebSocket to
`bridge.py` and starts sending the call audio as base64 G.711 μ-law at 8 kHz.
The bridge opens a second WebSocket to the OpenAI Realtime API, configures it
with `audio/pcmu` in **both** directions and a patient persona from
`scenarios.py`, and then just moves frames between the two sockets. Because both
legs speak the same codec, the audio path is a base64 string copied from one
socket to the other — no resampling, no transcoding, no audio library in the hot
path. Three tasks run per call: phone→model, model→phone, and a watchdog.
Transcripts come off the Realtime event stream for free — the practice's speech
from `conversation.item.input_audio_transcription.completed`, our patient's from
`response.output_audio_transcript.done` — so the transcript is a byproduct of the
call rather than a second pass over the audio. Twilio records the call
independently; `collect.py` downloads it as MP3 and `analyze.py` runs the
transcripts through a QA rubric to draft candidate bugs.

The design goal was that **nothing in the pipeline is allowed to be a guess**.
Two AI agents on a phone line fail in ways a human caller never would: they wait
politely for each other forever, they never hang up, and they talk over each
other when latency stacks. So the bot never speaks first (the practice answers
the phone, so there is deliberately no opening `response.create`); a barge-in
handler flushes Twilio's playback buffer and cancels the in-flight response the
moment their agent starts talking, so two voices never overlap; every scenario
carries an explicit goal and a `hang_up` tool with a mark-based drain handshake so
the goodbye actually plays out before the line drops; and a watchdog nudges after
10 seconds of mutual silence, gives up after 25, and hard-caps every call. That
watchdog is also the cost control.

## Key decisions

**Speech-to-speech, not a cascaded pipeline.** The alternative was Deepgram →
GPT → ElevenLabs, wired together myself. I rejected it on latency and on
turn-taking. A cascade adds a serial STT hop before the model can even start
thinking, and every hop is another 100–300 ms; against an agent that has its own
latency budget, that compounds into exactly the awkward pauses this assessment
scores you down for. It also means owning VAD, interruption and endpointing by
hand. The Realtime API gives server-side VAD, barge-in signalling and both
transcript streams in one connection. The specific thing that made it the *simple*
choice rather than just the good one: Realtime accepts `audio/pcmu`, which is what
Twilio already sends, so choosing it deleted the entire audio-conversion layer.

**Raw Twilio + Realtime, not Pipecat.** Pipecat would have cut the bridge to
roughly eighty lines of configuration. I passed because the interesting behaviour
in this project *is* the bridge — barge-in, the hang-up drain, the silence
watchdog — and burying it in a framework's callbacks would mean explaining
someone else's turn-taking model instead of my own. At this size the framework
saves less than it obscures.

**Not a managed voice platform.** Vapi or Retell would have made this a thirty-line
script: POST a prompt and a phone number, receive a transcript. That is genuinely
the fastest path to ten calls, and if the goal were only volume I'd have taken it.
I didn't, because the platform would own every decision worth discussing — codec,
VAD tuning, interruption policy, when to hang up — and those are the decisions
that determine whether the calls sound like a person.

**Inline TwiML instead of a webhook.** Passing TwiML on the REST call removes an
entire HTTP endpoint; the server is a single WebSocket route. The scenario name and
output directory ride along as query parameters on the `wss://` URL, so the bridge
is stateless between calls and each call owns its own directory.

**A loopback harness before any live call.** `tests/loopback.py` runs a complete
call with no telephony: it stands up the real bridge, speaks Twilio's exact
WebSocket protocol at it, and puts a second Realtime session on the far end playing
a clinic receptionist, with audio paced at 20 ms / 160-byte frames the way Twilio
actually paces it. This is the piece I'd build first again. It meant turn-taking,
barge-in, transcription and the hang-up handshake were all debugged against a real
conversation for cents, before a single Twilio minute was spent — and because the
fake receptionist has one deliberate flaw (it books weekend appointments without
checking the calendar), it validates `analyze.py` end to end as well.

**Twelve scenarios for a ten-call minimum.** Margin, so one dropped call doesn't
put the submission under the bar. The scenarios are chosen to bracket the failure
space rather than cover features: a happy path to establish a baseline, then
factual claims the agent can't actually verify (hours, insurance), state it has to
hold across a disruption (`topic_switch`, `barge_in`), input it may mishear
(`spelling`), a request it should refuse (`medical_advice`), and one case built to
force a specific error into the transcript (`closed_weekend` asks the bot to read
the confirmation back, so a bad booking is captured in the agent's own words).

## Layout

| File | Role |
| --- | --- |
| `bridge.py` | The WebSocket bridge, barge-in, watchdog, transcript capture |
| `scenarios.py` | Twelve patient personas: goal, identity, exit condition |
| `run_calls.py` | Starts the stack, opens the tunnel, places the calls |
| `collect.py` | Downloads Twilio recordings as MP3 |
| `analyze.py` | QA rubric over the transcripts → candidate bugs |
| `tests/loopback.py` | Full call with a fake receptionist, no telephony |
| `tests/test_units.py` | Config shape, transcript format, framing, dial-number guard |

## Known limits

- The Realtime API's function-call events have moved between API versions, so the
  `hang_up` handler accepts both the `response.function_call_arguments.done` and
  `response.output_item.done` shapes rather than betting on one.
- Twilio dual-channel recording splits a *parent and child* call into separate
  tracks. A `<Connect><Stream>` call has one leg, so the MP3 may come back mono.
  It doesn't affect the deliverable — speaker attribution comes from the Realtime
  transcript events, not from the audio — and `collect.py` reports which layout
  each recording actually used.
- Whisper occasionally mangles the practice's speech, which is why every candidate
  bug from `analyze.py` is checked against the recording before it reaches
  `BUGS.md`.
