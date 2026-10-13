---
name: team-standup
description: "Prepare the cheat sheet a team projects at its stand-up: for every attendee, what they did since the last meeting, what they are on now and by when, who they are waiting on and who is waiting on them, open questions, and what comes next — a one-line TL;DR per person above the detail, every claim linked to its source and every inference marked as one. Reads the tracker, the team channel, direct messages, the forge and the user's own time tracking for the window since the previous meeting; writes nothing but its own local file. Use when the user says \"připrav tahák na standup\", \"co dělal tým od minula\", \"standup pro celý tým\", \"shrň práci týmu na meeting\", \"team standup cheat sheet\", \"prepare the team stand-up\", \"what did the team do since the last meeting\". Not your own recap since the last stand-up — that is `work-standup`; not whether one teammate has enough work or waits on you — that is `teammate-check`."
argument-hint: "[since <YYYY-MM-DD[THH:MM]>] [people <name,name,…>]"
version: 0.1.0
license: MIT
---

# Team Standup

A cheat sheet for a team stand-up, made to be projected while everyone it describes is watching. Per person: what they did since the last meeting, what they are on now and when it is due, what they wait on, which questions are open, and what comes next. A one-line TL;DR per person sits on top, the detail below it.

Because the people described read it live, the rule that governs everything else is: **every claim about a person carries the link it came from, and anything not read from a source is marked as inference.** "No commits" is not "did nothing" — reviews, calls, testing and debugging often leave no trace on the surfaces this skill reads.

It reads; it never writes anywhere except its own local file. Nothing is posted, assigned, commented or relabelled.

## 0. Inputs

- **Window** — from the start of the previous meeting to now (§2). An explicit `since` wins.
- **People** — the attendee list from the project's map (§1). An explicit `people` list wins for this run.

## 1. Load the project's map

None of the project specifics are in this skill. They live in a project note — the same map `teammate-check` uses, if the project already has one. Search the project memory and any team roster the project keeps (often a local, untracked notes file) for a note that names `teammate-check` or `team-standup`. Project memory is wherever the agent keeps per-project notes, such as `<harness-home>/projects/<slug>/memory/`.

From that map, take what `teammate-check` §1 lists — each person's identity in every system and their language, every task container, what each status means and **who holds the ball** in it, the team channel(s), the direct-message channels, how pull requests reference tasks, review-state labels, where priority and due dates live, and the API rate limits. A saved map is a starting point: list the containers and channels once and tell the user in the conversation about any that are new — not in the cheat sheet, where a list of channel ids is noise to the room.

The stand-up adds these fields:

| Field | Meaning | When missing |
|---|---|---|
| `attendees` | The fixed list of people the cheat sheet covers, the user included | Ask |
| `language` | The language of the meeting, not the user's personal language | Ask; if the user cannot be asked, use English when any attendee's language differs from the user's |
| `schedule` | Meeting days, time and timezone | Take `standup.schedule` from the `work-*` skills' config (per-project override first) when present; otherwise ask |
| `output_dir` | Where the dated cheat sheets go | The project's local, version-control-ignored notes directory, under `standups/` |
| `dm_content` | `summary` (default): a direct message contributes a fact without its content, e.g. "waiting on a reply since 10 Oct". `full`: its content may be quoted | Use `summary` |
| `links` | URL patterns for the items whose API returns no link — typically a chat message | Link the channel instead and say so in Coverage |

When fields are missing, ask the user once for the whole set, then offer to record the answers in the same map note, naming both skills, so the next run finds them.

**Language.** Render the cheat sheet in the map's `language`. Every quoted output string below is an example written in English, not a literal to emit. Talk to the user in their own language; only the cheat sheet follows the meeting. A quotation in another language stays verbatim, followed by a short gloss in the meeting language.

## 2. The window

- **Previous meeting** — the most recent scheduled occurrence that started before now, walking back at most 14 days. When now falls less than an hour after a scheduled start, the meeting is in progress or just about to be prepared for: take the occurrence before it. When a calendar source is available and the map names the meeting's event, prefer the actual occurrences there — a cancelled or moved meeting then shifts the window correctly.
- **This meeting** — the next occurrence at or after now, or the one in progress. Its date names the output file.
- **Horizon for "next"** — up to the meeting after this one.

Compute every date and weekday with a command (`date`, `cal`, or a calendar tool), never in your head, and convert every epoch timestamp a source returns the same way. Echo the resolved window to the user before reading the work sources in §3.

**The previous cheat sheet.** If `output_dir` holds the file of the previous meeting, read each person's **Next** from it; §4 compares it with what happened.

## 3. Plan the calls

Probe which backends the session offers — a tracker, a chat, a forge, the user's time tracker — and make the needed tools available in one round. A surface with no backend is reported as **not checked**, never as empty.

When an API is rate-limited, and above all when other sessions of the same account share its budget, write down the planned call count before starting; it goes into Coverage. When the project asks to confirm the shared budget before a large read and the user cannot be asked, stay within the map's target. Spend calls on the whole team at once, never once per person where one query covers everybody.

**Round 1 — everything independent, issued together:**

1. **Tracker** — the attendees' open tasks across every container, in one bulk query filtered by all attendees together. Then every task updated since the window start, closed ones included and **without** an assignee filter, since a task closed after being unassigned is still work done: when the tracker cannot filter by update date, order by last update and page until the dates fall below the window start.
2. **Team channel(s)** — back to the window start.
3. **Direct messages** — the user's channel with each attendee, back to the window start. Only the user's own conversations are readable; the rest of the team's private talk is not a source.
4. **Forge** — per repository: open pull requests, pull requests merged since the window start, and the reviews submitted on both. On GitHub one command each covers the whole team, e.g. `gh pr list --repo OWNER/NAME --state merged --search "merged:>=<window start date>" --limit 200 --json number,title,author,mergedBy,mergedAt,url,labels,reviews` and the same with `--state open`. Without `--limit` the list stops at 30 silently. The search is day-granular, so drop what `mergedAt` puts before the window's start time; `mergedBy` is the source for who merged.
5. **The user's time tracker** — the user's own entries in the window, which catch reviews, calls and ops work that leave no commit. Never anyone else's.
6. **The previous cheat sheet** (§2).

**Round 2 — what depends on round 1:**

1. Status history of the tasks updated inside the window (a bulk call when the tracker offers one). Trackers often do not keep it, or keep it only behind a setting; when the call fails, say so in Coverage and follow §4 for tasks without history. A last-updated date is not a status change: a comment moves it too.
2. Comments on the tasks updated inside the window.
3. Threads with replies, in the channel and the direct messages — top-level messages alone miss the answers. When the API does not say when the replies were posted, expand first the threads whose top message is inside the window or asks an attendee something, and list the rest in Coverage as not read.
4. Dependencies of each person's in-progress tasks and of the first few ready tasks in their queue — only as many as "blocked" and "next" need.

When the budget runs out, whatever is left is listed in Coverage by name as not reached, and any value it would have supplied is written "not reached", never guessed.

## 4. Five things per person

For each attendee, collect the following. Each item gets a link and the date it happened.

1. **Done since the last meeting** — tasks closed or moved forward inside the window (name the transition, e.g. "→ QA"), pull requests merged or opened, reviews submitted, bugs filed or verified. For the user, add the time-tracker entries that match nothing else (an incident, a review, a call), cited as the time tracker since its entries have no link. **Attribute a change to a person only when the source names who made it** — a review's author, `mergedBy`, a comment's author, an actor in the status history. When the history gives the previous status but not the actor, attribute the change to whoever held the ball in that status according to the map, and mark it † (§6). When there is no history at all, a task's closing date (most trackers keep one) still proves a closure inside the window, but not who closed it; any other status is reported as the task's current state under 2 or 3, never as a transition. A change with no actor and no rule to apply goes under **Not attributed** (§6).
2. **Now** — the tasks where the ball is with the person according to the map, each with its due date or "no due date" and the state of its pull request. For an author that is usually "in progress"; for a tester or a reviewer it is the statuses the map gives to that role, and such lines carry † because the status rule, not the tracker's assignee, puts them there. A task "in progress" whose pull request waits on someone else's review is not *now* for its author: it belongs under 3.
3. **Waiting on / waited on by** — classify by where the ball actually is, using the classes in `teammate-check` §3: with the person, with someone else (who, and since when — from status history, or "since unknown"), blocked (on what, and what would unblock it). Every wait has two ends, and both people see it: list it once, in the shared **Hand-offs** section, rather than under each of them.
4. **Open questions** — questions addressed to an attendee, or to the team, that nobody answered: in task comments, pull-request review threads, the team channel and the direct messages. Questions asked inside the window, plus older ones still open. Before calling a question open, look for its answer on the other surfaces; a question in the channel is often answered in a direct message or a review thread.
5. **Next** — in this order of preference:
   - what the person wrote themselves about their next steps, inside the window — in any grammatical person, a plan they wrote in a task comment counts — quoted with its link;
   - otherwise the head of their queue: ready tasks by the map's priority, then by due date, marked as inferred;
   - when the previous cheat sheet exists, its **Next** for this person compared with what happened: each item done, still in progress, or not started.

A person with no trace on any source gets one line: "no trace in <sources read> since <window start>".

## 5. What may and may not reach the screen

- **Credentials never do.** No password, token, key, TOTP seed, reset or invitation link, or URL carrying a token in its query string — whatever `dm_content` says. A message that carries one is reduced to its fact: "<A> sent <B> access details for <environment>".
- **Direct messages** follow `dm_content` from the map: a fact without content by default, quotes only under `full`. Under either setting only what concerns this project reaches the sheet: a direct-message channel usually mixes several projects, and none of the others belongs on this screen. An opinion about a person — an attendee or anyone else — never does, under any setting.
- **The map is for routing only.** Project notes about people — assessments, access policies, contract details — locate sources; they are never content.
- **Facts, not judgements.** "Due 10 Oct, still in progress" — not "late" or "slow". A due date that has passed is stated with its date.
- **No actor without a source.** Who did, asked or decided something must be readable in a source this run read. A ticket's reporter is not automatically the person who hit the problem, nor a commit's author the person who decided the change.

## 6. Render and save

Conclusion first. The template shows the shape; every string in it is an example.

```markdown
# <Project> stand-up — Wed 14 Oct 2026 (since Mon 12 Oct 09:30)

## TL;DR
| Who   | Done since Mon            | Now (due)            | Waiting on              | Next              |
|-------|---------------------------|----------------------|-------------------------|-------------------|
| Alice | PROJ-12 merged; 2 bugs fixed | PROJ-14 (17 Oct)  | Bob: review of #318     | PROJ-15*          |
| Bob   | 3 reviews; PROJ-9 deployed | PROJ-20 (no due date) | —                     | "PROJ-21 on Mon"  |
| Carol | 4 tasks verified → closed† | BUG-41 retest†      | Dave: info on BUG-39    | PROJ-12 on test*  |

\* inferred from the queue, not stated by the person · † placed by the map's status rule, not recorded with the person

## Hand-offs — who waits on whom
- Alice → Bob: review of #318, since 13 Oct · <link>
- Carol → Dave: more information on BUG-39, since 9 Oct · <link>

## Open questions
- Alice in #318: "should the export include archived documents?" — unanswered since 13 Oct · <link>

## Alice
**Plan from last time:** PROJ-12 ✅ · PROJ-13 ⏳ still in progress
**Done:** …
**Now:** …
**Next:** …

## Bob
…

## Not attributed
- PROJ-30 closed Tue 13 Oct — the tracker records neither who closed it nor its previous status · <link>

## Coverage
Tracker: all task lists, status changes and comments since 12 Oct 09:30 (14 of 25 planned calls) · Team channel: back to 12 Oct · Direct messages: user ↔ Alice, Bob, Carol · Forge: open pull requests, merged since 12 Oct · Not read: …
```

Rules:

- A TL;DR cell holds about eight words at most, so it stays legible on a projected screen; the links and detail go into the person's section.
- **Hand-offs** and **Open questions** are shared sections because they are what a stand-up actually discusses. Each item appears once.
- Omit empty parts. **Plan from last time** appears only when a previous cheat sheet exists. **Not attributed** — changes inside the window that no source and no status rule ties to a person — goes after the people, only when it has items.
- A list longer than about eight items in a person's section shows a count and the first few by priority, with the rest inside a `<details>` block, so the screen stays readable while the file keeps everything.
- The legend under the TL;DR appears only for the marks actually used. There are two: * for an inferred **Next**, † for anything placed by the status rule.
- **Coverage** names each source with the window it was read back to, the sources not checked and why, and the calls spent against the plan.

**Save.** Write the cheat sheet to `<output_dir>/<meeting date YYYY-MM-DD>.md` and print it too. Before the first write, confirm the directory is ignored by version control (`git check-ignore <output_dir>`): the file can hold direct-message content and must never be committed. When it is not ignored, print only and tell the user why. A re-run for the same meeting overwrites that meeting's file — it is this skill's own output.

## 7. Afterwards

Offer, do not perform. A hand-off that waits on the user can go to `code-review`, `merge-pr` or `dm-catchup`; a nudge to someone else to `dm-compose`; a person whose runway looks short to `teammate-check`.

## Anti-patterns

| Shape | Why it fails |
|---|---|
| "Carol: nothing done" | Testing, reviews and calls often leave no trace on these surfaces. Write "no trace in <sources> since <date>". |
| "Carol closed four tasks" when the tracker never said who closed them | An actor without a source, shown to the whole team. Use the status history with the map's rule (†), or list it under Not attributed. |
| "PROJ-7 moved to QA on 12 Oct" read off the last-updated date | A comment moves that date too. Without status history, report the current status, not a transition. |
| "Next: PROJ-15" with no mark, taken from the queue | Reads as the person's commitment in front of everyone. Quote what they said, or mark the inference. |
| The same wait listed under both people | Doubles the item and invites two different readings. One line in Hand-offs. |
| An open question that was answered in a direct message | Read the other surfaces before calling it open. |
| Quoting a direct message with an access link | A credential projected to the room. Reduce it to the fact. |
| A week-long window because the meeting moved | Use the calendar's actual occurrences, and echo the window before reading. |
| One tracker query per person | The budget is shared; one bulk query covers the whole team. |

## Related

- `work-standup` — the user's own recap since the last stand-up, paste-ready for a channel.
- `teammate-check` — one person in depth from the lead's side: enough work, what waits on the lead, what to assign next. Shares its project map with this skill.
- `dm-catchup`, `dm-compose` — answering or starting a conversation that the cheat sheet surfaced.
