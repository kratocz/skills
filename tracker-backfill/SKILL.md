---
name: backfill
description: Fill gaps in today's time tracking from the current session's transcript. Use when the user says "/backfill", "doplň díry v Togglu", "backfill Toggl gaps", "doplň do Toggl práci na tomto", "fill in missing time for this session", or asks whether today's tracked time matches the session.
argument-hint: [date]
version: 1.6.0
allowed-tools: Read, Bash
---

# Backfill Session Gaps

Compare the current Claude Code session's real activity span (from its
transcript timestamps) with the day's tracker entries, and create entries for
the uncovered intervals — never overlapping anything already tracked.

## Steps

1. **Read config**: Read `~/.claude/plugins/session-tracker/config.json` using
   the Read tool.
   - If the file doesn't exist: "No configuration found. Please run
     /setup-tracker first." Then stop.
   - Read `config.language` (default `"en"`). Phrase all user-facing text in
     this language; keep IDs, URLs, and durations unchanged.

2. **Determine the target day**: from the argument (`YYYY-MM-DD`) or default
   to today in the user's local timezone.

3. **Locate the current session transcript and its activity span.**
   Transcripts live in `~/.claude/projects/<slug>/*.jsonl`, where `<slug>` is
   the session's working directory with `/` and `.` replaced by `-` (e.g.
   `/Users/me/proj` → `-Users-me-proj`). The current session is the most
   recently modified `.jsonl` in that directory (verify: its first-line
   timestamp must fall on the target day; if unsure which file is the right
   one, list candidates and ask).

   Extract the first and last event timestamps (they are UTC ISO-8601):
   ```bash
   FILE=$(ls -t ~/.claude/projects/<slug>/*.jsonl | head -1)
   python3 << EOF
   import json
   first = last = None
   with open("$FILE") as f:
       for line in f:
           try: ts = json.loads(line).get("timestamp")
           except Exception: continue
           if not ts: continue
           first = first or ts
           last = ts
   print("session span UTC:", first, "->", last)
   EOF
   ```

4. **Fetch the day's entries** (all of them — any project; overlaps must be
   computed against everything, not just this project's entries):

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     "https://api.track.toggl.com/api/v9/me/time_entries?start_date=<day>&end_date=<day+1>"
   ```
   (The stdin `--config` trick keeps the key out of argv and sidesteps
   sandboxes that rewrite colon-bearing arguments like `-u user:token`.)

   ### Clockify
   ```bash
   KEY=<config.clockify.api_key read into a shell variable, not echoed>
   curl -sS -H @- "https://api.clockify.me/api/v1/workspaces/<workspace_id>/user/<user_id>/time-entries?start=<day>T00:00:00Z&end=<day+1>T00:00:00Z&page-size=200" <<< "X-Api-Key: $KEY"
   ```

5. **Compute uncovered intervals**: within `[session_first, min(session_last,
   now)]`, subtract every existing entry's `[start, stop]` (a running entry
   covers from its `start` onward). Work in UTC; use `date` or Python for the
   arithmetic — never do timezone math in your head. Drop leftover fragments
   shorter than ~2 minutes (noise). If nothing remains, report "tracking
   already covers the whole session" and stop.

6. **Confirm before writing** (this is billing data — never create entries
   silently): show the proposed entries in **local time** (start–stop,
   duration, description, project) and ask the user to approve. Default
   description: the description of the session's existing/most recent entry
   for this work, else ask. Resolve project + `billable` the same way `/start`
   does. Overlapping time that belongs to another entry (e.g. parallel work
   already tracked) is intentionally NOT proposed — double-booking is
   overbilling; say so if the user asks about a "missing" covered interval.

7. **Create the approved entries.** Write each JSON payload to a temp file and
   send it with `--data-binary @file` (inline generated JSON is fragile in
   sandboxed shells):

   ### Toggl Track
   ```bash
   # payload file: {"description":"…","workspace_id":<id>,"project_id":<id?>,
   #   "start":"<UTC start>","stop":"<UTC stop>","duration":<seconds>,
   #   "billable":<billable>,"created_with":"session-tracker-claude-plugin"}
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     -H "Content-Type: application/json" \
     -X POST "https://api.track.toggl.com/api/v9/time_entries" \
     --data-binary @/path/to/payload.json
   ```

   ### Clockify
   ```bash
   # payload file: {"description":"…","start":"<UTC start>","end":"<UTC end>",
   #   "billable":<billable>}
   KEY=<config.clockify.api_key read into a shell variable, not echoed>
   curl -sS -H @- -H "Content-Type: application/json" \
     -X POST "https://api.clockify.me/api/v1/workspaces/<workspace_id>/time-entries" \
     --data-binary @/path/to/payload.json <<< "X-Api-Key: $KEY"
   ```

8. **Verify and report**: re-fetch the day (step 4) and print the timeline
   sorted by start, marking each adjacent pair as `[seamless]`, `[gap Ns]`, or
   `[OVERLAP!]` — an overlap means something went wrong and must be reported.
   Report created entries in **local time** with durations; state explicitly
   which intervals were left alone because other entries already cover them.
