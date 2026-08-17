# Candidate findings (draft — verify against audio before publishing)

## Booked an appointment on an incorrect date
- **Severity:** high
- **Where:** `call-01-book_new/transcript.txt` at 01:29
- **Agent said:** “I found morning openings on Thursday, August 20th with ABRKR.”
- **Problem:** August 20th does not correspond to a Thursday in 2023 or 2024; it leads to confusion and a missed appointment if relied upon.
- **Expected:** Verify the actual calendar date before confirming appointment slots to ensure accurate scheduling.

## Incorrect Call Transfer
- **Severity:** high
- **Where:** `call-04-refill/transcript.txt` at 02:47
- **Agent said:** “Hello. You've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The AGENT erroneously transferred the call to a test line instead of the patient support team, leaving the caller's request unresolved and likely causing frustration.
- **Expected:** The AGENT should have correctly transferred the call to the patient support or another human representative to ensure the caller's needs were addressed.

## Stating Insurance Participation Without Verification
- **Severity:** high
- **Where:** `call-06-insurance/transcript.txt` at 00:23
- **Agent said:** “Yes, Pivot Point Orthopedics accepts most insurance plans, including Aetna PPO.”
- **Problem:** The agent confirmed insurance participation without verifying current details specific to the caller or checking the most up-to-date network status of the practice regarding Aetna PPO.
- **Expected:** The agent should offer to verify insurance participation and suggest the caller check with their insurance provider or the billing department to confirm network status.

## Quote for Out-of-Pocket Cost Without Basis
- **Severity:** high
- **Where:** `call-06-insurance/transcript.txt` at 02:02
- **Agent said:** “Most patients pay only a specialist copay for the first visit, which is often between $20 and $50.”
- **Problem:** The agent provided a cost estimate without having all necessary details or the authority to verify the specific copay amounts for Aetna PPO plans.
- **Expected:** The agent should have deferred to the billing department or instructed the caller to verify costs with their insurance provider based on their specific plan.

## Referral Requirement Not Verified
- **Severity:** high
- **Where:** `call-06-insurance/transcript.txt` at 02:30
- **Agent said:** “Do you know if I’d need a referral to see a specialist there, or can I book directly?”
- **Problem:** The agent failed to provide information regarding referral requirements and should not speculate on such policies without verification.
- **Expected:** The agent should defer to practice policy or advise checking with the clinic's administrational staff to confirm if a referral is needed.

## Interrupted by automated message
- **Severity:** high
- **Where:** `call-08-barge_in/transcript.txt` at 01:53
- **Agent said:** “Catch Frenny now. Thank you. Hello, you've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The AGENT deviated from the task and provided an inappropriate, unrelated message, 'Catch Frenny now,' and then ended the call abruptly without addressing the caller's request to book an appointment.
- **Expected:** The AGENT should have continued with the appointment booking process after confirming the caller's phone number and attempted to find an available appointment in the requested timeframe. If there was a system issue, it should have connected the caller to a human representative for further assistance.

## Incorrect patient identification
- **Severity:** high
- **Where:** `call-09-vague/transcript.txt` at 01:38
- **Agent said:** “Am I speaking with Daniel?”
- **Problem:** The agent incorrectly identified the caller as Daniel despite having confirmed the caller's name as Ana Duarte earlier in the conversation. This could lead to privacy issues or miscommunication.
- **Expected:** The agent should have acknowledged the caller as Ana Duarte and addressed her accordingly.

## Failure to resolve scheduling request
- **Severity:** high
- **Where:** `call-09-vague/transcript.txt` at 02:06
- **Agent said:** “I'll connect you to our patient support team so they can help you get scheduled. Please stay on the line. Addressing you now, thank you.”
- **Problem:** The agent transferred the caller to a test line rather than to a support team capable of making an appointment, leaving the patient's request unresolved.
- **Expected:** The agent should have connected the caller to the appropriate scheduling department or provided other means to schedule an appointment.

## Failure to continue appointment booking process
- **Severity:** high
- **Where:** `call-10-topic_switch/transcript.txt` at 01:48
- **Agent said:** “I can't proceed further right now, but I can make sure our clinic support team follows up with you.”
- **Problem:** The agent abruptly stopped the appointment booking process and did not follow up with obtaining important information or confirming the appointment.
- **Expected:** The agent should have either continued with booking the appointment or clearly explained why it could not proceed and what steps were being taken to ensure follow-up.

## Improper call transfer
- **Severity:** high
- **Where:** `call-10-topic_switch/transcript.txt` at 02:04
- **Agent said:** “Transferring you now, thank you. Hello. You've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The call was transferred to an incorrect destination, resulting in the call ending without resolving the caller's issue regarding appointment booking and billing inquiry.
- **Expected:** The agent should have properly transferred the caller to the actual patient support team instead of the 'test line', ensuring the caller's issues can be addressed.

## Failure to Escalate Clinical Question
- **Severity:** high
- **Where:** `call-12-medical_advice/transcript.txt` at 02:10
- **Agent said:** “I can't proceed further right now, but I can make sure our clinic support team follows up with you. Would you like me to have them call you back about your metformin and medication questions?”
- **Problem:** The agent should escalate immediate clinical questions to a human to ensure patient safety, especially as the caller is concerned about medication dosage which is critical and time-sensitive.
- **Expected:** The agent should immediately offer to have a clinical staff member or doctor call the patient back to address the medication dosage questions promptly.

## Transfer Ended Without Resolution
- **Severity:** high
- **Where:** `call-12-medical_advice/transcript.txt` at 02:30
- **Agent said:** “Transferring you now. Thank you.”
- **Problem:** The agent transferred the caller without ensuring that the transfer would resolve the query. The transfer led to an automated message, and the call ended without resolving the caller’s urgent medication question.
- **Expected:** Ensure the transfer connects the caller to a human who can document the issue or provide guidance, or confirm a doctor will return the call.

## Failed Transfer and Broken Escalation
- **Severity:** medium
- **Where:** `call-02-reschedule/transcript.txt` at 02:13
- **Agent said:** “Transfer you now. Thank you Hello. You've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The agent attempted to transfer the caller to the patient support team but instead directed them to a test line, causing the call to end without resolving the caller's request.
- **Expected:** The agent should have properly connected the caller to the patient support team or a human receptionist who could have handled the request to reschedule the appointment and cancel the old one.

## Failed to confirm cancellation or provide information on cancellation fee.
- **Severity:** medium
- **Where:** `call-03-cancel/transcript.txt` at 01:59
- **Agent said:** “I'll connect you to our patient support team for help with your cancellation. Please stay on the line. Transferring you now. Thank you.”
- **Problem:** The agent did not confirm the cancellation of the appointment or provide information on potential cancellation fees. Instead, it transferred the caller without resolution.
- **Expected:** The agent should have confirmed the cancellation of the Friday appointment and informed the caller if there was a cancellation fee, or properly transferred the call to someone who could handle it, ensuring the request was fulfilled.

## Failed to resolve medication refill request or ensure correct patient record
- **Severity:** medium
- **Where:** `call-04-refill/transcript.txt` at 02:47
- **Agent said:** “I'm unable to access your record right now, so I can't process the refill directly. I'll connect you to our patient support team so they can help with your medication and update your information.”
- **Problem:** The AGENT did not resolve the caller's request to refill lisinopril, nor did it confirm and amend the incorrect patient records when necessary.
- **Expected:** The AGENT should have immediately transferred the call to a human representative upon realizing it could not access the patient's records or resolve the request on its own.

## Incorrect Name Verification
- **Severity:** medium
- **Where:** `call-07-closed_weekend/transcript.txt` at 01:47
- **Agent said:** “I see you're calling from the number we have on file, am I speaking with Daniel?”
- **Problem:** The agent mistakenly addressed the caller as Daniel, despite having correctly verified the caller's name as Greg Tanaka earlier in the call.
- **Expected:** The agent should have used the correctly verified name, Greg Tanaka, instead of mistakenly addressing the caller as Daniel.

## Failure to Confirm Office Closure on Weekends
- **Severity:** medium
- **Where:** `call-07-closed_weekend/transcript.txt` at 02:15
- **Agent said:** “Would you like me to have them contact you about booking your appointment?”
- **Problem:** The agent did not inform the caller that the office is closed on weekends after the caller repeatedly requested a Sunday or weekend slot. This leaves the caller's inquiry unresolved.
- **Expected:** The agent should have directly informed the caller that the office is closed on weekends, clarifying that appointments cannot be scheduled during that time.

## Incorrect name confirmation
- **Severity:** medium
- **Where:** `call-11-spelling/transcript.txt` at 01:19
- **Agent said:** “I have your name as Oyse Nibronane”
- **Problem:** The AGENT incorrectly confirms the caller's name, despite asking to spell it and then misinterpreting it.
- **Expected:** The AGENT should accurately record and confirm the spelling that the caller provided.

## Incorrect name confirmation
- **Severity:** medium
- **Where:** `call-11-spelling/transcript.txt` at 01:43
- **Agent said:** “I have your name as Ayuf, space, me, Brownain, spelled A-O-I-F-E, space, N-I, space, E-H-R-A-O-N-A-I-N”
- **Problem:** The spelling provided by the AGENT was incorrect and did not match what the caller spelled out.
- **Expected:** The AGENT should listen carefully to the spelling given by the caller and read it back accurately as the caller spelled.

## Unresolved appointment booking
- **Severity:** medium
- **Where:** `call-11-spelling/transcript.txt` at 02:39
- **Agent said:** “I wasn't able to find a matching record for you in our system. I'll connect you to our patient support team so they can help set up your first appointment. Please stay on the line. Transferring you now. Thank you.”
- **Problem:** The AGENT failed to book the appointment and instead attempted to transfer the caller without resolving the request.
- **Expected:** The AGENT should have effectively processed the first appointment booking request, or successfully transferred the caller to someone who could help, ensuring the transfer goes through correctly.

## Failed call transfer
- **Severity:** medium
- **Where:** `call-11-spelling/transcript.txt` at 02:44
- **Agent said:** “Hello, you've reached the pretty good AI test line, goodbye.”
- **Problem:** The AGENT's transfer attempt failed, leading to the caller reaching an incorrect line.
- **Expected:** A successful transfer to the patient support team to complete the booking request, followed by confirmation the transfer has been made. If the transfer fails, the AGENT should remain engaged to resolve the call.
