---
name: work-end
description: End-of-day summary — what got done, what carries over, what's new since /work-start. Use when the user says "/work-end", "konec dne", "shrnutí dne", "wrap up".
version: 0.3.0
allowed-tools: Read, Write, Bash, ToolSearch, AskUserQuestion, mcp__claude_ai_Todoist__find-completed-tasks, mcp__claude_ai_Todoist__find-tasks, mcp__claude_ai_Todoist__find-tasks-by-date, mcp__github__search_issues, mcp__github__search_pull_requests, mcp__plugin_ntit-common_clickup__clickup_filter_tasks
---

# Work End

End-of-day retrospective: what closed, what carries over, what arrived during the day.

## Steps

1. **Read snapshot**:

   Read `~/.claude/plugins/work/last-briefing.json` with the Read tool.

   - If missing: stop with "Žádný snapshot. Bez ranního /work-start nelze udělat end-of-day souhrn." Return.
   - If `schema_version` is not `1`: warn "Snapshot je z jiné verze pluginu. Pokračuju best-effort." Continue.
   - Compute age:
     ```bash
     date -u +%s
     date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "<snapshot.timestamp>" +%s  # macOS
     ```
     If `age_hours > 24`: warn "Snapshot je z předchozího dne (před <X> hodinami). Souhrn může být zavádějící."

2. **Read effective config** — same as `/work-start` step 1. Stop if missing.

3. **Re-fetch all enabled sources**:

   Same as `/work-start` step 3 (parallel fetch of all enabled and available sources), BUT also include completed items for the "completed today" computation:

   - **Todoist** (in addition to open tasks): call `mcp__claude_ai_Todoist__find-completed-tasks` with `{ "since": "<midnight today UTC>" }`. Get midnight via:
     ```bash
     date -u -j -v0H -v0M -v0S +%Y-%m-%dT%H:%M:%SZ  # macOS, today UTC midnight
     # Linux: date -u -d 'today 00:00' +%Y-%m-%dT%H:%M:%SZ
     ```

   - **GitHub**: in addition to open queries, run:
     - `mcp__github__search_issues` with `{ "q": "is:closed is:issue assignee:<username> closed:>=<today UTC>" }`
     - `mcp__github__search_pull_requests` with `{ "q": "is:closed author:<username> closed:>=<today UTC>" }`

   - **ClickUp**: ClickUp `clickup_filter_tasks` can also filter by status — call once with `status=closed, date_updated_gt=<midnight epoch ms>`. (Refer to the MCP tool's schema for exact arg names.)

   - **Calendar**: skip (events don't have a "completed today" sense).

   Build:
   - `current_open` — normalized open items (same as /work-start)
   - `completed_today` — normalized completed items closed/completed today

4. **Compute completed / carry-over / new-unhandled**:

   - **`completed_total`** = `completed_today` (all items that finished today, regardless of whether they were in the morning briefing)
   - **`completed_from_briefing`** = subset of `completed_today` whose `id` matches a snapshot item
   - **`carry_over`** = snapshot items whose `id` is in `current_open` (still open at end of day)
   - **`new_unhandled`** = items in `current_open` whose `id` is NOT in snapshot AND NOT in `completed_today`

   Sort each list by score descending (re-score `carry_over` and `new_unhandled` using current data via `/work-start` step 5 scoring; for `completed_today` use the score they had in the snapshot if available, else 0).

5. **Render summary** in the configured language (Czech default):

   ```markdown
   ## 📊 Souhrn dne — <today's date>

   Doba od /work-start: **<X>h <Y>min**

   ### ✅ Dokončeno: <N> celkem (<M> z ranního briefingu)

   1. **<title>** — <source>
   ...

   ### 📝 Přechází na zítra: <N>

   1. **<title>** — <source>, score <N>
   ...

   ### ⚠️ Nové během dne, neřešeno: <N>

   1. **<title>** — <source>, score <N>, dorazilo <H>h zpět
   ...

   <Warnings if any>
   ```

   If `completed_total == 0` and `carry_over == 0` and `new_unhandled == 0`: render "Žádná aktivita dnes. Vše uzavřeno před snapshotem."

6. **Optionally save to session log**:

   Check if the `session-log` plugin is installed by reading `~/.claude/plugins/session-log/config.json`. If it doesn't exist, skip this step silently.

   If it exists:
   - Read the config to find the session log directory (`session_log_dir` field, or default `~/Documents/claude-sessions/`).
   - Ask via AskUserQuestion: "Uložit dnešní souhrn do session logu?" Options:
     - "Ano (append k dnešnímu logu)"
     - "Ne, jen vypsat"
   - If "Ano":
     - Determine today's log file name (convention: `<dir>/YYYY-MM-DD.md`).
     - Use the Read tool to check if it exists. If yes, use the Write tool only if you can append (which Write doesn't support directly — use Bash `cat >> file`):
       ```bash
       printf '\n\n## work-end summary\n\n%s\n' '<rendered summary above>' >> '<path>'
       ```
     - If the file doesn't exist, use Write to create it with just the summary.

   Confirm: "Uloženo do <path>."

## Edge cases

- **No sources fetched successfully**: render only "Žádný zdroj nedostupný. Souhrn dne nelze sestavit. Zkontroluj MCP servery." Skip lists.
- **All snapshot items still open, nothing completed today**: render with `completed_total = 0` section saying "(žádné položky dokončeny dnes)", and full `carry_over` list.
- **Snapshot from prior day**: render but with warning about age. Don't try to "extend" the snapshot range — be honest that the comparison baseline is stale.
