---
name: merge-pr
description: Merge a pull request as the whole sequence rather than the button — re-verify the head SHA and CI, write the squash message instead of inheriting the branch's commit messages, then strip the labels the project says come off, clean up the branch only where one exists, test-merge the remaining open PRs against the new head, and move the tracker task. Use when the user says "mergni #N", "mergni to", "merge PR #N", "land that PR", "squash-merge it" and the merge is the task itself rather than the tail of a review round.
license: MIT
---

# Merge a pull request

The merge is one step of a sequence, and the steps after it are the ones that get
forgotten — a squash body nobody wrote, a label left on a merged PR, two other PRs
silently put into conflict, a tracker task claiming the wrong person is on the hook.
Finish all of it before reporting the merge.

**When a code review preceded the merge**, this sequence is that skill's step 14b —
run this skill from there rather than restating it, so the sequence has one source of
truth.

**Read the project's own instructions file first** (`AGENTS.md`, else `CLAUDE.md`, plus
whatever it points at). Everything repo-specific below — which labels come off, which
merge method, what status a merged task takes, whether direct pushes are allowed — is
that file's to state. Do not infer a label rule from a label's name, and do not infer it
from what a runbook calls the label's "semantics": a label documented as *add-only*
(meaning the automation only ever adds it) may still be one the reviewer strips at merge.
When the instructions are silent, ask rather than guess.

## 1. Pre-flight — verify, do not trust

```bash
gh pr view <N> --json state,isDraft,isCrossRepository,headRefName,headRefOid,mergeable,mergeStateStatus,reviewDecision,labels,author
gh pr checks <N>
```

- **The head SHA must be the one that was reviewed and that CI ran on.** A push that
  lands between reading the checks and clicking merge is invisible otherwise. Carry the
  SHA into the merge with `--match-head-commit <sha>` so the platform refuses the merge
  instead of landing a commit nobody looked at.
- **Read the checks per job, not the aggregate colour.** Where the repository has no
  branch protection, nothing mechanical stops a red merge — the person clicking is the
  gate. A pending check is a blocker too: report it and stop.
- **`mergeable` / `mergeStateStatus`** — `UNKNOWN` means the platform is still computing;
  re-read rather than proceeding. `CONFLICTING` is the author's to resolve.
- **Check what the diff touches before choosing the tool.** A PR changing
  `.github/workflows/*` cannot be merged with `gh pr merge` at all: the CLI's OAuth token
  carries `repo` but not `workflow`, and the refusal is about the file paths, not the PR.
  Merge it through the GitHub MCP's `merge_pull_request`, or refresh the token
  (`gh auth refresh -s workflow`).
- **Confirm the merge is authorised for this PR, now.** A question, a dialog choice or an
  earlier "looks good" is not a merge directive; neither is a review Approve. If the user
  has not said to merge this PR, stop and ask.

## 2. Merge — write the message

```bash
gh pr merge <N> --squash --match-head-commit <sha> \
  --subject "<type>(<scope>): <what it delivers> (#<N>)" \
  --body-file <path>
```

**Write the body; never let it default.** Where the repository's squash message is
configured from the commit messages, the default body is the branch's history verbatim —
`Fixed review notes`, `wip`, and the branch's own merges of the integration branch — and
that lands in the permanent history of the integration branch. Write instead what the PR
delivers, what it deliberately leaves out, and anything a future reader needs (a
follow-up ticket, a deferred decision). Check the repo's configuration to know which case
you are in:

```bash
gh api repos/{owner}/{repo} --jq '{squash_merge_commit_title, squash_merge_commit_message, delete_branch_on_merge, allow_squash_merge, allow_merge_commit, allow_rebase_merge}'
```

**Attribute the author explicitly.** Add `Co-authored-by: <name> <email>` for the PR
author rather than assuming the platform adds it — with a hand-written body it may not.

**Use the merge method the project uses.** Squash is the common default; some
repositories want a merge commit for a series worth keeping. The instructions file, or
the repo's `allow_*_merge` flags, say which.

**From a git worktree, `--delete-branch` reports a failure it did not cause.** Its last
step checks out the base branch locally to delete the branch and fails with
`fatal: '<branch>' is already used by worktree at …` — the merge already went through.
**Never retry the merge.** Verify and move on:

```bash
gh pr view <N> --json state,mergedAt,mergeCommit
```

## 3. Post-merge — the part that gets forgotten

Do all of these before reporting, in any order:

**Labels.** Strip exactly the ones the project's instructions say come off at merge.
The platform drops none of them on its own, so they linger on the merged PR forever.

```bash
gh pr edit <N> --remove-label "<label>" [--remove-label "<label>"]
```

**Branch cleanup depends on where the branch lives.** For a **fork** PR
(`isCrossRepository: true`) there is nothing to delete on the upstream remote — the branch
only ever existed on the fork — so `git ls-remote --heads origin <branch>` comes back
empty whether or not anyone cleaned up, and reading that emptiness as "already deleted" is
a false conclusion from a true output. For an in-repo branch, check
`delete_branch_on_merge`: if false, delete it yourself with
`git push origin --delete <branch>`.

**Test-merge every other open PR against the new head.** Landing one PR rebases the
problem onto its siblings, and the files that collide are usually prose — instructions
files, READMEs, ADRs, changelogs — because those are edited a paragraph at a time by
whoever is nearest. Several PRs from one author routinely touch the same paragraph.

```bash
for each open PR N:
  git fetch origin pull/<N>/head:pr-<N>-head
  git merge-tree --write-tree origin/main pr-<N>-head   # non-zero exit + CONFLICT line
```

Tell each affected author which file conflicts and where. It costs one command per PR and
saves them rebasing blind. (Generated build artifacts are a separate case: a lockfile or a
compiled stylesheet may merge cleanly and still be wrong — compare against a clean rebuild
if the project says so.)

**Move the tracker task.** A merge is rarely the end of a task: many projects route it to a
tester next, which is a different status from *done* and often a different assignee. Set
whatever status the project assigns to merged-but-untested work and add the closing note
its conventions ask for — saying what you believe is and is not testable, so the tester
decides rather than guessing. Note that in some trackers moving a task to a closed state
clears its assignees, which undoes a routing you just made.

**Timesheet.** If the user tracks time, this sequence is billable work on the task; log it
with the merge named in the description (`tracker-start` / `tracker-stop`, or the
project's configured tool).

## 4. Report

State: the merge commit SHA and that it is on the integration branch (verified, not
assumed), which labels came off, what happened to the branch, which other PRs now
conflict and where, and the tracker status you set. If you skipped a step because the
project's instructions were silent, say which and what you would need to decide it.

Never report a merge you have not verified with `gh pr view <N> --json state,mergeCommit`
— the one command that distinguishes "the merge failed" from "a local cleanup step
failed after the merge succeeded".
