---
name: work-reconcile
description: Backfill missing timesheet entries at the end of a period. Reconstructs what you actually worked on — primarily from Claude Code session logs, confirmed by git/GitHub/Calendar/ClickUp — diffs it against what is already logged in Toggl/ClickUp, and after you approve each item writes only the missing time. Use when the user says "/work-reconcile", "doplň výkaz", "dorovnej timesheet", "co jsem zapomněl vykázat", "fill my timesheet", "reconcile my hours", "co chybí ve výkazu za minulý měsíc".
argument-hint: [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--project <name>] [--dry-run]
version: 0.3.0
allowed-tools: Read, Bash, ToolSearch, AskUserQuestion, mcp__toggl__toggl_get_time_entries, mcp__toggl__toggl_list_projects, mcp__github__search_pull_requests, mcp__github__search_issues, mcp__github__list_commits, mcp__plugin_ntit-common_clickup__clickup_filter_tasks, mcp__plugin_ntit-common_clickup__clickup_get_task_comments, mcp__plugin_ntit-common_clickup__clickup_get_time_entries, mcp__plugin_ntit-common_clickup__clickup_add_time_entry, mcp__claude_ai_Google_Calendar__list_events
---

# Work Reconcile

Retrospective timesheet backfill: **what did I actually work on that I never
logged — and write the missing time.** The forward-looking siblings answer
different questions:

| Skill | Question | Direction |
|-------|----------|-----------|
| `/work-start` | What should I do? | forward |
| `/work-status` | What changed? | since AM |
| `/work-end` | What did I close today? | today |
| `/work-standup` | What did I do since last time? | back (report) |
| **`/work-reconcile`** | **What did I do but not log — and fill it in** | **back (write)** |

Unlike the others, this skill **writes** to the tracker. It never writes
automatically: the flow is always **propose → confirm → write**.

## Arguments

- `--since YYYY-MM-DD` (optional): start of the reconcile window (bare date = `T00:00` local). Default: see step 2.
- `--until YYYY-MM-DD` (optional): end of the window (bare date = `T23:59:59` local). Default: now.
- `--project <name>` (optional): restrict to one project by name (case-insensitive substring).
- `--dry-run` (optional): run the full flow through review and **only print** the proposals — write nothing.

## Steps

1. **Load effective config.** Read `~/.claude/plugins/work/config.json` with the
   Read tool.
   - If missing: stop with (in the configured language) "Žádná konfigurace work
     pluginu. Spusť `/work-setup`." / "No work plugin config. Run `/work-setup`."
   - Parse it. Read `config.language` (default `cs`, fallback `en`); phrase all
     user-facing text in it, keeping proper nouns/IDs/URLs/durations unchanged.
   - Build `effective_config` by overlaying the `reconcile` block on these
     defaults (a MISSING `reconcile` block or any missing key falls back here —
     do not crash):
     `default_window=last_month`, `gap_threshold_min=15`, `edge_pad_min=2`,
     `round_to_min=5`, `min_block_min=5`, `coverage_covered=0.9`,
     `coverage_missing=0.1`, `ai_sessions.enabled=true`,
     `ai_sessions.projects_dir=~/.claude/projects`, `calendar.as_work=true`,
     `calendar.exclude_all_day=true`, `calendar.exclude_declined=true`,
     `calendar.exclude_keywords=["oběd","lunch","dovolená"]`,
     `sink.target=toggl`, `sink.billable=true`, `sink.reconciled_tag=reconciled`.
     `calendar.as_work` also gates the Calendar source: when false, Calendar is
     not fetched at all.

2. **Resolve the window `[since, until]`.**
   - `until`: `--until` if given (bare date → `T23:59:59` local), else now.
   - `since`: `--since` if given (bare date → `T00:00` local), else derive from
     `effective_config.reconcile.default_window`:
     - `last_month` (default): first day of the **previous** calendar month at
       `00:00` local; and if `--until` was not given, set `until` to the last
       moment of that previous month (so the default run reconciles exactly last
       month).
     - `last_week`: now minus 7 days at `00:00` local.
     - a bare `YYYY-MM`: that whole month.
   Compute `last_month` boundaries with `date` (never by hand):
   ```bash
   # macOS: first day of previous month 00:00 local
   date -v1d -v-1m -v0H -v0M -v0S +%Y-%m-%dT%H:%M:%S
   # macOS: last moment of previous month = (first day this month) - 1 second
   date -v1d -v0H -v0M -v0S -v-1S +%Y-%m-%dT%H:%M:%S
   # Linux: date -d "$(date +%Y-%m-01) -1 month" +%Y-%m-%dT00:00:00
   #        date -d "$(date +%Y-%m-01) -1 second" +%Y-%m-%dT%H:%M:%S
   ```
   - Store `project_filter` = `--project` value or null; `dry_run` = whether
     `--dry-run` was passed.
   - **Echo the resolved window** before doing anything else, e.g. "Dorovnávám
     výkaz od **<since>** do **<until>**." so an unexpected default is visible.

3. **Fetch all enabled sources — IN PARALLEL** where they are MCP calls (one
   message, multiple tool_use blocks). Probe each MCP source with `ToolSearch`
   first; if absent, append a warning and skip. Build the list `blocks`.

   **A. Claude Code session logs** (primary, if
   `effective_config.reconcile.ai_sessions.enabled`):

   Session logs live under `<projects_dir>/<encoded-path>/*.jsonl`, one file per
   session. The directory name is the working directory with `/` → `-`. Each
   line is a JSON object with `timestamp` (ISO 8601 UTC), `type`
   (`user`/`assistant`/`ai-title`/…). Find sessions overlapping the window and
   turn each into one `candidate_block`:

   ```bash
   DIR="${projects_dir/#\~/$HOME}"        # expand ~
   SINCE_UTC=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "<since>" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
             || date -u -d "<since>" +%Y-%m-%dT%H:%M:%SZ)
   UNTIL_UTC=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "<until>" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
             || date -u -d "<until>" +%Y-%m-%dT%H:%M:%SZ)
   find "$DIR" -name '*.jsonl' -type f
   ```

   For each `*.jsonl`, extract with a small Python filter (robust to non-JSON
   lines) the sorted list of message timestamps and the `ai-title` value:

   ```bash
   python3 - "$f" "$SINCE_UTC" "$UNTIL_UTC" <<'PY'
   import json, sys
   f, since, until = sys.argv[1], sys.argv[2], sys.argv[3]
   ts, title = [], None
   for line in open(f, encoding='utf-8'):
       try: d = json.loads(line)
       except Exception: continue
       t = d.get('timestamp')
       if t: ts.append(t)
       if d.get('type') == 'ai-title':
           title = (d.get('content') or title)
   ts = sorted(t for t in ts if t)
   if not ts: sys.exit(0)
   # keep session if it overlaps [since, until]
   if ts[-1] < since or ts[0] > until: sys.exit(0)
   print(json.dumps({'first': ts[0], 'last': ts[-1], 'n': len(ts),
                     'title': title, 'ts': ts}))
   PY
   ```

   For each surviving session, create a `candidate_block`:
   - `source='ai'`, `raw_messages_ts=ts` (kept for the duration math later, step 4),
     `start`/`end` = first/last ts **converted to local** (via `date`),
     `title` = the `ai-title` (or, if null, "Práce v <dir>"),
   - `project_hint` = the repo/dir name decoded from the directory name (last
     path segment of the decoded working directory),
   - `origin_marks=[]`.
   - Clip `start`/`end` to `[since, until]` if the session spills over an edge.

   **B. Google Calendar** (primary, if
   `effective_config.reconcile.calendar.as_work` is true and MCP present —
   probe `select:mcp__claude_ai_Google_Calendar__list_events`):

   Call `mcp__claude_ai_Google_Calendar__list_events` for `[since, until]`. For
   each returned event, apply the work filter from
   `effective_config.reconcile.calendar`:
   - drop all-day events if `exclude_all_day`,
   - drop events the user declined if `exclude_declined`,
   - drop events whose title matches any `exclude_keywords` (case-insensitive
     substring).
   Each surviving event → a `candidate_block` with `source='calendar'`,
   `start`/`end` = event start/end (local), `title` = event summary,
   `project_hint` = null (resolved during project pairing, step 5), `origin_marks=[]`,
   `raw_messages_ts=[]`.
   If the MCP is absent, append a one-line warning "Kalendář nedostupný —
   schůzky vynechány." and skip.

   **C. Confirmatory sources** (git always; GitHub/ClickUp if enabled+present):

   - **git** (local, free): in the current repo (and, if configured, each repo
     under a known root), collect commits authored by the user in the window:
     ```bash
     git log --all --since="<since>" --until="<until>" \
       --author="$(git config user.email)" \
       --pretty='%h|%aI|%s' 2>/dev/null
     ```
     Each commit is a confirmatory hit with a timestamp, its repo name, and
     subject. Not a block yet — see step 5.
   - **GitHub** (probe `select:mcp__github__search_pull_requests`): search PRs
     reviewed/merged and issues closed by
     `effective_config.sources.github.username` in the window. Each is a
     confirmatory hit (timestamp = merged/review time, subject = title).
   - **ClickUp** (probe `select:mcp__plugin_ntit-common_clickup__clickup_filter_tasks`):
     tasks updated by the user in the window via `clickup_filter_tasks`;
     optionally `clickup_get_task_comments` for the user's comments. Confirmatory
     hits (timestamp = update/comment time, subject = task name).
   Absent MCP → warn once, skip that source.

4. **Estimate a duration for each block.** The estimate is always a *default to
   hand-edit*, never authoritative.

   **AI blocks — gap-capping** (`raw_messages_ts` sorted, UTC is fine here since
   we only take differences). With `G = gap_threshold_min`, `E = edge_pad_min`:

   ```
   minutes_raw = 0
   for consecutive (a, b) in raw_messages_ts:
       gap = (b - a) in minutes
       minutes_raw += gap if gap <= G else E     # long pause = break → only pad
   minutes_raw += E                               # trailing pad after last msg
   ```

   Rationale: a session left open overnight has one huge inter-message gap; it
   contributes only one `E`, not 8 hours. Compute in Python:

   ```bash
   python3 - <<'PY'
   from datetime import datetime
   ts = [ ... raw_messages_ts ... ]
   G, E = 15, 2   # from config
   def m(x): return datetime.fromisoformat(x.replace('Z','+00:00'))
   secs = 0
   for a,b in zip(ts, ts[1:]):
       gap = (m(b)-m(a)).total_seconds()/60
       secs += gap if gap<=G else E
   secs += E
   print(round(secs))
   PY
   ```
   Then round to `round_to_min` and set `minutes`. If `minutes < min_block_min`,
   drop the block as noise. Set `origin='ai-gapcapped'`.

   **Calendar blocks:** `minutes` = exact `(end - start)` rounded to
   `round_to_min` (no gap-capping — a meeting is contiguous). Set
   `origin='calendar-exact'`.

   **Origin marks** drive the review display (step 8):
   | `origin` | Review label |
   |----------|--------------|
   | `ai-gapcapped` | `~<m>m (AI, gap-capped)` |
   | `calendar-exact` | `<m>m (kalendář)` |
   | `commit-only` | `? (jen commit — DOPLŇ ČAS)` |
   | `manual` | `<m>m (ručně)` |

5. **Pair every block to a project** (same mechanism as `/start` and
   `/log-entry`):
   - Fetch active Toggl projects (`mcp__toggl__toggl_list_projects`, or the
     `session-tracker` key fallback).
   - For AI blocks: match `project_hint` (repo/dir name) case-insensitively
     against project names; on a hit set `project`. For Calendar blocks with no
     hint, leave `project=null` for now.
   - Fallback to `sources.toggl.project_id` /
     `session-tracker` `default_project_id` if no match (may be null).
   - If still unresolved, set `project=null` and add `'project?'` to
     `origin_marks` — the review (step 8) will force the user to pick before this
     block can be approved.
   - If `project_filter` (`--project`) is set, drop blocks whose resolved
     `project` does not match it (case-insensitive substring).

6. **Fold confirmatory hits into blocks — never double-count.** For each
   confirmatory hit (git commit / GitHub PR / ClickUp update):
   - If its timestamp falls **inside** an existing AI block's `[start, end]`
     (same repo/project where determinable), attach it: add a mark to that
     block's `origin_marks` (`git✓ Nc` with a commit count, `gh✓ #<pr>`,
     `clickup✓`), and optionally enrich the block `title`. Do **not** create a
     new block and do **not** add time.
   - If it falls **outside** every AI block, promote it to a standalone
     `candidate_block` with `source='commit'` (or `gh`/`clickup`),
     `origin='commit-only'`, `minutes=null` (unknown — user must fill in),
     `start` = the hit timestamp, `end` = null, `project` resolved by step 5's
     matching procedure applied to the hit's repo name (so it can also end up
     `null` with a `'project?'` mark).
   - Merge multiple outside-hits that are close in time on the same project into
     one `commit-only` block (list their subjects) to avoid a flood of tiny
     rows.
   - If `project_filter` is set, drop any newly-promoted `commit-only` block
     whose paired `project` does not match it (same rule as step 5's filter).

7. **Diff against what is already logged** — propose only the missing time.
   - Load existing entries for `[since, until]` **only from the trackers in
     `sink.target`** (reading a ClickUp busy-map is pointless when writing only
     to Toggl). Toggl: `mcp__toggl__toggl_get_time_entries` (`start_date`/
     `end_date`). ClickUp: probe `select:mcp__plugin_ntit-common_clickup__clickup_get_time_entries`
     first; if present, call it with `start_date`/`end_date` and
     `assignee=["me"]`-equivalent (omit `assignee` — it defaults to the
     authenticated user's own entries, which is what a personal reconcile
     wants). If the tool is absent, treat the ClickUp busy-map as **best-effort:
     skip it, warn once** ("ClickUp historie nedostupná — kontrola překryvu jen
     přes Togglu."), and fall through to Toggl-only coverage for ClickUp-bound
     blocks (they will simply not be marked COVERED by pre-existing ClickUp
     entries). Each existing entry → (start, end, project).
   - Build a **busy map** per (project, day): the union of already-logged
     intervals. Entries with no project go into a general per-day bucket.
   - For each candidate block, split it per calendar day if it crosses midnight,
     then compute against the same (project, day):
     ```
     overlap  = minutes of the block already inside busy intervals
     coverage = overlap / block_minutes        (block_minutes>0)
     ```
   - Decide with `coverage_covered` (0.9) and `coverage_missing` (0.1):
     - `coverage >= coverage_covered` → **COVERED**: drop the block; count it for
       the summary line only.
     - `coverage_missing <= coverage < coverage_covered` → **PARTIAL**: keep, but
       set proposed `minutes = round(block_minutes - overlap)`; label
       `~<m>m (doplněk k <overlap>m)`.
     - `coverage < coverage_missing` → **MISSING**: keep whole block; label
       `~<m>m (chybí)`.
   - `commit-only` blocks (`minutes=null`) skip coverage math (nothing to
     measure) and always appear, flagged to fill in.
   - ClickUp coverage is bucketed per (project, day), not per-task, so
     same-project same-day ClickUp time can mask a distinct task's block — the
     `reconciled_tag` idempotency check (step 9) is the finer backstop.

8. **Review — the heart of "confirm".** First print a **grouped table**
   (by project, then day), each row: proposed minutes + origin label +
   `origin_marks`. End with a summary line: `N návrhů (Σ h) · K pokrytých skryto
   · M bez času`. Example:

   ```
   Projekt X — po 2026-06-02
     ~90m  fix auth bug        (AI, gap-capped)  [git✓ 3c, PR#42✓]
      35m  code review          (doplněk k 25m)   [GitHub✓]
      60m  Sprint planning      (kalendář)
      ?    hotfix deploy         (jen commit — DOPLŇ ČAS)
   Souhrn: 12 návrhů (8.5 h) · 5 pokrytých skryto · 1 bez času
   ```

   Then approve **in batches** via `AskUserQuestion`, one group (project/day) at
   a time, options: **Vše / Vybrat / Přeskočit / Upravit časy**.
   - **Vybrat** → list the group's items so the user picks a subset.
   - **Upravit** → let the user overwrite `minutes` (and optionally
     `project`/`title`) on a chosen item.
   - **A block with `minutes=null` (the `?` items) CANNOT be approved until the
     user supplies a duration** — force the prompt; never write a `null`.
   - **A block with `'project?'` in `origin_marks` CANNOT be approved until the
     user picks a project.**
   - **If `sink.target` includes `clickup`:** a ClickUp time entry must attach to
     a `task_id` (AI sessions / commits / meetings have no inherent ClickUp
     task). So for each block the user approves for a ClickUp write, prompt them
     to pick the target ClickUp task — offer a shortlist from
     `clickup_filter_tasks` (filtered by `assignee=<sources.clickup.member_id>`,
     active) via `AskUserQuestion`,
     or let them paste a task ID / custom ID (e.g. `DEV-1234`). Store it as the
     block's `clickup_task_id`. A block **CANNOT** be approved for a ClickUp
     write without a `clickup_task_id`. (Toggl writes need no task — this gate
     applies only to the ClickUp sink.)
   - Choosing **Vše** approves every item in the group but does **not**
     bypass the gates above: any gated item (a `?` duration, a `project?`
     mark, or a required `clickup_task_id`) still forces its per-item prompt
     — "Vše" cannot manufacture a missing value.
   - Offer **"+ přidat ruční položku"** (phone call): ask start, duration,
     project, description → append as `source='manual'`, `origin='manual'`,
     fully specified.
   Everything the user OKs goes into `approved`. Nothing else is written.
   If `dry_run`, stop here after printing what *would* be written, grouped like
   the summary; write nothing.

9. **Write the approved entries.** For each item in `approved`, write to every
   tracker in `sink.target` (`toggl`, `clickup`, or `both`).

   **Safety (identical to `session-tracker`'s `/log-entry`):** never put the API
   key in argv. Read it into a shell variable and pass it via a stdin-fed config
   / header, so it stays out of `ps` and transcripts. Do all time conversion
   with `date`, never by hand.

   **Toggl** — `POST /api/v9/workspaces/<wid>/time_entries`. Use the **exact
   auth pattern proven in `session-tracker`'s `/log-entry`**: Basic auth via
   `curl --config -` fed on stdin (so the key stays out of argv), with the
   credential line `user = "<token>:api_token"`. `duration` is
   `round(minutes) * 60` (seconds; `minutes` is the approved per-item value).
   If the block's `end` is null (commit-only or manual items filled in without
   an end time), derive it with `date` as `start + duration` before building
   the payload. Body carries `start` (UTC ISO), `stop` (UTC ISO, the derived or
   original end), `duration` (seconds), `description`, `project_id` (only when
   resolved), `billable` (from `sink.billable`), and `tags` including
   `sink.reconciled_tag` — mirroring `/log-entry`'s Toggl body:
   ```bash
   KEY=<toggl api_key read into a shell var, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -sS --config - \
     -H "Content-Type: application/json" \
     -X POST "https://api.track.toggl.com/api/v9/workspaces/<wid>/time_entries" \
     --data-binary '{"created_with":"work-reconcile","workspace_id":<wid>,
       "start":"<utc>","stop":"<utc_end>","duration":<secs>,"description":"<desc>",
       "billable":<bool>,"tags":["<reconciled_tag>"]}'
   ```
   (Add `"project_id":<pid>` only when a project was resolved.)
   **ClickUp** — `mcp__plugin_ntit-common_clickup__clickup_add_time_entry`
   with `task_id` (the block's `clickup_task_id`, chosen during review — step 8),
   `start` (`YYYY-MM-DD HH:MM`), `duration` (`Xh Ym`), `description`, `billable`,
   `tags:[<reconciled_tag>]`. A block without a `clickup_task_id` was never
   approved for ClickUp (the step 8 gate) — skip it for this sink.

   **Per-item failure isolation:** if one write fails, record the error and
   **continue** with the rest; never abort the whole batch.

   **Idempotency:** before writing, and on any re-run, treat an existing entry
   that already carries `sink.reconciled_tag` overlapping the same block as
   already-written and skip it (belt-and-braces on top of the coverage diff, so
   a second `/work-reconcile` writes nothing).

   **No sink credentials** (neither Toggl nor ClickUp key available): do not
   write. Instead offer an **export** — print the approved items as a Markdown
   table (and offer to save a `.csv`) so the user can paste them manually. Say
   so explicitly.

10. **Summary.** Print what happened: per project, entries written (with
    durations) and total; then a line each for skipped-as-covered, skipped
    (user), and failed (with the error). If nothing was written, say why
    (dry-run / no approvals / no credentials).
