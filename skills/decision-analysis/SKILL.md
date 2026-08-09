---
name: decision-analysis
description: "Produce a context-anchored decision analysis that ends in a verdict: scaffold the document with dated decision rules written BEFORE any research, then research in rounds, recording every load-bearing claim with a numbered source reference and a verification date, keeping the verdict on a durable layer and quarantining perishable facts into a dated snapshot. Use when the user wants to decide between options and write the reasoning down — \"srovnej X a Y\", \"which should I pick\", \"help me decide between\", \"write up this decision\", \"udělej srovnání\", \"decision analysis\", \"rozhodovací analýza\" — or asks to research a choice thoroughly enough to defend it later."
license: MIT
---

# Decision analysis

A decision analysis is not a feature matrix. It is one concrete decision, made
for one concrete profile, with the trade-offs that were accepted written down —
so that a reader (including future-you) can tell whether the verdict still
applies to them.

This skill is methodology only. Repo-specific conventions — directory naming,
language pairs, index tables — belong in that project's `AGENTS.md`, not here.

**Load `kodex` alongside this skill** if it is installed. This skill is the
document-shaped application of several of its rules (decision rules before
results, fact/inference labelling, cheap verification first, adversarial
checking). Do not restate the codex here; follow it.

## Step 1 — Scaffold before researching

Create the document first, empty of findings. Research done before the frame
exists gets rationalised into whatever the research happened to find.

The scaffold has four parts:

**Context.** The concrete profile the verdict will claim validity for, and
nothing beyond it: who decides, what they already own or run, hard constraints,
budget, timeline, what "good" means here. Ask the user for anything load-bearing
that is missing — a decision analysis anchored to a guessed profile is worthless.

Pay particular attention to the **status quo**. If the user already owns or runs
one of the options, say so explicitly: it is not one candidate among equals, it
is the default, and every other option must additionally justify a switching
cost (migration, lost history, retraining, exit lock-in).

**Decision rules, dated, written now.** For each possible outcome, what follows
from it. Write them before any evidence arrives so they are *read* after the
results rather than invented to fit them. Mark the date in the document.

If this decision feeds a second, nearer decision (a purchase deadline, a
deployment window), state that chain in the rules explicitly — including any
outcome that would invalidate the second decision rather than merely adjust it.
That branch is usually the reason the analysis is worth doing at all.

**Empty durable and dated sections** (see step 4).

**A verdict section, empty**, with a template: the option chosen, the accepted
trade-offs, and a *revival clause* — the conditions under which the decision
should be reopened.

Confirm the scaffold with the user before researching. Rules the user has not
read are not rules.

## Step 2 — Research in rounds, cheapest decision-critical claims first

Do not research breadth-first. Order the work by *how much the answer moves the
verdict per unit of effort*.

The first round is usually a handful of claims that could invalidate whole
branches — compatibility, licensing, availability in the user's country,
platform lock. These are cheap to check and can collapse the option space before
expensive work starts. Report after each round what changed and what did not.

Between rounds, ask whether the next round is still worth running. A branch
eliminated in round one does not need its features tabulated.

## Step 3 — Record claims so they can be audited later

Every load-bearing claim carries a numbered reference `[R1]`, `[R2]`, … resolved
in a References section with a URL and the date it was verified.

- **Tag what is not verified**, inline, with `[VERIFY]` (or the user's language
  equivalent). A half-researched document must never read as finished. The
  document header states which parts are verified and names the open tags.
- **Label fact versus inference** in the prose: "X is still on the support list
  (fact); by the Y pattern its support likely ends around Z (inference)". An
  inference in a fact's clothes is the most expensive error this format makes.
- **Prefer primary sources** — the vendor's own spec or support page over a
  review quoting it, the standard over a blog explaining it.
- **Record contradictions** rather than silently picking a side. When two
  sources disagree, say so in the document, name which one is treated as
  authoritative, and why.
- **Findings from an earlier AI conversation are hypotheses, not sources.**
  Verify them against primary sources before they enter the document. When one
  turns out to be wrong, correct it plainly and say what it changes.

## Step 4 — Keep the verdict on the durable layer

Split the document explicitly:

- **Durable layer** — properties that will not change within the document's
  useful life: architecture, platform philosophy, lock-in and data ownership,
  licensing, formal support commitments, ecosystem coupling. **The verdict rests
  here.**
- **Dated snapshot** — prices, per-model specs, per-country availability,
  current promotions, benchmark numbers. Explicitly dated, explicitly not
  retro-updated, and explicitly *not* load-bearing for the verdict.

This is what lets the analysis age gracefully: a year later the snapshot is
stale, but the reasoning still stands and the reader can see exactly which part
expired.

Use the same split as a **go/no-go test before starting**. If a topic is almost
entirely perishable detail, say so — the write-up will be worth little, and the
user deserves to hear that before paying for the research rather than after.

## Step 5 — Summary tables, if the shape calls for one

When there are three or more options, add a symbol table: ✅ full / 🟡 with
caveats / ❌ missing / — not applicable, one column per option, grouped rows
under thematic sub-headers, followed by a short "how to read this" paragraph
naming who wins where.

Two rules that matter more than they look:

- State in the table's intro that ratings are **for this context**, not in
  general — and say how a different profile would flip them.
- Keep the **option ordering identical in every table** of the document,
  including small side tables, so the reader never has to re-orient.

If the audience has a distinct sub-interest (an athlete's feature set, an
operator's runbook concerns), give it its own table rather than bloating the
main one.

## Step 6 — Commit each round; do not merge without a verdict

Work on a branch with a draft PR. Each research round is one commit plus a
summary comment on the PR saying what was verified and what it changed. The
reasoning then survives even if the branch sits for months.

Do not finalise a document that lacks a verdict. A menu of options — "buy A if
you value X, B if you value Y" — is research, not a decision, and it is exactly
what this format exists to avoid. If the user has not decided yet, say so, park
the branch, and name the event that will unblock it (a purchase, a release date,
a trial period ending).

Publish only when: the verdict is written with its accepted trade-offs and
revival clause, load-bearing claims carry sources and dates, and open `[VERIFY]`
tags are either resolved or acknowledged in the header.

## Anti-patterns

- Researching first and framing afterwards.
- A verdict resting on a price or a spec that changes next quarter.
- "It depends" without saying what it depends *on*.
- Treating the status quo as just another candidate.
- Silently dropping an option that turned out to be unavailable — record why it
  went, so nobody re-proposes it next year.
- Padding the comparison with rows where all options are identical; they cost
  the reader attention and change nothing.
