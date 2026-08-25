---
name: work-reconcile
description: Reconcile the timesheet for a past period (week, month) across all sessions. Reconstructs what you actually worked on — primarily from agent session logs, confirmed by git/GitHub/Calendar/ClickUp — diffs it against what is already logged in Toggl/ClickUp, and after you approve each item writes only the missing time. Use when the user says "/work-reconcile", "doplň výkaz", "dorovnej timesheet", "co jsem zapomněl vykázat", "fill my timesheet", "reconcile my hours", "co chybí ve výkazu za minulý měsíc". For gaps in just the current session, that is tracker-backfill.
argument-hint: "[--since YYYY-MM-DD] [--until YYYY-MM-DD] [--project <name>] [--dry-run]"
version: 0.9.0
allowed-tools: Read, Bash, ToolSearch, AskUserQuestion, mcp__toggl__toggl_get_time_entries, mcp__toggl__toggl_list_projects, mcp__github__search_pull_requests, mcp__github__search_issues, mcp__github__list_commits, mcp__plugin_ntit-common_clickup__clickup_filter_tasks, mcp__plugin_ntit-common_clickup__clickup_get_task_comments, mcp__plugin_ntit-common_clickup__clickup_get_time_entries, mcp__plugin_ntit-common_clickup__clickup_add_time_entry, mcp_Google_Calendar__list_events
license: MIT
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

1. **Load effective config.** Read `~/.claude/plugins/work/config.json`.
   - If missing: stop with (in the configured language) "Žádná konfigurace work
     skillů. Spusť `/work-setup`." / "No work skills config. Run `/work-setup`."
   - Parse it. Read `config.language` (default `cs`, fallback `en`); phrase all
     user-facing text in it, keeping proper nouns/IDs/URLs/durations unchanged.
     **Every quoted user-facing string in this skill — review labels, menu
     options, warnings, the summary line — is an example written in `cs`.**
     Render it in `config.language`; none of them is a literal the user must
     see verbatim. Where a string is given as `"<czech>" / "<english>"`, those
     are one message in two languages, not two messages.
   - Build `effective_config` by overlaying the `reconcile` block on these
     defaults (a MISSING `reconcile` block or any missing key falls back here —
     do not crash):
     `default_window=last_month`, `gap_threshold_min=15`, `edge_pad_min=2`,
     `round_to_min=5`, `min_block_min=5`, `coverage_covered=0.9`,
     `coverage_missing=0.1`, `ai_sessions.enabled=true`,
     `ai_sessions.projects_dir=<harness-home>/projects` (`~/.claude` or
     `~/.gemini/antigravity-cli`, first that exists), `calendar.as_work=true`,
     `calendar.exclude_all_day=true`, `calendar.exclude_declined=true`,
     `calendar.exclude_keywords=["oběd","lunch","dovolená","holiday",
     "vacation","day off","out of office"]`,
     `sink.target=toggl`, `sink.billable=true`, `sink.reconciled_tag=reconciled`.
     `calendar.as_work` also gates the Calendar source: when false, Calendar is
     not fetched at all.
   - **Where the `reconcile` block is read from.** The canonical location is
     **top-level** `config.reconcile.*` — that is what `/work-setup` writes, and
     `calendar.*` lives at `config.reconcile.calendar.*`. A hand-edited config
     often puts the calendar half where it feels natural instead, under
     `config.sources.google_calendar.reconcile.*`; observed live on 2026-08-26,
     where a user's own `exclude_keywords` sat there and was silently ignored,
     so the built-in defaults ran and their filter never applied. **Read that
     nested block as a fallback, and say so out loud** — "Kalendářové nastavení
     načteno ze `sources.google_calendar.reconcile` (zastaralé umístění);
     přesuň ho do `reconcile.calendar`." / "Calendar settings read from
     `sources.google_calendar.reconcile` (legacy location); move them to
     `reconcile.calendar`." Never merge both halves silently: two live
     locations for one setting is how the first one stops being read.

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

   **A. Agent session logs** (primary, if
   `effective_config.reconcile.ai_sessions.enabled`):

   Session logs live at `<projects_dir>/<encoded-path>/*.jsonl`, one file per
   session; the directory name is the working directory with `/` → `-`. Each
   line is a JSON object with `timestamp` (ISO 8601 UTC), `type`
   (`user`/`assistant`/`ai-title`/…).

   **Three properties of this tree cost real hours if you take it at face
   value** — all three measured on a live `~/.claude/projects` on 2026-08-26,
   where the naive reading inflated one month from 141 h to 254 h:

   - **Subagent transcripts are nested one level deeper**, at
     `<projects_dir>/<slug>/<session-uuid>/subagents/agent-*.jsonl` (775 of
     1340 files on that machine). A subagent runs *inside* its parent session,
     so its timestamps are already covered by the parent's — counting them adds
     the same minutes twice. A recursive `find` sweeps them in silently, so
     **match at depth 1 only**.
   - **A `.jsonl` is a resumable session, not a work block.** The worst case
     observed spanned 2026-07-15 → 2026-08-09 with 24 259 messages and
     gap-capped to 3 425 min (57 h) in a single row. Split every session into
     one block **per local calendar day**.
   - **A session can straddle the window edge**, so compute from timestamps
     **inside `[since, until]` only** — clipping `start`/`end` while summing all
     of them charges the window for work outside it (that same session carried
     nine days of August).

   ```bash
   DIR="${projects_dir/#\~/$HOME}"        # expand ~
   # `since`/`until` are LOCAL wall-clock (step 2). On macOS `date -u -j -f`
   # parses its input as UTC, so converting them that way shifts the window by
   # the zone offset — verified 2026-08-26 in CEST: a July reconcile dropped the
   # first two hours of 1 July and pulled in the last two hours of 31 July as
   # "1 August" rows. Parse as local first (plain `-j -f` → epoch), then format
   # as UTC; this also picks up the DST rule in force *on that date*, which
   # appending a literal `$(date +%z)` would not.
   SINCE_UTC=$( { E=$(date -j -f "%Y-%m-%dT%H:%M:%S" "<since>" +%s) && date -u -r "$E" +%Y-%m-%dT%H:%M:%SZ; } 2>/dev/null \
             || date -u -d "<since>" +%Y-%m-%dT%H:%M:%SZ)   # Linux: -d already parses as local
   UNTIL_UTC=$( { E=$(date -j -f "%Y-%m-%dT%H:%M:%S" "<until>" +%s) && date -u -r "$E" +%Y-%m-%dT%H:%M:%SZ; } 2>/dev/null \
             || date -u -d "<until>" +%Y-%m-%dT%H:%M:%SZ)
   # depth 1 only: <slug>/<session>.jsonl, never <slug>/<uuid>/subagents/*.jsonl
   find "$DIR" -mindepth 2 -maxdepth 2 -name '*.jsonl' -type f
   ```

   For each `*.jsonl`, extract with a small Python filter (robust to non-JSON
   lines) the in-window timestamps grouped by local day, plus the `ai-title`:

   ```bash
   python3 - "$f" "$SINCE_UTC" "$UNTIL_UTC" <<'PY'
   import json, sys, collections, datetime
   f, since, until = sys.argv[1], sys.argv[2], sys.argv[3]
   P = lambda x: datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
   lo, hi = P(since), P(until)
   ts, title = [], None
   for line in open(f, encoding='utf-8', errors='replace'):
       try: d = json.loads(line)
       except Exception: continue
       if not isinstance(d, dict): continue
       t = d.get('timestamp')
       if t: ts.append(t)
       if d.get('type') == 'ai-title':
           # the field is 'aiTitle'; 'content' is a tolerant fallback for other
           # harnesses. Reading only 'content' yields None on every Claude Code
           # session (verified 2026-08-26: 550 of 567 files carry aiTitle), so
           # every row degrades to the "Práce v <dir>" placeholder.
           title = (d.get('aiTitle') or d.get('content') or title)
   ts = sorted(P(t) for t in ts if t)
   ts = [t for t in ts if lo <= t <= hi]          # clip, do not merely mark
   if not ts: sys.exit(0)
   perday = collections.defaultdict(list)          # local day (use the TZ offset
   for t in ts:                                    # the machine reports)
       perday[t.astimezone().strftime('%Y-%m-%d')].append(t.isoformat())
   for day, dts in sorted(perday.items()):
       print(json.dumps({'day': day, 'first': dts[0], 'last': dts[-1],
                         'n': len(dts), 'title': title, 'ts': dts}))
   PY
   ```

   Each emitted line is one `candidate_block`:
   - `source='ai'`, `raw_messages_ts=ts` (that day's slice, kept for step 4),
     `start`/`end` = that day's first/last ts **converted to local** (via `date`),
     `title` = the `ai-title` (or, if null, "Práce v <dir>"),
   - `project_hint` = the decoded working directory (see step 5 — the whole
     path, not just its last segment). **The encoding is lossy**: it maps both
     `/` and `.` to `-`, so `-Users-…-www-hunting-shop-cz` could be any of
     several real paths. Do not guess — resolve the slug by longest-prefix match
     against directories that actually exist under the checkout root, and where
     the directory is gone (a deleted worktree) keep the raw slug and let the
     step 5 markers speak,
   - `origin_marks=[]`.

   **B. Google Calendar** (primary, if
   `effective_config.reconcile.calendar.as_work` is true and MCP present —
   probe `select:mcp_Google_Calendar__list_events`):

   Call `mcp_Google_Calendar__list_events` for `[since, until]`. For
   each returned event, apply the work filter from
   `effective_config.reconcile.calendar`:
   - drop all-day events if `exclude_all_day`,
   - drop events the user declined if `exclude_declined`,
   - **drop events the user marked as Free** — `transparency: "transparent"`
     (equivalently `availability: "AVAILABILITY_FREE"`). That flag is the user's
     own statement that the slot is not work, and unlike a keyword list it needs
     no maintenance. Observed 2026-08-26: four grocery-courier slots carried it
     and had matched no keyword.
   - **mark, but do not drop, a solo event**: no attendee other than the user
     *and* the user is the organizer → add `'solo?'` to `origin_marks`. A block
     of focused solo work looks exactly like this, so dropping it would lose
     real time; but so does everything personal that was never meant as work.
     On the same day the Free flag caught the courier slots it did **not** catch
     a 150-minute cinema showing — that event carries no `transparency` field at
     all, it is a plain busy event, and `kino` was in nobody's keyword list. It
     would have been proposed as billable. (A note added here on 2026-08-26
     claimed the Free flag covered that case; it did not — the two events were
     conflated.) Measured over the same month, "no other attendee and organizer
     is self" separated every unambiguous work event from every unambiguous
     personal one, 6 for 6 — which is why it is a prompt, not a filter.
   - drop events whose title matches any `exclude_keywords` (case-insensitive
     substring). The default list is deliberately whole-word-ish: matching is a
     plain substring test, so a short token added here (`pto`, `ooo`, `off`)
     silently eats unrelated events — `pto` hits "symptom review", `off` hits
     "offsite". When adding keywords, prefer the longer form.
   Each surviving event → a `candidate_block` with `source='calendar'`,
   `start`/`end` = event start/end (local), `title` = event summary,
   `project_hint` = null (resolved during project pairing, step 5), `origin_marks=[]`,
   `raw_messages_ts=[]`.
   If the MCP is absent, append a one-line warning "Kalendář nedostupný —
   schůzky vynechány." and skip.

   **C. Confirmatory sources** (git always; GitHub/ClickUp if enabled+present):

   - **git** (local, free): **not just the current repo** — that is almost
     never where the window's work happened. Measured 2026-08-26 from a
     checkout of this very collection: the current repo held **0** in-window
     commits while 131 existed across seven others, so the whole source
     contributed nothing. Derive the repo list from the work you already found:
     every session block's decoded working directory (step 3A), resolved to its
     enclosing git repo. Add any configured root on top. Skip paths with no
     `.git` and say how many you skipped, so a missing local clone reads as
     "unconfirmed", never as "no work". Then in each repo collect commits
     authored by the user in the window:
     `--since`/`--until` filter on the **commit** date, while `%aI` is the
     **author** date — the one that says when the work happened, and the one a
     timesheet wants. Rebasing and amending move the commit date forward and
     leave the author date alone, so the two drift apart (7 of the commits in
     one repo's four-day window on 2026-08-26). Filtering on one and recording
     the other lets commits land outside the window: a commit authored at
     `2026-07-27 02:00` surfaced in a reconcile starting `2026-07-28`. Git has
     no author-date range filter, so **over-fetch on commit date and filter on
     `%aI` yourself**. A commit's author date effectively never postdates its
     commit date, so padding `--since` backwards a little (clock skew) and
     dropping `--until` entirely is enough:
     ```bash
     git log --all --since="<since> -7 days" \
       --author="$(git config user.email)" \
       --pretty='%h|%aI|%s' 2>/dev/null \
     | awk -F'|' -v s="<since_iso>" -v u="<until_iso>" '$2 >= s && $2 <= u'
     ```
     Each surviving commit is a confirmatory hit with a timestamp, its repo
     name, and subject. Not a block yet — see step 5.
   - **GitHub** (probe `select:mcp__github__search_pull_requests`): search PRs
     reviewed/merged and issues closed by
     `effective_config.sources.github.username` in the window. Each is a
     confirmatory hit (timestamp = merged/review time, subject = title).
   - **ClickUp** (probe `select:mcp__plugin_ntit-common_clickup__clickup_filter_tasks`):
     **there is no updated-date filter** — that tool ranges only over
     `due_date_*` and `date_closed_*`, so "tasks updated by the user in the
     window", which this step used to ask for, cannot be expressed and an agent
     rediscovers that every run. Use `date_closed_gt`/`date_closed_lt` for tasks
     the user closed in the window, and `clickup_get_task_comments` on the tasks
     you already have in hand for their comment timestamps. Both are
     confirmatory hits (timestamp = close/comment time, subject = task name).
     Anything needing "was this touched in the window" is out of reach here —
     say so once rather than fetching everything and filtering client-side.
   Absent MCP → warn once, skip that source.

   **D. Work that never ran through an agent** (ChatGPT/Gemini sessions, manual
   work, phone calls): sources A–C see none of it, so a window that looks empty
   may just be work done elsewhere. Before concluding "nothing to reconcile",
   ask whether the period included such work; when it did, reconstruct it from:

   - **Artifacts on disk.** Anything downloaded from a chat UI or produced by
     hand carries a creation time. On macOS read birth time, elsewhere mtime;
     each file is a timestamped anchor proving work happened at that moment.
     ```bash
     python3 -c "
     import os, datetime, pathlib, sys
     for f in sorted(pathlib.Path(sys.argv[1]).rglob('*')):
         if f.is_file() and f.name not in ('.DS_Store',):
             st = f.stat(); b = getattr(st, 'st_birthtime', st.st_ctime)
             print(f'{datetime.datetime.fromtimestamp(b):%Y-%m-%d %a %H:%M}  {f}')
     " <dir>
     ```
     Cluster anchors that fall close together into one block; a cluster's span
     is a *lower bound* on the block, never its length — the thinking around it
     leaves no file.
   - **IM history** (Slack/ClickUp DMs with whoever commissioned the work).
     Messages sent around the artifacts date the block from the other side and
     often state the work's substance. Best of all, the user's own past
     estimates ("cca 2 h, z toho 1 h už mám za sebou") are the strongest
     calibration available — prefer them over your own reconstruction.

   Blocks from this source get `source='offline'`, `origin='anchored'`, and a
   `minutes` estimate the user MUST confirm — the anchors fix *when*, never
   *how long*.

4. **Estimate a duration for each block.** The estimate is always a *default to
   hand-edit*, never authoritative.

   **AI blocks — gap-capping.** `raw_messages_ts` is one local day's slice of
   one session, already clipped to the window by step 3A — never a whole file.
   Sorted; UTC is fine here since we only take differences. With
   `G = gap_threshold_min`, `E = edge_pad_min`:

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

   **Sanity gate — per block AND per day.** Per-day splitting bounds a block at
   24 h, which is not the same as plausible: an agent left running unattended
   produces a dense timestamp stream with no gap long enough to break, and
   gap-capping happily sums it. Presence in the log proves the agent was
   working; it does not prove the user was.

   - **Per block:** over ~6 h in one day → mark `'long?'` in `origin_marks`.
   - **Per day:** once every block exists, sum them per local calendar day —
     **AI blocks only**. A meeting is wall-clock time someone else can vouch
     for; folding calendar hours into the gate would raise the threshold on
     exactly the days that are legitimately full of meetings. A
     day over ~10 h is implausible on its own, and the per-block gate will not
     catch it — the inflation usually arrives as dozens of small blocks across
     parallel repos, none individually long. Mark every block of such a day
     `'day?'`. Measured on 2026-08-26, four July days reconstructed to 19–30 h
     each with no single block above 6 h.

   The per-day gate matters most where the coverage diff (step 7) cannot help.
   Where the tracker already holds a normal day's entries, that diff absorbs
   almost all of the inflation on its own — 30.3 h reconstructed against 10.6 h
   logged proposed only 1.6 h. The exposure is the thinly-logged day: 12.6 h
   reconstructed against 1.0 h logged proposed 8.7 h, and a reconcile targets
   exactly those days. So treat `'day?'` as the backstop for the case the diff
   is blind to, not as a routine warning.

   **Calendar blocks:** `minutes` = exact `(end - start)` rounded to
   `round_to_min` (no gap-capping — a meeting is contiguous). Set
   `origin='calendar-exact'`.

   **Origin marks** drive the review display (step 8). The label says where the
   number came from and how much to trust it; the third column is only how that
   reads in `cs`:
   | `origin` | Label means | Rendered (`cs` example) |
   |----------|-------------|-------------------------|
   | `ai-gapcapped` | estimate, from session gaps | `~<m>m (AI, gap-capped)` |
   | `calendar-exact` | exact, from a meeting's length | `<m>m (kalendář)` |
   | `commit-only` | **no duration known — user must supply one** | `? (jen commit — DOPLŇ ČAS)` |
   | `manual` | supplied by the user | `<m>m (ručně)` |

5. **Pair every block to a project** (same mechanism as `/tracker-start` and
   `/tracker-log-entry`):
   - Fetch active Toggl projects (`mcp__toggl__toggl_list_projects`, or the
     API key from `~/.claude/plugins/session-tracker/config.json` as fallback).
   - For AI blocks: `project_hint` is the whole decoded working directory. Walk
     its segments **right to left** and take the first that matches a project
     name case-insensitively; on a hit set `project`. Do not just take the last
     segment — measured against a live tree, that yields `13` for
     `…/vault-platform/.claude/worktrees/INFRA-13` and `2026` for
     `…/krato-cluster-2026`, neither of which is a project. Skip segments that
     are purely numeric or are known scaffolding (`.claude`, `subagents`,
     `src`). The repository name — the segment right after the
     `<host>/<owner>/` prefix — is simply the last segment to try, **not** a
     fallback that assigns anything: if it also fails to match, the block has no
     project. For Calendar blocks with no hint, leave `project=null` for now.
   - **A worktree never names the project — the repository above it does.** On
     a path containing `/.claude/worktrees/`, truncate it there and match only
     the part to the left; the worktree's own name is a branch label chosen for
     a ticket or a topic and means nothing about billing. Measured 2026-08-26:
     `…/payroll-system-PMA/.claude/worktrees/monitoring` resolved to the Toggl
     project `Monitoring` — a different client's — for 12 blocks, and because
     the match *succeeded* no `'project?'` gate fired to surface it. Skipping
     the literal token `worktrees` is not enough; the segment after it has to go
     too.
   - **Matching rule.** Take the project name's last `/`-separated part as its
     *key*. Normalise key and segment alike: lowercase, and collapse every `-`,
     `_` and `.` to one separator character. A segment matches when it
     **equals** the key, or when the key is its **trailing separator-delimited
     component**. Nothing else counts.
     - `www-hunting-shop-cz` ≡ the key of `www.hunting-shop.cz` → equal, match.
     - `payroll-system-PMA` ends with the component `pma`, the key of
       `NTIT/PMA` → match.
     - `webserver` does **not** match the key `server`: no separator precedes
       it, so it is not a component. Requiring that boundary is the whole
       point — a plain substring test makes the segment `cz` match every
       `*.cz` project and `server` match three at once.
     An earlier wording said "equality … after replacing `-`/`_` with nothing"
     and then gave `payroll-system-PMA` → `NTIT/PMA` as an example of it. Those
     contradict — folding yields `payrollsystempma`, which equals nothing — and
     read literally it left **96 of 97 blocks unattributed on a live run**,
     including 31 h of the very project the example names. If two projects match
     equally well, treat it as no match and let step 8 ask.
   - **No match means no project — never a configured default.** Set
     `project=null` and add `'project?'` to `origin_marks`; the review (step 8)
     then forces the user to pick before the block can be approved. Do **not**
     fall back to `sources.toggl.project_id` or `default_project_id`: those name
     the project a *timer* starts on, which is a different question from where
     unattributed reconstructed time belongs. Measured on a live config on
     2026-08-26, that fallback put 55.4 of 68.4 proposed hours onto a billable
     client project — 14.6 h of them from a personal repo — and because the
     configured id was non-null, the `'project?'` branch below was unreachable,
     so nothing ever surfaced for review. A reconcile writes to a timesheet
     someone bills from; an unanswered question is cheap there and a silent
     default is not. Bulk-assigning a whole group to one project stays one
     keystroke away in step 8.
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
   - **Toggl only serves recent history** — `toggl_get_time_entries` rejects a
     `start_date` older than roughly three months with `"start_date must not be
     earlier than <date>"`. When the window starts before that cutoff, say so
     instead of reporting an empty busy-map as "nothing logged". A cheap
     cross-check for a project that did not exist yet: `GET
     /api/v9/workspaces/<wid>/projects/<pid>` returns `created_at`, which caps
     how far back entries could possibly go.
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
     intervals. Also build an **all-projects per-day bucket** — the union of
     every entry that day regardless of project.
   - **A block with `project=null` compares against the all-projects bucket for
     its day**, never against an empty one. Since step 5 stopped applying a
     default, unmatched blocks are the common case, not the exception: bucketing
     them by a project they do not have means no existing entry can ever mask
     them and every one is proposed as missing. Measured 2026-08-26, that is not
     a small error — a four-day window already carrying 33.8 h of tracked time
     produced **zero** COVERED blocks and proposed 66.6 h on top. A block whose
     project is unknown is a block whose overlap is unknown too; compare it
     against everything logged that day, and let step 8 refine it once the user
     supplies the project.
   - For each candidate block, split it per calendar day if it crosses midnight,
     then measure against its bucket — `(project, day)` when the project is
     known, the all-projects day bucket when it is not.

     **Do not divide wall-clock overlap by the gap-capped estimate.** They are
     different units: `block_minutes` is gap-capped and routinely a fraction of
     the block's `[start, end]` span, so that ratio exceeds 1.0 for any block
     with long internal pauses (23 of 89 blocks on a live run) and
     `block_minutes - overlap` goes negative. Scaling by the covered *fraction*
     of the span is no better — it assumes activity is spread evenly across the
     span, and on the same window it proposed 29.2 h on top of a period that
     already held 33.3 h.

     Instead **re-run the step 4 gap-capping over just the timestamps that fall
     outside the busy intervals**. That measures the un-logged work directly
     rather than inferring it, needs no density assumption, and is bounded in
     `[0, 1]` by construction:
     ```
     outside       = [t for t in raw_messages_ts if t not inside any busy interval]
     minutes_left  = gap_capped(outside)        # same G and E as step 4
     coverage      = 1 - minutes_left / block_minutes
     ```
     For a Calendar block there are no timestamps to re-cap — it is contiguous,
     so `minutes_left` is its span minus the busy overlap.
   - Decide with `coverage_covered` (0.9) and `coverage_missing` (0.1):
     - `coverage >= coverage_covered` → **COVERED**: drop the block from the
       proposals; it still counts toward the summary line and the roll-up below.
     - `coverage_missing <= coverage < coverage_covered` → **PARTIAL**: keep,
       with proposed `minutes = minutes_left`; label
       `~<m>m (doplněk k <block_minutes - minutes_left>m)`.
     - `coverage < coverage_missing` → **MISSING**: keep whole block; label
       `~<m>m (chybí)`.
   - `commit-only` blocks (`minutes=null`) skip coverage math (nothing to
     measure) and always appear, flagged to fill in.
   - **COVERED means "already logged", not "impossible".** When a block is
     buried under an entry for a *different* project, the overlap may be real
     parallel work — common when an agent runs unattended on one project while
     the user works another. Attention splits across parallel work, so a block
     approved as an overlap usually deserves fewer minutes than its anchors
     span.

     **How to surface those without drowning the review.** An earlier version of
     this step said both "drop the block, count it for the summary only" and
     "do not silently drop those, show the colliding entry" — fine while
     cross-project collisions were an occasional edge case, but once unmatched
     blocks compare against the all-projects bucket, *every* COVERED block is
     covered by some other project's entry, so the second rule would fire on all
     of them (32 blocks, 50 h of anchors, on a live run). Print a **one-line
     roll-up per (project, day)** — `pokryto: <N> bloků, <Σ>m, kolidují s
     <projekt(y)>` — never a row each, and let the user expand a day on request.
     Reserve the full colliding-entry detail (including its `at` field, which
     reveals whether the entry was measured live or entered retrospectively as
     one lump — the latter is far weaker evidence) for a day the user opens.
   - ClickUp coverage is bucketed per (project, day), not per-task, so
     same-project same-day ClickUp time can mask a distinct task's block — the
     `reconciled_tag` idempotency check (step 9) is the finer backstop.

8. **Review — the heart of "confirm".** First print a **grouped table**
   (by project, then day), each row: proposed minutes + origin label +
   `origin_marks`. Order groups by total proposed minutes, largest first, and
   put the unattributed (`project=null`) group **first** rather than leaving it
   unplaced — it is where the user's attention is actually needed, and it is
   usually the biggest. Sorting it last put a single 5-minute row at the top of
   a live run and buried a 28-row group beneath it. End with a summary line: `N návrhů (Σ h) · K pokrytých skryto
   · M bez času`. Example:

   ```
   Projekt X — po 2026-06-02
     ~90m  fix auth bug        (AI, gap-capped)  [git✓ 3c, PR#42✓]
      35m  code review          (doplněk k 25m)   [GitHub✓]
      60m  Sprint planning      (kalendář)
      ?    hotfix deploy         (jen commit — DOPLŇ ČAS)
   Souhrn: 12 návrhů (8.5 h) · 5 pokrytých skryto · 1 bez času
   ```

   Then approve **in batches**, one group (project/day) at a time, offering four
   options — referred to below by their function, and rendered in
   `config.language` (`cs`: **Vše / Vybrat / Přeskočit / Upravit časy**):
   - **all** → approve every item in the group.
   - **select** → list the group's items so the user picks a subset.
   - **skip** → approve nothing in this group.
   - **edit** → let the user overwrite `minutes` (and optionally
     `project`/`title`) on a chosen item.
   - **A block with `minutes=null` (the `?` items) CANNOT be approved until the
     user supplies a duration** — force the prompt; never write a `null`.
   - **A block with `'project?'` in `origin_marks` CANNOT be approved until the
     user picks a project.** Since step 5 no longer applies any default, a
     month's worth of personal-repo work can arrive as dozens of such blocks —
     so when a group holds more than one, **offer to set the project for the
     whole group in one answer** (with the per-block path shown) before falling
     back to asking block by block. The gate exists to stop a silent
     misattribution, not to charge a keystroke per row.
   - **A block marked `'long?'` (over ~6 h in one day, step 4) is shown with its
     span and message count before approval**, so the user can tell a genuinely
     long day from an agent that ran unattended while they were elsewhere. It
     can be approved as-is, but never silently as part of a bulk **all**.
   - **A block marked `'solo?'` (step 3B: a calendar event with no other
     attendee, organised by the user) is shown with its time of day and
     location before approval.** Solo focus time and a cinema ticket are the
     same shape to every automatic filter; only the user can tell them apart.
   - **A day whose blocks carry `'day?'` (over ~10 h reconstructed, step 4) is
     announced once at the head of that day's group** with its reconstructed
     total and what the tracker already holds for it, before any of its rows
     are offered. Bulk **all** on such a group asks for confirmation first.
   - **If `sink.target` includes `clickup`:** a ClickUp time entry must attach to
     a `task_id` (AI sessions / commits / meetings have no inherent ClickUp
     task). So for each block the user approves for a ClickUp write, prompt them
     to pick the target ClickUp task — offer a shortlist from
     `clickup_filter_tasks` (filtered by `assignee=<sources.clickup.member_id>`,
     active), or let them paste a task ID / custom ID (e.g. `DEV-1234`). Store
     it as the block's `clickup_task_id`. A block **CANNOT** be approved for a
     ClickUp write without a `clickup_task_id`. (Toggl writes need no task —
     this gate applies only to the ClickUp sink.)
   - Choosing **all** approves every item in the group but does **not**
     bypass the gates above: any gated item (a `?` duration, a `project?`
     mark, or a required `clickup_task_id`) still forces its per-item prompt
     — **all** cannot manufacture a missing value.
   - Offer an **"add a manual item"** option (`cs`: "+ přidat ruční položku")
     for work no source can see, such as a phone call: ask start, duration,
     project, description → append as `source='manual'`, `origin='manual'`,
     fully specified.
   Everything the user OKs goes into `approved`. Nothing else is written.
   If `dry_run`, stop here after printing what *would* be written, grouped like
   the summary; write nothing.

9. **Write the approved entries.** For each item in `approved`, write to every
   tracker in `sink.target` (`toggl`, `clickup`, or `both`).

   **Safety (identical to the `tracker-log-entry` skill):** never put the API
   key in argv. Read it into a shell variable and pass it via a stdin-fed config
   / header, so it stays out of `ps` and transcripts. Do all time conversion
   with `date`, never by hand.

   **Toggl** — `POST /api/v9/workspaces/<wid>/time_entries`. Use the **exact
   auth pattern proven in the `tracker-log-entry` skill**: Basic auth via
   `curl --config -` fed on stdin (so the key stays out of argv), with the
   credential line `user = "<token>:api_token"`. `duration` is
   `round(minutes) * 60` (seconds; `minutes` is the approved per-item value).
   If the block's `end` is null (commit-only or manual items filled in without
   an end time), derive it with `date` as `start + duration` before building
   the payload. Body carries `start` (UTC ISO), `stop` (UTC ISO, the derived or
   original end), `duration` (seconds), `description`, `project_id` (only when
   resolved), `billable` (from `sink.billable`), and `tags` including
   `sink.reconciled_tag` — mirroring `/tracker-log-entry`'s Toggl body:
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
