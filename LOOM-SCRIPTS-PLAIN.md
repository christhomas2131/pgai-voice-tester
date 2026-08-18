# Both Loom videos, in plain English

## Video 1 — What I built

I built a fake patient that phones your AI receptionist and holds real conversations
with it — twelve of them, each calling about something different. Think of me as a
switchboard operator in the middle. Twilio is the phone company: it dials your number,
and when your AI answers it pipes the live audio to my computer instead of to a human.
My computer passes that audio to OpenAI, which does the talking as the patient, then
passes its voice back down the line. Both ends happen to use the same audio format, so
I never convert anything — I just copy the sound across. That's why there's so little
code.

I could have chained three tools together instead — speech to text, then thinking, then
text back to speech — but that's translating through three people in a line, and every
handoff adds delay. Your AI is already slow, and two slow things talking means awkward
pauses, which is what you mark people down for. What I found: your AI has two ways of
checking who's calling. The short way works — people got appointments booked. The long
way asks for a name, a spelling, then a phone number, and every time it goes that
route the call dies. Twelve of eighteen calls went the long way. **Not one got what
they called for.**

## Video 2 — Fixing my own code with AI

My first real call lasted one second and my program logged nothing. Rather than guess,
I asked for the actual error — it said Twilio connected to my server and my server hung
up, blaming my code. I didn't accept that, so I had it connect the same way Twilio does
and check. Worked fine. The error was true but pointing at the wrong thing. So I
stopped theorising and said: my program can reject a call in three places and all three
are silent — make each one say why. One line of logging, and the next call told me
instantly.

Then the part I'd want to see if I were hiring. My own test rig had the same mistake,
so it agreed with me instead of testing me — that's why it passed while the real thing
failed. I fixed it and added a check so nobody repeats it. Then I asked the same
question about my own bug report: could my critical findings just be artifacts of how I
set up the test? They were. I re-ran six calls properly, and that uncovered the real
bug. Every time I went wrong I'd trusted how something was worded — first Twilio's
error, then my own conclusion.
