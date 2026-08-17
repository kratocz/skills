# Skills

Personal collection of agent skills by [Petr Kratochvíl](https://krato.cz/) — one source for every harness: Claude Code, Codex, Antigravity CLI, opencode, GitHub Copilot CLI, Gemini CLI, and any other agent that supports the [Agent Skills](https://agentskills.io/) `SKILL.md` standard.

## Installation

Via the [skills CLI](https://github.com/vercel-labs/skills) — you only need `npx`:

```bash
npx skills add kratocz/skills            # interactive: pick skills and agents
npx skills add kratocz/skills -g --all   # everything, globally, all detected agents
```

### Updating

```bash
npx skills update -g
```

Skills installed from GitHub are tracked by the CLI and update to the latest pushed version. Local-path installs (below) are not tracked — re-run the `add` after pulling or editing instead.

### Working on the skills

Install from a working clone the same way — local installs are plain copies, so re-run after editing:

```bash
npx skills add . -g -y --all
```

> **Note for Claude Code:** if you previously installed the skill plugins from `kratocz/claude-plugins`, uninstall them first — otherwise the same skills load twice.

## The kodex rule

`kodex` is distributed as a regular skill, but it is meant to be **always on**. To guarantee that, add one line to your agent's global instructions file (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, …):

> Před netriviální analýzou, rozhodnutím, odhadem či odevzdáním výstupu si načti skill `kodex` a řiď se jím po zbytek úkolu.

For Antigravity CLI the same line goes into its rules directory — write it directly:

```bash
mkdir -p ~/.gemini/antigravity-cli/rules
printf 'Před netriviální analýzou, rozhodnutím, odhadem či odevzdáním výstupu si načti skill `kodex` a řiď se jím po zbytek úkolu.\n' \
  > ~/.gemini/antigravity-cli/rules/kodex.md
```

(or symlink [rules/kodex.md](./rules/kodex.md) from a clone).

## State

The `tracker-*` and `work-*` skills read their configuration from `~/.claude/plugins/session-tracker/` and `~/.claude/plugins/work/` (a historical location — it is just a path, readable from any harness). Run `/tracker-setup-tracker` or `/work-setup` to create it.

## Available Skills

*Newest first — sorted by date added.*

| Name | Description | Added |
|---|---|---|
| [mcp-server-adopt](./skills/mcp-server-adopt) | Find, compare, security-vet, install and verify a third-party MCP server — audit runs *before* any build | 2026-08-18 |
| [decision-analysis](./skills/decision-analysis) | Context-anchored decision analysis ending in a verdict: dated decision rules before research, sourced claims, durable layer vs dated snapshot | 2026-08-10 |
| [skillify](./skills/skillify) | Analyze this session (and, on demand, past transcripts) for repeatable workflows worth capturing as a skill | 2026-07-17 |
| [kodex](./skills/kodex) | Thinking codex — rules 0–16 + pre-delivery self-test; pair with the one-line always-on rule pointer | 2026-07-10 |
| [dependency-diagrams](./skills/dependency-diagrams) | Generate task-dependency diagrams from any tracker (ClickUp, GitHub, Jira, etc.) as draw.io + SVG/PNG | 2026-07-10 |
| [retro](./skills/retro) | Session retrospective — migrate memory facts to AGENTS.md, capture session learnings, audit docs | 2026-06-10 |
| [work-*](./skills/work-start) | Work management suite: morning briefing (`work-start`), mid-day checks (`work-status`), end-of-day wrap up (`work-end`), standup recap, timesheet reconcile, setup | 2026-06-03 |
| [dockerize](./skills/dockerize) | Add Docker to a project: multi-stage Dockerfile, .dockerignore, optional docker-compose.yml | 2026-06-01 |
| [launchpad-fix](./skills/launchpad-fix) | *(macOS only)* Triage apps that won't launch — broken Spotlight index vs. missing Launch Services registration — and fix the right layer | 2026-06-01 |
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
