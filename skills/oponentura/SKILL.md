---
name: oponentura
description: Use when a written analysis, note, report, spec or decision document is about to be called done, promoted from draft, or handed to someone who will act on it — or when the user says "/oponentura", "vyvrať to", "udělej oponenturu", "zkus to rozbít", "refute this", "adversarially verify", "try to break this". Also for a section newly added to a document that already passed one.
---

# Oponentura — adversarial pass over a document

## Overview

A second reader in a **fresh context**, briefed to *refute* the document, not to *check* it. "Check" returns "looks fine"; "refute" returns the three claims that do not survive contact with their own sources. The author then verifies the reviewer's most expensive findings personally — reviewers are wrong too — and records the outcome in the document itself, so the next reader knows what was tested.

Proportionality applies: the pass is for documents where a wrong load-bearing claim costs something. A shopping list does not need one.

## The brief (what the subagent receives)

Dispatch one subagent (general-purpose, with web access when the document cites sources) and give it, verbatim, the document path(s) and this contract:

**Role.** "Your job is to REFUTE, not to check. Assume the document contains errors and go find them. Do not edit files — report only."

**REQUIRED targets, each named explicitly:**

1. **Numbers and attributions.** Every figure, sample size, effect, date and "who found what" — verified against the primary source's abstract or full text (publisher, PubMed, official record), never against a blog or press release. List the specific claims to verify; a bare "check the numbers" gets skimmed.
2. **Strongest counter-argument.** The best evidence *against* the central thesis, including newer replications, meta-analyses, retractions, corrections and expressions of concern the document may predate.
3. **Same standard.** Whether the document holds its *preferred* explanation to the same evidential bar as the explanation it *rejects*. Authors relax the bar for the frame they like; every pass run so far has found exactly this.
4. **Unverified sources.** Whether anything tagged unread, unverified or from memory carries a load-bearing claim (a table row, a summary bullet, a recommendation).
5. **Internal consistency.** Summary vs body vs tables; recommendations vs the evidence the document itself cites.

Add document-specific targets (a clinical boundary, a legal claim, a calculation) as further numbered items.

**Output contract.** Numbered findings, most damaging first. Each: (a) the exact quote from the document, (b) what is actually true with the URL it was verified against, (c) severity **CRITICAL** (a load-bearing claim is wrong) / **MEDIUM** (an overclaim or imprecision that changes the nuance) / **LOW** (cosmetic). Close with one paragraph: does the central thesis survive, and what is the single strongest counter-argument found. **Do not list what checks out.** Write in the document's language.

## After the subagent returns

1. **Verify the top 2–3 findings yourself** before touching the text — open the source the reviewer cites. A reviewer under a "refute" brief overreaches sometimes; a finding you cannot reproduce is dropped, not applied.
2. **Apply** the confirmed findings: rewrite the claims, downgrade "fact" to what the evidence supports, re-tag sources, add the reviewer's sources to the bibliography with a tag that says the reviewer verified them (e.g. `[verified by review: abstract, YYYY-MM-DD]`).
3. **Record** in the document header: date, number of findings by severity, the strongest counter-argument, and what changed because of it. A document that hides its own review is not reviewed.
4. Anything added to the document *after* the pass gets its own scoped pass: same contract, brief limited to the new parts.

## Quick reference

| Situation | Brief scope |
|---|---|
| New document | Full contract, targets 1–5 plus specifics |
| Section added after a pass | Contract limited to the new parts; header records a second pass |
| Quantitative claim the user will act on | Target 1 with every figure enumerated; target 3 mandatory |
| Reviewer finding you cannot reproduce | Drop it; note in the header that it was checked and not confirmed |

## Common mistakes

- Briefing "review" or "check" — the reviewer confirms instead of attacking.
- Applying findings without reproducing the top ones; the reviewer's URL may not say what the reviewer says it says.
- Running the pass in the same context that wrote the document — the anchor survives.
- Treating the pass as a gate to pass rather than a source of edits: a pass with zero applied changes on a non-trivial document usually means the brief was too soft.
- Skipping the header record, so the next session repeats the same pass or trusts an untested draft.
