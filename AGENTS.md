# AGENTS.md

Guidance for agents (and humans) maintaining this repository.

## What this is

A collection of portable [Agent Skills](https://agentskills.io/) — one directory per skill under `skills/<name>/` with a `SKILL.md` entry point — installable into 70+ agent harnesses via `npx skills add kratocz/skills`. Claude-Code-specific plugins (lifecycle hooks, statusline) live separately in [kratocz/claude-plugins](https://github.com/kratocz/claude-plugins); do not add hook-dependent skills here.

## Distribution model (verified 2026-08-01)

- `npx skills add` installs a **physical copy** of each skill into `~/.agents/skills/` (the "universal" directory) and creates per-agent symlinks to it (e.g. `~/.claude/skills/<name> → ../../.agents/skills/<name>`). Local-path installs are not tracked by `skills update` — refresh them by re-running the add.
- Directory reality on tested harnesses: `~/.agents/skills/` is read by Codex, Copilot CLI, Gemini CLI, opencode, Antigravity CLI (interactive sessions), and Claude Code (with a delayed index). `~/.claude/skills/` is picked up by Claude Code instantly, including hot-reload into running sessions.
- Antigravity's `agy -p` (non-interactive print mode) does not load skills at all — never use it to test skill visibility; test in an interactive session.
- Known upstream gap in the skills CLI: `-g -a antigravity-cli` installs only into `~/.agents/skills/` and never into `~/.gemini/antigravity-cli/skills/`, despite the CLI's own agent map listing that global path. It works in practice only because Antigravity reads `~/.agents/skills/`.
- The maintainer's machines use **live symlinks** from `~/.agents/skills/` and `~/.claude/skills/` straight into a working clone, so edits apply without reinstalling.

## Authoring rules

- **Stay harness-neutral.** Describe actions, not tools ("read the file", not "use the Read tool"), and never assume one specific harness is the runtime — harnesses may appear as examples. Frontmatter extras (`allowed-tools`, `argument-hint`, `version`) are Claude-specific and ignored elsewhere; keeping them is fine.
- **Paths.** Session transcripts and project memory live under `<harness-home>/projects/<slug>/`, where `<harness-home>` is `~/.claude` (Claude Code) or `~/.gemini/antigravity-cli` (Antigravity CLI) — use the first that exists. Skill state/config deliberately stays under `~/.claude/plugins/<name>/` (historical location; it is just a path, readable from any harness — no migration).
- **Names must be unique across the flat collection** and the directory name must equal the frontmatter `name`. Suites use prefixes (`tracker-*`, `work-*`).
- **Czech strings are functional, not accidental.** Trigger phrases in descriptions and user-facing message templates exist because the primary user works in Czech; skills phrase runtime output in the configured language. Do not "translate them away". Documentation prose, on the other hand, is English.
- **kodex** is a regular skill with an **always-on pointer**: one line in the user's instructions file makes agents load it before non-trivial work; `rules/kodex.md` is that line for Antigravity's rules mechanism. The English text in `SKILL.md` is canonical; the Czech original lives in `references/kodex-cs.md` — keep them in sync.
- Bundled assets (`scripts/`, `references/`, templates) belong inside the skill's directory and are referenced by paths relative to it.

## Dev loop

Edit in a working clone. Symlinked installs see changes immediately; copy installs refresh with `npx skills add . -g -y --all`. Verify discovery with `npx skills add . --list` (every skill must appear). When adding a skill, also add a row to the README table.
