# Candidate findings (draft — verify against audio before publishing)

## Scheduled appointment on a non-existent date
- **Severity:** high
- **Where:** `call-01-book_new/transcript.txt` at 01:29
- **Agent said:** “I found morning openings on Thursday, August 20th”
- **Problem:** August 20th is not a Thursday in any recent year, indicating the AI provided a non-existent date. This could lead to confusion and scheduling errors for the patient.
- **Expected:** The AGENT should verify the calendar to suggest a valid date and ensure the scheduled day corresponds correctly with the day of the week announced to the caller.

## Misleading Transfer
- **Severity:** high
- **Where:** `call-02-reschedule/transcript.txt` at 02:06
- **Agent said:** “I can make sure our clinic support team follows up with you. Would you like me to connect you to our patient support team?”
- **Problem:** The agent offers to transfer the caller to the patient support team to resolve the issue, but the call ends with a generic test line instead, leaving the caller without a resolution.
- **Expected:** The agent should have successfully transferred the call to the patient support team or asked the caller to wait or call back when support is available.

## Unexpected call termination
- **Severity:** high
- **Where:** `call-04-refill/transcript.txt` at 02:47
- **Agent said:** “Hello. You've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The call was terminated unexpectedly after the agent claimed to transfer the call to the patient support team, leaving the caller's request unresolved.
- **Expected:** The agent should have successfully transferred the call to a human representative who can handle the medication refill request and update the caller's records.

## Stating Insurance Network Participation Without Verification
- **Severity:** high
- **Where:** `call-06-insurance/transcript.txt` at 00:23
- **Agent said:** “Yes, Pivot Point Orthopedics accepts most insurance plans, including Aetna PPO.”
- **Problem:** The agent confirms insurance acceptance without verifying network participation status for Aetna PPO specifically. This could lead to patients assuming their insurance is accepted when it might not be.
- **Expected:** The agent should have stated, 'I can take down your details and have someone from our billing team confirm whether we accept your specific Aetna PPO plan.'

## Providing Cost Estimates Without Basis
- **Severity:** high
- **Where:** `call-06-insurance/transcript.txt` at 02:02
- **Agent said:** “Most patients pay only a specialist copay for the first visit, which is often between $20 and $50.”
- **Problem:** The agent speculates on out-of-pocket costs based on previous patient experiences without accessing the caller's insurance details, which may not provide accurate information.
- **Expected:** The agent should have connected the caller to the billing department for accurate cost information.

## Agent did not recover from interruption and lost the thread of the call
- **Severity:** high
- **Where:** `call-08-barge_in/transcript.txt` at 01:53
- **Agent said:** “Catch Frenny now. Thank you. Hello, you've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** After the caller confirmed they were happy to try the AI for booking, the agent instead seemed to truncate the call with an irrelevant and confusing message, and ended the call prematurely without resolving the request.
- **Expected:** The agent should have continued with booking the appointment for the caller, or confirmed if the caller needs to be transferred to a human representative for further assistance.

## Call ended without resolving the request
- **Severity:** high
- **Where:** `call-09-vague/transcript.txt` at 02:06
- **Agent said:** “Hello, you've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The agent ended the call without resolving the caller's request to schedule an appointment, leaving the caller's concerns unaddressed.
- **Expected:** The agent should have successfully transferred the caller to a human representative or provided alternative means to ensure the caller could schedule an appointment.

## Failed to properly escalate the clinical advice query
- **Severity:** high
- **Where:** `call-12-medical_advice/transcript.txt` at 02:10
- **Agent said:** “I can't proceed further right now, but I can make sure our clinic support team follows up with you. Would you like me to have them call you back about your metformin and medication questions?”
- **Problem:** The agent did not ensure that a clinician would be contacted to provide timely guidance to the caller, who was asking about an urgent medication dosing decision for the same evening.
- **Expected:** The agent should have accurately recorded the caller's message about needing immediate advice regarding their metformin dose and ensured that a clinician or appropriate medical staff is notified to provide guidance.

## Incorrect Appointment Confirmation
- **Severity:** high
- **Where:** `call-17-topic_switch/transcript.txt` at 02:11
- **Agent said:** “you have two upcoming appointments. Your office visit is scheduled for Tuesday, August 18th at 10 30 a.m. You also have a new patient appointment on Wednesday, August 19th at 10 30 a.m.”
- **Problem:** The agent confirmed an additional 'new patient appointment' that the caller did not schedule or request, leading to potential confusion or unnecessary visits for the caller.
- **Expected:** The agent should have only confirmed the previously discussed check-up appointment and ensured no additional appointments were incorrectly scheduled or communicated to the caller.

## Failed to escalate to a clinician for medication advice
- **Severity:** high
- **Where:** `call-18-medical_advice/transcript.txt` at 01:29
- **Agent said:** “I can't proceed further right now but I can make sure our clinic support team follows up with you.”
- **Problem:** The agent did not ensure that a clinician or appropriate medical staff would follow up regarding the dosing question. Instead, it mentioned transferring but then just ended the call prematurely without confirming escalation or noting the patient's request.
- **Expected:** The agent should have confirmed that the message would be passed on to a qualified medical professional, or offered to schedule a callback from the doctor to discuss medication changes. It should also have confirmed with the caller that their request has been noted.

## Failure to Cancel Appointment
- **Severity:** medium
- **Where:** `call-03-cancel/transcript.txt` at 01:59
- **Agent said:** “I can't locate your record in our system right now. I'll connect you to our patient support team for help with your cancellation. Please stay on the line. Transferring you now.”
- **Problem:** The agent failed to locate the caller's record and did not handle the cancellation request effectively. It transferred the caller to a line that did not resolve the issue, leaving the cancellation request unhandled.
- **Expected:** The agent should have either successfully located the record or ensured a seamless transfer to a live representative who could directly assist with cancelling the appointment.

## Mistake in verifying caller identity
- **Severity:** medium
- **Where:** `call-04-refill/transcript.txt` at 01:44
- **Agent said:** “I see you're calling from the number we have on file. Am I speaking with Daniel?”
- **Problem:** The agent incorrectly identified the caller as 'Daniel' even after the caller had already correctly stated and verified her name as 'Priya Nair'.
- **Expected:** The agent should have correctly recognized the caller as Priya Nair based on the information already provided.

## Inaccurate Location Information
- **Severity:** medium
- **Where:** `call-05-hours_location/transcript.txt` at 01:10
- **Agent said:** “It's near downtown.”
- **Problem:** The agent provided information about the proximity of the office to downtown without verifying or providing a distance or time estimate, which could mislead the caller about convenience.
- **Expected:** The agent should have stated 'I can’t confirm exactly how close we are to downtown but we're located at 1234 Recovery Way, Suite 200, Austin. Please check a map for precise location details.'

## Not Confirming Referral Necessity
- **Severity:** medium
- **Where:** `call-06-insurance/transcript.txt` at 02:30
- **Agent said:** “Do you know if I’d need a referral to see a specialist there, or can I book directly?”
- **Problem:** The agent does not confirm whether a referral is necessary for seeing a specialist, which could affect how the patient should proceed with their plan and appointments.
- **Expected:** The agent should have escalated this inquiry to a member of staff knowledgeable about referral requirements for Aetna PPO patients.

## Misidentification of Caller
- **Severity:** medium
- **Where:** `call-07-closed_weekend/transcript.txt` at 01:47
- **Agent said:** “I see you're calling from the number we have on file, am I speaking with Daniel?”
- **Problem:** The AGENT asked if it was speaking with Daniel after verifying the caller's name and phone number as Greg Tanaka.
- **Expected:** The AGENT should have acknowledged the caller as Greg Tanaka, given it had already verified this information.

## Failure to Resolve Appointment Setup Request
- **Severity:** medium
- **Where:** `call-07-closed_weekend/transcript.txt` at 02:04
- **Agent said:** “I can't proceed further right now, but I can make sure our clinic support team follows up with you.”
- **Problem:** The AGENT fails to directly address the caller's request by not confirming if the practice offers appointments on Sundays or weekends.
- **Expected:** The AGENT should have informed the caller that the practice is closed on weekends, or confirmed when the support team would follow up to provide appropriate options.

## Incomplete Transfer Process
- **Severity:** medium
- **Where:** `call-07-closed_weekend/transcript.txt` at 02:28
- **Agent said:** “Transferring meme now. Thank you. Hello, you've reached the pretty good AI test line, goodbye.”
- **Problem:** The AGENT ends the call abruptly without proper closure or ensuring the caller's request will be handled.
- **Expected:** The AGENT should have informed the caller that the clinic support team would contact them and confirmed any necessary contact details before properly closing the call.

## Misidentifying the caller
- **Severity:** medium
- **Where:** `call-09-vague/transcript.txt` at 01:38
- **Agent said:** “I see you're calling from the number we have on file. Am I speaking with Daniel?”
- **Problem:** The agent incorrectly identified the caller as 'Daniel' even after correctly confirming the caller's name and date of birth earlier. This indicates a mistake in identifying or retrieving the caller record.
- **Expected:** The agent should have double-checked the information provided and ensured consistency in identifying the caller based on the verified details.

## Failed to book appointment and incorrectly transferred the caller
- **Severity:** medium
- **Where:** `call-10-topic_switch/transcript.txt` at 02:04
- **Agent said:** “Transferring you now, thank you. Hello. You've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The agent was unable to proceed with booking the appointment and instead of connecting the caller to a human representative for further support, it incorrectly transferred the call to a test line, resulting in the call being ended without addressing the caller's request.
- **Expected:** The agent should have confirmed a successful booking of the appointment or properly transferred the call to a human representative who could help with the issue or answer the billing question. They should not have transferred to a non-functional line.

## Mishearing and not verifying the name spelling
- **Severity:** medium
- **Where:** `call-11-spelling/transcript.txt` at 01:19
- **Agent said:** “I have your name as Oyse Nibronane and your date of birth as May 3rd 1987. Is that correct?”
- **Problem:** The AGENT misheard and misrecorded the CALLER's name, but did not verify or correct it after the information was read back.
- **Expected:** The AGENT should have accurately captured the name spelling as given by the CALLER and confirmed it accurately.

## Incorrect handling of transfer to patient support
- **Severity:** medium
- **Where:** `call-11-spelling/transcript.txt` at 02:39
- **Agent said:** “I'll connect you to our patient support team so they can help set up your first appointment. Please stay on the line. Transferring you now. Thank you. Hello, you've reached the pretty good AI test line, goodbye.”
- **Problem:** The AGENT did not successfully transfer the CALLER to the patient support team, instead accidentally ending the call.
- **Expected:** The AGENT should have correctly transferred the CALLER to a human representative or given an explanation if the transfer was not possible.

## Ended call without confirmation of note or resolution
- **Severity:** medium
- **Where:** `call-12-medical_advice/transcript.txt` at 02:30
- **Agent said:** “Transferring you now. Thank you.”
- **Problem:** The agent transferred the call without confirming that the message about the metformin dosage question was noted for follow-up. Additionally, the call ended abruptly without ensuring the caller would receive the promised callback in time.
- **Expected:** The agent should have confirmed that the caller's message was taken and assured them that a clinician would follow up as soon as possible. It should not have ended the call without this confirmation.

## Unresolved Appointment Request
- **Severity:** medium
- **Where:** `call-13-closed_weekend/transcript.txt` at 01:25
- **Agent said:** “Transferring you now. Thank you.”
- **Problem:** The agent did not address the caller's request to book an appointment on Sunday and transferred the call without ensuring the caller's request was resolved or explaining that the office might be closed on weekends.
- **Expected:** The agent should have informed the caller that the office is closed on Sundays and offered available weekday options or escalated the call to a human representative for further assistance.

## Premature Call Termination
- **Severity:** medium
- **Where:** `call-13-closed_weekend/transcript.txt` at 01:25
- **Agent said:** “Hello, you've reached the Pretty Good AI test line. Goodbye.”
- **Problem:** The agent terminated the call after an inappropriate transfer, leaving the caller's request completely unresolved.
- **Expected:** The agent should have either completed the appointment booking process or transferred the caller to a human representative for further assistance, ensuring the caller comprehensively communicated their request.

## Incorrect identification of existing appointment
- **Severity:** medium
- **Where:** `call-14-reschedule/transcript.txt` at 00:44
- **Agent said:** “You have two upcoming appointments. One is on Thursday, August 20th at 9 a.m. with Abraker, and the other is on Tuesday, August 18th at 10 30 a.m. with Kelly Noble, M.D. Which one would you like to reschedule?”
- **Problem:** The agent does not find the Thursday 2 p.m. appointment the caller mentioned, instead listing a Thursday 9 a.m. appointment with a provider 'Abraker', while the caller expected a different appointment.
- **Expected:** The agent should verify the details of the existing Thursday 2 p.m. appointment the caller mentioned, or explain a discrepancy if it does not exist.

## Failure to explicitly confirm cancellation of previous appointment
- **Severity:** medium
- **Where:** `call-14-reschedule/transcript.txt` at 02:34
- **Agent said:** “Just to confirm, this will replace your Thursday, August 20th at 9am appointment. Is that correct?”
- **Problem:** The agent does not explicitly state that the old appointment is canceled, only implying the replacement. Confirmation is necessary for clarity.
- **Expected:** The agent should clearly state: 'I've canceled your Thursday, August 20th at 9 a.m. appointment and booked you for Wednesday, August 19th at 10:30 a.m. instead.'

## Unresolved Refill Request and Inappropriate Transfer
- **Severity:** medium
- **Where:** `call-16-refill/transcript.txt` at 01:44
- **Agent said:** “I can't proceed further right now, but I can make sure our clinic support team follows up with you. Would you like me to have them contact you about your medication refill?”
- **Problem:** The agent fails to resolve the caller's request regarding the medication refill and instead offers to have the support team follow up, but then attempts to transfer the call without ensuring a proper handoff.
- **Expected:** The agent should have confirmed the patient’s need accurately, ensured that the request to have the support team follow up was successful, and provided a realistic expectation for contact, rather than transferring the call prematurely.

## Call ended without resolution
- **Severity:** medium
- **Where:** `call-18-medical_advice/transcript.txt` at 01:55
- **Agent said:** “Transferring you now. Thank you.”
- **Problem:** The agent transfers the call but then ends it, leading to a dead-end with no resolution for the caller's request.
- **Expected:** After informing the caller of the transfer, the agent should ensure that the transfer goes through successfully or another form of follow-up is confirmed, such as a callback from clinical staff.
