---
name: code-review
description: Run a structured code review on a PR (or another target). Picks a CR title, starts timesheet logging, produces findings labelled C1/M1/m1/n1 with line references and fix snippets in `docs.local/code-reviews/`, runs verification passes, then posts inline + summary comments on GitHub. Use whenever the user asks you to review a PR, says "udělej CR", asks for a code review on a branch or diff, or otherwise wants structured review feedback.
---

# Code review workflow

This skill executes a code review following the conventions in this plugin's `CLAUDE.md`. The **conventions themselves** (severity codes, focus areas, comment language, review process) live in the `## Code review` section — read that first; this skill is the **procedure** to follow.

When invoked, follow this procedure in order:

1. **Identify the target.**
   - **Try to auto-detect first.** Match the current working directory's basename and `git branch --show-current` against these patterns:
     - `cr-pr-<N>` → target is PR #N in the repo's `origin`.
     - `cr-<slug>` → target is the branch `<slug>` (or `<slug>` as a short identifier).
     - Further fallback: `gh pr view --json number,headRefName` from the current checkout may identify a PR whose head is the current branch.
   - If a single clear candidate emerges, mention it inline (e.g. `Detected target: PR #27 — proceeding`) and move on without asking.
   - If ambiguous or no match, ask the user: a specific PR? A branch? Something else?
   - If the project uses an issue tracker (ClickUp, Jira, Linear, GitHub Issues, …) and the target references a ticket (e.g. `CU-1234`, `JIRA-42`, `#123`), pull it for context via the appropriate MCP if available — its scope informs the "does the diff do what the PR description claims" check.

2. **Gather inputs and check for prior CR rounds.** Read everything relevant: all commits on the target, the PR description, all existing review and discussion comments (including author replies), and any prior findings files in `docs.local/code-reviews/` matching `cr-pr-<number>-*.md` (PR targets) or `cr-<slug>-*.md` (branches/other targets).
   - No prior CR → proceed.
   - Prior CR exists → review only the new changes since (new commits, new discussion). **Read author replies to prior findings carefully** — don't re-flag what's been justified or resolved.
   - Prior CR exists and there are no new changes → tell the user and skip the CR; the author hasn't addressed earlier findings yet.
   - **Compute the diff against the right base — don't trust the local checkout.** In a CR worktree the local `HEAD`/`main` ref is often *not* on the PR commit and *not* on current `origin/main` (the session-start `gitStatus` is a stale snapshot, and repos with an auto-pin CI bot move `origin/main` independently). A raw `git diff <local-main>...<head>` can then show dozens of unrelated files. Always: `git fetch origin` (and `git fetch origin pull/<N>/head:pr-<N>` for a PR), then review against the **true merge-base** — `git merge-base origin/main pr-<N>` — or just trust GitHub's own calculation via `gh pr diff <N>` and cross-check the file count against the PR's `changedFiles`. If the local diffstat and `gh pr diff --name-only` disagree on the file list, the local base is wrong, not the PR.

3. **Pick a CR title and start timesheet logging.**
   - Decide a short, descriptive title for this CR.
   - If the user tracks time, start a new timer/entry for this CR using that title. **Prefer the `session-tracker` skill if available**; otherwise use the timesheet tool the user has configured (Toggl MCP, Clockify, ClickUp time tracking — they may have specific instructions in their global or project `CLAUDE.md`).
   - If a timesheet session is already running, ask the user whether to stop it and start a new one for this CR, or leave the current one running.

4. **Produce findings.** Label each one with a severity code (`C1`, `C2`, `M1`, `m1`, `n1`, …). If a finding needs a new category (e.g. off-topic), propose it to the user with a suggested letter prefix.
   - Write the findings to a file in `docs.local/code-reviews/` at the project root; content in English.
   - **Filename:** `cr-pr-<number>-round-<N>.md` for PR targets, or `cr-<slug>-round-<N>.md` for branches/other targets (slug = branch name lowercased and hyphenated, or another short identifier). **Each review round is a new file** — don't append to a prior round's file.
   - The file starts with a header: metadata (author, reviewer, date, PR/branch reference, round number) **plus a short summary of the changes — in your own words, based on what you actually found in the diff** (not a copy of the PR description).
   - A template is bundled with this skill at `${CLAUDE_SKILL_DIR}/findings-template.md` — use it as a starting point.
   - **Round 2+:** include a `## Status of prior findings` section in the new file listing every finding from prior rounds with its current status — **resolved** (author fixed it), **still open** (not addressed), or **waived** (author justified leaving it; include the justification). The latest round's file is then the canonical source of which blockers remain.
   - If `docs.local/` doesn't exist, ask the user whether to create it (with the `code-reviews/` subdirectory) and add `docs.local/` to the project `.gitignore`. If `docs.local/` already exists but `code-reviews/` doesn't, just create the subdirectory.

5. **Re-check severity.** Is each finding labelled at the right level (`Cx`/`Mx`/`mx`/`nx`)?

6. **Re-check for false positives.** Common. Remove the finding or downgrade its severity.

7. **Add line references** to each finding where it makes sense (`file:line` or `file:start-end`).

8. **Add a fix snippet** to each finding where it makes sense — a code change the author can apply with one click.

9. **Re-verify line numbers** against the actual file state; they often drift between earlier passes.

10. **Second verification pass:** for each finding, re-check severity, false-positive risk, line references, and suggested code.

11. **Third verification pass:** final check of everything to avoid wasting the author's time on inaccuracies.

12. **Freshness re-check.** Re-fetch the target's commits and comments. If anything is new since you started the review (a new commit, a new comment, a new reply), extend the review to cover the new content — pass through steps 4–11 for the new material and revise existing findings in light of any new context — before continuing.

13. **Summarise to the user** — e.g. `4 critical (C1,C2,C3,C4), 3 major (M1,M2,M3), 2 nits (n1,n2)`, mention the `docs.local/code-reviews/` file with the full CR, and wait for the user's go-ahead. **If there are no findings at all, summarise briefly as LGTM and offer immediate Approve.** **If there are no `Cx`/`Mx` blockers, also offer the "approve & merge" option** (see step 14).

14. **After approval, post to GitHub** (skip this step if the target is not a GitHub PR — the findings file is then the only deliverable):
    - Each `Cx` and `Mx` finding → its own inline comment (or a standalone comment if inline isn't possible).
    - `mx` and `nx` findings: default to the summary list (next bullet); inline is OK when the location really helps the author find the spot.
    - A summary comment with: an overview of all findings (including counts/lists for `mx` and `nx`), thanks to the author, **praise where deserved (skip rather than force a generic line)**, and clear instructions — what **must** be fixed (`Cx`, `Mx`), what should be **attempted** if easy (`mx`), and what is **optional** (`nx`).
    - **PR title / description `nx` findings:** include them in the summary comment as recommendations (GitHub has no inline slot for title or description).
    - **All GitHub comments in English.**
    - **Approve & merge:** only if **all four** hold — (a) no `Cx`/`Mx` findings remain unresolved **across all rounds** (check the latest round's `Status of prior findings` plus its new findings), (b) CI is green (treat a failing or pending CI as a blocker → don't merge; report the failing checks to the user instead), (c) the repo's required approval count would be met after your **Approve** (if not, still submit the Approve verdict but don't merge — tell the user how many more approvals are needed), and (d) the user pre-authorised it together with the go-ahead in step 13. If all four hold, after posting the comments also submit an **Approve** verdict and merge the PR using the repo's default merge button setting (squash / merge commit / rebase — ask the user if unsure).

15. **Stop the timesheet entry** once the CR work is complete — whether after posting (step 14), after a non-PR target's final summary (step 13), or if the user declined to proceed.
