---
name: work-start
description: Morning briefing — pull tasks/PRs from configured sources (Todoist, ClickUp, GitHub, Calendar), score them, and print top N with categories. Use when the user says "/work-start", "morning briefing", "co dneska řešit", "what's on my plate today".
argument-hint: [--fresh]
version: 0.3.0
allowed-tools: Read, Write, Bash, ToolSearch, mcp__claude_ai_Todoist__find-tasks, mcp__claude_ai_Todoist__find-tasks-by-date, mcp__github__search_issues, mcp__github__search_pull_requests, mcp__plugin_ntit-common_clickup__clickup_filter_tasks, mcp__claude_ai_Google_Calendar__list_events
---

# Work Start

Morning briefing across all configured task and code review sources.

## Arguments

- `--fresh` (optional): if passed, treat any existing snapshot as stale and always re-fetch. (For v1 the skill always re-fetches, so this is informational; it's a hook for future caching.)

## Steps

1. **Load effective config**:

   a. Read global config: `~/.claude/plugins/work/config.json` with the Read tool.

   If the file doesn't exist, stop with this message in Czech (or English if user prefers): "Žádná konfigurace work pluginu. Spusť `/work-setup` nejdřív." Then return — do not proceed.

   b. Locate per-project override:
   ```bash
   pwd
   ```
   Build slug as in `/work-setup` (absolute path with `/` → `-`, leading `-`). Try to read `~/.claude/projects/<slug>/memory/work_config.md` with the Read tool.

   If the file exists:
   - Find the first fenced ` ```json ... ``` ` block in the file.
   - Parse the JSON. If parse fails, print warning "⚠️ Per-project override `work_config.md` má nevalidní JSON. Pokračuju s globálním configem." and skip override.
   - Otherwise, deep-merge the override onto the global config:
     - Objects: recursively merge keys. Override values replace global values.
     - Arrays: replace entirely (override array replaces global array).
     - Scalars: override replaces global.

   The merged result is `effective_config`. Use it for the rest of the steps.

2. **Verify enabled MCP sources**:

   Initialize an empty list `warnings = []`.

   For each source in `effective_config.sources` where `enabled == true`:

   Use ToolSearch with `select:<a representative tool from the mcp_prefix>` to check availability. Use the same query table as `/work-setup` step 2:

   | Source | ToolSearch query |
   |---|---|
   | todoist | `select:mcp__claude_ai_Todoist__find-tasks` |
   | github | `select:mcp__github__search_pull_requests` |
   | clickup | `select:mcp__plugin_ntit-common_clickup__clickup_filter_tasks` |
   | google_calendar | `select:mcp__claude_ai_Google_Calendar__list_events` |

   If unavailable, mark the source as skipped, append to warnings:
   ```
   ⚠️ Source `<name>` je povolený v configu, ale MCP server není v této session. Přeskakuji. Spusť /work-setup pro aktualizaci, nebo zkontroluj ~/.claude.json.
   ```

   Continue with the remaining available sources.

3. **Fetch from each available source — IN PARALLEL**:

   Make ALL MCP fetch calls in a SINGLE message (multiple tool_use blocks in parallel). This is critical for speed.

   **Todoist** (if enabled):
   - Get today's date: `date +%Y-%m-%d`
   - Call `mcp__claude_ai_Todoist__find-tasks-by-date` with arguments `{ "dateFrom": "1900-01-01", "dateTo": "<today>" }` to get overdue + today's tasks. (Past date catches overdue; future date is exclusive.)
   - Call `mcp__claude_ai_Todoist__find-tasks` with arguments `{ "filter": "p1 | p2" }` to get all p1/p2 tasks regardless of due date.

   **GitHub** (if enabled):
   - Substitute `effective_config.sources.github.username` for `@me` in queries (GitHub MCP may not resolve `@me`).
   - Build base query — if `effective_config.sources.github.repos` is set (per-project override), AND-prefix each query with `repo:<owner/name>` for each repo in the list, joined with OR — e.g. `(repo:owner/a OR repo:owner/b)`. Otherwise no repo filter.
   - Call `mcp__github__search_issues` with `{ "q": "is:open is:issue assignee:<username> <repo_filter>" }`
   - Call `mcp__github__search_pull_requests` with `{ "q": "is:open review-requested:<username> <repo_filter>" }`
   - Call `mcp__github__search_pull_requests` with `{ "q": "is:open draft:false author:<username> <repo_filter>" }`

   **ClickUp** (if enabled):
   - Call `mcp__plugin_ntit-common_clickup__clickup_filter_tasks` with arguments that filter to the user's member_id (from `effective_config.sources.clickup.member_id`), open status, and due_date_lt = tomorrow midnight (covers overdue + today). Refer to the ClickUp MCP tool's exact schema for the argument shape.

   **Google Calendar** (if enabled):
   - Get current time and 12h-later time:
     ```bash
     date -u +%Y-%m-%dT%H:%M:%SZ
     date -u -v+12H +%Y-%m-%dT%H:%M:%SZ  # macOS; on Linux: date -u -d '+12 hours' +%Y-%m-%dT%H:%M:%SZ
     ```
   - Call `mcp__claude_ai_Google_Calendar__list_events` with `{ "timeMin": "<now>", "timeMax": "<now+window_hours>", "calendarId": "primary" }`.

   Collect all results into raw per-source response variables: `todoist_raw`, `github_raw`, `clickup_raw`, `calendar_raw`.

   If a call fails (returns error or empty array due to auth/network), append a warning and treat that source's contribution as empty:
   ```
   ⚠️ Fetch z `<source>` selhal: <error message>. Přeskakuji tento zdroj v dnešním briefingu.
   ```

4. **Normalize items to common shape**:

   Combine all raw responses into a single list `items`, each shaped as:

   ```json
   {
     "source": "todoist" | "github" | "clickup" | "google_calendar",
     "id": "<source-specific identifier>",
     "title": "<human-readable title>",
     "url": "<web URL or null>",
     "priority": "p1" | "p2" | "p3" | "p4" | null,
     "due": "<ISO 8601 date or datetime, or null>",
     "assigned_at": "<ISO 8601 datetime of when item entered queue, or null>",
     "type": "task" | "issue" | "pr_review" | "pr_mine" | "calendar_event",
     "raw": <original object, kept for debugging>
   }
   ```

   **Normalization rules per source:**

   **Todoist tasks** (from both `find-tasks-by-date` and `find-tasks`):
   - Deduplicate by task ID (a task may appear in both responses).
   - `source = "todoist"`, `type = "task"`.
   - `id = task.id`, `title = task.content`, `url = task.url` (if present), `due = task.due.date` (or null).
   - `priority`: Todoist `priority` is integer 1–4 where 4=p1 (highest) and 1=p4 (default). Map: `4 → "p1"`, `3 → "p2"`, `2 → "p3"`, `1 → "p4"`. If field missing, treat as `"p4"` (lowest).
   - `assigned_at`: use `task.added_at` or `task.created_at` (whichever Todoist returns).

   **GitHub items** (issues + PRs):
   - `source = "github"`, `id = "<owner>/<repo>#<number>"`, `title = item.title`, `url = item.html_url`.
   - `priority = null` (GitHub has no priority field).
   - `due = null` (GitHub issues don't have due dates by default).
   - `assigned_at`: for issues use `item.created_at` (best proxy for "in queue"); for PRs review-requested use `item.created_at` (or `requested_reviewers[].requested_at` if available).
   - `type`: from which query it came — `issue` from search_issues, `pr_review` from review-requested PR query, `pr_mine` from author query.

   **ClickUp tasks:**
   - `source = "clickup"`, `id = task.id`, `title = task.name`, `url = task.url`.
   - `priority`: ClickUp returns priority object with `priority` field ("1"=urgent, "2"=high, "3"=normal, "4"=low). Map: `"1" → "p1"`, `"2" → "p2"`, `"3" → "p3"`, `"4" → "p4"`. If null, treat as `"p4"`.
   - `due`: `task.due_date` (Unix millis → convert to ISO date).
   - `assigned_at`: `task.date_created` (Unix millis → ISO).
   - `type = "task"`.

   **Google Calendar events:**
   - `source = "google_calendar"`, `id = event.id`, `title = event.summary`, `url = event.htmlLink`.
   - `priority = null`, `due = event.start.dateTime` (or `event.start.date` for all-day).
   - `assigned_at`: `event.created`.
   - `type = "calendar_event"`.

   After normalization, you have a unified `items` list ready for scoring.

5. **Score and sort**:

   For each item in `items`, compute four component scores (each 0–100) and combine using weights from `effective_config.scoring.weights`.

   **`priority_score`:**
   - `p1 → 100`, `p2 → 75`, `p3 → 50`, `p4 → 25`, `null → 10`
   - For items where `type == "pr_review"` and `priority == null`, override to `75` (PRs blocking colleagues default to p2 importance)

   **`due_proximity_score`:**
   - Compute today's date and the item's due date (date-only, ignore time-of-day for tasks; for calendar events use full datetime).
   - `due == null → 0`
   - `due < today (overdue) → 100`
   - `due == today → 90`
   - `due == tomorrow → 70`
   - `2 <= days_until_due <= 7 → linear interpolation from 60 (at +2 days) down to 20 (at +7 days). Formula: `60 - (days_until_due - 2) * 8` → `60, 52, 44, 36, 28, 20`.
   - `days_until_due > 7 → 10`

   **`age_score`:**
   - `age_days = (today - assigned_at) in whole days`
   - `age_score = min(100, age_days * 5)`
   - If `assigned_at == null`, `age_score = 0`

   **`type_assignment_score`:**
   - `type == "pr_review" → 90`
   - `type == "issue"` and assigned directly to user → `80`
   - `type == "task"` (Todoist or ClickUp) with assignment → `80`
   - `type == "task"` in user's project but no specific assignee → `40` (not applicable in v1 since we filter assignee=me at fetch; reserve for future)
   - `type == "calendar_event"`:
     - If event starts in `<= 2 hours` → `100`
     - Else if event starts in `<= 6 hours` → `70`
     - Else → `40`
   - `type == "pr_mine"` → `50` (your own PRs — relevant but not blocking others)

   **Combine:**
   ```
   weights = effective_config.scoring.weights  // e.g. {priority: 40, due_proximity: 30, age: 15, type_assignment: 15}
   total_weight = sum(weights.values())  // normally 100, but defensive

   score = (priority_score * weights.priority
          + due_proximity_score * weights.due_proximity
          + age_score * weights.age
          + type_assignment_score * weights.type_assignment) / total_weight
   ```

   Round score to integer.

   Sort `items` by score descending. Tie-break (in this order):
   1. Higher `priority_score`
   2. Shorter due (overdue first, then today, then nearest future)
   3. Older `age_days`
   4. Alphabetical title (case-insensitive)

6. **Bucket items**:

   Assign each item to exactly one bucket based on its data (NOT its score):

   - **🔥 `OVERDUE`** — `due` is set and `due < today`
   - **👀 `WAITING_ON_REVIEW`** — `type == "pr_review"` (regardless of due)
   - **📅 `TODAY`** — `due == today` OR (`due == null` AND `priority in [p1, p2]`)
   - **📆 `UPCOMING`** — `due` is in the next 7 days (tomorrow through +7)
   - **(uncategorized)** — anything else: low-priority items with no due date, calendar events more than 12h out, etc. Default: drop from briefing.

   (The bucket enum values above — `OVERDUE`, `WAITING_ON_REVIEW`, `TODAY`, `UPCOMING` — are the canonical strings used in the snapshot JSON. The display labels in the rendered briefing in step 7 use friendlier names like "Čeká na tvůj review".)

   Bucket assignment priority (if an item matches multiple, pick the first match in this order): `OVERDUE` > `WAITING_ON_REVIEW` > `TODAY` > `UPCOMING`.

   **Top N filter:** keep only the top `effective_config.scoring.top_n` items across all buckets. The score determines which items survive the filter; the bucket determines where they're displayed. Within a bucket, sort by score descending (tie-break rules from step 5).

   Skip empty buckets in the rendered output.

7. **Render briefing + recommendation**:

   Build a markdown briefing in the configured language. Use this template (Czech default; translate the labels and recommendation prose if `effective_config.language` is something else):

   ```markdown
   ## 📋 Briefing — <today's date as DD. MM. YYYY>

   ### 🔥 Overdue
   1. **<title>** — <source>, score <N>, due <DD.MM.YYYY> (X dní po termínu)
      <url>
   ...

   ### 👀 Čeká na tvůj review
   1. **<title>** — <source/repo>, score <N>, otevřeno <X dní>
      <url>
   ...

   ### 📅 Dnes
   ...

   ### 📆 Tento týden
   ...

   ---

   💡 **Začni s [item #1 overall]** — <one-sentence reason from the dominant scoring component>.

   <Warnings section if any>
   ```

   For the recommendation, identify the item with the highest score across all buckets. Determine which component contributed most to its score (the largest weighted component), and articulate that:
   - If priority_score dominates: "má prioritu <p1/p2>"
   - If due_proximity_score dominates: "je <po termínu / due dnes / due zítra>"
   - If age_score dominates: "leží v queue už <X> dní"
   - If type_assignment_score dominates: "je PR čekající na review / je za <X> hodin v kalendáři"

   Pick the single dominant reason; don't list all.

8. **Write snapshot**:

   Compute `effective_config_hash`:
   ```bash
   echo -n '<effective_config as canonical JSON>' | shasum -a 256 | cut -d' ' -f1
   ```
   Prefix with `"sha256:"`.

   Build the snapshot:

   ```json
   {
     "schema_version": 1,
     "timestamp": "<UTC now as ISO 8601>",
     "effective_config_hash": "sha256:<hex>",
     "items": [
       {
         "source": "...",
         "id": "...",
         "title": "...",
         "url": "...",
         "score": <int>,
         "bucket": "OVERDUE" | "WAITING_ON_REVIEW" | "TODAY" | "UPCOMING",
         "status": "open"
       }
     ],
     "warnings": [...]
   }
   ```

   Only include the top_n items displayed in the briefing (not the full discarded set).

   Get UTC timestamp:
   ```bash
   date -u +%Y-%m-%dT%H:%M:%SZ
   ```

   Ensure dir exists:
   ```bash
   mkdir -p ~/.claude/plugins/work
   ```

   Write the snapshot with the Write tool to `~/.claude/plugins/work/last-briefing.json`.

9. **Print warnings**:

   If `warnings` is non-empty, after the briefing print:

   ```
   ---

   ⚠️ Upozornění:
   - <warning 1>
   - <warning 2>
   ```

   If `warnings` is empty, omit this section.

## Edge cases

- **No items returned from any source**: render `🎉 Žádné overdue tasky, žádné PRs k review. Užij si volný čas.` Skip all bucket sections. Still write the snapshot (empty `items`) so `/work-status` has a baseline.
- **Config exists but all sources are `enabled: false`**: same message as no-items, plus warning "Žádný zdroj není povolený. Spusť /work-setup pro úpravu."
- **Snapshot already exists from earlier today**: overwrite it silently. (No "are you sure" prompt — `/work-start` is idempotent.)
- **All MCP sources fail**: print warnings, render no buckets, message "Briefing selhal — všechny zdroje nedostupné. Zkontroluj MCP servery."
