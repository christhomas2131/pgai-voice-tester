# Both Loom videos, in plain English

No timings. Just say these things in order, in your own words.

---

## Video 1 — What I built

### Start with what it is

I built a fake patient that phones your AI receptionist and has real conversations
with it. Twelve different patients, each one calling about something different — one
wants an appointment, one wants a prescription refill, one is confused and can't say
what's wrong. It records both sides of every call and writes up what went wrong.

### How it works

Think of me as a switchboard operator sitting in the middle of the call.

Twilio is the phone company. I tell it to dial your number. When your AI picks up,
Twilio doesn't connect it to a human — it pipes the live audio to my computer
instead. My computer hands that audio straight to OpenAI, which is doing the talking
as the patient. Then it hands OpenAI's voice back down the phone line to you.

That's the whole thing. Audio in one ear, out the other.

The lucky part is that the phone company and OpenAI happen to use the exact same
audio format. So I never convert anything — I just copy the sound across untouched.
That's why there's so little code.

### Why I built it that way, and not the other ways

**I could have chained three separate tools together** — one to turn speech into
text, one to think about it, one to turn text back into speech. That's like
translating a conversation through three people standing in a line. Every handoff
adds a delay. Your AI is already slow to answer. Two slow things talking to each
other means long awkward pauses, and awkward pauses are exactly what you grade
people down for. So I didn't.

**I could have used a ready-made framework** that handles the phone plumbing for me.
I didn't, because the plumbing is the interesting part — knowing when to stop
talking, when to butt in, when to hang up. If a framework does all that, I can't
explain any of it to you.

**I could have used a service where you type a prompt and it makes the call for you.**
Thirty lines of code, done in an hour. I didn't, because then the service makes every
decision that matters and I'd have nothing to tell you.

### How I tested it without a huge phone bill

Phone calls cost money and take two minutes each. So before calling you at all, I had
two AIs talk to each other on my laptop with no phone involved — one playing my
patient, one playing a receptionist I made up. Exact same code, no phone company, no
bill.

That caught four of my six bugs for pennies. My favourite one: my program went
completely silent and nothing worked at all. It turns out a real phone line is never
actually silent — it's constantly sending "nothing" down the wire. The AI listens for
that "nothing" to know you've stopped talking. I wasn't sending it, so the AI thought
the other person had never finished their sentence, and just sat there waiting
forever.

### What I found

Your AI has two different ways of checking who's calling.

**The short way:** it recognises your phone number, asks your date of birth, done.
This works. People got appointments booked, appointments moved, questions answered.

**The long way:** it asks your name, then asks you to spell it, then asks for your
phone number, then reads it back to you. Every single time it goes down this route,
the call dies. It confirms all your details out loud, then says "I can't proceed
further right now," and transfers you to a line that immediately says goodbye.

Twelve of my eighteen calls went the long way. **None of them got what they called
for.** Six went the short way, and five of those got exactly what they wanted.

Same caller. Same details. Same information confirmed out loud. The only difference
was which route your AI happened to take.

A few smaller things: it offered someone a slot two days away and called it "next
week." It said the same sentence twice in a row on one call. It asked one caller their
date of birth four separate times in the same conversation.

And credit where it's due — when one caller insisted she had a Friday appointment, it
checked, told her honestly that she didn't, and refused to cancel anything. It didn't
make something up to please her. That's the best behaviour I saw.

### Finish

Eighteen recordings and eighteen transcripts are all in the repo, including the part
where I got the report wrong the first time.

---

## Video 2 — Fixing my own code with AI

You want to see how I actually work through a problem. So here's one bug, start to
finish, including the two times I was wrong.

### The problem

I placed my first real phone call. Twilio reported the call finished normally. It
lasted one second. My program didn't write down a single thing.

### First move: get the facts, don't guess

I asked for the real error instead of theorising:

> "The call ended after one second and my program logged nothing. Go pull the Twilio
> error for that call and tell me what it actually means."

The error said: Twilio connected to your server, and then your server hung up on it.

So it blamed my code. That framing is what cost me the most time.

### Second move: check whether the accusation is even true

> "Before we change anything — connect to my server the same way Twilio does and tell
> me whether it actually works."

It worked perfectly. So the error was pointing at the wrong thing. It was technically
true — my server *did* hang up — but it hung up deliberately, and nothing was
recording why.

### Third move: stop guessing, make it tell me

I'd been theorising about three different causes and couldn't prove any of them.

> "I'm guessing here. My program can reject a call in three different places and all
> three are silent about it. Make each one say why, then I'll call again."

One line of logging. The next call printed the answer straight away: it didn't know
which patient to play. I'd been attaching that information to the end of the web
address, like a link with a question mark in it. Twilio throws that part away. You
have to attach it a different way entirely.

### Fourth move: fix the thing that should have caught it

Here's the part I'd want to see if I were hiring someone.

My own test rig had the exact same mistake in it. It was attaching the information
the same wrong way — so it agreed with me instead of testing me. That's why it passed
while the real thing failed.

> "Change the test rig to do it the way Twilio actually does, and add a check that
> fails if anyone ever goes back to the old way."

### Fifth move: point the same question at my own conclusions

I'd already finished the bug report. Eight problems, two of them marked critical.
Then I asked the same question I'd asked about Twilio's error — what if the framing
is wrong?

> "Re-read all the transcripts and tell me whether my critical findings could just be
> artifacts of how I set up the test."

They could. And they were.

All eighteen calls came from one phone number, but I used twelve different patient
names. Their system remembers who owns a phone number. So ten of my twelve patients
looked like strangers ringing from someone else's phone and claiming to be someone
new — of course it couldn't find their records. I had built a test that was
guaranteed to fail, and then written it up as their bug.

So I re-ran six calls using the one name their system actually had on file. That's
what uncovered the real problem: even with the correct name and every detail right,
the long route still died. It was never about the name. It's the route.

The confound was hiding a better bug than the one it caused.

### The habit, in one sentence

Every time I went wrong, it was because I trusted how something was worded — first
Twilio's error message, then my own conclusion. Every time I got it right, it was
because I made something show me what it was actually doing.

---

## If you want to demo the bug live on camera

It costs nothing and takes twenty seconds — no phone call needed.

In `tests/loopback.py`, delete the `customParameters` block from the start frame,
then run:

```bash
python tests/loopback.py refill
```

The program prints `refusing stream: unknown scenario ''` and drops the connection —
the same failure Twilio hit. Put the block back afterwards.
