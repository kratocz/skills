---
name: work-status
description: Mid-day check — diff current state of volatile sources (GitHub PRs, Todoist completions) against the last /work-start snapshot. Use when the user says "/work-status", "what's new", "co se změnilo".
version: 0.3.0
allowed-tools: Read, Bash, ToolSearch, mcp__claude_ai_Todoist__find-completed-tasks, mcp__claude_ai_Todoist__find-tasks, mcp__claude_ai_Todoist__find-tasks-by-date, mcp__github__search_issues, mcp__github__search_pull_requests
---

# Work Status

Lightweight diff: what closed, what's new, what's still open — since `/work-start`.

## Steps

1. **Read snapshot**:

   Try to read `~/.claude/plugins/work/last-briefing.json` with the Read tool.

   - If missing: stop with message "Žádný snapshot. Spusť /work-start nejdřív." Return.
   - If `schema_version` is not `1`: warn "Snapshot je z jiné verze pluginu. Pokračuju best-effort." Continue.
   - Compute snapshot age:
     ```bash
     date -u +%s  # current epoch
     date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "<snapshot.timestamp>" +%s  # macOS
     # On Linux: date -u -d "<snapshot.timestamp>" +%s
     ```
     `age_hours = (now - snapshot_epoch) / 3600`
   - If `age_hours > 12`: warn "Snapshot je starý <X> hodin. Doporučuji /work-start." Continue anyway.

2. **Read effective config** — use the same logic as `/work-start` step 1 (global config + per-project override merge). If global config is missing, stop with "Žádná konfigurace work pluginu. Spusť /work-setup." Return.

   Compare current `effective_config_hash` (compute same way as in /work-start step 8) against snapshot's `effective_config_hash`. If different, append a warning: "⚠️ Konfigurace se od snapshotu změnila — diff může být zavádějící. Pro čistý stav spusť /work-start."

3. **Re-fetch volatile sources** (in parallel — single message with multiple MCP calls):

   Only sources that are `enabled` in `effective_config` AND in the volatile set (github, todoist). Skip calendar (stale events) and clickup (heavy re-fetch, defer to next /work-start).

   **GitHub** (if enabled and available — use ToolSearch to verify, same query as /work-start):
   - Use the same three queries as /work-start step 3 (search_issues + 2× search_pull_requests). Same `username` substitution and `repo` filter from override.

   **Todoist** (if enabled and available):
   - Get currently open tasks (for "new" and "still open" buckets):
     - Call `mcp__claude_ai_Todoist__find-tasks-by-date` with `{ "dateFrom": "1900-01-01", "dateTo": "<today>" }`.
     - Call `mcp__claude_ai_Todoist__find-tasks` with `{ "filter": "p1 | p2" }`.
   - Get tasks completed since snapshot timestamp:
     - Call `mcp__claude_ai_Todoist__find-completed-tasks` with `{ "since": "<snapshot.timestamp>" }` (or the equivalent argument shape per the MCP server's schema).

   Normalize all fetched items using the same normalization rules as `/work-start` step 4. Build `current_items` (open items now) and `completed_items` (Todoist completions since snapshot).

   For GitHub, also identify which snapshot items are now closed:
   - For each snapshot item with `source == "github"`, check if it appears in the current open results. If not, treat as closed.
   - **Caveat:** this is a heuristic. An item could also disappear because the user changed filters, removed assignment, etc. For v1 we accept this; in practice items in a morning snapshot rarely change assignment by mid-day. The next /work-start re-establishes ground truth.

4. **Diff snapshot vs. current**:

   - `closed`: snapshot items that are no longer open. (GitHub: not in current open results. Todoist: in `completed_items` OR not in current open results — Todoist completions appear in `completed_items` directly.)
   - `new`: current open items that don't appear in snapshot (matched by `id`).
   - `still_open`: snapshot items that are in current open results. Sort by `score` descending (use stored snapshot score; don't re-compute since we may be missing data from skipped sources).

   Sort `still_open` and pick the top 3 to display.

5. **Render terse summary** in the configured language (Czech default):

   ```markdown
   ## 📊 Status — <X>h od /work-start

   ✅ **Dokončeno:** <N>
   - <title> (<source>)
   - ...

   🆕 **Nové od briefingu:** <N>
   - <title> (<source>) — <url>
   - ...

   🔥 **Stále otevřené (top 3 podle scoru):**
   1. <title> (<source>) — score <N>
   2. ...

   <Warnings section if any>
   ```

   If `closed`, `new`, and `still_open` are all empty: "Nic nového. Snapshot je aktuální." (No subsections.)

## Edge cases

- **All volatile sources skipped (none enabled or all unavailable)**: print "Nelze re-fetchnout žádný zdroj — všechny volatile zdroje jsou neaktivní nebo nedostupné."
- **Snapshot is empty** (briefing had no items): print "Snapshot je prázdný (briefing nezachytil nic). Spusť /work-start znovu pro aktualizaci."
