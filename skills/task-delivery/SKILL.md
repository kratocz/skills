---
name: task-delivery
description: "Carry one tracker task from ready-to-start to closed — read the task and its parent epic for scope, implement, run the project's own gate set and read the LAST run's output, commit, rebase onto current origin/main, push, open a pull request in the project's house body shape, flip the tracker status, wait for CI and any advisory AI review, delegate the human review to `code-review`, and merge only on a separate explicit directive — reading branch naming, PR shape, gates and label flow from the project's AGENTS.md rather than hard-coding them. Use when the user says \"pojďme pracovat na tasku X\", \"vezmi task X\", \"dodej ten úkol\", \"take task X through to merge\", \"implement and ship this ticket\", or names a tracker task to deliver. The review round itself is `code-review`; founding the tasks in the first place is `epic-breakdown`; deciding how to integrate a branch that already exists is `superpowers:finishing-a-development-branch`."
license: MIT
---

# task-delivery — procedure

One task, one branch, one pull request, one merge. The failure this skill
exists to prevent is not a coding mistake: it is delivering the *letter* of a
ticket while missing a decision that belonged to the user, or reporting a gate
as green from a run that no longer describes the tree.

Everything project-specific — branch names, PR body shape, which gates exist,
label flow, tracker conventions — is **read from the project's knowledge file**,
never assumed. The examples below name a Django/ClickUp/GitHub project because
that is where the skill was written; substitute what the project actually says.

## 1. Read the conventions and the scope, in that order

Open the project's knowledge file (`AGENTS.md`, else `CLAUDE.md`). Take from it:

- **branch naming** and whether work goes through a PR at all;
- the **gate set** CI enforces, and the exact commands to run locally;
- **PR body shape** (e.g. a required "What's in" / "What's NOT in" pair);
- **review-state labels** and who flips them when;
- **tracker conventions** — prefix scheme, subtask shape, status names;
- any **migration / additive-only / artifact** rules that constrain the change.

Then read the task **and its parent epic**. The epic carries the scope
boundary and the out-of-scope list; the task alone routinely under-specifies.
Read sibling tasks that depend on this one — their descriptions tell you which
fields and names they will expect, and a five-minute read here prevents a
follow-up migration.

If a tracker MCP is available, read the task through it rather than from the
user's paraphrase.

## 2. Decide what is genuinely open, and ask once

Before writing code, separate:

- **routine judgment calls** — make them, mention them in the summary;
- **decisions that change an interface, a schema, or a data format** — these
  are the user's, and they are cheap now and expensive after merge.

Batch them into **one** question round with a recommendation per item. Do not
ask about things the task or the epic already answers, and do not ask twice.

State any deviation from the literal task text out loud, in the PR body and in
the summary — never silently.

## 3. Implement, then run the gates and read the *last* run

Follow the surrounding code's idiom over your own preference. Then run the
project's full gate set locally.

**A gate result is valid only for the tree it ran on.** Two rules follow, and
both were learned the expensive way:

- After **any** later edit — including a comment or a test added while a run is
  in flight — the earlier result is void for the files you touched. Re-run.
- **Never report a check from a run whose output you only tailed.** A
  multi-gate script's tail shows the last gate, not all of them. Grep for every
  `exit=` line, or print a summary block the tail is guaranteed to include.

If a gate fails on something the change did not touch, establish that before
reporting it: re-run the failing test after the environment step it needs
(a static-asset build, a message compile, a seeded database). Unrelated
environmental failures are noise; reporting them as findings wastes the round.

## 4. Commit and open the pull request

Stage files **explicitly, one by one** — never `git add .` — and check
`git status` first. Write the commit body to explain *why*, wrapped for a
terminal (~72 chars), since `git log` does not reflow.

Then:

1. `git fetch origin` and **rebase onto current `origin/main`**. Repos with an
   auto-pin CI bot move `main` without human activity, so the base you branched
   from is stale more often than not.
2. Rename the branch to the project's convention if it does not match — tooling
   often creates a working branch under its own scheme.
3. Push with upstream tracking.
4. Open the PR in the house body shape. Include a **verification section**
   naming the commit the gate results came from, and — when the task carries QA
   steps — a table mapping each QA step to the test that covers it. That table
   is what lets a reviewer skip re-deriving your evidence.
5. Apply the project's defaults for assignee, reviewer and labels. **Do not
   attach a reviewer or a label unless the project's conventions say so** —
   defaulting to "helpful" here is a recurring annoyance.
6. Flip the tracker status to whatever the project calls "ready for review".

## 5. Wait for CI and any advisory AI review

Watch the checks rather than polling: a background watcher that emits one event
per settled check and exits when all have settled. Cover **every** terminal
state in the filter, not just success — a watcher that greps only for the happy
path is silent through a failure, and silence looks like "still running".

If the project runs an advisory AI reviewer, read its findings before your own
pass and treat them as **claims to verify, not conclusions**. In particular,
verify any proposed *fix* actually works before accepting or rejecting the
finding on its basis — a plausible-sounding mitigation that the framework
defeats is worse than no suggestion, and the check is usually a short
throwaway experiment. Put such a probe in a scratch directory, or delete it
from the repository afterwards.

## 6. Review

Delegate the review round to the **`code-review`** skill. Do not re-implement
severity codes, findings files or GitHub posting here.

Two things this skill adds around it:

- **A self-review is still a review, and it has a hole.** GitHub refuses
  `Approve` on your own pull request, so the verdict goes in as an ordinary
  comment. Say in that comment that it is not a formal approval and that no
  human signed off — the merge is not bypassing a gate if branch protection
  requires none, but the absence should be stated, not left implicit.
- **When a finding is real but its fix belongs elsewhere**, do three things
  rather than one: record the reasoning at the place in the code that
  surprised you, move the requirement into the downstream task's description
  *with its own QA step*, and say in the review why the deferral is sound. A
  finding waived without a home is a finding lost.

## 7. Merge only on a separate explicit directive

A merge is irreversible shared state. Neither a question ("can this be
merged?"), nor a selection in an options dialog, nor a prior approval of the
review is authorization. Require an imperative — "merge it", "ship it" — in the
user's own message, and read a standing instruction narrowly.

After merging:

- **A `--delete-branch` failure from inside a git worktree does not mean the
  merge failed.** The last step checks out the base branch to delete the local
  one and hits `fatal: '<base>' is already used by worktree at …`, *after* the
  merge has already landed. Confirm with the PR's state and merge commit, then
  delete the remote branch directly. Never retry the merge on that message.
- Remove review-state labels — most trackers and GitHub do not drop them on
  merge.
- Close the tracker task.
- Record follow-ups where the next person will look: open questions, waived
  findings and their new home, and anything the merge deliberately left undone.

## 8. Report

Say what landed, where, and what you did *not* do. Name the commit the gate
results came from. List the decisions you made on the user's behalf and the
ones still open. If any part of the task was left out, say which and why —
scaling the work down is the user's call, not yours.
