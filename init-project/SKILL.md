---
name: init-project
description: Bootstrap a new project repository — creates .gitignore (with macOS junk + project-type-specific entries), AGENTS.md, CLAUDE.md, README.md, runs git init if needed, commits the baseline, and optionally creates a GitHub repo via gh CLI. Use when the user wants to initialize a new project, says "založ projekt", "inicializuj projekt", "bootstrap repo", "/init-project", or has just created/inherited a new directory and wants the standard baseline files in place.
---

# init-project — procedure

Bootstrap a new project at the current working directory. Always operate in the user's current `pwd` — never `cd` elsewhere. Never overwrite existing user content; only **append** to existing `.gitignore`, and **skip** an existing `AGENTS.md` / `CLAUDE.md` / `README.md` (tell the user it already exists).

Follow these steps in order. Where a step calls for a decision the user should make, ask via `AskUserQuestion`.

## 1. Survey the directory

- Run `pwd` to capture the target directory.
- List the root with `ls -la` (or equivalent) so you can see what's already there.
- Check if it is a git repo: `git rev-parse --is-inside-work-tree 2>/dev/null`.
- Note which of these already exist: `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `README.md`.

## 2. Detect the project type

Look for marker files in the root and classify. Multiple matches are fine — union the resulting `.gitignore` entries.

| Marker file(s) | Type |
|---|---|
| `package.json` | Node.js |
| `pyproject.toml`, `setup.py`, `requirements*.txt`, `Pipfile` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `composer.json` | PHP |
| `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle*` | Java/JVM (Maven/Gradle) |
| `Gemfile` | Ruby |
| `mix.exs` | Elixir |
| `pubspec.yaml` | Dart/Flutter |
| `*.csproj`, `*.sln` | .NET |

If none match, treat it as **generic** (only the baseline entries below).

## 3. Build the `.gitignore`

Always start from this baseline (macOS junk + JetBrains IDE + selective VS Code — ignore personal state but allow project-scope config to be shared with the team):

```
.DS_Store
._*
/.idea/
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json
!.vscode/*.code-snippets
```

Then add type-specific entries:

- **Node.js:** `node_modules/`, `dist/`, `build/`, `.env`, `.env.local`, `*.log`, `coverage/`, `.next/`, `.nuxt/`, `.cache/`
- **Python:** `__pycache__/`, `*.py[cod]`, `.venv/`, `venv/`, `env/`, `.env`, `dist/`, `build/`, `*.egg-info/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`
- **Go:** `/vendor/`, `*.exe`, `*.test`, `*.out`
- **Rust:** `/target/`
- **PHP:** `/vendor/`, `.env`
- **Java/JVM:** `/target/`, `/build/`, `*.class`, `.gradle/`, `*.iml`, `hs_err_pid*`, `out/`
- **Ruby:** `/vendor/bundle/`, `.bundle/`, `*.gem`, `.env`
- **Elixir:** `/_build/`, `/deps/`, `*.ez`, `erl_crash.dump`
- **Dart/Flutter:** `.dart_tool/`, `/build/`, `.packages`
- **.NET:** `bin/`, `obj/`, `*.user`, `.vs/`

**If `.gitignore` already exists**, read it and append only the entries that aren't already there (preserve the existing order and any user customizations). If nothing new to add, leave it alone and note that.

## 4. Create `AGENTS.md` (if it doesn't exist)

Use this minimal template — leave placeholders where you don't know the answer. Don't invent specifics; the user will fill them in.

```markdown
# AGENTS.md

Guidance for AI coding agents working in this repository (Claude Code, Cursor, Aider, Copilot, …).

## Project overview

<one or two sentences about what this project is — fill in based on what you can infer from the code, leave a TODO if unknown>

## Setup

<install/dependency commands, e.g. `npm install`, `pip install -e .`>

## Run / build / test

- **Run:** <e.g. `npm run dev`>
- **Build:** <e.g. `npm run build`>
- **Test:** <e.g. `npm test`>

## Conventions

- <coding style, formatter, linter — fill in or leave a TODO>
- <commit message style — fill in or leave a TODO>
```

If `AGENTS.md` already exists, skip and tell the user.

## 5. Create `CLAUDE.md` (if it doesn't exist)

Contents — keep it to a single redirect so AGENTS.md is the single source of truth:

```markdown
See [AGENTS.md](AGENTS.md).
```

If `CLAUDE.md` already exists, skip and tell the user.

## 6. Create `README.md` (if it doesn't exist)

Best effort based on what you can see — **only fill in what you actually know** from the directory contents. Don't invent features or usage instructions.

Reasonable defaults for the name and description:
- Name: `package.json#name` / `pyproject.toml [project].name` / `go.mod` module last segment / basename of `pwd` (in that order of preference).
- Description: any existing one-liner in those files; otherwise leave a single placeholder line the user can edit.

Minimal template:

```markdown
# <name>

<one-line description or TODO placeholder>
```

If you can see clear setup or usage commands in the existing code (e.g. scripts in `package.json`), add them. Otherwise stop at the name + description — don't pad with empty sections.

If `README.md` already exists, skip and tell the user.

## 7. Initialize git if needed

If the directory is not a git repo, run `git init`. Use the user's default branch (don't force `main` if their git config sets something else).

## 8. Commit

- `git add` only the files this skill created or modified (do not blanket `git add .` — there may be other untracked files the user doesn't want committed yet).
- Single commit is the default. Suggested messages:
  - First commit in a fresh repo: `chore: initial project setup`
  - Adding baseline files to an existing repo: `chore: add project baseline (.gitignore, AGENTS.md, CLAUDE.md, README.md)`
  - .gitignore-only change to an existing repo: `chore: extend .gitignore with macOS + <type> entries`
- Multiple commits are fine if the changes naturally split (e.g. one commit per file kind) — but don't manufacture artificial splits.

Do not use `--no-verify` or skip hooks.

## 9. Handle the remote and pushing

Check the remote: `git remote -v`.

**If `origin` already exists:** confirm with the user whether to push (`git push -u origin <branch>`), then push.

**If no remote exists:** ask the user, in one `AskUserQuestion` call with three questions:

1. **Create a GitHub repo for this project?** — `Yes (recommended) / No, leave it local for now`.
2. **Repo name** — offer the basename of `pwd` as the default; let the user override.
3. **Visibility** — `Private (recommended) / Public`. Default to Private unless the user already indicated it's an open-source project.

If the user said "Yes":
- Run `gh auth status` first to make sure they're authenticated; if not, tell them to run `gh auth login` and pause.
- Create the repo and push in one step:
  ```
  gh repo create <name> --<private|public> --source=. --remote=origin --push
  ```
- Confirm the URL of the new repo from `gh repo view --json url --jq .url`.

If the user said "No", stop after the local commit — the baseline is ready, they can add a remote later.

## 10. Final summary

Tell the user:
- Which files were created vs. skipped (because they already existed).
- The commit SHA(s) and message(s).
- The GitHub repo URL (if pushed) or that the repo is local-only.
- Any obvious follow-ups (e.g. "your `AGENTS.md` has TODO placeholders — fill them in when you know the run/test commands").
