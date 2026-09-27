---
name: session-recall
description: Find the transcript of an earlier agent session — by the `Claude-Session` trailer of a commit, by session UUID, or by topic — and recover what the USER said in it (their prompts verbatim, in order), which commits that session made, and what was said after its last commit and therefore may never have reached the repo. Use when the user says "/session-recall", "načti předchozí session", "dokázal bys načíst session, kde jsme…", "co jsme řešili minule", "víš, jak jsme se bavili o…", "recall the session where we…", "what did we discuss last time", "load the previous conversation about X". Not time tracking over transcripts — that is tracker-backfill / work-reconcile.
argument-hint: "[commit | session-uuid | topic keywords]"
version: 1.0.0
allowed-tools: Read, Bash
license: MIT
---

# Session Recall

A new session does not remember the last one, but the last one is on disk: every
Claude Code session writes a JSONL transcript, and a commit made by a session
carries its `Claude-Session` trailer. This skill turns "do you remember when we
talked about X?" into a verified answer — the user's own words from that session,
what landed in the repo, and what did not.

Two things this skill exists to prevent, both from the founding case (2026-09-24):

- **Confusing the artifact with the conversation.** The repo document is the
  session's *output*; half the conversation can happen *after* the last commit
  (follow-up questions, decisions, corrections) and live only in the transcript.
- **Calling something "not in the repo" from a stale checkout.** The founding
  session read a worktree 16 commits behind `origin/main` and told the user the
  document lacked things that upstream had carried for two weeks. Every claim
  about repo state goes through `git fetch` first (Step 5).

## Steps

1. **Resolve the transcript directory.** Transcripts live in
   `<harness-home>/projects/<slug>/*.jsonl`, where `<harness-home>` is
   `~/.claude` (Claude Code) or `~/.gemini/antigravity-cli` (Antigravity CLI) —
   use the first that exists — and `<slug>` is a working directory with `/` and
   `.` replaced by `-` (`/Users/me/proj` → `-Users-me-proj`). A repo with
   worktrees has **one directory per worktree** (`…-proj--claude-worktrees-x`);
   the session you want may sit under the main checkout's slug even if today's
   session runs in a worktree — list all slugs that share the repo prefix:

   ```bash
   ls -d ~/.claude/projects/*<repo-name>* 2>/dev/null
   ls -lat ~/.claude/projects/<slug>/*.jsonl | head -20
   ```

   Filenames are session UUIDs with no date; the `mtime` is the session's last
   activity. Ignore `<uuid>/subagents/*.jsonl` unless the trail leads there.

2. **Find the session.** Three routes, in order of reliability:

   - **By commit.** The trailer names the session:
     ```bash
     git log -1 --format='%(trailers:key=Claude-Session,valueonly)' <sha>
     grep -l '<session-id-from-url>' ~/.claude/projects/<slug>*/*.jsonl
     ```
     The id matches **every** transcript that ever displayed that commit — the
     session that wrote it, and any later session that ran `git show` or `git
     log` on it (today's included). The author is the file whose **first user
     prompt predates the commit and whose mtime is after it**; verify with
     Step 3's timestamps before trusting it.
   - **By UUID.** If the user or a note has it: `~/.claude/projects/<slug>/<uuid>.jsonl`.
   - **By topic.** Count hits per file and rank; prefer distinctive words
     (a filename the session created, a proper noun) over common ones:
     ```bash
     for f in ~/.claude/projects/<slug>*/*.jsonl; do printf '%6d %s\n' "$(grep -c -i '<keyword>' "$f")" "$f"; done | sort -rn | head
     ```
     Then confirm with Step 3 — a high count can be a session that merely read
     the file the earlier session wrote.

   Exclude the running session: its UUID is the second-to-last component of
   the scratchpad path in your system prompt.

3. **Extract what the user said — and only that.** A transcript mixes the
   user's typed prompts with tool results, injected skill text, task
   notifications and local-command echoes, all under `type: "user"`. The typed
   prompts are the entries whose `message.content` is a **string** (or an array
   made only of `text` items with no `tool_result`), minus the harness noise:

   ```bash
   F=~/.claude/projects/<slug>/<uuid>.jsonl
   jq -r '
     select(.type=="user" and (.isMeta|not))
     | .message.content as $c
     | ( if ($c|type)=="string" then $c
         elif ($c|type)=="array" and ([$c[]|select(.type=="tool_result")]|length)==0
              then [$c[]|select(.type=="text")|.text]|join("\n")
         else empty end ) as $t
     | select($t|test("^<(task-notification|bash-input|bash-stdout|bash-stderr|local-command|command-name|command-message|command-args|system-reminder)")|not)
     | select($t|test("^Base directory for this skill")|not)
     | .timestamp + " || " + $t' "$F"
   ```

   Read the result as a timeline. Timestamps are UTC (`Z`); convert when the
   user reasons in local time. Keep the user's lines **verbatim** — they are
   the evidence, and paraphrase is where invented attribution starts.

   For the other side of the dialogue, take assistant text selectively — the
   last reply, or the reply after a specific prompt — never the whole file:
   ```bash
   jq -r 'select(.type=="assistant" and .timestamp > "<ISO>") | [.message.content[]?|select(.type=="text")|.text]|join(" ")' "$F" | grep -v '^$' | tail -3
   ```

   Transcripts can be megabytes; never `cat` one, and never dump a transcript
   into a subagent or an external service — it may hold personal content, keys,
   and other people's messages. Quote only what answers the question.

4. **Map the session onto the repo.** Which commits did it make, and when did
   the last one land relative to the conversation?
   ```bash
   git log --format='%h %aI %s' --since='<first-prompt-ts>' --until='<mtime + 1h>'
   ```
   Split the user timeline at the last commit's time: **before** it is the work
   the repo reflects; **after** it is the part that may exist only in the
   transcript — follow-ups, corrections, preferences stated once the artifact
   was already committed. That second half is usually what the user is asking
   about without knowing it.

5. **Before saying "this never reached the repo", fetch.** The checkout you are
   in — especially a worktree — can be far behind `origin/main`, and a later
   session may have absorbed exactly the after-commit conversation you found:
   ```bash
   git fetch origin && git rev-list --count HEAD..origin/main
   git log --format='%h %ad %s' --date=short HEAD..origin/main -- <file>
   ```
   If behind and the checkout is clean, `git merge --ff-only origin/main` and
   re-read the file. Only then compare the transcript's after-commit items
   against the **current** document, one by one.

6. **Report.** Conclusion first:
   - which session (UUID, first–last timestamps, how you identified it, and
     what else matched and was rejected),
   - the user's prompts as a dated timeline (verbatim, trimmed to the relevant
     ones — say how many were omitted),
   - commits the session made,
   - **what was said after the last commit and whether it is in the repo now**
     — one line per item, checked against `origin/main`, marked *in repo (sha)*
     / *not in repo* / *partly*,
   - a next step, if one follows (update the document, ask the user the open
     question the session ended on).

   A statement about who said or decided what must point at a transcript line
   you read. If the transcript is silent, say so — do not fill the gap from the
   commit message.

## Edge cases

- **Several transcripts match a commit** — expected; the founding case had
  three (author, a subagent's `subagents/*.jsonl`, and the running session
  that had just run `git show`). Decide by timestamps (Step 2), and say which
  you rejected.
- **Session spanned a `Došly tokeny` / rate-limit pause** — the transcript is
  still one file; long gaps between prompts are pauses, not session ends.
- **Session ran in a worktree whose directory is gone** — the slug directory
  under `~/.claude/projects/` survives the worktree; search by repo prefix.
- **Content `.message.content` is an array of `text` items with no
  `tool_result`** — that is a typed prompt with an attachment or pasted text;
  the filter above keeps it. An array with `tool_result` is a tool round-trip,
  not the user.
- **No transcript found** — say so; offer the commit history as the only
  record and be explicit that the conversation itself is unrecoverable.
