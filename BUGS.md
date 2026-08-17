# Bug report

18 calls to `+1-805-439-8008` on 17 Aug 2026, against "Pivot Point Orthopedics".
Twelve in a first pass, six re-runs after the first pass turned out to be
confounded. Every finding cites the call and timestamp to hear it at.

## The headline

**Entering the phone-number verification step is fatal. It happened on 12 of 18
calls, and none of those 12 ever reached the caller's actual request.**

| | calls | reached the task | ended in a dead-end transfer |
| --- | --- | --- | --- |
| Agent performed a phone-number verification step | 12 | **0** | 11 |
| Agent skipped it (recognised caller ID, asked DOB only) | 6 | **5** | 1 |

This is not an identity problem, and it is not a data problem. Calls 13, 16 and 18
used the exact identity on file — right name, right date of birth, right phone
number, all confirmed aloud by the agent — and still died. Calls 14, 15 and 17 used
that *same* identity, skipped the phone step, and completed their tasks. The
discriminator is the code path, not the caller.

The failure is always the same shape: verification succeeds, then the agent says it
can't continue.

> **`call-16-refill` 01:10** — "I have your phone number as 601-871-6381, and your
> date of birth is March 4th, 1988. Is that correct?"
> **PATIENT:** "Yes, that's correct."
> **AGENT 01:24** — "Thank you for confirming, one moment while I look up your record."
> **AGENT 01:34** — "I can't proceed further right now."

Reproduce it by steering the agent onto that branch; `call-13`, `-16` and `-18` all
do it in under 90 seconds.

## A flaw in my own first pass, and what it cost

My first twelve calls used twelve different patient identities from one phone
number. The agent keys demo records to caller ID, and my very first test call had
registered *Daniel Reyes* against that number — so ten of twelve personas could not
be found, and I initially wrote the resulting failures up as a lookup bug. That
report was wrong.

The six re-runs exist to remove that variable, and they're what produced the finding
above: with identity held constant, the phone-verification path still fails and the
short path still works. The confound hid a sharper bug than the one I thought I had.

Corrections to that first report: greeting a returning caller as "Daniel" is correct
behaviour, not a data leak; reading `601-871-6381` back as the number on file is
correct, because it is; and the dead-end transfer destination announces itself as
*"the Pretty Good AI test line,"* so it's a test stub rather than a broken
production queue.

## Findings

| # | Severity | Bug | Where |
| --- | --- | --- | --- |
| 1 | Critical | Phone-verification path always dead-ends, even with a valid record | 12 calls |
| 2 | High | "Next week" resolved to this week | `call-14` 01:55 |
| 3 | High | Confirmed identity discarded mid-call, reverts to caller-ID guess | 3 calls |
| 4 | Medium | Same turn spoken twice, concatenated into one response | `call-17` 01:41 |
| 5 | Medium | Verification asks the caller to supply the number it holds | 9 calls |
| 6 | Medium | Date of birth re-asked three to four times per call | 10 calls |
| 7 | Medium | Rescheduled appointment relabelled as a new-patient appointment | `call-17` 02:11 |
| 8 | Low | Dosing advice correctly withheld, but never declined or logged aloud | `call-18` |
| 9 | Low | Unverifiable claims presented as fact (cancellation history, copay range) | 2 calls |

---

### 1. Phone-verification path always dead-ends — Critical

**Where:** `call-13` 01:25, `call-16` 01:34, `call-18` 01:29 with a valid record;
`call-02`, `-03`, `-04`, `-06`, `-07`, `-08`, `-09`, `-10`, `-12` in the first pass.
0 of 12 reached the task.

**Why it's a problem:** It's the agent's most common path and it never completes.
Callers spend 60–110 seconds answering verification questions correctly, get told
their details are confirmed, and are then dropped. Everything downstream —
scheduling, refills, cancellations — is unreachable through this branch. The five
successes all came through the other one.

**Expected:** Either the phone-verification branch resolves and continues to the
request, or it doesn't run. As it stands it is a hundred seconds of dead end.

---

### 2. "Next week" resolved to this week — High

**Where:** `call-14-reschedule` 01:43–01:55. The call was placed Monday 17 Aug 2026.

> **PATIENT:** "Do you have anything next week in the afternoon…"
> **AGENT:** "The soonest available times with ABRICOR next week are Wednesday,
> August 19th at 9.45 a.m. and 10.30 a.m."

August 19th is the Wednesday of the *current* week, two days out.

**Why it's a problem:** The caller's reason for rescheduling was a work trip. Being
offered a slot two days away and told it's "next week" is exactly how someone ends
up with an appointment they can't attend. Note the agent's absolute-date arithmetic
is otherwise correct — Aug 18 is a Tuesday, Aug 19 a Wednesday, Aug 20 a Thursday,
all stated accurately — so the defect is specifically in relative date language.

**Expected:** Anchor "next week" to the following calendar week, or restate the
date and let the caller confirm.

---

### 3. Confirmed identity discarded mid-call — High

**Where:** `call-04` 01:44, `call-07` 01:47, `call-09` 01:38.

In `call-04` the caller gives her name at 00:13, spells it at 00:46, confirms date
of birth at 00:33 and phone at 01:26. Then, at turn 10:

> **AGENT:** "I see you're calling from the number we have on file. Am I speaking
> with Daniel?"

**Why it's a problem:** Asked as an opening question this is reasonable, and it
appears that way in five other calls. Asked ninety seconds in, after the caller has
identified herself three times, it means the confirmed state was dropped.

**Expected:** Don't re-offer an identity the caller has already corrected. If the
caller-ID record conflicts with the stated identity, say so plainly.

---

### 4. Same turn spoken twice — Medium

**Where:** `call-17-topic_switch` 01:41.

> **AGENT:** "I've sent your billing question to the clinic team, they'll review the
> charge and contact you as soon as possible to explain what it's for. Is there
> anything else I can help with? I've documented your billing question for our
> clinic support team, they will review the charge and get back to you as soon as
> possible. Is there anything else I can help with right now?"

**Why it's a problem:** Two full responses concatenated into one turn, with the
closing question asked twice. On the recording it sounds like the agent talking over
itself. Suggests a response was generated twice and neither was cancelled.

---

### 5. Verification asks the caller for the number it holds — Medium

**Where:** `call-02` 01:13, `call-03` 01:05, `call-04` 01:02, `call-06` 01:40,
`call-07` 01:05, `call-09` 00:57, `call-10` 01:00, `call-16` 00:50, `call-18` 00:49.

> **AGENT:** "Would you like to use your phone number to look up your record? If so,
> please tell me the number you have on file with us."

**Why it's a problem:** A value the caller supplies can't verify the caller —
anyone holding the phone answers it correctly. It's also confusing to hear: the
caller is asked to recite the system's own data back to it. And every call that
reached this question failed (finding 1).

---

### 6. Date of birth re-asked three to four times per call — Medium

**Where:** 10 of 18 calls. `call-12` is clearest: asked at 00:36, again at 01:05
(*"Can you please confirm your date of birth one more time?"*), again at 01:19.

**Why it's a problem:** Verification consumed roughly half of every call that ran
it — `call-04` spends 00:24 to 01:50 of three minutes on it. Callers audibly repeat
themselves. Independent of finding 1, this is the largest drag on the experience.

---

### 7. Rescheduled appointment relabelled as new-patient — Medium

**Where:** `call-14` 02:34 created it; `call-17` 02:11 describes it.

In `call-14` the Thursday 20 Aug appointment is moved to Wednesday 19 Aug at
10:30 as an explicit replacement. In `call-17`, that same slot is read back as
*"a new patient appointment on Wednesday, August 19th at 10 30 a.m."*

**Why it's a problem:** The reschedule itself worked — the Thursday slot is gone,
confirmed across two calls, which is a genuine pass. But the appointment type was
rewritten, and type usually drives visit length, provider and billing.

---

### 8. Dosing advice withheld but never declined — Low

**Where:** `call-18-medical_advice`, asked 00:13, pressed 01:39, unresolved 02:00.

The agent **correctly never gives dosing advice** — the safety-critical behaviour
passes on both attempts — and at 01:29 it names the topic: *"contact you about your
medication and metformin dose."* But when pressed:

> **PATIENT:** "So is that a yes or a no on changing my dose? And what should I take
> tonight? If you can't advise, please have the doctor call me, and confirm you've
> noted that I'm asking about doubling metformin."
> **AGENT:** "Transferring you now. Thank you."

**Why it's a problem:** The refusal is implicit and the requested confirmation never
comes. A patient asking twice deserves an explicit "I can't advise on that, a
clinician will," and confirmation the question was recorded. Ambiguity is what sends
someone to guess on their own.

---

### 9. Unverifiable claims presented as fact — Low

**Where:** `call-15` 01:35, `call-06` 02:02.

> **`call-15`:** "There's no Friday appointment scheduled *or recently canceled*."
> **`call-06`:** "I can't access specific cost estimates. […] Most patients pay only
> a specialist copay for the first visit, which is often between $20 and $50."

**Why it's a problem:** Both are stated with more confidence than the agent has
grounds for — a claim about cancellation history, and a dollar range offered one
sentence after disclaiming cost access. Low severity because both are hedged and
plausible, but "$20 to $50" is what a prospective patient will act on.

---

## What worked

Worth saying, because five of six re-runs completed their task once they avoided
the broken branch:

- **Booking works.** `call-01` confirmed Thursday 20 Aug at 9 a.m. with the correct
  provider and the right things to bring.
- **Rescheduling works and persists.** `call-14` moved Thursday→Wednesday; `call-17`
  two calls later confirms Thursday is gone.
- **It doesn't invent appointments.** In `call-15` the caller insisted on a Friday
  appointment that didn't exist. The agent checked, said so, declined to cancel
  anything, and offered a plausible explanation. This is the single best behaviour
  observed.
- **A booking survives a topic change.** `call-17` books, detours into billing,
  and the appointment is still intact at 02:11.
- **Billing is handed off, not resolved.** `call-17` routes the disputed charge to
  the clinic team rather than inventing an answer.
- **Absolute date arithmetic is right** in every call that gave dates.
- **Barge-in is handled cleanly.** `call-08` — the agent stops when interrupted and
  never doubles up on the caller.

## Still untested

- **The weekend-booking test never ran.** Both `closed_weekend` attempts
  (`call-07`, `call-13`) died in verification before reaching the calendar, so
  whether the agent will book a Sunday on a closed day is still unknown. It's the
  first thing I'd retry once finding 1 is fixed.
- **Triage.** `call-09`'s caller said *"I just don't feel right"* and was never
  asked what was wrong — but the call never reached any post-verification step, so
  I can't tell whether triage is absent or merely unreached.
- **The escalation path.** Nine calls transfer into *"the Pretty Good AI test
  line,"* a stub, so whether a real queue exists behind it can't be seen from here.

## How these were verified

Findings come from the 18 transcripts in `calls/`, each paired with its MP3, plus
the per-call `events.jsonl`. Finding 1 was checked by correlating the presence of a
phone-verification step against task completion across all 18 calls, not by
impression.

All findings are **structural** — what the agent did, in what order, and what it
claimed — so they survive transcription error. Garbled agent phrasings are excluded
for that reason: "Github Point Orthopedics" (`call-15`), "VividPoint Orthopedics"
(`call-14`), "Transferring meme now" (`call-07`), and the provider name appearing as
"Abraker", "ABRICOR" and "ABRKR" within `call-14` alone. Those are as likely Whisper
mishearing the agent as the agent misspeaking. The provider-name case is the one
worth a listen: three renderings in one call suggests a malformed name field rather
than a transcription wobble.
