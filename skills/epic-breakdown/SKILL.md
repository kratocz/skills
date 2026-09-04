---
name: epic-breakdown
description: "Turn a written work breakdown (a design document's items-and-estimates section, a plan) into a tracker epic with numbered subtasks in the project's house shape and formal, transitively reduced dependency edges — reading the naming, shape and priority conventions from the project's AGENTS.md rather than hard-coding them, applying a granularity test before anything is created, showing the whole cut for approval first, and rewriting the epic body afterwards so it matches what was actually founded. Use when the user says \"založ tasky z §12\", \"rozpadni to do ClickUpu\", \"založ epic a podúkoly\", \"udělej z toho návrhu tickety\", \"found the epic\", \"break this plan down into tracker tasks\", \"create the subtasks with dependencies\". Reading the resulting graph back as diagrams is `dependency-diagrams`; the Jira-bound cousin is `atlassian:spec-to-backlog`; preparing questions for the party who owes the inputs is `client-questions`."
license: MIT
---

# epic-breakdown — procedure

A breakdown in a design document is written to be *read*; a tracker epic is
written to be *worked*. The two have different grain, and the most common
mistake is founding one subtask per document line. The result looks tidy for
an hour and then has to be deleted and re-founded — which happened on the
occasion that produced this skill.

## 1. Read the conventions before the content

Open the project's knowledge file (`AGENTS.md` or equivalent) and find its
tracker section. Take from it, and only from it:

- the **prefix scheme** — which prefixes are phases of the original plan and
  which are feature epics added later, and what a **phase number means**.
  In some projects it tracks priority, so a new epic is *inserted* and the
  ones below it renumbered; in others it is arrival order. Get this wrong
  and the number says the opposite of what it should.
- the **subtask shape** — section headings, numbering (`PREFIX-NN`), language,
  whether estimates go in the body, how follow-ups are named.
- the **dependency rule** — usually "formal edges, transitively reduced,
  prose is invisible to the tooling".
- any listed **tracker traps**.

If the knowledge file has no tracker section, read one existing epic and two
of its subtasks and infer the shape; say that you inferred it.

## 2. Read the tracker before the breakdown

Two things the document cannot tell you:

- **What already exists.** Review follow-ups filed from a merged PR often
  cover part of the new breakdown under an older prefix. Do not found a
  duplicate — reference the existing task and, if the design has since
  superseded its wording, update *that* task instead. Check whether it
  contradicts the merged design; a follow-up written the same night as a
  proposal can carry a decision the proposal's reviewer never saw.
- **What is in progress.** A subtask someone has started is not yours to
  restructure. Leave it exactly as it is, and cut the new set around it.

## 3. Apply the granularity test to every line — before proposing

One subtask is **one pull request with its own QA steps**. Concretely:

- if the title needs a "+" or a comma to describe it, it is two subtasks;
- if the QA steps fall into two groups that could pass independently, it is
  two subtasks;
- a document line is *not* a task boundary — "rendering engine: CSV and XML
  writers, transforms, golden tests" is four PRs;
- a piece that cannot be split without leaving an undeliverable intermediate
  state (a formset, a migration and its model) stays whole, and you say so.

Calibrate against the project's existing epics: count their subtasks and
divide the scope. Roughly half a day to a day per subtask is the usual grain;
an epic of ten to fifteen days is twenty subtasks, not eight.

Splitting shifts small costs too. A rule such as "every PR that adds a
user-facing string ships its own translation entries" means a late "i18n
pass" item becomes a *verification* task, not the place strings land — read
those rules and re-home the work accordingly.

## 4. Draw the graph

- Every real prerequisite becomes a formal edge; nothing lives only in prose.
- **Transitively reduce**: if A waits on B and B on C, do not add A→C.
- Attach a **hard sequencing constraint to the subtasks that produce the
  constrained artifact**, not to the first subtask in their area. "Storage
  before the engine" means the two file writers wait on the storage task;
  the engine's skeleton and its transforms do not.
- Name every edge that leaves the epic — those are the ones people miss.
- List the subtasks with **no dependencies at all**. They are the first
  tickets for whoever is free next, and the grain often reveals two or three
  that the coarse cut had hidden inside larger items.

## 5. Show the whole cut, then stop

Present it as one table per area — subtask, one-line scope, estimate, waits
on — plus the totals, the external edges, and the dependency-free starters.
Say what you deliberately kept whole and why. Then wait for approval. This
step is not ceremony: the first cut of the founding occasion was rejected in
full at this point, and it was cheap only because nothing had been created.

Keep the estimate honest about its unit. Engineering effort at the team's
actual velocity and the figure a customer is billed are different numbers in
some shops; say which one the table shows, and where the conversion is
recorded.

## 6. Found it

In this order, and only after approval:

1. **The epic** — or reuse the one that exists. Its body carries the design
   links, the scope and non-goals, the decisions already taken, the
   relationship to any older-prefix tasks it depends on, and a placeholder
   for the breakdown.
2. **The subtasks**, all under the epic, in the house shape, numbered in the
   order they will be worked. Priority by tier — the engine path high, the
   later surfaces normal — not all-high. Unassigned unless told otherwise;
   assignment is a decision that belongs to the person managing the queue.
3. **The edges**, in one batch, from the reduced graph of §4.
4. **Rewrite the epic body** so it matches what now exists: the table of
   founded subtasks with estimates, the series total, the external
   prerequisites, and what can start immediately. An epic whose body still
   says "only the first task exists so far" after twenty were founded is the
   next reader's trap.

Verify by reading one subtask back: rendered shape, edges present on both
endpoints, no heading swallowed.

## 7. Traps that cost time on the founding occasion

- **ClickUp discards a `##` heading placed inside a `>` blockquote** on save.
  A dated "update" marker written that way vanishes; write it as a bold
  lead-in to the paragraph instead.
- **Deleting a subtask needs explicit approval per task**, and when a cut is
  rejected, delete-and-recreate is cleaner than renaming eight tasks into
  different content — provided nobody has started on them (§2).
- **Dependencies are stored on both endpoint tasks**, so fetching one side
  reconstructs an edge; deleting a task drops its edges silently.
- **Renumbering when a phase is inserted**: change the titles from the
  bottom up so two epics never carry the same number at once, and leave
  dated snapshot artifacts alone — they correct themselves when regenerated.
- **Do not put weekday names next to dates** in anything that goes to the
  team without checking a calendar first.

## 8. Deliver

Links to the epic and to the dependency-free starters; the external edges
named; the series total with its unit stated; and the one or two decisions
the founding surfaced that are somebody else's to make — a storage choice
that turned out to have a third option, a rule the breakdown bends. Those
are the useful output; the task links are just the receipt.
