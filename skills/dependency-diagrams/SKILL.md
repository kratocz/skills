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

### Refresh scope — ask before any per-task fetch

A refresh has two tiers, and they differ in cost by more than an order of
magnitude:

- **Statuses** — what actually changes day to day. On ClickUp one paginated
  `clickup_filter_tasks` call covers a whole list (100 tasks/page).
- **Dependency edges** — what changes only when someone founds or rewires
  tasks. Costs **one API call per task**, so a 92-task list is ~92 calls.

**Default to statuses only, and carry the edges over from the committed
`model.json`.** Refetch edges only when the user asks or when the run has a
concrete reason to expect the graph moved — new tasks founded, an epic broken
down, dependencies rewired. When it does, get the scope named explicitly
first: *which* group/epic, or an explicit "everything". Do not read "all" into
a bare "regenerate the diagrams"; ask, and offer the status-only default as
the cheap answer.

This is not frugality for its own sake — the tracker's rate budget is shared
across everything you do with it that day, so one unscoped fan-out can block
*writes and reads* for hours afterwards, for work that has nothing to do with
diagrams. See the budget note in the ClickUp recipe below.

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
  **Rate budget — the real constraint is per day, not per burst.** The
  workspace-wide limit blocks *writes and reads* for hours once tripped, and
  it is consumed by everything that touches the tracker that day, not just
  this pipeline. Measured on PMA: a 92-task fan-out at 06:20 on 2026-09-04
  went through with no throttling at all, and 59 further ordinary calls
  through that day were fine too — 151 cumulative. The next morning at 00:27
  a *twelve-call* single-epic fetch died on its eighth call, i.e. at 159
  cumulative within the rolling 24 h, with `retryAfter` ≈ 481 minutes. So the
  ceiling sits near **160 calls per rolling 24 h**, one full dependency
  fan-out spends **more than half of it**, and the run that pays for it is
  usually not the run that spent it.

  Three consequences. **One:** a burst succeeding proves nothing about the
  budget — concurrency is not what is being metered. **Two:** cache the
  fragments in the scratchpad and reuse them; a re-run is then free, and the
  09-04 snapshot was regenerated twice more that day for ~5 calls total
  because its fragments were still on disk. **Three:** do ClickUp edits
  (renames, new dependencies, status flips) **before** the fetch, not after —
  after a fan-out you may have no budget left to write with.

  If a 429 lands mid-fetch, stop; do not retry into the block. Keep whatever
  fragments arrived, mark the unreached tasks as not-refreshed (see `fetched`
  in Step 3) and say so in the snapshot README — a half-updated model that
  looks complete is worse than an obviously partial one.
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
  "fetched": {"default": "2026-09-04 15:57", "edges": "2026-09-04 06:20"},
  "tasks": [
    {"id": "abc123", "label": "INFRA-01", "group": "INFRA", "status": "closed",
     "since": "2026-09-04 08:41", "fetched_at": "2026-09-05 00:27"},
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

**Record provenance, because a partial refresh is invisible in the picture.**
Once scoped refreshes are the default (Step 1), most snapshots are partial —
and a node whose status is a day old is drawn exactly like a node refetched a
minute ago. Prose in the README cannot fix that: the artifact people actually
pass around is a PNG. So put it in the data. Top-level `fetched.default` is
when everything not stated otherwise was read from the tracker, and
`fetched.edges` when the dependency arrays were last fetched; a task
refreshed more recently carries its own `fetched_at`. All are local
`"YYYY-MM-DD HH:MM"`, same as `since`.

The generator scripts ignore all three, so this costs nothing to carry. What
it buys: the README's staleness section can be derived instead of remembered,
a later run can tell at a glance what it may leave alone, and a reviewer
diffing two models sees which tasks were actually re-read rather than assuming
all of them were. Set `fetched.default` to the timestamp of the run that last
did a full status refresh — not to "now" — whenever this run only touched a
subset.

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
  at the very top — snapshot date and time, source list, scope, what this run
  actually refreshed, and the commit of the previous snapshot:

  ```markdown
  - **Snapshot taken:** 2026-09-04 15:08 CEST
  - **Source:** ClickUp list **Tasks - PMA** (`901216620944`)
  - **Scope:** 92 tasks across 8 epics, 80 edges after transitive reduction
  - **Refresh scope:** statuses for all 92 tasks; edges carried over from
    2026-09-04 06:20
  - **Previous snapshot:** commit `4484f85`, 2026-09-03
  ```

  Derive the *Refresh scope* bullet from `fetched` / `fetched_at` in the model
  rather than from memory, and state it even when the run was complete — a
  reader cannot tell a full refresh from a partial one by looking, so "all of
  it" is information too.

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
