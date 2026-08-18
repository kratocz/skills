---
name: dm-catchup
description: Catch up on direct messages with a named person across whatever IM the environment offers (ClickUp chat, Slack), including thread replies, then summarize, assess what needs action, and draft a reply for approval. Use when the user says "/dm-catchup", "přečti si zprávy od/s <person>", "co mi psal <person>", "catch up on DMs with <person>", or "shrň konverzaci s <person>".
argument-hint: "[person] [time-window]"
version: 1.0.0
license: MIT
---

# DM Catch-up

Read the direct-message history with one person, including thread replies,
and turn it into: a summary, an assessment of what needs action, and — when
something does — a draft reply the user approves before anything is sent.

## Steps

### 1. Detect the IM backend

Probe which chat-capable MCP tools the session actually offers (load deferred
schemas via the platform's tool-search in ONE batched call):

- **ClickUp chat:** `clickup_get_chat_channels`, `clickup_get_chat_channel_messages`,
  `clickup_get_chat_message_replies`, `clickup_find_member_by_name`,
  `clickup_send_chat_message`
- **Slack:** `slack_search_users`, `slack_read_channel`, `slack_read_thread`,
  `slack_send_message_draft` / `slack_send_message`

If more than one backend is available, prefer the one named in project
config, memory, or AGENTS.md; otherwise ask (one question). If none is
available, say so and stop.

### 2. Resolve the person and their DM channel

- Check project memory / AGENTS.md first — teams often keep a roster with DM
  channel IDs; a pinned ID beats a fresh lookup.
- Names may arrive misspelled (dictation, autocorrect). Match tolerantly
  against known members (first name + closest surname); when you settle on a
  non-exact match, **say so explicitly** in the report ("beru X jako
  překlep/přeslech Y") so a wrong guess is visible.
- If no candidate matches, list the closest members and ask — never read a
  channel you merely hope is the right one.

### 3. Read the window — threads included

- Default window: **today + yesterday** in the user's local timezone; honor
  an explicit window from the arguments instead.
- Fetch channel messages, then **ALWAYS expand threads before claiming
  absence or completeness**: ClickUp's API returns only top-level messages —
  every message with `has_replies: true` needs a separate
  `clickup_get_chat_message_replies` call; Slack threads likewise need
  `slack_read_thread`. The newest development is usually IN a thread, not at
  the top level.
- Convert message timestamps to local time before deciding what falls inside
  the window; label which day each item belongs to.

### 4. Summarize, assess, recommend

Deliver three layers, in this order:

1. **What happened** — the topics of the window, each in a sentence or two,
   with who said what (only claims traceable to a message you actually read —
   no invented actors; when the source is silent about "who", phrase it
   actor-less).
2. **Assessment** — separate *closed threads* (acknowledged, answered,
   nothing owed) from *open items that wait on the user*, and say which is
   which. Where you disagree with a proposal in the messages, say so directly
   with the reason and an alternative.
3. **Draft reply** — only for items that need one. Follow outward-message
   rules: continuous paragraphs (no mid-sentence line breaks), no greeting
   mid-conversation, expand abbreviations at first use ("Virtual Private
   Cloud (VPC)") while keeping team-established ones (QA), and run a
   claim-by-claim audit — every "who did what" must be traceable, tense
   honest (present tense only for things actually done).

### 5. Send only on approval

Show the draft; send **exactly what was shown** (what you show is what you
send — no silent edits) as a thread reply when the conversation lives in a
thread, top-level otherwise. Report the sent message ID. If the user edits
the draft, send the edited version verbatim.

## Notes

- Reading is safe to do proactively; **sending is outward-facing** — never
  send without the user's explicit go-ahead for that specific text.
- If the backend's send tool ignores threading or formatting quirks are
  known (project memory often records them), mention the limitation instead
  of discovering it live on a real recipient.
