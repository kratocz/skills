---
name: semver-release
description: Cut a SemVer release driven by Conventional Commits since the last tag. Bumps the version in detected manifest files (package.json, pyproject.toml, Cargo.toml, .claude-plugin/plugin.json, …), updates CHANGELOG.md in Keep a Changelog format, commits, tags, pushes, and optionally creates a GitHub release. Use when the user says "/semver-release", "cut a release", "tag a new version", "vydej release", "udělej release", or asks to ship a new version.
---

# semver-release — procedure

Cut a SemVer release from Conventional Commits. Every interactive choice goes through `AskUserQuestion` so the user can override. Never bypass hooks (`--no-verify`); never force-push.

Follow these steps in order.

## 1. Pre-flight

- Working tree must be clean: `git status --porcelain` should be empty. If not, stop and tell the user to commit or stash first.
- Capture the current branch: `git branch --show-current`.
- Find the latest tag: `git describe --tags --abbrev=0 2>/dev/null` (may fail if no tags exist — that's fine, this will be the first release).
- Capture the tag format: did the last tag use a `v` prefix (`v1.2.3`) or not (`1.2.3`)? Match that format. If no prior tags, default to `v` prefix.

## 2. Read commits since the last tag

```
git log <last-tag>..HEAD --pretty=format:'%H%x09%s%x09%b%x1e'
```

(`%x1e` is record-separator; split on that.)

Parse each commit:
- **Subject** matches `^(?<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\((?<scope>[^)]+)\))?(?<bang>!)?: (?<subject>.+)$`.
- **Breaking change** is signalled by either `!` in the subject (e.g. `feat!:`) **or** a `BREAKING CHANGE: <desc>` footer in the body.
- Commits that don't match the Conventional Commits pattern are classified as `other` — count them but don't drive bump decisions off them.

If no tag exists yet (first release), use the full `git log` since the initial commit.

If there are no commits since the last tag, stop and tell the user there's nothing to release.

## 3. Read the current version

Search the repo root for a manifest with a version field, in this priority order (first hit wins for "current version"; you'll write back to all detected files in step 6):

| File | How to read |
|---|---|
| `package.json` | `.version` (JSON) |
| `pyproject.toml` | `[project].version` or `[tool.poetry].version` (TOML) |
| `Cargo.toml` | `[package].version` (TOML) |
| `composer.json` | `.version` (JSON, optional — often missing) |
| `.claude-plugin/plugin.json` | `.version` (JSON) — for Claude Code plugins |
| `pubspec.yaml` | `version:` (YAML) |
| `mix.exs` | `@version` attribute |
| `*.csproj` | `<Version>` element |
| `VERSION` (plain file) | the trimmed contents |

If none are found, ask the user for the current version (or assume `0.0.0` if it's a first release).

Validate the version against SemVer (`MAJOR.MINOR.PATCH`, optional `-prerelease` and `+build`). If it doesn't parse, ask the user to confirm or correct.

## 4. Propose a version bump

Decision tree:

- **If current version ≥ 1.0.0:**
  - Any commit with breaking change → **major**
  - Else any `feat` → **minor**
  - Else any `fix` / `perf` / `refactor` → **patch**
  - Else (only `chore`/`docs`/`test`/`build`/`ci`/`style`) → **patch** (and warn the user — usually you don't release pure infra commits)

- **If current version < 1.0.0 (pre-1.0):**
  - Pre-1.0 SemVer is ambiguous; ask the user via `AskUserQuestion`:
    - Option 1: `Treat feat as minor, BREAKING as major (post-1.0 rules)` — recommended for projects close to 1.0
    - Option 2: `Treat feat as patch, BREAKING as minor (stay in 0.x experimental)` — recommended for early-stage
    - Option 3: `Custom — let me pick the bump kind directly`
  - Apply the chosen rule to decide the bump kind.

Compute the proposed version and show the user a summary:

```
Current: 0.5.3
Proposed: 0.6.0 (minor)

Reason: 3 feat commits since v0.5.3
- feat(auth): add OAuth login (abc1234)
- feat: support custom themes (def5678)
- feat(api): expose /metrics endpoint (1a2b3c4)

(also: 2 fix, 1 chore — see CHANGELOG entry below)
```

Then ask via `AskUserQuestion`:
- `Accept proposed version (X.Y.Z)` (recommended)
- `Bump differently — major` (offer the major version)
- `Bump differently — minor` (offer the minor version)
- `Bump differently — patch` (offer the patch version)
- `Custom version` — drop out to let user type the exact string
- `Cancel`

If the user picks a custom version, validate it as SemVer before continuing.

## 5. Generate the CHANGELOG entry

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).

Section mapping:
- `feat` → **Added**
- `fix` → **Fixed**
- `perf`, `refactor` (user-visible) → **Changed**
- Breaking changes → **Changed** with a `**BREAKING:**` prefix on the bullet (or a separate **Removed**/**Changed** entry if the change is purely removal)
- Skip `chore`, `docs`, `style`, `test`, `build`, `ci`, `revert` from the changelog (they're noise for users) — but note `revert` if it reverts a feature shipped in a prior release.

Entry template:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- <subject from feat commit> ([<short-sha>](https://github.com/<owner>/<repo>/commit/<sha>))

### Changed
- <subject from refactor/perf>

### Fixed
- <subject from fix commit>
```

Use today's date in `YYYY-MM-DD` form.

If `CHANGELOG.md` already exists, splice the new entry between the header (and any "Unreleased" section) and the previous most recent entry. Don't overwrite anything else.

If `CHANGELOG.md` doesn't exist, ask the user whether to create it. If yes, scaffold it with:

```markdown
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<new entry goes here>
```

## 6. Update version in manifest files

For every file detected in step 3, update the version string. Use precise `Edit` calls — don't rewrite the whole file.

Examples of exact patterns to match:
- `package.json`: `"version": "<old>"` → `"version": "<new>"`
- `pyproject.toml`: `version = "<old>"` (inside `[project]` or `[tool.poetry]`) → `version = "<new>"`
- `Cargo.toml`: `version = "<old>"` (inside `[package]`) → `version = "<new>"`
- `.claude-plugin/plugin.json`: `"version": "<old>"` → `"version": "<new>"`

Show the user the list of files about to be updated and ask via `AskUserQuestion`:
- `Update all detected files` (recommended)
- `Pick a subset` — list each file as a yes/no
- `Cancel`

After the edits, run `git diff --stat` to show what changed.

## 7. Check CI for the head commit

Before tagging, check whether CI on the current commit is green:

```
gh run list --branch <branch> --limit 5 --json headSha,status,conclusion,workflowName
```

Filter to runs whose `headSha` matches `git rev-parse HEAD`. Classify:
- All `conclusion: success` → green, continue.
- Any `status: in_progress` or `queued` → pending, **warn the user** via `AskUserQuestion`:
  - `Wait for CI to finish, then re-run /semver-release` (recommended)
  - `Release anyway — I know what I'm doing`
  - `Cancel`
- Any `conclusion: failure`/`cancelled`/`timed_out` → **failing**, warn the user more strongly:
  - `Cancel and fix CI first` (recommended)
  - `Release anyway — I have a justification`
  - `Cancel`

If `gh run list` fails (no GitHub remote, no `gh` auth, no workflows) — skip the CI check silently.

## 8. Final confirmation

Show the user a summary of what's about to happen:

```
About to:
  • Update version in <files…> to X.Y.Z
  • Append entry to CHANGELOG.md
  • Commit: "chore(release): vX.Y.Z"
  • Tag: vX.Y.Z (annotated)
  • Push commit + tag to origin/<branch>
```

Ask via `AskUserQuestion`:
- `Do it` (recommended)
- `Stop after commit — I'll tag/push manually`
- `Cancel`

## 9. Commit + tag

Stage **only** the version files and `CHANGELOG.md` (not everything). Then commit:

```
git commit -m "chore(release): vX.Y.Z"
```

(Match the tag format you captured in step 1 — drop the `v` prefix in the message if the project doesn't use it.)

Annotated tag with the changelog entry as the message:

```
git tag -a vX.Y.Z -m "<one-line release summary>"
```

Never use `--no-verify`. If a hook fails, stop, show the user the hook output, suggest a fix, and let them decide.

## 10. Push

Ask via `AskUserQuestion` (default yes):
- `Push commit and tag to origin/<branch>` (recommended)
- `Don't push — I'll do it myself`

If yes:

```
git push origin <branch> && git push origin vX.Y.Z
```

## 11. GitHub release

Ask via `AskUserQuestion`:
- `Create a GitHub release with the changelog entry as notes` (recommended)
- `Skip — just leave the tag`

If yes:

```
gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(cat <<'EOF'
<changelog entry body — without the H2 header line>
EOF
)"
```

If the version is a prerelease (contains `-alpha`, `-beta`, `-rc`, etc.), pass `--prerelease`.

## 12. Final summary

Tell the user:
- The new version and tag
- Files updated
- Commit SHA and tag
- GitHub release URL (if created), or "tag pushed, no GitHub release"
- Reminder to bump the dev branch back to the next `-dev` version if their workflow needs that (don't do it automatically — surface it as a follow-up).
