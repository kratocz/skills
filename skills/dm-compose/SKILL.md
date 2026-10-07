---
name: dm-compose
description: Compose a proactive direct message to a colleague — a status check-in, a nudge, a heads-up, a handover note — by gathering the verifiable state first, asking the user what happened outside the tracker, drafting in the recipient's language, and sending only on an explicit go-ahead. Use when the user says "napiš kolegovi", "zeptej se ho, jak mu to jde", "napiš mu, ať…", "pošli mu zprávu", "draft a DM to X", "ask X how it's going", "message the team about Y", or otherwise wants a message they have not received yet. Replying to messages that arrived is `dm-catchup`; e-mail through the Gmail MCP is `gmail-compose`.
version: 1.1.0
license: MIT
---

# DM Compose

Write a message the user is *initiating*, not answering. The risk here is the
opposite of a reply's: there is no thread to anchor to, so everything the
message asserts comes from the agent's own snapshot of the world — which is
systematically incomplete. Meetings, calls and side DMs the agent never saw
have already moved things, and a check-in that ignores them reads to the
recipient as if the sender forgot the conversation they had yesterday.

## Steps

### 1. Detect the backend and resolve the recipient

Probe which chat-capable MCP tools the session offers (load deferred schemas in
ONE batched call):

- **ClickUp chat:** `clickup_get_chat_channels`, `clickup_send_chat_message`,
  `clickup_find_member_by_name`
- **Slack:** `slack_search_users`, `slack_send_message`

Check project memory and `AGENTS.md` first for a roster with pinned DM channel
IDs — a pinned ID beats a fresh lookup and costs no API budget. Note the
recipient's **language** and anything recorded about how they read messages
(non-native speaker, prefers terse, does not know internal task IDs).

Then read the tail of that DM channel (the last handful of messages). It tells
you whether a conversation is running (no greeting) and, more importantly,
what the recipient has **already been told** — by the user, or by another
agent session working in parallel that this one never saw. Read it again right
before sending (step 7) if any time has passed: real case (2026-10-07), a
drafted "the tech lead will do the fix" was approved, but earlier that day the same
recipient had been promised the fix "tonight" from a message this session
never saw; only the re-read caught it, and the draft had to change to correct
that promise.

### 2. Gather only what you can verify

Collect the state the message will rest on, and keep it to things with a
source you actually read:

- tracker: subtask statuses, assignees, the parent epic
- forge: open and recently merged PRs, review state, labels
- repo: `git fetch` first, then `git log origin/main` — never the working tree
  of a worktree, which is routinely behind

Write down which of these you checked. The message may state these facts
plainly; everything else is a question, not an assertion.

### 3. Ask the user what the tracker cannot show — before drafting

**This is the step that is skipped, and it is the one that matters.** Ask one
question:

> Is there an agreement or meeting outcome about this that I would not see?

Agreements made in meetings, calls and DMs are invisible here, and they change
what the right question even is. A check-in built purely from statuses asks
"when do you expect to open the PRs?" — when the answer was settled at
yesterday's stand-up, that reads as not having listened.

If the user says there is nothing, say so explicitly in the note that
accompanies the draft, so the assumption is visible rather than silent.

### 4. Draft

Shape:

1. **One line of verified context** — what landed, what is now where. This is
   where the state from step 2 goes, and nowhere else.
2. **The ask itself.** For a status check-in the default phrasing is
   *on-track + blockers*: "Is <the agreed plan> on track — and is anything
   blocking you?" Not a list of open questions the recipient may already have
   answered.
3. **At most one extra item.** A second topic in a check-in buries the first.

Rules that apply to every outward message, and bite hardest here:

- **The recipient's language**, not the user's. Czech colleague → Czech; an
  external contractor who works in English → English.
- **Continuous paragraphs.** No hard line breaks mid-sentence; the client
  reflows the text itself.
- **No idioms** in a message to a non-native speaker — "your call", "give me a
  ring", "ballpark" invite literal readings. Say the plain thing.
- **No internal task IDs** to anyone who does not live in the tracker (a
  stakeholder, a manager). Name the thing in words.
- **No greeting mid-conversation** if the thread is already running; a fresh
  proactive message may open with one.

### 5. Flag every sentence the user did not say

Before showing the draft, re-read it and mark, in a note *outside* the draft,
anything that is:

- a **commitment** ("I will take this over", "we will have it by Friday"),
- a **handover** or reassignment,
- a **deadline**,
- an inference about who does what.

A rule that *implies* one of these — a policy the agent knows, an access
constraint, a convention — is a reason to **ask the user**, never to commit on
their behalf. The message goes out under their name; a promise invented by the
agent becomes a promise they made. Saying "this sentence assumes X, which you
have not stated" is what lets it get caught in review.

### 6. Show, then send only on an explicit go-ahead

Show the draft exactly as it would be sent — the draft *is* the message, so if
it is shown wrapped, formatted or abbreviated, that is what will arrive.

An approval covers **only the drafted message**. A follow-up, a correction sent
after it, or a second message to someone else each needs its own go-ahead, even
when it feels like a natural continuation.

### 7. Send and verify

If time has passed since the draft was approved, re-read the channel tail
first (step 1): a message that changed what the draft should say means
re-showing the draft, not sending the approved one.

Send, then report the message id and channel so the user can find it. If the
backend returns an error, say what was *not* sent rather than retrying blind.

## Anti-patterns

| Shape | Why it fails |
|---|---|
| "Could you let me know what you are working on and when you expect the PRs?" | The answer often already exists — from a meeting the agent did not see. Ask step 3 first. |
| "TASK-15, which I will take over" | A handover nobody decided. Derived from a rule, not from the user. |
| Three topics in one check-in | The recipient answers the last one. |
| Draft shown reflowed "for readability" | The draft is the message; what you show is what goes out. |
| Sending the obvious follow-up after a "send it" | The approval covered one message. |

## Related

- `dm-catchup` — the inverse: read an existing thread and draft a *reply*.
- `gmail-compose` — same job over e-mail, with its own link-mangling traps.
- `client-questions` — assembling what is blocked on an external party before a
  meeting, rather than messaging one teammate.
