---
name: tracker-stop
description: Stop the running time tracking timer (Toggl/Clockify) and report its duration — now, or at an earlier time the user names ("stop it at 17:28"). Always acts on the currently running entry. Use when the user says "/tracker-stop", "stop timer", "stop tracking", "zastav stopky", "zastav timer k 17:28", or otherwise wants the running time entry closed. Not the end-of-day summary — that is work-end.
argument-hint: "[stop time, e.g. 17:28 — default: now]"
version: 1.7.0
allowed-tools: Read, Bash
license: MIT
---

# Stop Session

Stop the currently running time tracking session and report its duration.

## Steps

1. **Read config**: Read `~/.claude/plugins/session-tracker/config.json`.
   - If the file doesn't exist: "No configuration found. Please run /tracker-setup-tracker first." Then stop.
   - Read `config.language` (default `"en"` if missing). Phrase user-facing messages below in this language; keep numeric durations, quoted descriptions, and URLs unchanged.

   **Optional stop time.** With an argument (`17:28`, `2026-10-28 17:28`), the entry ends at that moment instead of now. A bare clock time means today in the user's local time zone. Convert it to UTC with a command (`date`, Python), never in your head, and refuse it when it is not after the entry's `start` or lies in the future. Use it when the work ended earlier than the moment the user asks: the user names the time, or you take it from the transcript, commits or PR timestamps. Do not use a guess.

2. **Get the current running timer**:

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     https://api.track.toggl.com/api/v9/me/time_entries/current
   ```
   If the response body is `null`, tell the user (in the configured language) that no session is currently running. Then stop. (The path must include `/me/` — the legacy `api/v9/time_entries/current` returns HTTP 405 with an empty body, which is easy to misread as "no timer running". The stdin `--config` trick keeps the key out of argv and sidesteps sandboxes that rewrite colon-bearing arguments like `-u user:token` into file paths.)

   Before stopping, verify the running entry is one this session started (match the description or remembered id) — a parallel session's timer may be running instead; stopping someone else's work needs the user's explicit OK.

   ### Clockify
   ```bash
   curl -s -H "X-Api-Key: <config.clockify.api_key>" \
     "https://api.clockify.me/api/v1/workspaces/<workspace_id>/time-entries?in-progress=true&page-size=1"
   ```
   If the array is empty, tell the user (in the configured language) that no session is currently running. Then stop.

3. **Stop the timer**:

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     -H "Content-Type: application/json" \
     -X PATCH "https://api.track.toggl.com/api/v9/workspaces/<workspace_id>/time_entries/<timer_id>/stop"
   ```
   With a stop time, follow the stop with a `PUT` to the same entry (`…/time_entries/<timer_id>`, without `/stop`) whose body carries both its original `start` and the new `stop`. Toggl then recomputes `duration`. Report the `stop` and `duration` from the PUT response, not from the stop call.

   ### Clockify
   With a stop time, send it as `end` instead of the current time. Otherwise get the current UTC time first:
   ```bash
   date -u +%Y-%m-%dT%H:%M:%SZ
   ```
   Then stop:
   ```bash
   curl -s -H "X-Api-Key: <config.clockify.api_key>" \
     -H "Content-Type: application/json" \
     -X PATCH "https://api.clockify.me/api/v1/workspaces/<workspace_id>/user/<user_id>/time-entries" \
     -d '{"end":"<current UTC time>"}'
   ```

4. **Calculate and report duration** (phrased in the configured language; keep the duration format and quoted description verbatim):
   - Parse the `start` timestamp from the timer response.
   - Calculate elapsed time (hours and minutes) up to the stop time actually written.
   - Report an equivalent of: `Session stopped: <Xh Ym> — '<description>'`
   - Example (en): `Session stopped: 1h 23m — 'Refactoring auth module'`
   - Example (cs): `Session ukončena: 1h 23m — 'Refactoring auth module'`
