---
name: log-entry
description: Log a retroactive (already finished) time entry to the configured tracker. Use when the user says "/log-entry", "log this to Toggl/Clockify", "add a time entry for ...", "track 2 hours retroactively", "zaloguj to do Toggl", or names a past time window they want recorded.
argument-hint: [time-window] [description]
version: 1.6.0
allowed-tools: Read, Bash
---

# Log Retroactive Entry

Create a completed time entry (start + end in the past) in the configured
backend — unlike `/start`, no live timer is involved.

## Steps

1. **Read config**: Read `~/.claude/plugins/session-tracker/config.json` using
   the Read tool.
   - If the file doesn't exist: "No configuration found. Please run
     /setup-tracker first." Then stop.
   - Read `config.language` (default `"en"`). Phrase all user-facing text in
     this language; keep proper nouns, IDs, URLs and durations unchanged.

2. **Determine the time window.** Parse it from the arguments if given
   (formats to accept: `9:00-11:30`, `0:00 to now`, `2h`, `45m`,
   `yesterday 14:00-16:00`, an explicit date `2026-07-01 22:00-23:15`).
   Interpretation rules:
   - A bare duration (`2h`) means "ending now".
   - Times without a date mean **today** (or the stated relative day) in the
     **user's local timezone**.
   - If no window can be parsed, ask the user for it (one question, in the
     configured language). Never guess a duration.

   Convert the window to what the API needs using `date` (never do timezone
   arithmetic in your head):
   ```bash
   date -u +%Y-%m-%dT%H:%M:%SZ                      # now, UTC
   date -j -f "%Y-%m-%d %H:%M" "<local datetime>" -u +%Y-%m-%dT%H:%M:%SZ   # macOS
   date -u -d "<local datetime>" +%Y-%m-%dT%H:%M:%SZ                        # GNU/Linux
   ```
   Compute `duration` in seconds as `end - start`. Echo the resolved window
   back to the user in local time in the final report so an off-by-timezone
   mistake is visible.

3. **Determine description**: remaining argument text, or ask (in the
   configured language). Optionally derive context from the current git repo
   as `/start` does.

4. **Resolve tracker project** (same as `/start`): fetch active projects, match
   the repo/dir name case-insensitively, fall back to `default_project_id`
   (may be null → omit the field).

5. **Read `config.billable`** (default `true` if missing). If the user named
   tags in the arguments, include them (Toggl: `"tags": [...]`; Clockify uses
   tag IDs — resolve via `GET /workspaces/<id>/tags` and match by name, skip
   silently if no match).

6. **Create the entry.** Keep the API key out of argv (it would land in the
   process table and transcripts): pass it via a config file / header read
   from stdin, with the key expanded from a shell variable — never as a
   literal in the command.

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -sS --config - \
     -H "Content-Type: application/json" \
     -X POST "https://api.track.toggl.com/api/v9/workspaces/<workspace_id>/time_entries" \
     --data-binary '{"created_with":"session-tracker-claude-plugin",
       "workspace_id":<workspace_id>,"description":"<description>",
       "start":"<UTC start>","stop":"<UTC end>","duration":<seconds>,
       "billable":<billable>}'
   ```
   (Add `"project_id":<id>` / `"tags":[...]` only when resolved.)

   ### Clockify
   ```bash
   KEY=<config.clockify.api_key read into a shell variable, not echoed>
   curl -sS -H @- -H "Content-Type: application/json" \
     -X POST "https://api.clockify.me/api/v1/workspaces/<workspace_id>/time-entries" \
     --data-binary '{"description":"<description>","start":"<UTC start>",
       "end":"<UTC end>","billable":<billable>}' <<< "X-Api-Key: $KEY"
   ```
   (Add `"projectId"` / `"tagIds"` only when resolved.)

7. **Verify and report** (concise, in the configured language): parse the
   response; on success show the entry id, the window in **local time**, the
   rounded duration in hours, billable flag, and project/tags if attached.
   On HTTP error show the API message verbatim and suggest checking
   `/setup-tracker`. If the response indicates a billable/project constraint
   (e.g. Toggl "workspace does not allow non-billable entries in billable
   projects"), retry once with `billable: true` and say so.
