---
name: tracker-backfill
description: Fill gaps in time tracking from the current session's transcript, splitting it into activity blocks — works for sessions spanning several days. Use when the user says "/tracker-backfill", "doplň díry v Togglu", "backfill Toggl gaps", "doplň do Toggl práci na tomto", "fill in missing time for this session", or asks whether tracked time matches the session.
argument-hint: [date]
version: 1.6.0
allowed-tools: Read, Bash
---

# Backfill Session Gaps

Compare the current agent session's real activity blocks (from its
transcript timestamps) with the tracker entries of the days those blocks
touch, and create entries for the uncovered intervals — never overlapping anything already tracked.

## Steps

1. **Read config**: Read `~/.claude/plugins/session-tracker/config.json` using
   the Read tool.
   - If the file doesn't exist: "No configuration found. Please run
     /tracker-setup-tracker first." Then stop.
   - Read `config.language` (default `"en"`). Phrase all user-facing text in
     this language; keep IDs, URLs, and durations unchanged.

2. **Determine the day filter (optional)**: a `YYYY-MM-DD` argument limits the
   work to blocks overlapping that day; with no argument, process every day
   the session's blocks touch.

3. **Locate the current session transcript and its activity span.**
   Transcripts live in `<harness-home>/projects/<slug>/*.jsonl`, where
   `<harness-home>` is `~/.claude` (Claude Code) or `~/.gemini/antigravity-cli`
   (Antigravity CLI) — use the first that exists — and `<slug>` is
   the session's working directory with `/` and `.` replaced by `-` (e.g.
   `/Users/me/proj` → `-Users-me-proj`). The current session is the most
   recently modified `.jsonl` in that directory (verify: its most recent
   events are from right now; if unsure which file is the right
   one, list candidates and ask).

   **Split the transcript into activity blocks — never treat `first → last` as
   one span.** A session can stay open across days (sleep, other projects,
   meetings), so its raw span is not time worked; on a multi-day session that
   difference is tens of hours. Group consecutive events and start a new block
   wherever the gap exceeds a threshold.

   **Choosing the threshold.** A pause between prompts is usually *not* a break
   — the user is reading, thinking, or writing the next one. Default to **60
   minutes**, and say which threshold you used when presenting the proposal.
   Compute the total for several (20 / 45 / 60 / 90) and mention it only if they
   differ; when they agree, the choice is not worth the user's attention. If the
   user has said how they work, follow that over the default.

   ```bash
   export FILE=$(ls -t ~/.claude/projects/<slug>/*.jsonl \
     ~/.gemini/antigravity-cli/projects/<slug>/*.jsonl 2>/dev/null | head -1)
   python3 << 'EOF'
   import json, os
   from datetime import datetime, timedelta
   GAP = timedelta(minutes=60)
   ts = []
   with open(os.environ["FILE"]) as f:
       for line in f:
           try: t = json.loads(line).get("timestamp")
           except Exception: continue
           if t: ts.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
   ts.sort()
   blocks = []; s = e = ts[0]
   for t in ts[1:]:
       if t - e > GAP: blocks.append((s, e)); s = t
       e = t
   blocks.append((s, e))
   for a, b in blocks:
       print(f"{a:%Y-%m-%d %H:%M} -> {b:%H:%M} UTC  {b-a}")
   print("blocks:", len(blocks), "total:", sum((b-a for a,b in blocks), timedelta()))
   EOF
   ```

   Each block is then treated like the span was before: subtract existing
   entries from it, and propose what remains. A session spanning several days
   produces blocks on each of them — do not restrict the work to one target day
   unless the user asked for that.

4. **Fetch existing entries for every day the blocks touch** (all of them —
   any project; overlaps must be computed against everything, not just this
   project's entries). One range query covers it — `<first day>` to
   `<last day + 1>`:

   ### Toggl Track
   ```bash
   KEY=<config.toggl.api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     "https://api.track.toggl.com/api/v9/me/time_entries?start_date=<first day>&end_date=<last day+1>"
   ```
   (The stdin `--config` trick keeps the key out of argv and sidesteps
   sandboxes that rewrite colon-bearing arguments like `-u user:token`.)

   ### Clockify
   ```bash
   KEY=<config.clockify.api_key read into a shell variable, not echoed>
   curl -sS -H @- "https://api.clockify.me/api/v1/workspaces/<workspace_id>/user/<user_id>/time-entries?start=<first day>T00:00:00Z&end=<last day+1>T00:00:00Z&page-size=200" <<< "X-Api-Key: $KEY"
   ```

5. **Compute uncovered intervals per block**: if a day filter is set, first
   drop blocks that do not overlap it. Then, for each remaining block, within
   `[block_start, min(block_end, now)]`, subtract every existing entry's
   `[start, stop]` (a running entry
   covers from its `start` onward). Work in UTC; use `date` or Python for the
   arithmetic — never do timezone math in your head. Drop leftover fragments
   shorter than ~2 minutes (noise). If nothing remains in any block, report
   "tracking already covers the whole session" and stop.

6. **Confirm before writing** (this is billing data — never create entries
   silently): show the proposed entries in **local time** (start–stop,
   duration, description, project) and ask the user to approve. Default
   description: the description of the session's existing/most recent entry
   for this work, else ask. Resolve project + `billable` the same way `/tracker-start`
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
   #   "billable":<billable>,"created_with":"session-tracker"}
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
