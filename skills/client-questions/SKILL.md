---
name: client-questions
description: "Prepare the question list for a meeting with a client, customer or external party who owes you decisions and data — sweep the repo and the tracker in parallel for everything blocked on them, find what was already asked (usually in chat, not the repo), triage into live / deliberately parked / already answered, phrase each live question as it would be spoken plus one line on what changes based on the answer, and cross-check against the last set so nothing is asked twice. Use when the user says \"co se máme zeptat klienta\", \"otázky na klienta\", \"připrav otázky na zítřejší call s klientem\", \"co po klientovi potřebujeme\", \"máme na zítra něco pro klienta?\", \"what should we ask the client\", \"prepare questions for the customer meeting\", or asks what is currently blocked on an external party. Not catching up on what someone wrote to you — that is `dm-catchup`; not the personal task queue — that is `work-start`."
license: MIT
---

# client-questions — procedure

A meeting with the party who owes you decisions is a one-shot resource. The failure mode is not asking a bad question; it is spending the slot on questions whose answers were already given, while the one question that would have saved a month goes unasked because nobody swept for it.

## 1. Establish who is asked, and who forwards

Before searching anything, read the project's instructions file (`AGENTS.md`, `CLAUDE.md` or equivalent): who the other party's contacts are, who the PM is, where the tracker and the chat live, which channels are read-only, and any API rate limits. The sweep in §2 depends on all of it, and none of it is in the skill. Then settle three things with the user:

- **Who answers.** The client's decision-maker, their lawyer, a platform vendor's consultant, and an end customer of theirs are four different audiences with four different competences. Mixing them into one list produces questions nobody in the room can answer.
- **Who carries the list.** Usually a PM, not you. That decides the register: the PM has to be able to ask each question without further briefing.
- **How much room there is.** Ten minutes buys three questions, not twenty. Ask, then rank ruthlessly to fit. Fitting does not mean dropping: live questions that do not fit go below a divider, marked for sending in writing after the call, so the list still forwards without editing (§9).

If several audiences turn out to be in scope, produce **one list per audience** and say explicitly what each one *cannot* answer (§7). Two people on the same side with different remits are one audience with a named addressee per question, not two lists.

If the user is not available to answer, state the assumptions you are proceeding on at the top of the output and carry on; do not stop.

## 2. Sweep, in parallel, from three sources

These are independent and each is a broad read, so dispatch them as separate read-only agents rather than doing them in sequence — unless two of them sit behind the same rate-limited API, in which case sweep those two one after the other and give each a call budget.

**The repository.** Planning and gap-analysis documents; architecture records and their dated amendments; proposals with an "open decisions" section; runbooks carrying "pending" or "to be supplied" markers; and any sample data the other party supplied. Search in every language the project is written in.

**The tracker.** Tasks whose status, description or comments say they are blocked on the other party, waiting on a decision, waiting on data (sample files, code lists, schemas, credentials), or carrying legal questions that must be answered on their side. Few trackers have a blocked-on-them status; learn the project's own marker first — a naming convention such as `DCZ-CONFIRM`, a section title like "Open with client", a tag — and search for that. Include closed tasks — a question answered once should end up in the "already answered" bucket, not be re-asked.

**Chat and mail.** This is the source people skip, and it is usually where the last question set actually lives — sent as a message to the PM, or by the PM to the other party, rather than committed anywhere. Without it you will re-ask half of it. Look for messages *to the other party from anyone* — the PM, the tech lead — not only for messages to the PM. Expand threads: the answer is usually a reply, and often an attachment. An attachment you cannot open is "an answer exists, unread" — record it as that, never as answered and never as missing. Record message ids alongside dates, so a claim can be re-fetched later without re-sweeping.

Report a clean negative honestly, and keep it apart from a truncated one: "searched X, Y, Z — nothing" is a finding; "not reached within the call budget" is a gap, and the two must never share a label. "No record of this anywhere" is a finding, and it is often the point: a question asked four months ago with no recorded answer is stronger material than a new one.

## 3. Triage into three buckets

**Live** — ask now.

**Deliberately parked** — the user decides to defer it (with the user absent, propose the parking and mark it as proposed). Keep it in the written output anyway, each with **the cost of parking it stated in one clause**. Parking is a legitimate choice; parking silently is how a risk disappears.

**Already answered** — with the date and the answer. This bucket earns its place twice: it stops the same question going out again, and it lets the PM see that the list was built on what the other party already said. Asking someone to re-supply something they explicitly told you they cannot supply reads as not listening, and costs credibility you will need later.

## 4. Write each live question the way it would be spoken

For every live question, two parts:

- **The question in the client's language** — the natural language the project mandates for client-facing artefacts, and the client's own vocabulary — phrased as the PM would say it out loud, not as an internal ticket title.
- **Why it matters**, in one or two sentences: what is blocked, and what changes depending on the answer. This is what lets the PM push when the answer is vague, and what lets them drop the question if the meeting runs short.

Never phrase a question as an open invitation where a decision is what you need ("what is your vision for the editor?"). Offer the concrete options instead, priced where you can price them.

## 5. Rank by what the answer is worth

Put first the questions where:

- **A wrong guess is expensive and hard to reverse** — money moves, data is destroyed, a schema is fixed.
- **The answer cannot be obtained any other way.** Anything you could determine yourself from documentation or a test environment is not a question for the meeting; go and determine it, within a bounded effort. If determining it would cost more than the rest of the preparation, keep it on the list labelled "determinable, not yet determined" rather than asking it as an open question.
- **Trying it out cannot reveal the answer.** This is the class most often missed. When the failure mode is a *successful* operation with wrong results — a duplicate import that is accepted and quietly pays someone twice — no amount of iterating against the real system will surface it. Say so in the "why it matters" line; it is the strongest argument for asking.
- **The cost of asking is near zero for them** — a contact, a file they already have, a number they know.

## 6. Read their own data back to them

If the other party has supplied a sample file, a spec or an export, go through it for internal inconsistencies and unrepresented cases: the same field encoded two ways in two rows, a supported variant that never appears, a blank where a zero was expected, a format variant not covered. These make excellent questions — cheap, precise, answerable on the spot — and they demonstrate the sample was actually read, which changes how the rest of the list is received.

If the sample is a PDF or a spreadsheet the sweep cannot parse, run the check against the project's own transcription of it (an ADR, a seed file) and say so — an inconsistency in the transcription is still worth one question.

Check the date on it, too. "This sample is from April and the structure has moved since — is it still current?" is one line and prevents building against a stale shape.

## 7. Say what each audience cannot answer

Split what is **per-platform** from what is **per-installation**, and route accordingly. A vendor's generic consultant can tell you the shape and the rules of a format; only a specific end customer can give you their own code lists, identifiers and configuration. Writing this boundary into the list prevents a wasted round trip and an answer of "that depends". When the per-platform party is reachable only through the other party — or they have asked you not to contact the vendor directly — the question stays on their list and becomes "please route this to them, or give us direct contact".

## 8. Cross-check before it goes out

Against every previous question set found — all of them, not only the last; the sets from months ago are where the unanswered follow-ups live — item by item: anything already asked either moves to the "already answered" bucket with its answer, or is re-asked *explicitly as a follow-up* naming when it was first asked and that no answer came. The second form is far stronger than asking afresh — a question outstanding since April is evidence, not just a question.

Then verify every factual claim in the list against its source. A list that states "you told us X in April" must be able to point at where. Where two records disagree about who asked what and when, cite the message actually sent to the other party, with its date and id, over an internal note.

## 9. Deliver

A list the PM can forward without editing: the live questions in priority order, the parked ones with their cost, the closed ones with their answers, and — separately — anything that is not a question for this audience at all but an internal follow-up for a named colleague.

Offer to persist it where the team will find it later — in the committed project docs, not in a gitignored local folder and not in a chat message. A question set that exists only in a chat message is the same gap that §2 had to work around, one iteration later.
