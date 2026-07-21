---
name: conventional-commit
description: Generate a Conventional Commits message (type, optional scope, subject, body for non-trivial diffs) from the currently staged diff and create the commit. Use when the user says "/conventional-commit", "commit staged changes", "udělej commit", "commitni to", "make a conventional commit", or asks for a Conventional Commits–style message for the current diff.
---

# conventional-commit — procedure

Generate a [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) message from the staged diff and create the commit. All commit messages in **English** (consistent with code and PR titles).

Follow these steps in order.

## 1. Check staged state

Run `git status --short` and `git diff --cached --stat`.

- If **something is staged** → continue with step 2.
- If **nothing is staged** → ask the user via `AskUserQuestion`:
  - `Stage all changes (git add -A) and continue` (note: will include untracked files — call it out if there are any)
  - `Stage by patch (git add -p)` — drop out of the skill and tell the user to run it interactively
  - `Cancel` — stop here

Never run `git add` blindly without asking. Never use `--no-verify` anywhere in this skill.

## 2. Read the staged diff

- `git diff --cached` for content (cap output mentally if it's huge — focus on file headers and key hunks).
- `git diff --cached --name-only` for the file list.
- `git diff --cached --shortstat` for the size signal (used in step 5 to decide whether to add a body).

## 3. Pick the Conventional Commits type

Decide based on the files and the changes inside them. Use the official set:

| Type | When to pick it |
|---|---|
| `feat` | A new exported function, endpoint, component, CLI flag, or user-facing capability. |
| `fix` | A change that corrects incorrect behavior (often paired with a test that would fail without the fix). |
| `docs` | Only `*.md`, doc comments, or inline docs changed. |
| `style` | Whitespace, formatting, semicolons — no code logic change. Rare; usually a formatter caught it. |
| `refactor` | Restructuring without changing observable behavior or external API. |
| `perf` | A change motivated by performance. |
| `test` | Only test files changed (added/updated tests, no production code change). |
| `build` | Build system, package dependencies, lockfiles (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Dockerfile`, `Makefile`). |
| `ci` | CI config (`.github/workflows/`, `.gitlab-ci.yml`, `.circleci/`, etc.). |
| `chore` | Repo housekeeping that doesn't fit elsewhere: `.gitignore`, `.editorconfig`, license, repo metadata. |
| `revert` | Pure revert of a previous commit (matches `git revert` style). |

**Mixed diffs** — if the diff spans multiple types (e.g. `feat` + `test` for the new feature), pick the **dominant** one. A new feature with its tests is `feat`, not split. If you can't honestly pick a dominant type, ask the user whether to split the commit (see step 8).

**Breaking changes:** if the diff removes or changes the signature of an exported API, plan to add `BREAKING CHANGE: <description>` to the footer in step 5, and append `!` to the type/scope in step 4 (e.g. `feat(api)!: change auth header`). Don't guess — if it looks borderline, ask the user.

## 4. Draft the subject line

Format: `<type>(<scope>)?: <subject>`

- **Subject:** imperative mood (`add` not `added`/`adds`), lowercase first letter, no period at end.
- **Length:** the whole subject line ≤ 72 characters. If it gets too long, prefer trimming the subject before dropping the scope.
- **Scope** — propose a sensible default by looking at the changed paths:
  - All changes under a single top-level module/dir (e.g. `src/auth/…`) → propose that name (`auth`).
  - All changes under one package in a monorepo (e.g. `packages/foo/…`) → propose the package name.
  - Cross-cutting changes → propose `none`.

Then ask the user via `AskUserQuestion` to confirm the scope:
- Option 1: Use the proposed scope (e.g. `auth`)
- Option 2: No scope
- Option 3: Other (user types their own)

Once the scope is settled, you have the final subject line.

## 5. Decide whether to add a body

A body is **required** if either:
- More than 1 file changed (`git diff --cached --name-only | wc -l > 1`), **or**
- More than 30 lines changed (sum of insertions + deletions from `--shortstat`).

If neither holds, **skip the body** — just the subject.

If a body is required:
- Format: a blank line after the subject, then 1–3 short sentences.
- Focus on **why**, not what. The diff already shows what. Body explains motivation, the constraint that drove the choice, or a non-obvious consequence.
- Wrap at ~72 chars per line.
- Skip platitudes ("This commit adds …", "Refactored for clarity"). If you have nothing meaningful to say about *why*, write one specific sentence about *the user-visible effect* instead.

If you flagged a breaking change in step 3, add a `BREAKING CHANGE:` footer after a blank line below the body. Pattern:

```
<type>(<scope>)!: <subject>

<body>

BREAKING CHANGE: <description of what breaks and how to migrate>
```

## 6. Show the final message and confirm

Show the user the full proposed message in a fenced code block. Then ask via `AskUserQuestion`:

- `Commit as proposed` (recommended)
- `Edit message` — drop out and let the user run `git commit` themselves with their own message
- `Split commit` — see step 8
- `Cancel` — stop, leave everything staged

## 7. Create the commit

Run:

```
git commit -m "$(cat <<'EOF'
<message>
EOF
)"
```

(HEREDOC keeps multi-line bodies intact.)

If a **pre-commit hook fails**, do **not** retry with `--no-verify`. Show the user the hook output, suggest a fix, and stop. Never bypass hooks.

After the commit succeeds, show the new commit SHA and the subject line back to the user.

## 8. Optional: split commit

If the user picked "Split commit" in step 6 (or you detected truly unrelated changes in step 3), drop out of the skill and tell the user:

> The staged diff mixes unrelated changes. Run `git reset` to unstage everything, then `git add -p` to stage one logical group at a time and re-run this skill for each.

Don't try to split commits automatically — `git add -p` is interactive and belongs to the user.
