---
name: task-estimate
description: "Use when open tracker tasks need time estimates — or start and due dates so that a Gantt or timeline view means something — and the numbers should come from what comparable work in the same project actually took, not from a guess; also when past estimates are to be checked against outcomes. Triggers: \"odhadni tasky\", \"dej taskům estimace\", \"kolik to zabere\", \"jak dlouho trvaly dokončené tasky\", \"naplánuj to do Ganttu\", \"stihneme to do termínu?\", \"estimate the open tasks\", \"add time estimates\", \"schedule these for the Gantt chart\", \"how long did our tasks take\", \"recalibrate the estimates\". Not founding the tasks — that is `epic-breakdown`; not whether one teammate has enough work for the next hours — that is `teammate-check`; not filling a timesheet — that is `work-reconcile`."
license: MIT
---

# Task Estimate

An estimate is a measurement of a reference class, not an opinion about one task. The project's own history — merged pull requests, the days people committed to them, tracked hours where they exist — says what each kind and size of change costs; this skill turns that into one number per task for the tracker, keeps the range and its basis beside it, and, when dates are wanted, schedules the work against each person's real capacity.

Three rules carry most of the accuracy, because an unaided estimate breaks exactly these:

- **The estimate and the capacity it is scheduled against are in the same unit.** Hands-on hours scheduled against an eight-hour day finish early by construction.
- **Whatever gets summed is an expected value, not a median or a "most likely".** Effort is right-skewed; on the calibration project the class means were 1.3–1.8× the medians, and a plan built from medians came out 28 % shorter than what really happened (backtest, 2026-10-15).
- **A recent burst is not a new rate.** A few fast days usually mean longer days or many parallel pull requests, and the slow ones are still open.

## 0. Load the project's map

Nothing project-specific lives in this skill. Look for a saved note naming this skill in the project memory or the instructions file (`AGENTS.md`, `CLAUDE.md`); without one, collect:

| What | Why it matters |
|---|---|
| Per person: forge login, whether their time is tracked (and where), or whether commits are the only trace | Decides the calibration method for that person (§1) |
| Per person: hours per week on this project for the planning window, minus code review, meetings and recurring unplanned work; announced absences | The one schedule input not measured from history. Ask; do not infer it from the tracker |
| Task containers, and which statuses mean "not started", "in code review", "implementation done" | §2 decides what gets an estimate |
| What a due date means here (end of implementation, of QA, of delivery) | Sets where the review latency goes |
| The unit of the tracker's estimate field, and any client-facing scale that must never leak into it | A sales multiplier written as effort corrupts every later calibration |
| Tasks not to schedule, existing estimates and dates someone set by hand | §6 changes only what the user approved |
| Holidays, the tracker API budget, where calibration and the estimate log live | Per-person data stays local and untracked |

Ask once for whatever is missing, then offer to save the answers as a note naming this skill.

## 1. Calibrate

Do this when no calibration is younger than about a month, when task granularity changed (many small subtasks or bug tickets replacing large tasks), or when asked. Run:

```
python3 scripts/calibrate.py --repo OWNER/NAME --since YYYY-MM-DD --commit-authors LOGIN[,LOGIN] \
  --tz Area/City --holidays YYYY-MM-DD,... [--time-entries export.json --key-regex '...'] --out calib.json > calib.md
```

(`--help` lists the rest. The time-entry export is a list of `{description, start, seconds}`.) Read the output with these rules:

- **Commit-attributed effort is in person-days of capacity.** Convert to capacity hours with the project's day length, and schedule that person at day length × availability — never at day length alone, and never against hands-on or session hours.
- **Use class means for anything summed; P50–P80 is the range.** Before relying on the table, backtest: re-plan the merged pull requests of the window with the class means and the availability; the result should land within about 10 % of the real window. If it does not, find out why first.
- **Class means come from the whole window (variant B); the recent rate enters as velocity, not as new class means.** A month whose day looks different (far more commits per day, longer spans) or that has many open pull requests is not evidence that a change got cheaper — never re-derive class means from a handful of recent days. But it can be evidence that the person now works longer days. The script's velocity table answers that: the class-mean estimates of the work merged per working day. When the last three to four weeks differ from the window figure, schedule that person at the recent velocity (§4), and write their estimates in hours of the current day: class mean × day length / recent velocity. Say which velocity was used and why it differs.
- **Below 10 core lines is not cheaper than 10–50**: translation-, test- and CI-only changes have their own class row; use it. Classes with fewer than five samples are not a calibration — split such a task instead. When a class mean falls below its P50, the range starts at the mean.
- **Availability: a recent full month minus announced absences**, not the window blend, which absorbs holidays.
- **Review cost: the aggregate per merged pull request** (it includes batch reviews booked without a PR number), not the per-PR attribution alone. **Lead time** from opening to merge is what a due date must allow after implementation.
- **Tracked hours per task key are lower bounds**: work booked under another description is missing. A tracked person's own pull requests often show no hours of their own, because entries name the task, not the PR — add the key hours to the PR hours. Build that person's classes by kind of work (application subtask, docs-only, infrastructure S/M/L) from the closed keys and compute a mean per class; where a class has fewer than five closed keys, use the fallback bands in §3.6 for its range.

Write the result as a dated calibration note in the project's local folder, then **refute it before use**: give a fresh-context agent the note, the raw dumps and the contract "these numbers will schedule real work — find what is wrong", and record the outcome in the note's header.

### When the calibration does not fit the project

The method is general; `calibrate.py` was built on one Python/Django and JavaScript project on GitHub, and it measures nothing where these assumptions fail. Check them before the first calibration on a new project, and suspect them first when the backtest misses.

- **GitHub pull requests are the only source.** The script reads them through `gh`. On another forge, or where work lands by direct pushes, there is no change-set history to measure; estimate from tracked hours alone, or from the fallback bands (§3.6) with the probabilities labelled as guesses, and say that no calibration exists.
- **One change set per task.** The size classes describe pull requests. Large batch pull requests that close many tasks, or many tiny ones per task, make the class means describe something other than a task; split or merge them by hand in the analogue lookup and say so.
- **Test and migration paths are recognised by pattern.** The defaults fit Python and JavaScript (`test_*.py`, `*_test.py`, `*.spec.ts`, `/tests/`, `/migrations/`). For other stacks pass `--test-regex` and `--migration-regex` (Go `_test\.go$`, JVM `(^|/)src/test/`, Rails `(^|/)db/migrate/`) and `--generated-regex` for build output, or tests are counted as core lines and every pull request moves up a size class. Look at the per-bucket line counts in the JSON output: core lines in obvious test files mean a pattern is missing.
- **Size classes are fixed line counts** (below 10, 10–50, 50–200, 200–600, 600–2000, above). Where a line costs very differently — infrastructure code, configuration, generated schemas — most pull requests can land in one or two classes, and a table that does not discriminate is not a calibration. Say so rather than estimate from it.
- **Commit-attributed effort assumes that commit days are working days on this project.** People who commit rarely and in batches, or who split their days across projects, appear as low availability and high effort per pull request. Prefer tracked hours for them, or ask how their week is divided.
- **History needs volume.** A class with fewer than five merged pull requests is not a calibration (§1), so a young project or a new person gets ranges from the fallback bands, labelled as such.

## 2. Select the tasks

- **Not started, or in progress with no change set yet**: estimate.
- **The change set exists** — in code review, or already merged while the task stays open for a rollout or a verification step: the estimate is post hoc — the class mean of the actual change set's size. Record it with `post_hoc: true` (it never enters recalibration) and schedule only what is left: the review wait plus the mean post-review effort for that size (about half an hour when the fixes are already pushed), or the remaining step. A task sent back from QA after its change merged is estimated as the rework change set only.
- **Implementation done** (in QA, closed): no estimate and no new dates. A number written after the fact is a measurement, and it would teach recalibration nothing.
- **Parents and epics**: never; roll-ups double-count.
- **Conditional tasks** (to be done only if something happens) and tasks the project map says not to schedule: estimate, no dates.

Read each task's description **and its comments**; scope changes are usually in the comments. For a task in code review, the pull request's description and review threads stand in when the comments were not fetched.

## 3. Estimate one task

1. The unit of work is the change set (pull request) that will close the task. When one change set closes several tasks, estimate the change set and split its cost by sub-scope, so the parts add up to the whole.
2. Find one to three closed analogues — same area, same kind of change — and look up their size and effort in the calibration output.
3. When the description leaves scope open, read the code it touches: how many call sites, whether a data migration or a permission change is involved, whether a base class many things inherit from moves. A scope surprise changes the class, not the hours by a fifth. When the reading shows the written scope cannot reach the task's own goal, that goes to the task's owner before any scheduling; estimate the expected value over "as written" and "what the goal needs" meanwhile.
4. Class mean = the estimate; the class P50–P80 = the range. Move only with a written reason, anchored on the closest analogue's measured effort (a new integration surface → towards the upper end; an analogue to copy → towards that analogue, even below the class P50). A reason that already chose the class does not move the estimate again.
5. A decision is meeting or message time — use the tracked mean for decision calls and messages, and a quarter of an hour when there is none. When the work after it depends on the outcome, estimate each plausible outcome, use the probability-weighted mean as the estimate and the spread of the outcomes as the range, and label the probabilities as guesses. A decision another person's task waits on — by a tracker edge or only by the text of either task — becomes its own scheduled step for the person who decides, with an edge to the waiting task, and goes first.
6. Fallback bands where a tracked person's class has too few samples: S ≤ 1 h · M 2–6 h · L 15–30 h (infrastructure); propose a split for L. The bands were measured on one project's infrastructure work, so they are a prior, not a calibration: say in the task's reason that the band was used, and replace them with the project's own class means once a class has five closed samples. A task that should be split but is not yet gets the sum of the proposed parts.
7. A task with two assignees gets one estimate per person in that person's unit, scheduled as two steps with an edge in the order the work happens; the tracker field carries their sum in hours, and propose splitting the task. A person with no time data at all gets an expected value over the fallback bands, with the probabilities labelled as guesses, and no dates unless the user supplies their capacity. An unassigned task is estimated in the most likely assignee's unit, labelled so.
8. A hand-set estimate already inside your range stays; propose a change only when it falls outside.
9. Record per task: estimate, range, class, analogues, reason, `post_hoc`, and the remaining hours (equal to the estimate for unstarted work).

## 4. Schedule

Only when dates are wanted. Build the input and run `python3 scripts/schedule.py spec.json --table` (the script's docstring has the format; `--self-test` checks it). Feed it:

- `start` = the next working day, the holidays, a `milestone` if there is one;
- per person `hours_per_day` = plannable capacity in the estimate's unit (§0, §1) — for a person scheduled at their recent velocity, the day length, since their estimates were already converted to hours of the current day;
- `review.latency_days` = the lead-time P50 in working days, with the reviewer in `skip_for` if their own changes merge without waiting;
- per task the **remaining** hours (an estimate for unstarted work, one fix round for work in review), priority, the tracker's dependency edges, and a `not_before` date wherever the task text says it may not start earlier. An edge to a task outside the plan — closed, or already past implementation — counts as satisfied.

A task flagged after the milestone is the finding, not a defect: never raise capacity or trim estimates until the plan fits.

## 5. Present for approval

One table per person: task, status, estimate, range, class and analogue, start, due, after-milestone flag. Then the totals against each person's capacity up to the milestone, what was not estimated and why, every existing estimate or date that would change (old → new), and the tracker calls the write will cost. Nothing is written before an explicit go-ahead.

## 6. Write

- One update per task carrying the estimate and both dates, where the tracker accepts them together. Writes go before any bulk read; on a rate-limit error stop, do not retry, and list what is unwritten.
- Change hand-set estimates and dates only where the user approved it in §5.
- Re-read two or three of the written tasks to confirm the values landed.
- Append every estimate to the local log as one JSON line: task id, date, assignee, estimate, range, class, analogues, `post_hoc`.

## 7. Recalibrate

Monthly, or once a batch of logged tasks has closed: measure their actual effort with the §1 method (for people without tracked time, commit attribution is the only actual there is) and compare it with the logged estimate, leaving out `post_hoc` entries. If more than a third are off by more than 2×, run §1 again, refute it again, and note in the project's map what changed.

## Common mistakes

| Mistake | What it does | Instead |
|---|---|---|
| Hands-on hours scheduled at a full working day | The plan finishes early by construction | One unit for estimate and capacity |
| Summing medians or "most likely" values | About a quarter too short over a batch | Class means, range beside them |
| Rate taken from the last few days | Different day length, censored slow work | Whole window by size class |
| Estimating work already in QA | Hindsight enters the calibration | Skip; dates stay as they are |
| Tuning capacity until the milestone fits | A schedule that hides the overflow | Report what lands after the milestone |
| A client-facing scale in the estimate field | Every later comparison is off by the multiplier | Effort in the project's real unit only |
