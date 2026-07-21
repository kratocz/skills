---
name: log-where
description: Show where session-log stores summaries for the current project, and list the most recent ones. Use when the user says "/log-where", asks where logs are saved, wants to find a past session summary, or wants to know which sessions have been logged.
version: 1.0.0
---

# Log Where

Show the session-log directory for the current project and list recent summaries.

## Steps

1. Compute the logs directory for the current project. The directory name is the **encoded `$PWD`** — same encoding Claude Code uses for `~/.claude/projects/` (both `/` and `.` become `-`):

   ```bash
   # CLAUDE_PLUGIN_DATA is set in hook context; may not be set in skill context.
   # Fallback mirrors what Claude Code uses: ~/.claude/plugins/data/<plugin>-<marketplace>/
   DATA_DIR="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/plugins/data/session-log-kratocz}"
   CWD_ENCODED=$(printf '%s' "$PWD" | tr './' '--')
   LOGS_DIR="$DATA_DIR/logs/$CWD_ENCODED"
   echo "$LOGS_DIR"
   ```

2. Tell the user the directory path.

3. If the directory exists, list the 10 most recently modified summaries with their goal (parsed from YAML frontmatter). Run:

   ```bash
   if [ -d "$LOGS_DIR" ]; then
     ls -1t "$LOGS_DIR"/*.md 2>/dev/null | head -10 | while read -r f; do
       goal=$(awk '/^## Goal/{flag=1; next} /^## /{flag=0} flag && NF' "$f" | head -1 | cut -c1-80)
       printf '%s\n  %s\n' "$(basename "$f")" "${goal:-(no goal captured)}"
     done
   fi
   ```

4. Format the output as a short, human-readable summary — for example:

   ```
   Logs for '/home/user/code/my-app':
     ~/.claude/plugins/data/session-log-kratocz/logs/-home-user-code-my-app/

   Recent sessions:
   - 2026-04-18_fe19949a.md
     Ahoj! V některém z předchozích chatů tady jsi mi navrhoval nějaké...
   - 2026-04-17_abc12345.md
     Fix the authentication bug in login flow
   ```

5. If the directory does not exist, tell the user there are no logged sessions yet for this project — the first summary will be written automatically when the current session ends.

## Notes

- The plugin writes one summary per Claude Code session via the `SessionEnd` hook.
- The encoded directory name is the same key Claude Code uses for session JSONL in `~/.claude/projects/<encoded>/`. So `ls ~/.claude/plugins/data/session-log-kratocz/logs/<encoded>/` and `ls ~/.claude/projects/<encoded>/` list logs and raw transcripts for the same working directory.
- Each summary frontmatter contains a `transcript:` link pointing to the raw JSONL.
