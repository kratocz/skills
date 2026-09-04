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

> Before any non-trivial analysis, decision, estimate, or deliverable, load the `kodex` skill and follow it for the rest of the task.

For Antigravity CLI the same line goes into its rules directory — write it directly:

```bash
mkdir -p ~/.gemini/antigravity-cli/rules
printf 'Before any non-trivial analysis, decision, estimate, or deliverable, load the `kodex` skill and follow it for the rest of the task.\n' \
  > ~/.gemini/antigravity-cli/rules/kodex.md
```

(or symlink [rules/kodex.md](./rules/kodex.md) from a clone).

The same line in Czech is [rules/kodex-cs.md](./rules/kodex-cs.md) — the skill body is English either way, so use whichever reads better in your own instructions file.

## State

The `tracker-*` and `work-*` skills read their configuration from `~/.claude/plugins/session-tracker/` and `~/.claude/plugins/work/` (a historical location — it is just a path, readable from any harness). Run `/tracker-setup-tracker` or `/work-setup` to create it.

## Available Skills

*Newest first — sorted by date added.*

| Name | Description | Added |
|---|---|---|
| [task-delivery](./skills/task-delivery) | Carry one tracker task from ready-to-start to closed — scope from the task *and* its parent epic, gates re-run after every edit and read from the last run, house-shape PR with a QA-step-to-test table, review delegated to `code-review`, merge only on a separate explicit directive | 2026-09-04 |
| [epic-breakdown](./skills/epic-breakdown) | Turn a written work breakdown into a tracker epic with house-shape subtasks and transitively reduced dependency edges — conventions read from AGENTS.md, granularity test (one subtask = one PR with its own QA) applied before founding, whole cut shown for approval first | 2026-09-04 |
| [mail-catchup](./skills/mail-catchup) | Catch up on an IMAP mailbox via the zerolib-email MCP — per-thread briefing of what is asked of you and by when, dated draft file for approval, in-thread send with an RFC 2047 subject, verified against Sent before it counts as sent | 2026-09-03 |
| [oponentura](./skills/oponentura) | Adversarial pass over a document in a fresh context — refute, not check: numbers against primary sources, strongest counter-argument, same evidential standard for the preferred and the rejected explanation, findings by severity, outcome recorded in the document header | 2026-09-03 |
| [client-questions](./skills/client-questions) | Build the question list for a meeting with a client or other external party — parallel sweep of repo, tracker and chat, triage into live / parked / already answered, each live question phrased as spoken plus what changes on the answer | 2026-09-01 |
| [debate-reply](./skills/debate-reply) | Answer a public challenge to a claim you have written down — steelman and verify against primary sources, fix your own note first, reply conceding then closing with one question, archive with receipts | 2026-08-27 |
| [skillset-adopt](./skills/skillset-adopt) | Adopt a third-party skill collection: inventory first, name-collision and trigger-overlap detection, per-skill verdict install / borrow / skip, verified install | 2026-08-26 |
| [skill-dry-run](./skills/skill-dry-run) | Prove a skill works by running it on real data in a clean context — writes made structurally impossible, findings re-verified | 2026-08-26 |
| [dm-catchup](./skills/dm-catchup) | Catch up on DMs with a person across ClickUp chat/Slack — threads expanded, summary + assessment + approved-draft reply | 2026-08-18 |
| [resource-busy](./skills/resource-busy) | Find which process blocks an eject/unmount or holds a file — incl. holders invisible to lsof/fuser (TM snapshot mounts, mount namespaces) — and release it safely | 2026-08-18 |
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

- [kratocz/claude-plugins](https://github.com/kratocz/claude-plugins) — Claude Code plugins that genuinely need the plugin mechanism (hooks): session-log, claude-statusline-state, tmux-hooks, desktop-notify.

### Used alongside

This collection is deliberately incomplete — it does not re-implement what the following already do well:

- [obra/superpowers](https://github.com/obra/superpowers) — the process spine (brainstorming, planning, TDD, review). `kodex` sits above it as the thinking discipline, not beside it.
- [mattpocock/skills](https://github.com/mattpocock/skills) — cherry-picked standalone skills: `grilling`, `wizard`, `codebase-design`, `diagnosing-bugs`, `resolving-merge-conflicts`. Its engineering suite needs its own tracker setup, and it ships a `code-review` and a `retro` that would replace the ones here — install the ones you want with a repeated `-s` (`-s grilling -s wizard …`), not `--all`.
- [anthropics/skills](https://github.com/anthropics/skills) — `docx`, `xlsx` and `pdf` for document work.
- [vercel-labs/skills](https://github.com/vercel-labs/skills) — the installer used above, plus `find-skills` for searching the [skills.sh](https://skills.sh/) directory. [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) is the other curated index.

Popular collections overlap heavily with each other and with the above; `skillset-adopt` is the skill here that weighs a new one against what is already installed before anything gets added.

*This repository was formerly `antigravity-skills`; skills were originally developed as Claude Code plugins, then migrated to the portable Agent Skills layout.*
