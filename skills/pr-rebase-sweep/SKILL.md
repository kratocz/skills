---
name: pr-rebase-sweep
description: Clear the merge conflicts on every open pull request of ours after main moved — survey them with a local test-merge instead of trusting GitHub's mergeable flag, rebase in dependency order (code before docs, stack parents before children, `--onto` when a parent was squash-merged, dropped copies of a squash-merged sibling recognised and skipped), re-chain migrations, run the project's gates, prove the branch's own diff is unchanged, push with a lease on the last pushed SHA, then wait for CI and the AI review and fix what it reports. Use when the user says "rebasni všechny PR", "vyřeš konflikty na otevřených PR", "needs-rebase", "rebase all open PRs", "clear the merge conflicts on our PRs", "sweep the stack after main moved", or a reviewer asks for conflicts on several PRs to be resolved.
license: MIT
---

# PR rebase sweep

Main moved — a reviewer merged a few PRs — and now a row of open pull requests carry `needs-rebase`, stacked PRs show their merged parent as their own diff, and the reviewer asks for the conflicts to be cleared. The job is not one rebase; it is a sweep with an order, a proof per branch that nothing but the base changed, and a second pass because main keeps moving while you work. On 2026-10-08 this sweep covered sixteen PRs in one afternoon; this skill is that afternoon without the detours.

**Read the project's own instructions file first** (`AGENTS.md`, else `CLAUDE.md`). Which gates to run, whether migrations have a re-point tool, what the force-push and review conventions are — that file's to say. When it is silent, the defaults below apply.

## 1. Survey — a local test-merge per PR, not the mergeable flag

GitHub's `mergeable` is `null` for minutes after every push to main and stale for longer; `needs-rebase` labels come from a bot and lag too. Test-merge locally:

```bash
git fetch origin --prune
gh api "repos/<owner>/<repo>/pulls?state=open&per_page=100" --paginate \
  --jq '.[] | "\(.number) \(.user.login) \(.base.ref) \(.head.ref) [\([.labels[].name]|join(","))] \(.title)"'
# per PR of ours:
git merge-tree --write-tree --name-only origin/<base> origin/<head>    # exit 1 + file list = conflict
git rev-list --count origin/<head>..origin/<base>                       # how far behind
```

Put the loop in a script file and run it as one command — a `for` loop over `gh`/`git` is refused in worktree-isolated sessions. Fork branches are not on `origin`; skip PRs by other authors unless asked. Record for every PR: base, head SHA, conflict files, behind-count. A PR whose base is another open PR is a **stack child**; note the parent.

Read the output as a whole before touching anything: a conflict in a stack child that lists the parent's files is usually not a conflict of the child at all — it is the parent's commits replaying against their own squashed copy (step 3b).

## 2. Order the work

1. Code and infra PRs before docs-only PRs (the reviewer's priority, and the ones with tests).
2. Stack parents before children; after a parent is pushed, every child is replayed onto the new parent head.
3. Docs PRs last — they conflict only with each other in the shared knowledge file and are quick.
4. Before each branch, `git fetch origin --prune` again and re-check its base: the reviewer merges while you work. A merged parent makes its children's base `main` (GitHub retargets them) and turns step 3a into step 3b.

Tell any other live agent session on the same repo which branches you are taking (`ListAgents` / `SendMessage`) and ask what they hold; two sessions force-pushing one branch is the one failure this sweep cannot undo.

## 3. Rebase one branch

```bash
git switch --detach origin/<head>        # works even when the branch is checked out in another worktree
OLD_HEAD=$(git rev-parse HEAD)           # note it; the lease in step 6 needs the SHA you will have pushed LAST
```

**3a. Branch based on main:** `git rebase origin/main`.

**3b. Stack child whose parent was squash-merged:** `git rebase --onto origin/main <old parent head>` (or `--onto <new parent head> <old parent head>` while the parent is still open). The parent's commits are not ancestors of main after a squash, so a plain rebase replays them — against their own copy — and every one conflicts.

**3c. The branch carries a cherry-picked copy of a sibling PR's commits** (a docs PR stacked "by copy" rather than by base): after the sibling is squash-merged those copies are **not** dropped automatically — `rebase` drops a commit only when its patch-id is upstream, and a squash changed it. They surface as add/add conflicts on the sibling's files. Confirm the copy is fully upstream, then skip it:

```bash
git diff --stat origin/main <copy head> -- <the sibling's files>   # empty = nothing left to carry
git rebase --skip
```

If the diff is not empty, the copy diverged from what merged: resolve it as a real conflict, and say so in the PR.

**3d. Conflicts.** Read every hunk before resolving; `git diff --diff-filter=U` shows them, and when a classifier refuses the pipe into `grep`, `awk '/^<<<<<<</{p=1} p{print NR": "substr($0,1,900)} /^>>>>>>>/{p=0}' <file>` prints the blocks from the file itself. Resolve with a small script that asserts each anchor occurs exactly once (a conflict file is a bad place for a free-hand edit). The shapes that recur:

- *Both sides appended to the same line* (a dated amendment list, an index row): keep ours and append theirs' tail. Two amendments made the same day share a prefix up to the date — cut at the ` · ` separator, not at the last common character, or the second amendment's date is lost.
- *Both sides added a sibling line* (a new bullet next to another new bullet, two `**Revision:**` lines): keep both, main's first.
- *Both edited one line* (a prose bullet both PRs touched): apply the branch's edits onto main's version of the line; never pick a side wholesale — that silently drops the other PR's merged change.
- *Import moved on main* (`from x.models import E` → `from x.constants import E`): keep main's import line, add the branch's new lines beneath it.

Then `git -c core.editor=true rebase --continue` (no editor in a non-interactive session) and check `grep -rn '^<<<<<<<\|^>>>>>>>' <touched files>` finds nothing.

**3e. Migrations.** If main inserted a migration below yours, your migration still names the old parent: fix `down_revision` **and** the `Revises:` docstring, or run the project's re-point tool when it has one (`make migrate-repoint`-style). Commit it as its own small commit on the branch with the reason in the message.

## 4. Gates

Run what the project runs in CI — quality gate, migration check, test suite, `tofu fmt -check` + `tofu validate` for infra — and read the last lines, not the exit code of the first step. One trap worth remembering: after a re-point, a local test database that already sat at the branch's head revision skips the upstream migration you just chained below it, so the schema check reports model/DB drift that looks real. Drop the volumes (`services-down`, with the project-name and port overrides a worktree needs) and run again from empty, which is what CI does.

A long suite occupies the worktree; while it runs, do the gh-side work (survey, CI reads, messages) or replay other branches with step 7.

## 5. Prove the branch is the same branch

Before pushing, the branch's own diff must be unchanged — the base moved, nothing else:

```bash
git diff --stat <old base> <old head>      # what the PR added before
git diff --stat <new base> HEAD            # what it adds now — same files, same counts
```

A difference here is either a resolved conflict that belongs in the PR body (step 8) or a mistake.

## 6. Push with a lease on the last pushed SHA

```bash
git push --force-with-lease=<branch>:<sha you pushed last> origin HEAD:refs/heads/<branch>
```

The lease value is the SHA the remote holds **now** — after your own earlier push in the same sweep that is your previous push, not the head you started the day from; a stale lease is rejected as "stale info", which is the guard doing its job. Pushing `HEAD:refs/heads/<branch>` works from a detached HEAD and leaves the branch checked out elsewhere untouched; the other worktree's local copy then lags and needs a fetch before its next push — tell its owner.

Re-check the survey (step 1) after every parent you push: its children's conflict list changes shape.

## 7. Replaying without a checkout (the worktree is busy)

A branch whose commits apply cleanly can be rebased with plumbing while tests occupy the working tree, or when the branch is locked in another worktree:

```bash
tree=$(git merge-tree --write-tree --merge-base <old parent> <new base> <commit> | head -1)   # exit ≠ 0 = conflict → use step 3
new=$(GIT_AUTHOR_NAME=… GIT_AUTHOR_EMAIL=… GIT_AUTHOR_DATE=… git commit-tree "$tree" -p <new base> -F <msg from git log -1 --format=%B>)
```

Chain it per commit (`old parent` = the commit's original parent, `new base` = the previous replayed commit), verify with step 5's two `diff --stat`s, push with step 6. `--merge-base` is what makes it a rebase of one commit: without it the squash-merged parent shows up as add/add conflicts on every file it touched.

## 8. Afterwards

- **CI and the AI review:** wait for the `review` check-run on the pushed SHA, read the bot's latest summary line (`C:… M:… m:… n:…`) and fix what is cheap — a reviewer who asks for conflicts cleared usually also expects the bot's findings closed before their own review (on this project they said so in writing). Nits across several PRs are fast-forward commits, no force-push.
- **PR body:** when a conflict resolution changed content (not only line placement), add a line saying which hunk and why; list the expected conflicts with other open PRs so the next merger is not surprised.
- **Second pass:** `git fetch` and re-run the survey. Main moved during the sweep; a branch you pushed clean two hours ago may be dirty again. The sweep ends when every PR of ours is CLEAN in the local test-merge, not when the list was walked once.
- **Report** per PR: new head, what conflicted and how it was resolved, gates run, what the bot still lists (waived items included), and the merge order the reviewer must keep (`#345 → #349`, `#339 → #347`). Branches held by other worktrees go in the report with "fetch before pushing".

## Common mistakes

- Trusting `mergeable`/`needs-rebase` from the API: `null` is not "clean", and a label removed by a bot on push is not "verified".
- `git rebase origin/main` on a stack child after a squash-merge of the parent — every parent commit conflicts with itself; use `--onto`.
- Resolving a same-day double amendment by common prefix: the two entries share "· 2026-10-07 (amended:" and the cut lands inside the second one.
- A lease with the original head after an earlier push in the same sweep.
- Declaring the sweep done after one pass.
- Force-pushing a branch another session is mid-rebase on; ask first, it costs one message.
