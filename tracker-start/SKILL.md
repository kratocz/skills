---
name: start
description: Start a time tracking session or timer. Use when the user says "/start", "start session", "start timer", "begin tracking", "I'm starting work on...", or any similar phrase indicating they want to begin tracking time.
argument-hint: [task-description-or-url]
version: 1.6.0
allowed-tools: Read, Bash, WebFetch
---

# Start Session

Start a new time tracking session in the configured backend.

## Steps

1. **Read config**: Read `~/.claude/plugins/session-tracker/config.json` using the Read tool.
   - If the file doesn't exist: "No configuration found. Please run /setup-tracker first." Then stop.
   - Read `config.language` (default `"en"` if missing). All user-facing text generated in the steps below — prompts, confirmations, URL-derived descriptions — should be phrased in this language. Keep proper nouns, code identifiers, URLs, and numeric durations unchanged.

2. **Gather project context** (best-effort — ignore errors if not in a git repo):
   ```bash
   git remote get-url origin 2>/dev/null
   git branch --show-current 2>/dev/null
   pwd
   ```
   Derive a project name: take the last path segment of the git remote URL and strip a trailing `.git` (e.g., `git@github.com:user/my-repo.git` → `my-repo`). If not a git repo, fall back to the current directory name.

3. **Check for an already-running timer**:

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     https://api.track.toggl.com/api/v9/me/time_entries/current
   ```
   (The path must include `/me/` — the legacy `api/v9/time_entries/current` returns HTTP 405 with an empty body, which is easy to misread as "no timer running". The stdin `--config` trick keeps the key out of argv **and** sidesteps sandboxes that rewrite colon-bearing arguments — Claude Code's Bash sandbox turns `-u user:token` into a file path, so never pass the credential as a plain `-u` argument.)

   ### Clockify
   ```bash
   curl -s -H "X-Api-Key: <config.clockify.api_key>" \
     "https://api.clockify.me/api/v1/workspaces/<workspace_id>/time-entries?in-progress=true&page-size=1"
   ```

   If a timer is already running, show its description and ask the user (in the configured language) whether to stop it first (via `/stop`) or keep it running. Do not auto-stop.

4. **Determine description**:
   - If arguments were provided, trim them. If the trimmed argument starts with `http://` or `https://`, treat as a URL:
     - Use `WebFetch` with a prompt like "Return only the primary title of this page (e.g., pull/merge request title, issue title, or `<title>` tag). No commentary."
     - Compose the description as `<title> — <URL>`. If the configured language differs from the title's apparent language, translate/rephrase the title naturally (keep proper nouns, code identifiers, branch names, IDs intact).
     - If `WebFetch` fails or returns nothing usable, fall back to the URL as the full description.
   - If the argument is plain text, use it as-is (the user already chose the wording).
   - If no arguments were provided, ask the user — in the configured language — for a brief description of what they're working on.

5. **Resolve tracker project** (optional):
   - Fetch the active project list and look for a project whose name matches the detected repo/dir name (case-insensitive).
   - If matched, use its ID. Otherwise fall back to `default_project_id` from config (may be null — in which case no project is attached).

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     "https://api.track.toggl.com/api/v9/workspaces/<workspace_id>/projects?active=true"
   ```

   ### Clockify
   ```bash
   curl -s -H "X-Api-Key: <config.clockify.api_key>" \
     "https://api.clockify.me/api/v1/workspaces/<workspace_id>/projects"
   ```

6. **Get current UTC time**:
   ```bash
   date -u +%Y-%m-%dT%H:%M:%SZ
   ```

7. **Start timer** based on `config.backend`. Include the project ID field only if resolved in step 5; otherwise omit it entirely. Read `config.billable` (top-level field) and pass it in the payload — if the field is missing from the config, default to `true`.

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     -H "Content-Type: application/json" \
     -X POST "https://api.track.toggl.com/api/v9/time_entries" \
     --data-binary '{"description":"<description>","workspace_id":<workspace_id>,"start":"<UTC time>","duration":-1,"billable":<billable>,"created_with":"session-tracker-claude-plugin"}'
   ```

   ### Clockify
   ```bash
   curl -s -H "X-Api-Key: <config.clockify.api_key>" \
     -H "Content-Type: application/json" \
     -X POST "https://api.clockify.me/api/v1/workspaces/<workspace_id>/time-entries" \
     -d '{"description":"<description>","start":"<UTC time>","billable":<billable>}'
   ```

8. **Report result** (keep it concise, phrased in the configured language):
   - Success: an equivalent of `Session started: '<description>'` — append project name if resolved.
   - On HTTP error: show the API error message (verbatim, not translated) and suggest re-running `/setup-tracker`.
