---
name: dependency-diagrams
description: "Generate task-dependency diagrams from any tracker (ClickUp, GitHub, Jira, Todoist, or a CSV/JSON export): full dependency graph with transitive reduction, group/epic overview, and per-phase detail diagrams, exported as .drawio + SVG + PNG into a dated snapshot directory. Use when the user asks to generate, regenerate, or update task dependency diagrams / graphs (\"vygeneruj diagramy závislostí\", \"dependency graph snapshot\", \"task dependency diagrams\")."
license: MIT
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
  scratchpad) — the per-task payload includes the full description, so pulling
  ~70 of them into the main context is what you are avoiding. Each edge appears
  in **both** endpoint tasks' arrays → dedup `(task_id, depends_on)` pairs;
  `depends_on` is the prerequisite. That redundancy is also your safety net:
  if some tasks fail to fetch, their edges still arrive from the other side.
  Include uncoded follow-up tasks too (give them explicit short labels +
  `"wide": true`) and fetch **their** dependency arrays as well — an edge
  between two follow-ups is invisible from the coded tasks' side.
  `clickup_filter_tasks` does not return a task's parent; when you need the
  epic a task hangs under, `clickup_search` returns it in `hierarchy.task`
  far more cheaply than `clickup_get_task`.
  **Rate limit:** a full-list fetch of this shape (~70 `clickup_get_task`
  calls) can trip a workspace-wide hard limit that blocks *writes and reads*
  for hours. Budget it: fetch once, cache the fragments, and do any ClickUp
  edits (renames, new dependencies) **before** the fetch, not after.
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
done
```

(Skip `model.json` itself in the loop if it matches the glob.)

**Export with a watchdog — never call `drawio -x` synchronously.** The draw.io
CLI (at least on macOS) writes the output file correctly and then leaves its
Electron process alive, so the call never returns and the export looks hung.
Killing it blindly is worse than waiting: it discards the file in progress and
each restart pays another cold start. Run it in the background instead, poll
the output until it exists and stops growing, then kill that PID — ~6 s per
file instead of minutes:

```bash
export_one() {   # export_one <src.drawio> <out> <drawio flags...>
  local src="$1" out="$2"; shift 2
  [ -s "$out" ] && return 0
  drawio -x "$@" -o "$out" "$src" >/dev/null 2>&1 &
  local pid=$! waited=0 last=0 size=0
  while [ "$waited" -lt 180 ]; do
    sleep 3; waited=$((waited + 3))
    if [ -f "$out" ]; then
      size=$(stat -f%z "$out" 2>/dev/null || stat -c%s "$out" 2>/dev/null || echo 0)
      [ "$size" -gt 0 ] && [ "$size" -eq "$last" ] && { kill "$pid" 2>/dev/null; return 0; }
      last="$size"
    fi
    kill -0 "$pid" 2>/dev/null || break
  done
  kill "$pid" 2>/dev/null
  [ -s "$out" ] || echo "FAILED: $out"
}

for d in <prefix>-*.drawio; do
  n="${d%.drawio}"
  export_one "$d" "$n.svg" -f svg
  export_one "$d" "$n.drawio.png" -f png --scale 2
done
```

Put the whole pipeline in a script file and run it as one `bash script.sh` — in
a worktree-isolated session a compound loop typed straight into the shell tool
is rejected as unverifiable.

### Optional — task names inside the nodes

By default a node shows only the task code, which forces the reader to keep the
tracker open. To add the name on a second, smaller line, post-process the
generated `<prefix>-*.json` between `gen_diagrams.py` and `autolayout.py`: node
styles carry `html=1`, so labels accept markup. Append
`<br><font style="font-size:9px;color:#5a6672">Short name</font>` to each label,
widen the node to ~190 px and add ~14 px of height per wrapped line of the name
(ghost nodes one font step smaller, ~165 px wide; overview nodes take the full
group name plus the task count). Carry the names in `model.json` as a `name`
field per task — `gen_diagrams.py` ignores unknown fields, and the
post-processor maps them onto node ids.

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
