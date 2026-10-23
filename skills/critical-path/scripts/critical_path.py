#!/usr/bin/env python3
"""Longest dependency chain through the work that is not done yet.

    critical_path.py <tasks.json> [--edges]

Input is either a raw ClickUp task array (clickup_fetch.py output) or a model
with `tasks` + `edges` (see SKILL.md; an optional per-task `estimate_h` is the
weight). Closed tasks are done, so they and their edges drop out.

Prints the estimate coverage, the longest chain by number of steps and by
estimated hours (a task without an estimate weighs 0), the open tasks that
block two or more others, and open tasks waiting on something outside the
input. --edges also lists every edge between open tasks: when several chains
tie, the chain printed is an arbitrary one of them, and the edge list is the
whole picture.
"""
import argparse
import json
from datetime import datetime
from functools import lru_cache
import sys


def from_clickup(raw):
    tasks, edges = {}, set()
    for t in raw:
        due = datetime.fromtimestamp(int(t["due_date"]) / 1000).strftime("%Y-%m-%d") if t.get("due_date") else None
        tasks[t["id"]] = {
            "label": t["name"],
            "status": t["status"]["status"],
            "open": t["status"]["type"] != "closed",
            "who": ",".join(u["username"].split()[0] for u in t["assignees"]),
            "due": due,
            "estimate_h": int(t["time_estimate"]) / 3600000 if t.get("time_estimate") else None,
        }
        # Each edge appears on both endpoint tasks; the set dedups it.
        for d in t.get("dependencies") or []:
            edges.add((d["depends_on"], d["task_id"]))
    return tasks, edges


def from_model(model):
    tasks = {t["id"]: {"label": t["label"], "status": t["status"], "open": t["status"] != "closed",
                       "who": t.get("who", ""), "due": t.get("due"), "estimate_h": t.get("estimate_h")}
             for t in model["tasks"]}
    return tasks, {(e["from"], e["to"]) for e in model["edges"]}


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("tasks_json")
    ap.add_argument("--edges", action="store_true", help="also list every edge between open tasks")
    args = ap.parse_args()

    data = json.load(open(args.tasks_json))
    tasks, edges = from_clickup(data) if isinstance(data, list) else from_model(data)

    outside = {(a, b) for a, b in edges if a not in tasks or b not in tasks}
    live = sorted((a, b) for a, b in edges - outside if tasks[a]["open"] and tasks[b]["open"])
    succ = {}
    for a, b in live:
        succ.setdefault(a, []).append(b)
    open_ids = [i for i, t in tasks.items() if t["open"]]

    def longest(weight):
        visiting = set()

        @lru_cache(None)
        def best(i):
            if i in visiting:
                sys.exit(f"dependency cycle through {i}")
            visiting.add(i)
            tail = max((best(j) for j in succ.get(i, [])), key=lambda r: r[0], default=(0, ()))
            visiting.discard(i)
            return weight(i) + tail[0], (i,) + tail[1]

        return max((best(i) for i in open_ids), key=lambda r: r[0], default=(0, ()))

    def line(i):
        t = tasks[i]
        est = f'{t["estimate_h"]:.1f}h' if t["estimate_h"] else "-"
        return (f'{t["label"][:70]:70} | {t["status"]:12} | {t["who"] or "-":14} '
                f'| due {t["due"] or "-"} | est {est} | {i}')

    with_est = sum(1 for i in open_ids if tasks[i]["estimate_h"])
    print(f"open tasks: {len(open_ids)} (with estimate: {with_est}) | edges: {len(edges)}, "
          f"between open tasks: {len(live)}, reaching outside the input: {len(outside)}")
    for title, weight in [("steps", lambda _: 1),
                          ("estimated hours", lambda i: tasks[i]["estimate_h"] or 0)]:
        total, chain = longest(weight)
        print(f"\nlongest chain by {title}: {total:g}")
        for i in chain:
            print("  " + line(i))

    hubs = sorted((i for i in succ if len(succ[i]) >= 2), key=lambda i: -len(succ[i]))
    if hubs:
        print("\nopen tasks blocking two or more open tasks:")
        for i in hubs:
            print(f"  {line(i)} | blocks {len(succ[i])}")

    waiting_outside = sorted({b for _, b in outside if b in tasks and tasks[b]["open"]})
    if waiting_outside:
        print("\nopen tasks waiting on something outside the input (check it by hand):")
        for i in waiting_outside:
            print("  " + line(i))

    if args.edges:
        print("\nevery edge between open tasks (prerequisite -> dependent):")
        for a, b in live:
            inverted = tasks[a]["due"] and tasks[b]["due"] and tasks[b]["due"] <= tasks[a]["due"]
            print(f"  {line(a)}\n    -> {line(b)}{'  <-- due not after its prerequisite' if inverted else ''}")


if __name__ == "__main__":
    main()
