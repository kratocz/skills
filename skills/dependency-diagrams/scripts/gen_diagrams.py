#!/usr/bin/env python3
"""Generate autolayout graph JSONs from a normalized task-dependency model.

Input: a model.json produced by the skill (see SKILL.md for the fetch step):

  {
    "prefix": "vault",            # output file prefix (default "deps")
    "direction": "LR",            # passed through to autolayout (default LR)
    "clusters": {                 # optional grouping of groups (phases, milestones)
      "phase-1": {"title": "Phase 1 — Foundation", "groups": ["INFRA", "AUTH"]},
      "x":       {"title": "Cross-cutting",         "groups": ["ARCH"]}
    },
    "tasks": [                    # every node of the graph
      {"id": "t1", "label": "INFRA-01", "group": "INFRA",
       "status": "closed",        # open | in_progress | closed (default open)
       "wide": false}             # true => wider node (long label)
    ],
    "edges": [                    # from = prerequisite, to = dependent task
      {"from": "t1", "to": "t2"}
    ]
  }

Outputs (in --outdir, default cwd), each a graph JSON for autolayout.py:
  <prefix>-graph.json      full graph: tasks grouped by group, transitive reduction
  <prefix>-overview.json   one node per group, clustered; edge label = dep count
  <prefix>-<cluster>.json  per cluster (only when "clusters" given): that cluster's
                           tasks + grey dashed ghost nodes for upstream inputs

Statuses render as: closed = green + " ✓", in_progress = blue + " ▸", open = white.
Edges whose endpoints are not in "tasks" are dropped silently.
"""
import argparse
import json
import os
from collections import defaultdict

STYLE = {
    "closed": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#5a9a4e;fontSize={fs};fontStyle=1;",
    "in_progress": "rounded=1;whiteSpace=wrap;html=1;fillColor=#cfe2ff;strokeColor=#3a78c2;fontSize={fs};fontStyle=1;",
    "open": "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#9e9e9e;fontSize={fs};",
}
SUFFIX = {"closed": "  ✓", "in_progress": "  ▸", "open": ""}
GHOST = ("rounded=1;whiteSpace=wrap;html=1;fillColor=#f0f0f0;strokeColor=#bdbdbd;"
         "fontColor=#777;fontSize=11;dashed=1;")
EDGE = ("edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
        "strokeColor=#546e7a;strokeWidth=1.4;endArrow=block;endFill=1;")
EDGE_EXT = ("edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
            "strokeColor=#90a4ae;strokeWidth=1.4;endArrow=block;endFill=1;dashed=1;")
# One (fill, stroke) per cluster for the overview, cycled in order of appearance.
CLUSTER_COLORS = [("#cfe2ff", "#3a78c2"), ("#d5e8d4", "#5a9a4e"), ("#ffe6cc", "#d79b00"),
                  ("#fdd9ec", "#c2407f"), ("#e1d5e7", "#9673a6"), ("#fff2cc", "#d6b656"),
                  ("#eeeeee", "#9e9e9e")]


def node(task, fs, w, h):
    st = task.get("status", "open")
    return {
        "id": task["id"],
        "label": task.get("label", task["id"]) + SUFFIX.get(st, ""),
        "style": STYLE.get(st, STYLE["open"]).format(fs=fs),
        "group": task["group"],
        "groupLabel": task["group"],
        "width": int(w * 1.35) if task.get("wide") else w,
        "height": h,
    }


def transitive_reduction(edges):
    succ = defaultdict(set)
    for a, b in edges:
        succ[a].add(b)

    def reachable_via_detour(start):
        seen, stack = set(), []
        for m in succ[start]:
            for n in succ[m]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        while stack:
            x = stack.pop()
            for y in succ[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        return seen

    return {(a, b) for a, b in edges if b not in reachable_via_detour(a)}


def main():
    ap = argparse.ArgumentParser(
        description="Generate autolayout graph JSONs from a normalized task-dependency model.")
    ap.add_argument("model", help="model.json (see module docstring)")
    ap.add_argument("--outdir", default=".", help="output directory (default: cwd)")
    args = ap.parse_args()
    m = json.load(open(args.model, encoding="utf-8"))
    prefix = m.get("prefix", "deps")
    direction = m.get("direction", "LR")
    tasks = {t["id"]: t for t in m["tasks"]}
    groups = {}  # group -> [task ids], insertion-ordered
    for t in m["tasks"]:
        groups.setdefault(t["group"], []).append(t["id"])
    edges = {(e["from"], e["to"]) for e in m.get("edges", [])
             if e["from"] in tasks and e["to"] in tasks and e["from"] != e["to"]}
    clusters = m.get("clusters") or {}
    group_cluster = {g: key for key, c in clusters.items() for g in c["groups"]}

    def dump(name, nodes, elist):
        path = os.path.join(args.outdir, f"{prefix}-{name}.json")
        json.dump({"direction": direction, "nodes": nodes, "edges": elist},
                  open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"{path}: nodes={len(nodes)} edges={len(elist)}")

    # --- full graph (transitive reduction) ----------------------------------
    reduced = transitive_reduction(edges)
    dump("graph",
         [node(tasks[tid], 11, 110, 36) for g in groups for tid in groups[g]],
         [{"source": a, "target": b, "style": EDGE} for a, b in sorted(reduced)])

    # --- overview: one node per group ---------------------------------------
    pair = defaultdict(int)
    for a, b in edges:
        ga, gb = tasks[a]["group"], tasks[b]["group"]
        if ga != gb:
            pair[(ga, gb)] += 1
    seen_clusters, onodes = [], []
    for g, members in groups.items():
        ckey = group_cluster.get(g)
        if ckey is not None and ckey not in seen_clusters:
            seen_clusters.append(ckey)
        fill, stroke = CLUSTER_COLORS[seen_clusters.index(ckey) % len(CLUSTER_COLORS)] \
            if ckey is not None else ("#dae8fc", "#6c8ebf")
        n = {"id": g, "label": f"{g}\n({len(members)} tasks)",
             "style": f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontStyle=1;fontSize=14;",
             "width": 130, "height": 52}
        if ckey is not None:
            n["group"], n["groupLabel"] = ckey, clusters[ckey]["title"]
        onodes.append(n)
    dump("overview", onodes,
         [{"source": a, "target": b, "label": str(n),
           "style": EDGE + f"strokeWidth={1 + min(n, 6) * 0.5:.1f};fontSize=10;fontColor=#37474f;"}
          for (a, b), n in sorted(pair.items())])

    # --- per-cluster details -------------------------------------------------
    for ckey, c in clusters.items():
        in_groups = [g for g in c["groups"] if g in groups]
        in_tasks = {tid for g in in_groups for tid in groups[g]}
        internal = [(a, b) for a, b in edges if a in in_tasks and b in in_tasks]
        external = [(a, b) for a, b in edges if a not in in_tasks and b in in_tasks]
        nodes = [node(tasks[tid], 12, 120, 38) for g in in_groups for tid in groups[g]]
        for a in sorted({a for a, _ in external}):
            nodes.append({"id": "ext_" + a, "label": tasks[a].get("label", a),
                          "group": "↑ upstream", "groupLabel": "↑ external inputs",
                          "style": GHOST, "width": 110, "height": 32})
        elist = ([{"source": a, "target": b, "style": EDGE} for a, b in sorted(internal)]
                 + [{"source": "ext_" + a, "target": b, "style": EDGE_EXT}
                    for a, b in sorted(external)])
        dump(ckey, nodes, elist)


if __name__ == "__main__":
    main()
