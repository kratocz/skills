---
name: debate-reply
description: "Answer a public challenge to a claim the user has written down — verify the opponent's case against primary sources rather than summaries, concede what they actually get right, strengthen the user's own note first when the challenge exposed a gap, then draft a reply that opens with the concession and closes with one question the opponent must answer, and archive the exchange with its receipts. Use when the user forwards someone's counter-argument, article or comment and asks \"co je pravda?\", \"kdo má pravdu?\", \"lze mu na to smysluplně odpovědět?\", \"napiš mu odpověď\", \"is he right?\", \"draft a reply to this\", or wants a rebuttal they will post under their own name."
license: MIT
---

# debate-reply — procedure

For public arguments where the user defends a position they have already written down somewhere (a notes repo, a blog, a spec) and someone has pushed back. The output is three things, in this order: **a corrected note, a postable reply, an archived record.** Getting them in that order is the whole point — the note is what survives, the reply is what gets read once.

Respond in the language the user has been using. The reply itself goes in the language of the debate.

## 1. Get both texts raw

Fetch the opponent's source yourself and read the whole thing. Note who wrote it and what they are — not to attack them, but because "professor at X" and "self-published ministry" carry different default weight, and the user may not know.

**Do not argue against a summary.** A summarizing fetch of a scripture/legal/primary-source site returned a garbled paraphrase that silently dropped the exact clause the argument turned on. When the wording is load-bearing, pull raw text:

- scripture: `bible-api.com/<book>+<ch>:<v>?translation=web` (English), `obohu.cz/bible/index.php?styl=<TRANSLATION>&k=<book>&kap=<ch>` (Czech B21/ČEP), `biblehub.com/text/<book>/<ch>-<v>.htm` (Hebrew/Greek morphology)
- anything else: fetch the page and strip tags locally rather than asking a model to summarize it

**Quote the opponent's own translation/edition.** An argument made in their text is much harder to wave off than the same argument made in yours.

## 2. Steelman before you refute

Find the strongest version of their case *before* writing a word against it. Specifically look for:

- **a real fact they have** that the user's note does not mention at all
- **a textual or technical detail** that genuinely supports them (a grammatical form, a date, a measurement)
- **a fair concession** the user should make regardless of who wins

If you cannot state their position in a form they would accept, you are not ready to answer it. A rebuttal that only beats the popular version invites the correction "but you didn't address X" — and then the user has lost the exchange on procedure.

## 3. Verify every load-bearing claim on both sides

Theirs *and* the user's. The user's note is not exempt — it is the thing most likely to contain an unexamined weak sentence, because nobody has attacked it before.

Record what each check cost: claims you had to withdraw, weaken, or could only source to an encyclopedia summary rather than the primary evidence. Those go in the archive (step 6) and, where they touch the note, into the note.

## 4. Fix the user's own note FIRST, and commit it

If step 2 found something real, the note is now known-weak. Fix it before drafting the reply, and commit that separately. Two reasons: the reply then points at something true, and if the user never sends the reply, the durable artifact is still better than it was.

The fix is usually not a retraction. It is: **concede the strong point explicitly, then defeat it.** Say in the note that an earlier draft omitted it — a note that only shows its wins is advertising.

## 5. Shape the reply

Structure that works:

1. **Open with the concession.** Name what they got right, specifically, and thank them for it. If they conceded things too, list those — it makes visible how far the defended thesis has already moved.
2. **Name the shift, if there is one.** People often start defending claim A ("the text is never wrong") and end up defending claim B ("you can't decisively prove this instance wrong"). Both may be reasonable; they are not the same claim, and only one was the original.
3. **Two to four numbered objections, strongest first.** Each should be checkable, not rhetorical.
4. **Pre-empt their best comeback** inside the relevant objection, rather than leaving it as a gotcha they can spring.
5. **Close with exactly one question** they have to answer.
6. **Hostile-reader pass.** Before handing the draft over, re-read every sentence as an opponent who treats each concession as a confession ("so you admit science is wrong"; "so you admit archaeology confirms it"). A concession that stands alone in its sentence is a quote for their audience: put its limit or consequence in the same sentence, and spell the consequence out — what their own claim implies for their own predictions — rather than leaving it to be inferred. When the reply needs cutting, cut whole paragraphs, never the fork half of a sentence. And when the opponent hands you the hook ("we lack the information for a definitive verdict"), an unsent symmetry thread belongs in this reply, not in a separate one.

Then tell the user separately (not in the reply): which objection is actually strongest, which sentence is the weakest link, and anything you would leave out and why.

### The two moves that generalize

**The dial.** When someone claims a text is both *precisely* fulfilled (in the convenient part) and *loosely* meant (in the inconvenient part), name the dial explicitly: every setting that saves the claim from being false costs exactly as much evidential force as it saves. Either it is precise — and then it is checkable and it failed — or it is loose, and then there is nothing left to admire. This move works far outside scripture: forecasts, business cases, retrospective predictions of any kind.

**Symmetry.** If the opponent has made, or can be drawn into making, a checkable claim of their own, offer the same rule to both sides *in advance*, before anyone knows the outcome: "what result would mean this was wrong?" Agreement turns the dispute into a dated bet; refusal demonstrates the double standard better than any argument. When they do supply dates, offer to put them in the user's calendar with the verbatim quote and the pre-agreed criterion in the description.

## 6. Archive the exchange

One directory per person, one file per exchange, in whatever repo the user keeps for this (check memory; often a separate private repo, not the public notes repo). File shape:

```markdown
# <Topic> — <Person>

- **Datum:** YYYY-MM-DD
- **Kanál:** where it happened
- **URL:** link (TODO if the user will add it)
- **Stav:** draft / odesláno YYYY-MM-DD
- **Zdrojová poznámka:** path in the notes repo

---

## Odeslaná odpověď
<the reply, verbatim as sent>

---

## Podklady (interní, neposílat)
<what each claim is verified against, which claims are weak, what to avoid saying and why>
```

The internal section is the part with long-term value: in a year nobody remembers which sentence was solid and which was borrowed from a summary.

## 7. Discipline

- **Never attribute without a source.** Who said a thing, who chose the topic, who raised which point — check it in the actual text before writing it. Getting this wrong in a public reply hands the opponent a free correction, and it is the single easiest mistake to make when summarizing a long thread.
- **A draft over ~300 words goes in a file, not in chat.** The user will edit and paste it; terminal scrollback is a bad place for that, and every revision reprints the whole thing.
- **Distinguish attacking the argument from attacking the tradition.** Note when a line of attack (their denomination's own record, their sources' reputation) would derail a solvable dispute into an identity fight, and recommend leaving it out. Say so to the user; do not put it in the reply.
- **Check the user's own tone in the thread.** If they opened mockingly, say so plainly — it is usually why the opponent reframed the exchange from evidence to identity, and the draft should de-escalate rather than match it.
- **Do not state the user's beliefs for them.** When the reply needs a line about what the user does or does not hold, write it from what they have actually written down and flag it for them to check.
