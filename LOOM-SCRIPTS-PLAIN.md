# Both Loom videos, in plain English

Two paragraphs each. Say them in your own words.

## Video 1 — What I built

I built a fake patient that phones your AI receptionist and holds real conversations
with it. Twelve different patients, each calling about something different — booking
an appointment, a prescription refill, someone who can't say what's wrong. Think of me
as a switchboard operator sitting in the middle. Twilio is the phone company: I tell
it to dial your number, and when your AI picks up, instead of connecting a human it
pipes the live audio to my computer. My computer hands that audio straight to OpenAI,
which does the talking as the patient, then hands OpenAI's voice back down the line to
you. The lucky part is the phone company and OpenAI happen to use the same audio
format, so I never convert anything — I just copy the sound across untouched. That's
why there's so little code.

I could have chained three separate tools together instead — one to turn speech into
text, one to think, one to turn text back into speech — but that's like translating
through three people standing in a line, and every handoff adds a delay. Your AI is
already slow to answer, and two slow things talking means long awkward pauses, which
is exactly what you mark people down for. I also skipped the ready-made frameworks,
because the plumbing is the interesting part and a framework hides it. What I found:
your AI has two ways of checking who's calling. The short way recognises the phone
number, asks a date of birth, and works — people got appointments booked and moved.
The long way asks for a name, a spelling, then a phone number, and every single time it
goes that route the call dies: it confirms all your details out loud, says "I can't
proceed further," and transfers you to a line that immediately says goodbye. Twelve of
eighteen calls went the long way and not one got what they called for. Same caller,
same details — the only difference was the route.

## Video 2 — Fixing my own code with AI

My first real phone call lasted one second, and my program didn't write down a thing.
So instead of guessing I asked for the actual error, and it said Twilio connected to my
server and then my server hung up — which blamed my code. I didn't accept that. I asked
it to connect to my server the same way Twilio does and tell me whether it actually
worked, and it worked fine. So the message was technically true but pointing at the
wrong thing: my server did hang up, deliberately, and nothing was recording why. I'd
been theorising about three different causes and couldn't prove any of them, so I
stopped guessing and said: my program can reject a call in three places and all three
are silent, make each one say why. One line of logging, and the next call told me
immediately — it never knew which patient to play, because I'd attached that
information to the end of the web address like a link with a question mark in it, and
Twilio throws that part away.

The part I'd actually want to see if I were hiring is what came next. My own test rig
had the same mistake in it — it attached the information the same wrong way, so it
agreed with me instead of testing me, which is why it passed while the real thing
failed. I fixed it to behave exactly like the phone company and added a check that
fails if anyone goes back to the old way. Then I pointed the same question at my own
conclusions. I'd already finished the bug report — eight problems, two critical — so I
asked whether my critical findings could just be artifacts of how I'd set up the test.
They were. All eighteen calls came from one phone number but I'd used twelve different
patient names, and their system remembers who owns a number, so ten of my patients
looked like strangers ringing from someone else's phone. I'd built a test guaranteed to
fail and written it up as their bug. So I re-ran six calls using the one name their
system actually had on file, and that's what uncovered the real problem: even with
every detail correct, the long route still died. It was never about the name. Every
time I went wrong I'd trusted how something was worded — first Twilio's error, then my
own conclusion — and every time I got it right I'd made something show me what it was
actually doing.
