---
name: dependency-diagrams
description: "Generate task-dependency diagrams from any tracker (ClickUp, GitHub, Jira, Todoist, or a CSV/JSON export): full dependency graph with transitive reduction, group/epic overview, and per-phase detail diagrams, exported as .drawio + SVG + PNG into a stable snapshot directory that is regenerated in place. Use when the user asks to generate, regenerate, or update task dependency diagrams / graphs (\"vygeneruj diagramy závislostí\", \"dependency graph snapshot\", \"task dependency diagrams\")."
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
  Calibration, not a licence: on 2026-09-04 a 94-call fetch (92 tasks across
  five subagents, each capped at four calls in flight and told to stop on the
  first 429) completed with no throttling at all. So the ceiling is above 94
  at that concurrency — but one clean run does not measure where it actually
  is, and the cached fragments are what make a re-run free either way.
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
    {"id": "abc123", "label": "INFRA-01", "group": "INFRA", "status": "closed",
     "since": "2026-09-04 08:41"},
    {"id": "def456", "label": "FU: audit wiring", "group": "AUTH",
     "status": "open", "wide": true}
  ],
  "edges": [{"from": "abc123", "to": "def456"}]
}
```

Status mapping: done/complete/closed → `closed` (green ✓); waiting on a
reviewer — in review, ready for CR — → `review` (yellow ⟳); work in the code
is what it is waiting for — in progress, testing, changes requested —
→ `in_progress` (blue ▸); everything else → `open` (white). The split is by
*who is on the hook*, not by tracker status name, so check which statuses the
tracker actually has before mapping: on PMA, "waiting for fix(es)" is a GitHub
PR label with no ClickUp status of its own, and those tasks read as `review`
unless the tracker status is flipped back. State the mapping you used in your
summary. `clusters` is optional — without it you get the full graph and a flat
overview, no detail diagrams.

Optionally give each task a `since` — when it entered its current status,
`"YYYY-MM-DD HH:MM"` local time — and `annotate_names.py` renders it as a third
node line ("Closed from: …", "Review from: …"). Only fill it where the tracker
gives you a real status-change timestamp; a task without `since` just gets no
third line, which is far better than a plausible-looking wrong date. **A generic
"last updated" field is not that timestamp** — it moves on any edit, including
the ones this pipeline makes. ClickUp exposes `date_closed` on every task but
needs the "Total time in Status" ClickApp enabled workspace-wide for anything
else; without it, fill `since` for closed tasks only.

**Write it with a fixed formatting: `json.dump(..., indent=2, ensure_ascii=False)`
plus a trailing newline, keys left in the order above rather than sorted.**
`model.json` is committed next to the diagrams and is the file a reader diffs to
see what moved between two snapshots, so its formatting is load-bearing: on one
real project two consecutive snapshots were written with `indent=1` and
`indent=2`, which turned a 25-line content change into a 2081-line whole-file
rewrite and hid every status change. If a regeneration shows `model.json` fully
rewritten, the formatting drifted — renormalize before committing.

## Step 4 — Generate and export

From the directory holding `model.json` (`SCRIPTS` = this skill's `scripts/`
directory):

```bash
python3 "$SCRIPTS/gen_diagrams.py" model.json --outdir .
python3 "$SCRIPTS/annotate_names.py" model.json --outdir .   # optional, see below
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

**A missing `ok` line is not a failure.** `export_one` only prints its success
line when it observes two equal sizes in a row; when draw.io exits on its own
first, the loop leaves through the `kill -0` break and prints nothing at all.
Judge the run by the output files — every expected path present and non-empty,
no `FAILED:` line — not by counting log lines. Seen 2026-09-04: 14 `ok` lines
for 22 correct exports.

### Optional — task names inside the nodes

By default a node shows only the task code, which forces the reader to keep the
tracker open. `annotate_names.py` adds the name on a second, smaller line,
in place, between `gen_diagrams.py` and `autolayout.py`. It reads the same
`model.json`, so give each task a `name` field and, for the overview diagram,
add a top-level `groups` map of group key → one-line description:

```json
{"tasks":  [{"id": "t1", "label": "INFRA-01", "name": "K3s cluster & networking", "...": "..."}],
 "groups": {"INFRA": "Infrastructure & baseline"}}
```

`gen_diagrams.py` ignores both keys, so one model drives the whole pipeline, and
a task with no `name` is left exactly as generated — which is how uncoded
follow-up nodes, whose label is already a sentence, stay untouched. The full
graph is skipped by default (at ~90 nodes the second line stops helping and the
file doubles); pass `--include-graph` to annotate it too, and `--wrap N` if your
names need a different height estimate than the default 26 characters per line.

## Step 5 — Snapshot directory and verification

- Place the set in a **stable, undated** directory, e.g. `docs/task-dependencies/`,
  and regenerate **in place**. Only one snapshot is ever committed; the previous
  ones stay reachable through git history
  (`git log --oneline -- docs/task-dependencies/`). Do not put the date in the
  directory name: since the old set is deleted on every refresh anyway, a dated
  path buys nothing and costs a broken link in every doc, ticket and chat message
  that pointed at the previous one.
- **The date goes in the directory's README instead**, as a metadata bullet list
  at the very top — snapshot date and time, source list, scope, and the commit
  of the previous snapshot:

  ```markdown
  - **Snapshot taken:** 2026-09-04 15:08 CEST
  - **Source:** ClickUp list **Tasks - PMA** (`901216620944`)
  - **Scope:** 92 tasks across 8 epics, 80 edges after transitive reduction
  - **Previous snapshot:** commit `4484f85`, 2026-09-03
  ```

  **The date names the day whose end-of-day state the snapshot captures** —
  a run early in the morning gets *yesterday's* date, not today's. Say in the
  README that this is a point-in-time artifact and that a link to the default
  branch will silently show a newer set later; a commit permalink is the way to
  reference a particular day.
- Before committing, verify the new set is complete (same file-name set as the
  previous revision, no empty files) — `git status` should show modifications,
  not a pile of deletions.
- **Verify visually:** render one detail PNG and check statuses, new nodes,
  and new edges against what the fetch reported.
- Re-check that the docs index (e.g. `docs/README.md`) and the project's
  knowledge file still describe the set correctly — with a stable path their
  links no longer need touching on every refresh, only their prose.
- Offer a commit following the project's workflow; report node/edge counts
  and what changed since the previous snapshot (new tasks, status moves,
  added/removed edges).
