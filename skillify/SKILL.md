---
name: skillify
description: Analyze this session (and, on demand, past session transcripts) for repeatable workflows worth capturing as a skill, propose candidates, and create the approved ones. Use when the user says "/skillify", "skillify", "make a skill from this", "turn this into a skill", "co by z tohohle šlo udělat skill", "udělej z toho skill", or wants to capture a workflow as a reusable skill.
version: 0.1.0
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, Task, AskUserQuestion, Skill
---

# Skillify

Analyze the work done in this session for repeatable workflows worth capturing
as a skill, propose candidates, and create the approved ones. The on-demand,
runnable-any-time counterpart to `/retro`'s skills area.

Respond in the language the user has been using in this session.

Hard rules, valid for the whole skill:

- **Interactive by default.** Nothing is created or edited without the user
  approving the specific candidate (Phase 2). Analysis (Phase 1) is read-only.
- **Never invent findings.** A session with no repeatable workflow legitimately
  produces an empty result — say so honestly, do not pad.
- **No duplicates.** Never propose a skill equivalent to one that already
  exists; mention the existing skill instead.
- **Never commit automatically.** Offer a commit at the end; the user decides.
- **Never write outside the current project** without explicit approval.

## Modes

Parse the invocation argument:

- **no argument** → *default*: analyze the current session inline.
- **`deep [N]`** → *deep*: inline analysis PLUS a subagent scan of the last N
  (default 10) past session transcripts of this project.
- **any other text** → *targeted*: treat the text as a description of one
  workflow to capture; skip discovery and go straight to shaping that single
  candidate (Phase 2, starting at the placement decision). Still consult
  Phase 0's skill map first: if the description duplicates an existing
  skill, say so instead of creating one (the No-duplicates rule applies
  here too). This is also how `/retro` delegates an approved skill
  candidate.

## Phase 0 — Context

1. Parse the argument into mode (default / deep N / targeted description).
2. Map the existing skill environment to avoid duplicate proposals:
   - project skills: Glob `.claude/skills/*/SKILL.md`
   - installed-plugin skills: the skills listed in your available-skills
     system context.

## Phase 1 — Analysis (read-only)

Skip this phase entirely in targeted mode (the candidate is given).

Look for two kinds of findings:

- **New skill** — a repeated or clearly repeatable multi-prompt workflow: the
  user drove you through the same shape of work more than once, or said they do
  it often. A workflow the user iteratively corrected until it worked also
  counts — the corrected final form is what to capture.
- **Improved skill** — a skill invoked this session misfired or needed manual
  correction.

**Inline (all modes except targeted):** review the current conversation for
both kinds.

**Deep scan (deep mode only):** dispatch ONE subagent (type `Explore`) over the
project's past transcripts. First resolve the transcript directory and the
running session's own transcript:

- The scratchpad directory path in your system prompt has the form
  `.../<project-slug>/<session-uuid>/scratchpad`. Its second-to-last component
  is the running session's UUID; the component before that is the project slug.
- The transcript directory is `~/.claude/projects/<project-slug>/`; transcripts
  are its `*.jsonl` files. Filenames are session UUIDs with no embedded date.
- List newest-first by modification time: `ls -t ~/.claude/projects/<slug>/*.jsonl`.
- Exclude `<session-uuid>.jsonl` (the running session). If you cannot resolve
  the UUID, include it — the merge step dedupes the overlap with the inline
  findings.

Take at most N paths (newest first, default 10) and pass them to the subagent
with these instructions:

> Read the given Claude Code transcript files (JSONL). For each, focus on the
> user messages and the skill/tool invocations — grep first, these files can be
> huge. **Ignore `<system-reminder>` blocks entirely** — they are injected
> context, not the user's or the assistant's words. Identify workflow shapes
> that recur across sessions (the same kind of multi-step task driven more than
> once). Return ONLY a compact list: for each workflow, a one-line name, which
> sessions it appears in, and a ≤1-line piece of evidence. Return no transcript
> excerpts beyond those one-line evidences.

Merge the inline and deep findings. A workflow recurring across sessions is a
stronger signal than one seen once. Drop any candidate already covered by an
existing skill (from Phase 0) — mention the existing skill instead.

For each surviving candidate, record: proposed name, what it automates, trigger
phrases, rough steps, a placement recommendation, and the evidence.

## Phase 2 — Interactive approval and creation

**Approval (skip in targeted mode — the single candidate is already chosen):**
show the numbered candidates, then use AskUserQuestion (`multiSelect: true`,
max 4 options per question — batch into several questions if there are more).
Each option label is the candidate name; the description states what the skill
would do and where it would live.

For each approved **new skill**, decide placement (state your recommendation,
let the user choose):

- **Project-specific workflow** → scaffold `.claude/skills/<name>/SKILL.md` in
  this project. If `superpowers:writing-skills` is available, invoke it as
  guidance for writing a quality skill; otherwise write the file directly with:
  - frontmatter: `name`, and a `description` that is a one-line summary ending
    with the trigger phrases (the words a user would say to invoke it),
  - a body of concrete, step-by-step instructions distilled from what the
    session actually did — not a vague outline.
- **Generally useful workflow** → recommend creating a plugin in the user's
  marketplace. If the current working directory is that marketplace repo,
  follow its `CLAUDE.md` "Adding a new plugin" procedure. Otherwise print the
  steps (and mention `plugin-dev:create-plugin` if it is installed) — do not
  write outside the current project.

For each approved **improved skill**: quote the current `SKILL.md` text and the
replacement. For a skill installed from a marketplace cache, edit the plugin's
**source repo**, never the cache:

- the cache lives at `~/.claude/plugins/cache/<owner>/<plugin>/<version>/...`;
- find the working clone (e.g. under the user's projects directory) and confirm
  the source `SKILL.md` matches the cache copy before proposing the edit;
- after editing the source, note that the change reaches the cache only on
  reinstall / version bump.

Apply each approved item immediately, in list order. If an apply step fails,
report it, leave the item unapplied, and continue with the rest.

## Phase 3 — Summary

Report per candidate: created / edited / skipped (one line each). Then:

- If repo files changed (new project skills under `.claude/skills/`, or an
  edited source `SKILL.md`): list them and offer — do not run — a commit.
- If nothing was created, say so plainly.

## Edge cases

- **No candidates** → honest "nothing worth capturing as a skill from this
  session"; never invent one.
- **Deep scan, no or unreadable transcripts** → report it and continue with the
  inline findings only. Read at most N files (default 10), never the whole
  directory.
- **Equivalent skill already exists** → mention it, do not propose a duplicate.
- **Re-run in the same session** → re-check `.claude/skills/` and do not
  re-propose candidates already created or rejected earlier in the session.
