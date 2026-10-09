---
name: teammate-check
description: "Check on a teammate you lead: do they have enough work for the next hours, and what of theirs is waiting on you — reviews, merges, unanswered questions in direct messages, the team channel or the tracker, and your own drafts not yet posted. Works with any tracker, chat and forge; the project's own notes supply the specifics. Ends in a two-line verdict, the waiting items ordered by what they block, and the next work to assign, in depth when the runway runs short; nothing is assigned, sent or relabelled without a go-ahead. Use when the user says \"má <kolega> dost práce?\", \"čeká na mě <kolega>?\", \"čeká na mě někdo z týmu?\", \"co <kolegovi> přidělit dál?\", \"má tým co dělat?\", \"does X have enough work\", \"what should X work on next\", \"is X blocked on me\", \"what is waiting on me from X\". Not reading one conversation and replying — that is `dm-catchup`; not your own queue — that is `work-start`; not writing a check-in message — that is `dm-compose`."
argument-hint: "<person> [window, default today and the 2 preceding working days] [runway threshold, default 4 h]"
version: 1.0.0
license: MIT
---

# Teammate Check

A lead's two standing questions about someone they lead are "do they have enough to do?" and "are they waiting on me?". Both are answered from the same surfaces — the tracker, the forge, the direct messages, the team channel — and both go wrong the same ways: a surface not read, a status taken at face value, an absence claimed without naming the window that was searched. This skill reads them in one pass and turns them into a verdict the user can act on in a minute.

It reports; it does not act. Assigning work, replying, reviewing, merging and relabelling are each a separate step the user starts, and the step usually belongs to another skill (§7).

## 0. Inputs

- **Person** (required) — one teammate; for the whole team see *Team mode* at the end. Names may arrive misspelled (dictation, autocorrect): match tolerantly against the roster and say so when the match is not exact.
- **Window** — bounds the team channel and the tracker comments: today and the two working days before it (weekends and the user's public holidays skipped), from 00:00 in the user's timezone. For the direct-message channel only, it extends back to the user's own last message there when that is older, because that message is where "unanswered" starts — capped at 30 days, with anything older reported in Coverage as not read; the cap wins over any paging rule. Forge reads have no window: they take the open pull requests as they stand now, and Coverage gives the time of that read instead. An explicit window from the user wins.
- **Runway threshold** — default 4 hours of work the person can do without waiting on anyone.

## 1. Load the project's map — before calling any API

None of the following is in this skill; it belongs to the project.

**Look for a saved map first.** An earlier run may have left one: search the project memory and the team roster for a note that names this skill. Project memory is wherever the agent keeps per-project notes — often a directory with an index file listing them, such as `<harness-home>/projects/<slug>/memory/`. A saved map is a starting point, not a guarantee: list the workspace's task containers and chat channels once, compare them with the map, and report anything new — a board created after the map was saved is otherwise never scanned.

Without a map, read the project's instructions file (`AGENTS.md`, `CLAUDE.md` or equivalent), the project memory, and any team roster the project keeps (often a local, untracked notes file), and collect:

| What | Why it matters |
|---|---|
| The person's and the user's identity in each system (chat user, tracker member, forge handle) and the person's working language | Queries filter by them; a handle that exists in one system silently matches nothing in another |
| The direct-message channel with the person, and the team channel(s) to scan | A pinned id costs no API call and rules out reading a channel you merely hope is the right one |
| **Every** task container to scan — lists, projects, boards, the bug tracker included | Work assigned in a second list is invisible to a query of the first |
| What each status means and **who holds the ball** in it — for every container, since a bug tracker usually has a status set of its own | "review" is code review in one project and the tester's QA rung in the next. A status set read from the API gives names, not owners: when the project does not say, ask the user and record the answer |
| How pull requests reference tasks — an id in the title or branch, a closing keyword in the body, a link field | §3 finds a task's pull requests this way |
| Review-state labels on pull requests, if the project uses them | The label, not the review API, is often the only "waiting on the reviewer" signal |
| Where the user's unposted work lives — a review-findings folder, draft notes, memory | §4.5: the forge cannot see a draft |
| What the person may not be assigned (access, skills, contract) | A candidate in §5 that needs access the person lacks is not a candidate |
| Where priority lives (a field, a label, an order in the backlog) and which way is higher | §5 orders candidates by it |
| Task size — estimates on the tasks, or a calibration such as "a subtask is half a day to a day", and the hours in a working day when it is given in days | The only honest way to turn a task count into hours in §3 |
| Rate limits on the tracker or chat API, and whether other sessions share the budget | The call plan in §2 |

When entries are missing, ask the user once for the whole set, then offer to record it in the project's memory or roster as a note that names this skill, so the next run finds it. Never guess a channel or a container silently. The one exception is a run where the user cannot be asked: then read at most three candidate channels, label them in Coverage as candidates rather than the mapped team channel, and ask at the end which one it is.

## 2. Plan the calls

Probe which backends the session actually offers — a tracker (ClickUp, Jira, Linear, GitHub Issues, …), a chat (ClickUp chat, Slack, Teams, …), a forge (GitHub, GitLab, …) — and make the tools you need available in one round. A surface with no backend is reported as **not checked**, never as empty.

When an API is rate-limited, and above all when other sessions of the same account draw on the same budget, note the planned number of calls before starting (it goes into Coverage) and spend them in the order of what can change the verdict:

1. **Tasks** — one bulk query for the person's open tasks across the containers; one status-set read per container whose mapping the map lacks; with a saved map, one listing of containers and channels to compare against it.
2. **Chat** — the direct-message channel and each team channel back to the window's start (a single read with a generous limit often covers a week or more; page further only within the 30-day cap), plus one expansion per thread with replies inside the window.
3. **Forge** — the person's open pull requests by author in one call, then reviews, commits, comments and changed files per pull request; plus one search per in-progress task that has no pull request in that list, to catch a follow-up someone else opened.
4. **Dependencies** of the person's tasks that have not started, when the bulk query does not return them. This is usually the largest line, one call per task. A tracker without a dependency model has none to check.
5. **Task comments and status history** — only for the person's tasks updated inside the window, or a single mentions search when the tracker offers one.
6. **Candidates** (§5) — one query for open unassigned tasks, and dependencies in both directions for the ones picked; on an *enough* verdict this line goes last and may stay unspent.

Reserve a call per item for the cross-checks in §4: an answer looked up elsewhere, a third-party conversation, a message re-fetched before acting on it. When the reserve is spent, the remaining cross-checks are listed in Coverage as not done. When the budget runs out, whatever is left goes into Coverage by name as not reached, and any value it would have supplied (a dependency, a "since when") is written as "not reached", never guessed. Without a rate limit there is no plan, and Coverage lists the reads only.

## 3. Runway — what the person can work on next

Classify each of the person's open tasks by **where the ball actually is**, not by its status alone:

- **In progress, with the person** — they are working on it and nothing of it waits on anyone else. Cross-check with the forge through the link convention from §1. Never page the most recently updated pull requests instead: that drops a follow-up as soon as other pull requests are busier.
- **Ready** — not started, every dependency resolved, assignable to this person under the constraints from §1. When the budget did not reach a task's dependencies, it is **ready, dependencies unchecked**, counted separately and never silently as ready.
- **With the user** — waiting for the user's review, merge, decision or input. This includes a task "in progress" whose pull request waits on the user's review. Goes to §4 as well.
- **With someone else** — QA, a client's answer, another teammate, a reviewer who is not the user. Note who and since when. Without status history, or when the budget did not reach it, write "unknown" or "not reached" rather than substituting the last-updated date, which any comment moves.
- **Blocked** — an unresolved dependency, or an external wait with no owner. Also *soft* blocks: the task should not start yet because it collides with a pull request in flight or its description is known to be wrong. And a task assigned against the person's constraints, which needs reassignment rather than work. Say what would unblock each.

**Hours.** The runway is the ready work plus what remains of the work in progress with the person. Convert it with the project's estimates or calibration into hours, as a **range with its basis** ("2 ready tasks × 4–8 h ≈ 8–16 h, project calibration of half a day to a day at 8 h a day"). What remains of a task in progress comes from its estimate minus what is visibly done, or it is "unknown remaining". Tasks with the user or with someone else count as zero; *ready, dependencies unchecked* counts toward the upper bound only. When the calibration is a quoting or billing scale, or was measured on a different kind of task (feature subtasks against bug tickets), say so next to the range. The person's own velocity is usually not recorded anywhere, so do not invent one.

**Verdict:**

- **enough** — the lower bound reaches the threshold;
- **thin** — there is work, every part of it is bounded, and the lower bound stays below the threshold;
- **dry** — nothing ready (dependencies checked or not) and nothing in progress with the person;
- **unknown** — the bounded part stays below the threshold and something cannot be bounded: no estimates or calibration, an "unknown remaining", dependencies unchecked. Report the counts instead of hours.

An agreement found during the sweep, such as a work order in the direct messages, decides the order of the runway and is quoted in the report.

The trap this section exists for: four open tasks read as "busy", while three of them sit with the reviewer and the fourth waits on a dependency — a teammate with nothing to do. Its mirror image is just as wrong: one large task in progress and nothing else assigned is not "dry".

## 4. Waiting on you — four surfaces and your own drafts

Read every source. For each item record what is asked, where (a link), since when (convert timestamps with a command, never in your head), and the kind of action it needs: **review**, **post** (the work is done and only needs publishing), **merge**, **answer**, **decide** or **unblock** (access, data, a missing input).

1. **Forge.** Open pull requests by the person where review was requested from the user, where a review-state label says the reviewer is up, or where commits arrived after the user's last review. Also the person's replies in the user's review threads that nobody answered, and approved pull requests that wait on the user to merge.
2. **Tracker.** The person's tasks in a status where the ball is with the user (§1) or blocked on the user's decision, and comments on them inside the window that mention the user or ask a question nobody answered.
3. **Direct messages.** Messages from the person after the user's last message, threads included: expand every thread with replies before claiming anything is unanswered. The reading rules of `dm-catchup` apply — page back to the last message you know (within the 30-day cap from §0), name the window you reached, and re-fetch a message right before acting on what it says.
4. **Team channel.** Inside the window: messages from the person, messages mentioning the user, and questions the person put to the channel that nobody answered — a question to "anyone" left hanging lands on the lead. Expand threads here too.
5. **The user's own pending work** — at the place §1 names: a review written but not posted, a reply drafted but not sent, a decision promised to the person. None of it shows on the four surfaces. The forge says "review requested" while the review may be one approval from done, and then the action is **post**, not **review**.

**Before calling an item open, look for its answer on the other sources.** A question asked in the channel is often answered in the direct messages, a review comment in a call. When an item waits on a third party, such as a decision the user asked someone else for, the user's own conversation with that party is a source too. When the answer rests on repository state, read the remote's default branch, through the forge API or after a fetch, not a local checkout.

**Absence is a claim.** "Nothing is waiting on you" has to name the window each source was read back to, and say which sources were not reached.

## 5. Next work to assign

Always runs; its depth follows the verdict. On *thin*, *dry* or *unknown*, propose up to three candidates with every check below. On *enough*, name only the one or two next in line, so the user can line them up before the runway runs out, and check their dependencies only if the budget allows — otherwise mark them "dependencies unchecked".

Candidates come from two places:

- **Tasks that exist** — open, with every dependency resolved, within the person's constraints, and either unassigned or assigned to the user and delegable, meaning they need none of the user's access, authority or knowledge that the person lacks.
- **Work that is not a task yet** — review follow-ups, deferred findings and to-dos sitting in the user's notes or memory (the place §1 names). Propose it as "file and assign", with the text the task would carry, and never as an existing task.

Leave out anything that collides with what the person has in flight, judged from the changed files of their open pull requests and the task descriptions. Order the candidates by the project's priority, then by how much downstream work each one unblocks. For each: one line on why, and the estimate with its basis.

Then ask the user the one question the tracker cannot answer: **is there an agreement — a meeting, a call, a message not read here — about what the person does next?** Plans made outside the tracker are invisible to this sweep, and a recommendation that ignores yesterday's agreement is worse than none. If the user is not available to answer, put the assumption ("no agreement outside the tracker") right next to the candidates.

## 6. Report

In the user's language, conclusion first. The template is an example of the shape, not a literal to emit:

```
<Person> — runway: <enough | thin | dry | unknown>, ~<range or counts> (<basis>)
Waiting on you: <N> actions (<what they cover: pull requests, tasks, messages, drafts>; oldest: <age>, <what>)
```

Count actions, not objects, and give each action one kind from §4. Approving ten pull requests in one sitting is one *review* action, and answering three questions in one thread is one *answer* action. Three questions in three places are three actions, and so are reviewing five pull requests and merging three others: one *review*, one *merge*. The grouping is for counting only; approvals in §7 are per write.

Then:

1. **Waiting on you** — in this order: what stops the person now (when the runway is thin or dry), then what unblocks their tasks, then the rest by age. Each item gets its action and link.
2. **Runway** — the tasks by class from §3, as a compact table: task, class, where the ball is, since when.
3. **Next work** — from §5: the full candidate list when the runway is short, one or two lines when it is enough.
4. **Coverage** — each source with the window it was read back to, sources not checked and why, and the calls spent against the plan.

Close with one recommendation: the single thing to do first, chosen by the same order. It is rarely the most interesting item.

## 7. Hand-off — only on an explicit go-ahead

Offer the next steps and perform none of them unprompted. An approval covers exactly the writes it names: "do the first one" on an action that covers ten pull requests is not a go-ahead for ten posts.

- **review** → `code-review`
- **post** → show the saved draft, then publish it as it stands; do not redo the review
- **merge** → `merge-pr`
- **answer** in the direct messages → `dm-catchup`; in the team channel, a pull-request review thread or a task comment → draft the reply in that thread under the same drafting and approval rules
- a check-in or heads-up the person has not asked for → `dm-compose`
- **decide** and **unblock** → the user acts; hand over what the sweep found
- assigning a candidate, filing work that is not a task yet, changing a status, setting a label → only after the user names the task and the change; then read the task back to confirm it took

## Team mode

For "the team": load one map and make one call plan for everyone, with the budget split across the people. Read each team channel once rather than per person. Run §3–§5 per person, and never propose the same candidate to two people. Report per person, under a one-line summary: who is thin, dry or unknown, and how many actions wait on the user in total.

## Anti-patterns

| Shape | Why it fails |
|---|---|
| "Four open tasks — busy" | Counted by status. Three wait on the reviewer and one on a dependency; classify by where the ball is (§3). |
| "Runway: dry" for someone deep in one large task | Work in progress left out of the runway; §5 then piles tasks on someone fully loaded. |
| "No reply from them" after reading the channel's top level | The answer sits in a thread, or arrived between two reads. Expand threads, page back, name the window. |
| Scanning only the main task list | The bug tracker or a second board holds half of the assignments. |
| "Ten pull requests await your review" when the reviews are already written | The forge cannot see a draft. Read the user's own pending work (§4.5); the action is to post, and it takes minutes rather than an evening. |
| "About six hours of work" with no basis | A number without its source reads as measured. Give a range and its source, or say the hours are unknown. |
| Recommending the next task without asking about agreements | The plan was settled in yesterday's call, and the recommendation contradicts it. |
| Assigning the obvious candidate "to save a step" | The tracker notifies a real person, and the choice is the user's. |
| A source with no backend reported as "nothing there" | *Not checked* is a different finding from *empty*. |

## Related

- `dm-catchup` — read one conversation and draft the reply.
- `dm-compose` — write a message the user initiates: a check-in, a nudge, a heads-up.
- `work-start` — the user's own queue for the day.
- `code-review` — perform a review this check found waiting; `merge-pr` — merge one it found approved.
- `task-delivery` — carries one task through to merge; its status-check paragraph covers one task in depth, while this skill covers one person across all of their tasks.
