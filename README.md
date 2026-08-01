# Skills

Personal collection of agent skills by [Petr Kratochvíl](https://krato.cz/) — one source for every harness: Claude Code, Codex, Antigravity CLI, opencode, GitHub Copilot CLI, Gemini CLI, and any other agent that supports the [Agent Skills](https://agentskills.io/) `SKILL.md` standard.

## Installation

Via the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add kratocz/skills            # interactive: pick skills and agents
npx skills add kratocz/skills -g --all   # everything, globally, all detected agents
```

### Development install (live symlinks)

If you work on the skills themselves, symlink them from a working clone instead — edits are then picked up without reinstalling:

```bash
git clone https://github.com/kratocz/skills.git
cd skills
./install.sh
```

This links every skill into `~/.agents/skills/` (read by Antigravity CLI, Codex, Copilot CLI, Gemini CLI, opencode — and Claude Code with a delay) and into `~/.claude/skills/` (picked up by Claude Code instantly), and links the `kodex` rule pointer for Antigravity.

> **Note for Claude Code:** if you previously installed the skill plugins from `kratocz/claude-plugins`, uninstall them first — otherwise the same skills load twice.

## The kodex rule

`kodex` is distributed as a regular skill, but it is meant to be **always on**. To guarantee that, add one line to your agent's global instructions file (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, …):

> Před netriviální analýzou, rozhodnutím či odevzdáním výstupu si načti skill `kodex` a řiď se jím.

For Antigravity CLI, `install.sh` links [rules/kodex.md](./rules/kodex.md) (the same one-liner) into `~/.gemini/antigravity-cli/rules/`.

## State

The `tracker-*` and `work-*` skills read their configuration from `~/.claude/plugins/session-tracker/` and `~/.claude/plugins/work/` (a historical location — it is just a path, readable from any harness). Run `/tracker-setup-tracker` or `/work-setup` to create it.

## Available Skills

*Newest first — sorted by date added.*

| Name | Description | Added |
|---|---|---|
| [skillify](./skills/skillify) | Analyze this session (and, on demand, past transcripts) for repeatable workflows worth capturing as a skill | 2026-07-17 |
| [kodex](./skills/kodex) | Thinking codex — 15 rules + pre-delivery self-test; pair with the one-line always-on rule pointer | 2026-07-10 |
| [dependency-diagrams](./skills/dependency-diagrams) | Generate task-dependency diagrams from any tracker (ClickUp, GitHub, Jira, etc.) as draw.io + SVG/PNG | 2026-07-10 |
| [retro](./skills/retro) | Session retrospective — migrate memory facts to AGENTS.md, capture session learnings, audit docs | 2026-06-10 |
| [work-*](./skills/work-start) | Work management suite: morning briefing (`work-start`), mid-day checks (`work-status`), end-of-day wrap up (`work-end`), standup recap, timesheet reconcile, setup | 2026-06-03 |
| [dockerize](./skills/dockerize) | Add Docker to a project: multi-stage Dockerfile, .dockerignore, optional docker-compose.yml | 2026-06-01 |
| [launchpad-fix](./skills/launchpad-fix) | *(macOS only)* Re-register apps missing from Launchpad with Launch Services and reset the Dock | 2026-06-01 |
| [semver-release](./skills/semver-release) | Cut a semver release from Conventional Commits: bump version, update CHANGELOG.md, tag, push | 2026-06-01 |
| [conventional-commit](./skills/conventional-commit) | Create a Conventional Commits message from the staged diff | 2026-06-01 |
| [init-project](./skills/init-project) | Bootstrap a new project: .gitignore, AGENTS.md, CLAUDE.md, README.md, initial commit | 2026-05-30 |
| [code-review](./skills/code-review) | Structured code review with severity codes (Cx/Mx/mx/nx), per-round findings files, and GitHub posting | 2026-05-30 |
| [mikrotik-audit](./skills/mikrotik-audit) | Read-only security audit for Mikrotik RouterOS devices via SSH | 2026-04-20 |
| [tracker-*](./skills/tracker-start) | Time tracking for Toggl or Clockify: `tracker-start`, `tracker-stop`, `tracker-backfill`, `tracker-log-entry`, `tracker-setup-tracker` | 2026-04-09 |
| [second-opinion](./skills/second-opinion) | Get a second opinion from Gemini or GPT on any important topic or decision | 2026-04-04 |

## Related repositories

- [kratocz/claude-plugins](https://github.com/kratocz/claude-plugins) — Claude Code plugins that genuinely need the plugin mechanism (hooks): session-log, statusline, tmux-hooks, desktop-notify.

*This repository was formerly `antigravity-skills`; skills were originally developed as Claude Code plugins, then migrated to the portable Agent Skills layout.*
