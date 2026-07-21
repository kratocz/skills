# Antigravity Skills

A collection of skills and rules for the [Google Antigravity CLI](https://antigravity.google/) by [Petr Kratochvíl](https://krato.cz/).
*These were originally developed as Claude Code plugins and have been migrated to native Antigravity skills.*

## Installation

Antigravity CLI loads user skills from `~/.gemini/antigravity-cli/skills` and rules from `~/.gemini/antigravity-cli/rules`.

To install these skills, simply clone this repository and symlink the folders:

```bash
# Clone the repository
git clone https://github.com/kratocz/antigravity-skills.git
cd antigravity-skills

# Create Antigravity directories if they don't exist
mkdir -p ~/.gemini/antigravity-cli/skills
mkdir -p ~/.gemini/antigravity-cli/rules

# Symlink all skills
for skill in *; do
  if [ -d "$skill" ] && [ "$skill" != "rules" ] && [ "$skill" != ".git" ]; then
    ln -sfn "$PWD/$skill" "$HOME/.gemini/antigravity-cli/skills/$skill"
  fi
done

# Symlink rules
ln -sfn "$PWD/rules/kodex.md" "$HOME/.gemini/antigravity-cli/rules/kodex.md"
```

## Available Skills & Rules

*Newest first — sorted by date added.*

| Name | Type | Description | Added |
|---|:---:|---|---|
| [skillify](./skillify) | Skill | Analyze this session (and, on demand, past transcripts) for repeatable workflows worth capturing as a skill | 2026-07-17 |
| [kodex](./rules/kodex.md) | Rule | Thinking codex for AI agents — 15 rules + pre-delivery self-test injected into every session | 2026-07-10 |
| [dependency-diagrams](./dependency-diagrams) | Skill | Generate task-dependency diagrams from any tracker (ClickUp, GitHub, Jira, etc.) as draw.io + SVG/PNG | 2026-07-10 |
| [retro](./retro) | Skill | Session retrospective — migrate memory facts to AGENTS.md, capture session learnings, audit docs | 2026-06-10 |
| [work-*](./work-start) | Skills | Suite of work management skills: morning briefing (`work-start`), mid-day checks (`work-status`), end-of-day wrap up (`work-end`), etc. | 2026-06-03 |
| [dockerize](./dockerize) | Skill | Add Docker to a project: multi-stage Dockerfile, .dockerignore, optional docker-compose.yml | 2026-06-01 |
| [launchpad-fix](./launchpad-fix) | Skill | *(macOS only)* Re-register apps missing from Launchpad with Launch Services and reset the Dock | 2026-06-01 |
| [semver-release](./semver-release) | Skill | Cut a semver release from Conventional Commits: bump version, update CHANGELOG.md, tag, push | 2026-06-01 |
| [conventional-commit](./conventional-commit) | Skill | Create a Conventional Commits message from the staged diff | 2026-06-01 |
| [init-project](./init-project) | Skill | Bootstrap a new project: .gitignore, AGENTS.md, CLAUDE.md, README.md, initial commit | 2026-05-30 |
| [code-review](./code-review) | Skill | Structured code review with severity codes (Cx/Mx/mx/nx), per-round findings files, and GitHub posting | 2026-05-30 |
| [mikrotik-audit](./mikrotik-audit) | Skill | Read-only security audit for Mikrotik RouterOS devices via SSH | 2026-04-20 |
| [log-*](./log-where) | Skills | Save a structured summary of each session to a markdown file (`log-where`, etc.) | 2026-04-19 |
| [tracker-*](./tracker-start) | Skills | Time tracking integration for Toggl or Clockify (`tracker-start`, `tracker-stop`, `tracker-backfill`, etc.) | 2026-04-09 |
| [second-opinion](./second-opinion) | Skill | Get a second opinion from Gemini or GPT on any important topic or decision | 2026-04-04 |

*(Note: Claude Code specific plugins like `tmux-hooks`, `claude-statusline-state`, and `desktop-notify` were deprecated during migration as Antigravity handles these natively via `settings.json`.)*
