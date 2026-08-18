# Both Loom videos, in plain English

## Video 1 — What I built

It's all Python. I built a fake patient that phones your AI receptionist and holds real
conversations with it — twelve of them, each calling about something different. Think of
me as a switchboard operator in the middle. **Twilio** is the phone company: it dials
your number, and when your AI answers, Twilio's **Media Streams** pipes the live audio
to a small **FastAPI** server on my laptop instead of to a human. **cloudflared** gives
Twilio a public address to reach me at. My server passes the audio to **OpenAI's
Realtime API** — the `gpt-realtime-2.1` model — which does the talking as the patient,
then passes its voice back down the line. Both ends use the same audio format, G.711
μ-law, so I never convert anything. I just copy the sound across.

I could have chained three tools instead — **Deepgram** for speech to text, **GPT** to
think, **ElevenLabs** for the voice back — but that's translating through three people
in a line, and every handoff adds delay. Your AI is already slow, and two slow things
talking means awkward pauses, which is what you mark people down for. I also skipped
**Pipecat**, and **Vapi** and **Retell**, because then the framework owns the decisions
worth discussing. **Whisper** transcribes your side, **Twilio** records the audio, and
**GPT-4o** does a first pass over the transcripts. What I found: your AI has two ways
of checking who's calling. The short way works. The long way asks for a name, a
spelling, then a phone number — and every time it goes that route, the call dies.
Twelve of eighteen went that way. **Not one got what they called for.**

## Video 2 — Fixing my own code with AI

I did all of this in **Claude Code**. My first real call lasted one second and my
program logged nothing. Rather than guess, I had it pull the actual **Twilio** error —
error 31921, which says Twilio connected to my server and my server hung up. So it
blamed my code. I didn't accept that, so I had it connect to my server the same way
Twilio does and check. Worked fine. The error was true but pointing at the wrong thing.
So I stopped theorising: my program can reject a call in three places and all three are
silent — make each one say why. One line of logging, and the next call told me
instantly.

Then the part I'd want to see if I were hiring. My own test rig had the same mistake, so
it agreed with me instead of testing me — that's why it passed while the real thing
failed. I fixed it and added a **pytest** check so nobody repeats it. Then I asked the
same question about my own bug report: could my critical findings just be artifacts of
how I set up the test? They were — all eighteen calls came from one number but I'd used
twelve patient names. So I re-ran six calls properly, and that uncovered the real bug.
Every time I went wrong I'd trusted how something was worded — first Twilio's error,
then my own conclusion.
