---
name: critical-path
description: "Find the critical path through a project's open tasks — the longest chain of not-yet-done dependent tasks, by steps and by estimated hours — plus the tasks that block several others and the waits that leave the tracker, from one cheap bulk fetch (ClickUp REST with a personal token: one request per 100 tasks, dependencies included). Use when the user asks \"jaká je kritická cesta\", \"kritická cesta v úkolech\", \"co blokuje dokončení\", \"na čem stojí termín\", \"what is the critical path\", \"longest dependency chain\", \"what is blocking the finish date\". Not drawing the dependency graph — that is `dependency-diagrams`; not estimating the tasks — that is `task-estimate`."
license: MIT
---

# Critical path

Answer "what bounds the finish date" from the tracker's own dependency data: the longest chain of open dependent tasks, the tasks that hold up several others, and the waits that point outside the tracker. The answer is only as good as the dependencies and estimates recorded, so the coverage is part of the answer, not a footnote.

## Step 1 — Resolve the scope

Which tracker and which list or board. **Project-specific coordinates (list ids, which list holds delivery work) live in the project's memory or AGENTS.md — read them there and never write them into this skill.** On a first run, ask and record the answer in project memory.

## Step 2 — Fetch, cheaply

**ClickUp, with a personal API token (preferred):**

```bash
python3 "$SCRIPTS/clickup_fetch.py" --whoami          # verify the token
python3 "$SCRIPTS/clickup_fetch.py" <list_id> -o tasks.json
```

(`SCRIPTS` = this skill's `scripts/` directory.) One request per 100 tasks, subtasks and closed tasks included, and every task carries its `dependencies` array. The REST API is metered per token per minute, not against the MCP integration's daily call cap, so a fetch costs nothing from the budget other sessions depend on. Write `tasks.json` somewhere git-ignored or temporary: it is a point-in-time dump of the tracker, not project content.

The token comes from `CLICKUP_API_TOKEN` or the macOS Keychain item `clickup-api-token` (`--keychain-service` overrides the name). The user creates it in ClickUp under Settings → Apps → API Token and stores it **from a real terminal**: `security add-generic-password -a "$USER" -s clickup-api-token -U -w`. Run through an agent's `!`-style shell, which has no TTY, the interactive prompt reads empty input and stores an empty password; the first call then fails with `Authorization header required`, and `--whoami` reports the missing token. Never ask for the token in the chat.

**ClickUp without a token (MCP):** the bulk task search returns statuses but not dependencies, so edges cost one task read per task — the whole list's worth of calls against a daily cap shared with every other session. Say the cost and ask before doing it, and suggest the token instead.

**Other trackers:** build the model input below yourself — GitHub "blocked by" relations or `Blocked-by: #N` lines, Jira "Blocks" issue links, or a CSV/JSON export with the user's column mapping.

```json
{"tasks": [{"id": "a1", "label": "API-01 Auth endpoints", "status": "open",
            "who": "ana", "due": "2026-03-12", "estimate_h": 6}],
 "edges": [{"from": "a1", "to": "b2"}]}
```

`status` is `closed` for done work and anything else otherwise; `from` is the prerequisite. `who`, `due` and `estimate_h` are optional. A `model.json` written by `dependency-diagrams` already fits.

## Step 3 — Compute

```bash
python3 "$SCRIPTS/critical_path.py" tasks.json --edges
```

It drops closed tasks and their edges, then prints the coverage line, the longest chain by steps and by estimated hours, the open tasks blocking two or more open tasks, open tasks waiting on something outside the input, and with `--edges` every edge between open tasks with a flag on each dependent whose due date is not after its prerequisite's. Keep `--edges` on whenever the chains are short: several chains of equal length are common, the script prints an arbitrary one of them, and the edge list is the only output that shows all of them.

## Step 4 — Read it, then report

**Read the coverage line first.** The hours-weighted chain is only as good as the estimates: when most open tasks have none, it is mostly the tasks that happen to be estimated, and the step chain is the more honest answer. Report the coverage with the result ("12 of 40 open tasks have an estimate") rather than presenting either chain as *the* critical path. And do not take a planning step for granted — an estimating pass that was supposed to fill every open task may have filled a fraction of them, and only the fetched data says which.

**A short chain on a large open backlog is a finding, but an ambiguous one.** Either the remaining work really is independent, or dependencies stopped being recorded for newer tasks. The data cannot tell which, so ask the user instead of choosing.

Then lead with what someone can act on:

- **The task that blocks the most** — a hub holding up two or more open tasks usually matters more than the end of the longest chain.
- **Who holds the ball on each link.** Read it from the status, not the assignee: a prerequisite in review waits on a reviewer, not on its developer, and a chain stuck there is a review-queue problem.
- **An unassigned task on a chain**, and **a dependent due no later than its prerequisite** (the `--edges` flag) — unless both are already in review, that schedule cannot hold.
- **Waits that leave the tracker** — a prerequisite in another list or tracker, or one that is a document or decision from someone outside the team. The script lists the first kind; the second you see only from the task names, so read them.

Report in a table or a short list per chain, each task with its status, assignee, estimate and due date, and close with the coverage caveat and the question about missing dependencies when it applies.
