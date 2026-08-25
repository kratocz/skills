---
name: work-setup
description: Configure the work-* skills — detect available MCP sources (Todoist, GitHub, ClickUp, Google Calendar) and write ~/.claude/plugins/work/config.json. Use when the user says "/work-setup", "configure work", or when /work-start fails because config is missing.
version: 0.4.0
allowed-tools: Read, Write, Bash, ToolSearch, AskUserQuestion, mcp__plugin_ntit-common_clickup__clickup_get_workspace_members
license: MIT
---

# Work Setup

Configure the work-* skills: detect which MCP sources are available in this session, ask the user which to enable, and write the config file.

## Steps

1. **Load existing config** — silently; produce no output yet, the language is not settled until step 2.

   Try to read `~/.claude/plugins/work/config.json`.

   - If the file exists: parse it and remember it as `existing_config`. You're in **edit mode** — prefill defaults from existing values when asking questions.
   - If it doesn't exist: you're in **create mode** — use the defaults in this skill.

2. **Language** — ask this **first**, before any other question: every step below talks to the user, and until this is answered there is nothing to phrase them in.

   Resolve the default to offer; first hit wins:
   - `existing_config.language` (edit mode),
   - the `language` field of `~/.claude/plugins/session-tracker/config.json`, if that file exists,
   - the language the user has been writing in this session,
   - `en`.

   Ask **bilingually** — at this point you cannot know which language the user reads: "Jazyk pro výstup briefingu? / Language for briefing output?" (ISO 639-1 code — `en`, `cs`, `de`, … — default: `<resolved_default>`). Accept any 2-letter ISO 639-1 code. Store as top-level `language`.

   **Every quoted user-facing string below is an example written in `cs`** — render it in the chosen language, keeping proper nouns, IDs, paths, code identifiers and JSON values unchanged. Where a string is given as `"<czech>" / "<english>"`, those are one message in two languages, not two messages.

   Only now report the mode:
   - Edit mode: "Existující konfigurace nalezena, projdu ji s tebou znovu. Stiskni Enter na otázce pro ponechání aktuální hodnoty." / "Existing config found — I'll walk through it. Press Enter to keep current values."
   - Create mode: "Nová konfigurace. Projdu s tebou dostupné zdroje." / "Fresh setup. I'll walk you through available sources."

3. **Detect available MCP sources** via ToolSearch:

   For each known source, call ToolSearch with a representative tool name to verify the MCP server is connected in this session. Use these queries:

   | Source | ToolSearch query |
   |---|---|
   | todoist | `select:mcp_Todoist__find-tasks` |
   | github | `select:mcp__github__search_pull_requests` |
   | clickup | `select:mcp__plugin_ntit-common_clickup__clickup_filter_tasks` |
   | google_calendar | `select:mcp_Google_Calendar__list_events` |

   If the query returns a function definition, the source is **available**. If the query returns no match, the source is **unavailable**.

   Build a list `detected_sources` of available sources. If `detected_sources` is empty, tell the user "Žádný známý MCP server (Todoist/GitHub/ClickUp/Calendar) není v této session připojený. Nelze pokračovat se setupem — přidej alespoň jeden MCP server v konfiguraci svého harnessu (např. `~/.claude/settings.json`) a restartuj session." / "No known MCP server (Todoist/GitHub/ClickUp/Calendar) is connected in this session. Setup cannot continue — add at least one MCP server to your harness configuration (e.g. `~/.claude/settings.json`) and restart the session." and stop.

4. **Per-source Q&A** — for each source in `detected_sources`:

   Ask "Zapnout zdroj `<source_name>` ve work briefingu?" / "Enable source `<source_name>` in the work briefing?" and offer the options:
   - "Ano (Recommended)" / "Yes (Recommended)" — `enabled: true`
   - "Ne" / "No" — `enabled: false`

   In edit mode, mark the option matching the existing value as recommended.

   **GitHub-specific follow-up:** if user enables `github`, ask for their GitHub username (free-text). Pre-fill with `existing_config.sources.github.username` in edit mode, or with the output of `gh api user --jq .login 2>/dev/null` if `gh` CLI is available (best-effort, don't fail if it errors). Store as `sources.github.username`.

   **ClickUp-specific follow-up:** if user enables `clickup`, the skills need the user's member ID to filter `assignee=me`. Call `mcp__plugin_ntit-common_clickup__clickup_get_workspace_members` (no args) — it returns a list of members. If exactly one workspace member matches the user's name (heuristic: contains the GitHub username collected above, OR the user's email local-part), pick that ID automatically. Otherwise, offer the members as options for the user to pick from (at most four — if there are more, list them inline with numbers and let them pick by number). Store as `sources.clickup.member_id`.

   **Default filter sets** for each source (used unless user later edits the JSON manually — no per-source filter UI in v1):

   - todoist: `{ "priorities": ["p1", "p2"], "scope": "today_and_overdue" }`
   - github: `{ "include": ["assigned_issues", "review_requested_prs", "my_open_prs"] }`
   - clickup: `{ "include": ["assigned_to_me"], "scope": "today_and_overdue" }`
   - google_calendar: `{ "window_hours": 12 }`

   Store the result for each source as an object. The exact shape varies per source :
   - `todoist`: `{ "enabled": bool, "mcp_prefix": "...", "filters": { "priorities": [...], "scope": "..." } }`
   - `github`: `{ "enabled": bool, "mcp_prefix": "...", "username": "...", "include": [...] }` — note `include` at source level, NOT inside `filters`
   - `clickup`: `{ "enabled": bool, "mcp_prefix": "...", "member_id": "...", "filters": { "include": [...], "scope": "..." } }`
   - `google_calendar`: `{ "enabled": bool, "mcp_prefix": "...", "window_hours": 12 }` — note `window_hours` at source level, NOT inside `filters`

   (mcp_prefix is the prefix used during detection in step 3 — e.g. `mcp_Todoist__`.)

5. **Optional: timesheet reconciliation** (`/work-reconcile`):

   Ask "Nastavit dorovnávání výkazů (`/work-reconcile`)?" / "Configure timesheet reconciliation (`/work-reconcile`)?" and offer the options:
   - "Ne, použít výchozí (Recommended)" / "No, use defaults (Recommended)" — skip; write nothing under `reconcile` (the skill falls back to its built-in defaults at runtime).
   - "Ano, nastavit" / "Yes, configure"

   In edit mode, mark the option matching whether `existing_config.reconcile` is present as recommended.

   If the user picks "Ano"/"Yes":

   Ask "Kam zapisovat dorovnaný čas?" / "Where should reconciled time be written?" and offer the options:
   - "Toggl (Recommended)" — `sink.target: "toggl"`
   - "ClickUp" — `sink.target: "clickup"`
   - "Obojí" / "Both" — `sink.target: "both"`

   In edit mode, prefill the option matching `existing_config.reconcile.sink.target` (default `toggl`).

   Ask "Jaké výchozí období dorovnávat?" / "What's the default reconcile window?" and offer the options:
   - "Minulý měsíc (Recommended)" / "Last month (Recommended)" — `default_window: "last_month"`
   - "Minulý týden" / "Last week" — `default_window: "last_week"`

   In edit mode, prefill the option matching `existing_config.reconcile.default_window` (default `last_month`).

   Store the result as:
   ```json
   { "reconcile": { "default_window": "<chosen>", "sink": { "target": "<chosen>" } } }
   ```
   All other `reconcile` keys (`gap_threshold_min`, `edge_pad_min`, `round_to_min`, `min_block_min`, `coverage_covered`, `coverage_missing`, `ai_sessions.*`, `calendar.*`, `sink.billable`, `sink.reconciled_tag`) are not configurable here in v1 — they keep the skill's built-in defaults unless the user edits the JSON manually.

6. **Scoring config**:

   Ask "Použít výchozí scoring váhy (priority=40, due=30, age=15, type=15)?" / "Use default scoring weights (priority=40, due=30, age=15, type=15)?"

   - "Ano (Recommended)" / "Yes (Recommended)" — store defaults
   - "Vlastní hodnoty" / "Custom values" — prompt for each weight separately (priority, due_proximity, age, type_assignment). Each must be a non-negative integer. Validate that they sum to 100 (if not, tell the user the actual sum and re-ask). Store as `scoring.weights`.

   Then ask: "Kolik položek zobrazit v briefingu? (výchozí 8)" / "How many items to show in briefing? (default 8)" — free text, validate as integer 1–20. Store as `scoring.top_n`.

   In edit mode, prefill defaults with existing values.

7. **Write global config**:

   Ensure the config directory exists:
   ```bash
   mkdir -p ~/.claude/plugins/work
   ```

   Build the config object in memory:
   ```json
   {
     "language": "<from step 2>",
     "sources": {
       "todoist":         { "enabled": <bool>, "mcp_prefix": "mcp_Todoist__", "filters": { "priorities": ["p1", "p2"], "scope": "today_and_overdue" } },
       "github":          { "enabled": <bool>, "mcp_prefix": "mcp__github__", "username": "...", "include": ["assigned_issues", "review_requested_prs", "my_open_prs"] },
       "clickup":         { "enabled": <bool>, "mcp_prefix": "mcp__plugin_ntit-common_clickup__", "member_id": "...", "filters": { "include": ["assigned_to_me"], "scope": "today_and_overdue" } },
       "google_calendar": { "enabled": <bool>, "mcp_prefix": "mcp_Google_Calendar__", "window_hours": 12 }
     },
     "scoring": {
       "weights": { "priority": 40, "due_proximity": 30, "age": 15, "type_assignment": 15 },
       "top_n": 8
     }
   }
   ```

   **Important:** include ALL four sources in the JSON even if some are disabled or weren't detected in this session. Sources that weren't detected get `enabled: false` and the canonical `mcp_prefix` from the detection table (so the user can manually enable later when they add the MCP server). Sources that were detected but the user said "No" also get `enabled: false` but keep any collected metadata (username, member_id).

   If step 5 collected a `reconcile` block, merge it in as a top-level `reconcile` key alongside `sources` and `scoring`. If step 5 was skipped, omit `reconcile` entirely — do not write an empty object.

   Write the JSON to `~/.claude/plugins/work/config.json` with 2-space indentation.

8. **Optional per-project override**:

   Detect the current project's slug:
   ```bash
   pwd
   ```

   The project memory dir follows the harness convention: `<harness-home>/projects/<slug>/memory/`, where `<harness-home>` is `~/.claude` (Claude Code) or `~/.gemini/antigravity-cli` (Antigravity CLI) — use the first that exists — and `<slug>` is the absolute path of the current working directory with `/` replaced by `-` and a leading `-` (so `/Users/krato/IdeaProjects/foo` becomes `-Users-krato-IdeaProjects-foo`).

   Ask "Chceš uložit per-project override pro projekt `<basename>`?" / "Save a per-project override for `<basename>`?" and offer the options:
   - "Ne, jen globální config (Recommended)" / "No, global config only (Recommended)" — skip
   - "Ano, uložit override soubor" / "Yes, write an override file"

   If the user picks "Ano"/"Yes":

   Compute the slug from `pwd`. Verify the memory dir exists:
   ```bash
   ls <harness-home>/projects/<slug>/memory/ 2>/dev/null || echo "MEMORY_DIR_MISSING"
   ```

   If `MEMORY_DIR_MISSING`, create it:
   ```bash
   mkdir -p <harness-home>/projects/<slug>/memory
   ```

   Ask the user (free text): "Co chceš v tomto projektu změnit oproti globálnímu configu? Napiš jednou větou (např. 'vypnout clickup, jen github repo X')." / "What should differ from the global config in this project? One sentence (e.g. 'disable clickup, only github repo X')." Use the answer as a hint for which fields to override.

   Then ask for the specific override, offering these options (this v1 supports only a small set):
   - "Vypnout některé zdroje v tomto projektu" / "Disable some sources in this project" — multi-select from `[todoist, github, clickup, google_calendar]`, the selected ones get `enabled: false` in the override.
   - "Pouze z konkrétních GitHub repos" / "Only specific GitHub repos" — free text, comma-separated owner/repo list. Adds `sources.github.repos` array.
   - "Hotovo — nic dalšího" / "Done — nothing else" — proceed to write.

   Loop until the user picks "Hotovo"/"Done".

   Build the override JSON (only the fields to override) and write to `<harness-home>/projects/<slug>/memory/work_config.md`:

   ````markdown
   ---
   name: work-config-override
   description: Per-project work skills overrides for <basename>
   metadata:
     type: project
   ---

   Per-project overrides for the work skills in this project. The skill reads only the JSON block below.

   ```json
   { "sources": { "clickup": { "enabled": false } } }
   ```

   <user's one-sentence reason from above>
   ````

   Append a line to `<harness-home>/projects/<slug>/memory/MEMORY.md` (create the file if missing):
   ```
   - [Work skills override](work_config.md) — per-project source/scoring overrides
   ```

   If MEMORY.md already contains a line referencing `work_config.md`, don't add a duplicate.

9. **Confirm**:

   Print a summary in the configured language:
   ```
   ✅ Setup hotov.

   Global config: ~/.claude/plugins/work/config.json
   Povolené zdroje: <comma-separated list of enabled source names>
   Per-project override: <path or "není" / "none">

   Spusť /work-start pro ranní briefing.
   ```
