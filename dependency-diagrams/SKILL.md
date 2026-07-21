---
name: dependency-diagrams
description: "Generate task-dependency diagrams from any tracker (ClickUp, GitHub, Jira, Todoist, or a CSV/JSON export): full dependency graph with transitive reduction, group/epic overview, and per-phase detail diagrams, exported as .drawio + SVG + PNG into a dated snapshot directory. Use when the user asks to generate, regenerate, or update task dependency diagrams / graphs (\"vygeneruj diagramy závislostí\", \"dependency graph snapshot\", \"task dependency diagrams\")."
---

# Task-dependency diagrams

Turn a task tracker's dependency data into a consistent set of diagrams:

1. **Full graph** — every task, grouped by group/epic, transitively reduced
   (an edge A→C is dropped when a longer path A→…→C exists).
2. **Overview** — one node per group, clustered by phase/milestone; edge
   labels count the underlying task dependencies.
3. **Per-cluster details** — one diagram per phase/milestone: its tasks plus
   grey dashed "ghost" nodes for upstream dependencies from earlier phases.

The pipeline is **source-agnostic**: fetching is your job (step 2, per-source
recipes below); rendering is deterministic via the bundled scripts.

## Prerequisites

- Graphviz `dot` on PATH (`brew install graphviz` / `apt install graphviz`).
- draw.io CLI for SVG/PNG export: `drawio` on PATH or the desktop app binary
  (macOS: `/Applications/draw.io.app/Contents/MacOS/draw.io`). If missing,
  still produce `.json` + `.drawio` and tell the user exports were skipped.
- Python 3 (stdlib only).

## Step 1 — Resolve source and scope

Determine which tracker and which task set. **Project-specific coordinates
(list/board IDs, group structure, label conventions, output directory) belong
in the project's memory or AGENTS.md — read them from there; never hardcode
them into this skill.** If this is the first run for a project, ask the user
for: source, scope (list/board/label), grouping (epics? labels? prefixes?),
and where snapshots live — then record the answers in project memory.

## Step 2 — Fetch tasks and dependency edges

Collect for every task: stable `id`, short `label` (the task's code like
`INFRA-01` if the project uses codes, else a concise name), `group`, and
`status`. Collect edges as *prerequisite → dependent* pairs.

Per-source recipes:

- **ClickUp (MCP):** `clickup_filter_tasks` with `list_ids`, `subtasks: true`,
  `include_closed: true` returns names + statuses but **not dependencies** —
  paginate (100/page). Dependencies require per-task `clickup_get_task` with
  `include: ["dependencies"]`. For large lists fan the per-task calls out to
  parallel subagents (~20 IDs each, each writing a JSON fragment to the
  scratchpad). Each edge appears in **both** endpoint tasks' arrays → dedup
  `(task_id, depends_on)` pairs; `depends_on` is the prerequisite. Include
  uncoded follow-up tasks too (give them explicit short labels + `"wide": true`)
  and fetch **their** dependency arrays as well — an edge between two
  follow-ups is invisible from the coded tasks' side.
- **GitHub:** `gh api graphql` on issues — native "blocked by" relations where
  available, else task-list checkboxes (`- [ ] #123`) or `Blocked-by: #123`
  lines in bodies; group by label/milestone.
- **Jira:** issue links of type "Blocks" via MCP or REST
  (`/rest/api/3/search?fields=issuelinks,status,labels`); group by
  epic/component.
- **CSV/JSON export:** ask the user for the column/field mapping, then
  normalize directly.

## Step 3 — Normalize into model.json

Write `model.json` (in the scratchpad or the working directory):

```json
{
  "prefix": "vault",
  "direction": "LR",
  "clusters": {
    "phase-1": {"title": "Phase 1 — Foundation", "groups": ["INFRA", "AUTH"]},
    "x":       {"title": "Cross-cutting",         "groups": ["ARCH"]}
  },
  "tasks": [
    {"id": "abc123", "label": "INFRA-01", "group": "INFRA", "status": "closed"},
    {"id": "def456", "label": "FU: audit wiring", "group": "AUTH",
     "status": "open", "wide": true}
  ],
  "edges": [{"from": "abc123", "to": "def456"}]
}
```

Status mapping: done/complete/closed → `closed` (green ✓); anything actively
in flight — in progress, in review, ready for CR, testing — → `in_progress`
(blue ▸); everything else → `open` (white). Note the collapse of
review-like states into `in_progress` in your summary so the user can ask
for a finer split. `clusters` is optional — without it you get the full graph
and a flat overview, no detail diagrams.

## Step 4 — Generate and export

From the directory holding `model.json` (`SCRIPTS` = this skill's `scripts/`
directory):

```bash
python3 "$SCRIPTS/gen_diagrams.py" model.json --outdir .
for f in <prefix>-*.json; do
  n="${f%.json}"
  python3 "$SCRIPTS/autolayout.py" "$f" -o "$n.drawio"
  drawio -x -f svg -o "$n.svg" "$n.drawio"
  drawio -x -f png --scale 2 -o "$n.drawio.png" "$n.drawio"
done
```

(Skip `model.json` itself in the loop if it matches the glob.)

## Step 5 — Snapshot directory and verification

- Place the set in a dated directory, e.g. `docs/task-dependencies-<DATE>/`.
  **The date names the day whose end-of-day state the snapshot captures** —
  a run early in the morning gets *yesterday's* date, not today's.
- Keep only the latest set: after verifying the new directory (same file-name
  set as the previous one, no empty files), delete/`git rm` the old dated
  directory — but only after the user confirmed or previously asked for it.
- **Verify visually:** render one detail PNG and check statuses, new nodes,
  and new edges against what the fetch reported.
- Update any docs index that lists the dated directory (e.g. `docs/README.md`)
  and re-check the project's knowledge file still describes the set correctly.
- Offer a commit following the project's workflow; report node/edge counts
  and what changed since the previous snapshot (new tasks, status moves,
  added/removed edges).
