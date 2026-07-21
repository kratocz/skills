---
name: work-standup
description: Standup recap — what you actually worked on since the last standup, pulled from Toggl time entries + git commits + GitHub reviews/merges and grouped into a report you can paste into the standup channel. Use when the user says "/work-standup", "standup", "stand-up status", "co jsem dělal od minula", "co jsem udělal od posledního stand-upu", "recap since last standup".
argument-hint: [--since YYYY-MM-DD[THH:MM]] [--project <name>]
version: 0.3.0
allowed-tools: Read, Bash, ToolSearch, AskUserQuestion, mcp__toggl__toggl_get_time_entries, mcp__toggl__toggl_list_projects, mcp__github__search_issues, mcp__github__search_pull_requests, mcp__github__list_commits
---

# Work Standup

Retrospective status for a standup: **what did I actually do since last time?**

This is the backward-looking sibling of the daily-work triad. It answers a
different question than the others, from different sources:

| Skill | Question | Sources | Window |
|-------|----------|---------|--------|
| `/work-start`  | What should I do? | open tasks / PRs | forward |
| `/work-status` | What changed? | diff vs morning snapshot | since AM |
| `/work-end`    | What did I close today? | diff vs morning snapshot | today |
| **`/work-standup`** | **What did I do since last time?** | **Toggl + git + GitHub reviews/merges** | **since last standup** |
| **`/work-reconcile`** | **What did I do but not log — and fill it in** | **Toggl/ClickUp write** | **back (write)** |

The point of pulling **Toggl** is that a lot of real work — ops firefighting,
code reviews, meetings — leaves *no commit*. Time entries capture it; git and
GitHub alone would under-report a review-heavy or ops-heavy stretch.

## Arguments

- `--since YYYY-MM-DD[THH:MM]` (optional): start of the recap window. If
  omitted, the skill derives a default (see step 2).
- `--project <name>` (optional): restrict to a single Toggl project by name
  (case-insensitive substring). Overrides the config's default project filter
  for this run.

## Steps

1. **Load effective config** — identical to `/work-start` step 1:

   a. Read global config `~/.claude/plugins/work/config.json` with the Read
      tool. If missing, stop with: "Žádná konfigurace work pluginu. Spusť
      `/work-setup` nejdřív." and return.

   b. Locate the per-project override: build the slug from `pwd` (absolute
      path, `/` → `-`, leading `-`) and try to read
      `~/.claude/projects/<slug>/memory/work_config.md`. If it has a fenced
      ```json``` block, parse it and deep-merge onto the global config (arrays
      replace, scalars override). Invalid JSON → warn and skip the override.

   The merged result is `effective_config`. Read `effective_config.language`
   (default `"cs"`); render all user-facing prose in it. Keep proper nouns,
   code identifiers, URLs, and durations unchanged.

2. **Determine the recap window `[since, now]`**:

   - `now` = current time. Get UTC now:
     ```bash
     date -u +%Y-%m-%dT%H:%M:%SZ
     ```
   - `since`:
     - If `--since` was passed, use it (interpret a bare date as `T00:00`
       local).
     - Else use `effective_config.standup.default_window` if set. Supported
       values:
       - `"last_workday_noon"` (default): the most recent **previous** weekday
         at 12:00 local. If today is Mon, that's Fri noon; Tue–Fri → yesterday
         noon; weekend → Fri noon. This matches a daily standup that skips the
         weekend.
       - `"24h"` / `"48h"` / `"72h"`: now minus that many hours.
       - a bare `YYYY-MM-DD`: that calendar day at 00:00 local.
     - If nothing is configured, default to `"last_workday_noon"`.

     Compute `last_workday_noon` on macOS:
     ```bash
     # day-of-week: 1=Mon .. 7=Sun
     dow=$(date +%u)
     case "$dow" in
       1) back=3 ;;   # Mon → Fri
       7) back=2 ;;   # Sun → Fri
       6) back=1 ;;   # Sat → Fri
       *) back=1 ;;   # Tue-Fri → yesterday
     esac
     date -v-${back}d -v12H -v0M -v0S +%Y-%m-%dT%H:%M:%S   # local time
     # Linux: date -d "12:00 $back days ago" +%Y-%m-%dT%H:%M:%S
     ```

   Echo the resolved window to the user before fetching, e.g.
   "Rekapituluji od **<since>** do teď." so an unexpected default is visible.

3. **Resolve git identity** (best-effort; used for `git log` + GitHub author):
   ```bash
   git config user.name
   git config user.email
   ```
   Use `effective_config.sources.github.username` for GitHub queries (the
   GitHub login), and the git `user.name`/`user.email` for `git log --author`.

4. **Fetch all enabled sources — IN PARALLEL**:

   Make every fetch call in a SINGLE message (multiple tool_use blocks). Before
   calling an MCP source, verify it's available with `ToolSearch`
   (`select:<a representative tool>`); if unavailable, append a warning and
   skip that source (see the availability table in `/work-start` step 2).

   **Toggl** (if `effective_config.sources.toggl.enabled`, default on):

   - Preferred path — MCP. Verify with `select:mcp__toggl__toggl_get_time_entries`.
     Call `mcp__toggl__toggl_get_time_entries` with:
     ```json
     { "start_date": "<since date, YYYY-MM-DD>", "end_date": "<today, YYYY-MM-DD>",
       "project_id": <effective_config.sources.toggl.project_id if set, else omit> }
     ```
     The MCP result is already hydrated (`project_name`, `client_name`,
     `duration_seconds`, `tag_names`, `billable`) — no manual project lookup
     needed.
   - Filter the returned entries to the window `[since, now]` by each entry's
     `start` (the MCP `start_date` is date-granular, so an entry from the
     morning of the `since` day that predates `since`'s time-of-day must be
     dropped).
   - If `--project` was passed (or `project_id` is unset but
     `sources.toggl.project_name` is), keep only entries whose `project_name`
     matches (case-insensitive substring).
   - Optionally, if `sources.toggl.billable_only` is true, keep only
     `billable == true` entries.
   - **Fallback if the Toggl MCP server is absent** but
     `effective_config.sources.toggl.api_key` (or `session-tracker`'s config)
     is available: read the key into a shell var (never echo it) and pass it
     via stdin `--config -`, never on the command line (keeps the token out of
     `ps` / shell history — same pattern as `session-tracker`'s `/log-entry`):
     ```bash
     KEY=<config.toggl.api_key read into a shell variable, not echoed>
     printf 'user = "%s:api_token"\n' "$KEY" | curl -sS --config - \
       "https://api.track.toggl.com/api/v9/me/time_entries?start_date=<since ISO>&end_date=<now ISO>"
     ```
     then hydrate project names via
     `GET /workspaces/<workspace_id>/projects`. Prefer the MCP path; only fall
     back when MCP is unavailable. If neither is available, warn and treat
     Toggl as empty — the recap degrades to git+GitHub only.

   **git** (always, if inside a git repo — check `git rev-parse --git-dir`):
   ```bash
   git log --all --since="<since ISO>" \
     --author="<git user.name>" \
     --pretty=format:'%h%x09%cI%x09%s' --date-order
   ```
   Also capture commits by the user's email (some commits attribute differently):
   run a second `--author="<user.email>"` pass and union by short-SHA. In a
   monorepo where only some paths are relevant, honor
   `effective_config.sources.git.paths` (a list of pathspecs) by appending
   `-- <paths>` if set.

   **GitHub** (if enabled). Substitute the configured `username` for `@me`.
   If `effective_config.sources.github.repos` is set, OR-join
   `repo:<owner/name>` filters and AND them into each query. Run in parallel:
   - Merged PRs I authored:
     `mcp__github__search_pull_requests` with
     `{ "q": "is:pr author:<username> merged:>=<since date> <repo_filter>" }`
   - PRs I reviewed:
     `mcp__github__search_pull_requests` with
     `{ "q": "is:pr reviewed-by:<username> updated:>=<since date> <repo_filter>" }`
   - PRs I'm otherwise involved in (opened/commented, still open):
     `mcp__github__search_pull_requests` with
     `{ "q": "is:pr is:open involves:<username> updated:>=<since date> <repo_filter>" }`
   - Issues I closed:
     `mcp__github__search_issues` with
     `{ "q": "is:issue assignee:<username> closed:>=<since date> <repo_filter>" }`

   If any call fails, append a warning and treat that source's contribution as
   empty.

5. **Normalize and de-duplicate**:

   Build these lists, keyed for cross-referencing so the same work isn't
   double-counted between narratives:

   - `time_entries` — normalized Toggl rows: `{ description, project_name,
     client_name, minutes: round(duration_seconds/60), billable, tag_names,
     start }`. Sum `minutes` into `total_minutes` (and a per-tag / per-project
     breakdown if useful).
   - `commits` — `{ sha, date, subject }`, de-duplicated by short-SHA across
     the name/email passes.
   - `prs_merged`, `prs_reviewed`, `prs_open_involved`, `issues_closed` —
     `{ repo, number, title, url }` each. A PR that appears in both
     `prs_merged` and `prs_reviewed` belongs in `prs_merged` (you don't review
     your own merge for standup purposes) — remove it from `prs_reviewed`.

   Classify the Toggl entries into buckets for the narrative using their
   `tag_names` and description keywords (best-effort, don't be rigid):
   - tag `code-review` or description starting `CR ` → **Code reviews**
   - tag `devops`/`ops`/`incident`, or description mentioning
     incident/outage/fix/deploy → **Ops / incidents**
   - everything else → **Development / other**

6. **Render the recap** in the configured language (Czech default). Structure
   it so it's paste-ready for a standup, most-important first:

   ```markdown
   ## 🧭 Standup recap — <since as DD. MM. HH:MM> → teď

   _Projekt: <project filter or "vše">, trackováno: **<Hh Mm>** celkem_

   ### 🔥 Ops / incidenty
   - <entry.description or synthesized line> — <minutes>m
   ...

   ### 👀 Code reviews
   - <PR/CR line> — <minutes>m  ·  <url if PR>
   ...

   ### 🛠️ Vývoj / commity
   - <subject> (`<sha>`) — <date>
   ...

   ### ✅ Mergnuté PR / uzavřené issues
   - <repo>#<number> <title> — <url>
   ...

   ### ⏭️ Zůstává otevřené (carry-over)
   - <repo>#<number> <title> (<label if known>) — <url>
   ...
   ```

   Rules:
   - Merge Toggl entries and GitHub items that describe the same work into one
     line where obvious (e.g. a `CR PR #76` Toggl entry + the #76 PR link →
     one bullet with both the time and the URL). Prefer showing time from
     Toggl and the link from GitHub.
   - Omit any section that would be empty.
   - Keep durations from Toggl authoritative; don't invent time for
     commit-only or review-only items that weren't tracked — list them without
     a duration.
   - The "carry-over" section is `prs_open_involved` (open PRs you're on) plus
     anything the user's per-project notes flag as pending. This is the
     forward hook the standup usually ends on.

7. **Offer to copy / save** (optional): after printing, ask via
   AskUserQuestion whether to also (a) copy the raw markdown to the clipboard
   (`pbcopy` on macOS), or (b) do nothing. Do not post anywhere automatically —
   posting to a channel is the user's call.

## Edge cases

- **Not in a git repo**: skip the git source silently; run Toggl + GitHub only.
  (Standup recaps are sometimes run from a scratch dir.)
- **Toggl MCP absent and no api_key**: warn once, produce a git+GitHub-only
  recap, and note in the output that time totals are missing.
- **Empty window (nothing tracked, no commits, no PRs)**: render
  "Od posledního stand-upu (<since>) není žádná zaznamenaná aktivita na
  tomto projektu. Zkontroluj, jestli sedí `--since` a filtr projektu." — do
  not pad with empty sections.
- **Multiple projects tracked in the window** and no `--project`/config
  filter: show all, grouped by `project_name`, with a per-project time
  subtotal, so a mixed day is still legible.
- **Window longer than ~2 weeks**: still works, but warn that a long window
  makes the "since last standup" framing misleading — suggest a tighter
  `--since` for the next run.
- **No target project configured**: the recap covers *all* Toggl projects.
  That's a valid default; mention it so the user knows nothing was filtered
  out.
