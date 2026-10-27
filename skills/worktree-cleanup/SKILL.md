---
name: worktree-cleanup
description: "Delete a repository's accumulated git worktrees without losing anything: inventory them, prove every commit survives (branches are kept), rescue files that live only in a worktree — above all gitignored notes, which no git command reports as unsaved — find the agent sessions still working in them by process working directory rather than by worktree name, then remove them with a guarded, dry-run-first script and prune. Use when the user says \"smaž worktrees\", \"worktrees zabírají místo\", \"ukliď worktrees\", \"můžu smazat ty worktrees?\", \"clean up worktrees\", \"delete all worktrees\", \"worktrees are eating my disk\". Not cleaning up branches whose remote is gone, and not finishing one branch's work — that is the integration of a single development branch."
license: MIT
---

# worktree-cleanup — procedure

Agent harnesses create a worktree per session (Claude Code puts them under `.claude/worktrees/<name>`) and nobody deletes them. Each one carries its own virtualenv, `node_modules` and build output, so a busy repository collects tens of gigabytes. Deleting them is cheap; the work is proving that nothing is lost with them.

**What deletion actually destroys.** `git worktree remove` deletes the directory and its administrative entry — **not the branch**. Every commit stays reachable from its branch, so commits are not the risk. The risk is everything git does not track:

- uncommitted and untracked files,
- **gitignored files that exist only in that worktree** — local notes, review write-ups, plans, `settings.local.json`, an `.env` that differs from the main checkout's. `git status` does not show them, so a check built on `git status` alone reports a worktree as clean while it holds the only copy of a document.

Real case (2026-10-27): a repository held 39 worktrees taking 17 GB on a full disk. Eight review write-ups and one plan existed only inside worktrees, in gitignored directories. A memory note had said "copy the review files out before the worktree dies" for two and a half months, and the files had still never been copied. A reminder does not protect them; a deletion script that refuses to delete them does.

## 1. Inventory

Run from the main checkout:

```bash
git worktree list --porcelain        # 'prunable' = directory already gone; 'locked' = a harness holds it
du -sh <worktrees-dir>; df -h .
```

Report the total size and free disk space — that is the reason the user is asking.

## 2. Commits: prove they survive

For each worktree: `git -C <wt> rev-list --count HEAD --not --remotes` (fetch first). Commits on no remote are still safe because the branch is kept, but say what they are:

- `gh pr list --state all --head <branch>` (or the forge's equivalent) — a `MERGED` PR means a squash merge put the content on the main branch under a different SHA, so these commits are history, not lost work;
- for a branch with no PR, `git cherry origin/main <branch>` — `-` lines are already upstream as an equivalent patch, `+` lines are not.

Name every branch with `+` commits and no PR. Deletion does not touch it, but the user should know it exists.

## 3. Files that exist only in a worktree

For each worktree, list uncommitted, untracked **and ignored** files:

```bash
git -C <wt> status --porcelain --untracked-files=all
git -C <wt> ls-files --others --ignored --exclude-standard --directory
```

Drop what is regenerable (virtualenvs, `node_modules`, caches, build output, coverage files, stale plan files). **Do not truncate this listing** with `head` or similar — a cap of eight lines per worktree hid part of one worktree's list in the real case above. For every remaining file, compare it with the same path in the main checkout (`cmp -s`):

- identical → nothing to do;
- **missing** from the main checkout → copy it to its canonical place there (`cp -pn`, never overwrite);
- **different** → copy it into a rescue directory, `<rescue>/<worktree>/<path>`, and leave the main checkout's version alone; when both versions matter, show the user the diff.

Verify every copy with `cmp`. Only the files the user cares about need rescuing; scratch reports and stale plans can go — ask when unsure, do not decide alone.

## 4. Live sessions

**Find them by process working directory, not by worktree name or lock.** A session started for worktree A can switch into worktree B mid-session; its name and its lock still say A, and only its current directory says B. Seen 2026-10-27: a session started as `claude -w <A>` was found working in `<B>`; the user believed they were two separate sessions.

```bash
lsof +c 0 -d cwd -Fcn | awk '/^c/{c=substr($0,2)} /^n/{print c "\t" substr($0,2)}' | grep '<worktrees-dir>/'
```

Map each hit to its session through its parent process (`ps -o ppid=,command= -p <pid>`). Two kinds of hit are not sessions:

- **Docker VM helpers** (OrbStack, Docker Desktop) keep the working directory of wherever the Docker CLI first started them. They block nothing and survive the deletion.
- **Containers** whose compose project directory or bind mounts point into a worktree: `docker ps --format '{{.Names}}\t{{.Label "com.docker.compose.project.working_dir"}}'` and `docker inspect --format '{{.Name}} {{range .Mounts}}{{.Source}} {{end}}'`. A running container keeps running after its source directory is gone; say so and offer to stop it afterwards.

A worktree with a live session is not deleted. Tell the user which sessions are still running and which uncommitted work they hold, and wait until the user says they are closed. **Never delete the worktree of the session you are running in** — the harness keeps binding the session to the deleted path.

## 5. The deletion script

Use the bundled `scripts/cleanup-worktrees.sh`; copy it next to the project's local notes so the user can rerun it later. It:

- runs as a **dry run** unless given `--yes`;
- skips a worktree that a process works in (Docker VM helpers excepted, via `IGNORE_PROCS`);
- skips a worktree with uncommitted changes, untracked files, or **ignored files that are not regenerable** (`REGENERABLE`), unless an identical copy exists at the same path in the main checkout or under `$RESCUE/<worktree>/`;
- removes with `git worktree remove --force --force`, which also takes locked worktrees, then runs `git worktree prune`, which also clears entries whose directory is already gone;
- prints the space freed and one `OK` / `FAIL` line.

When the rescue directory is not the default `<main checkout>/.worktree-rescue`, set `RESCUE`. Make sure the rescue directory itself is gitignored (or lives in a directory that already is).

Before the first real run in a repository, test it on a throwaway worktree (`git worktree add --detach <path> origin/main`, add an ignored file, expect `SKIP`; copy that file into the rescue directory, expect `would remove`; then run it with `--yes`). Then show the user the dry-run output for the real worktrees.

## 6. Delete

Only after the user confirms every session is closed:

1. Rerun step 4's process check — sessions end and start while you wait.
2. Run the script with `--yes`.
3. A worktree skipped only because of a process you have identified as not a session (a Docker VM helper the regex missed): confirm it is clean and its branch is pushed, then remove it with the same `git worktree remove --force --force`, and say that you did.
4. Report: worktrees removed, space freed, branches kept, where the rescued files are, and what is left (skipped worktrees, unregistered directories the script did not touch, running containers).

## Safety rules

- Never `rm -rf` a worktree directory instead of `git worktree remove` — the administrative entry stays behind and the branch stays checked out "elsewhere".
- Never delete branches as part of this skill. Branch cleanup is a separate decision with its own checks.
- Never overwrite a file in the main checkout with a worktree's version.
- Never delete on the strength of a `git status` that does not include ignored files.
