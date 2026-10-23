#!/usr/bin/env python3
"""Capacity-based list scheduler: turn per-task effort estimates into start/due dates.

Each person works through their tasks one at a time at a fixed number of plannable hours per
working day (weekends and listed holidays skipped). A task starts once its assignee is free and
every dependency inside the plan has finished; a dependency on a task outside the plan counts as
already satisfied. Among ready tasks the order is: status rank, then priority, then due hint,
then an explicit order, then id. A task that needs review gets its due date pushed by the review
latency, so due = "implementation including review is done".

Input (JSON, path or "-" for stdin):
{
  "start": "YYYY-MM-DD",                 # first plannable day (today or later)
  "holidays": ["YYYY-MM-DD", ...],
  "people": {"<name>": {"hours_per_day": 6.0}},
  "review": {"latency_days": 1, "skip_for": ["<reviewer name>"]},   # optional
  "milestone": "YYYY-MM-DD",             # optional, tasks finishing after it are flagged
  "status_rank": {"in progress": 0, "ready to cr": 0, "Open": 1},   # optional, default shown
  "tasks": [{"id": "...", "name": "...", "assignee": "<name>", "hours": 3.0,
             "priority": 1..4 (1 = most urgent), "depends_on": ["<id>", ...],
             "status": "...", "due_hint": "YYYY-MM-DD"|null, "order": int|null,
             "needs_review": true|false, "not_before": "YYYY-MM-DD"|null}]
}
Output (JSON on stdout): {"tasks": [{id, assignee, start, impl_end, due, late}], "people": {...},
"unscheduled": [{id, reason}]}. Run with --table for a readable table, --self-test to check itself.
"""
import json
import sys
from datetime import date, timedelta

DEFAULT_STATUS_RANK = {"in progress": 0, "ready to cr": 0, "open": 1}


class Calendar:
    def __init__(self, start, holidays):
        self.start = start
        self.holidays = set(holidays)

    def is_workday(self, d):
        return d.weekday() < 5 and d not in self.holidays

    def first_workday_from(self, d):
        while not self.is_workday(d):
            d += timedelta(days=1)
        return d

    def next_workday(self, d):
        return self.first_workday_from(d + timedelta(days=1))

    def add_workdays(self, d, n):
        for _ in range(n):
            d = self.next_workday(d)
        return d


def schedule(spec):
    cal = Calendar(date.fromisoformat(spec["start"]), [date.fromisoformat(h) for h in spec.get("holidays", [])])
    people = spec["people"]
    review = spec.get("review") or {}
    latency = int(review.get("latency_days", 0))
    skip_review_for = set(review.get("skip_for", []))
    rank = {k.lower(): v for k, v in (spec.get("status_rank") or DEFAULT_STATUS_RANK).items()}
    milestone = date.fromisoformat(spec["milestone"]) if spec.get("milestone") else None

    unscheduled = []
    plan = {}
    for t in spec["tasks"]:
        if t.get("assignee") not in people:
            unscheduled.append({"id": t["id"], "reason": f"assignee {t.get('assignee')!r} has no capacity entry"})
        elif not t.get("hours") or t["hours"] <= 0:
            unscheduled.append({"id": t["id"], "reason": "no positive hours"})
        else:
            plan[t["id"]] = t
    skipped = {u["id"] for u in unscheduled}

    # dependency check inside the plan; deps on skipped tasks block the dependent
    for tid, t in list(plan.items()):
        bad = [d for d in t.get("depends_on", []) if d in skipped]
        if bad:
            unscheduled.append({"id": tid, "reason": f"depends on unscheduled {bad}"})
            skipped.add(tid)
            del plan[tid]

    cursor = {p: (cal.first_workday_from(cal.start), 0.0) for p in people}  # (day, hours used that day)
    done = {}
    out = []

    def key(t):
        return (rank.get(str(t.get("status", "")).lower(), 9), t.get("priority") or 9,
                t.get("due_hint") or "9999-12-31", t.get("order") if t.get("order") is not None else 10**6, t["id"])

    remaining = dict(plan)
    while remaining:
        ready = [t for t in remaining.values() if all(d in done or d not in plan for d in t.get("depends_on", []))]
        if not ready:
            raise SystemExit(f"dependency cycle among: {sorted(remaining)}")
        def earliest(t):
            """(day, hours already used that day) at which t could start for its assignee."""
            cap = float(people[t["assignee"]]["hours_per_day"])
            day, used = cursor[t["assignee"]]
            dep_end = max([done[d] for d in t.get("depends_on", []) if d in done], default=None)
            if dep_end is not None and dep_end >= day:
                day, used = cal.next_workday(dep_end), 0.0
            if t.get("not_before"):
                nb = cal.first_workday_from(date.fromisoformat(t["not_before"]))
                if nb > day:
                    day, used = nb, 0.0
            if used >= cap - 1e-9:
                day, used = cal.next_workday(day), 0.0
            return day, used

        # list scheduling: the task that can start earliest goes first; ties go to the better rank,
        # so a person waiting on a dependency fills the gap with other ready work instead of idling
        ready.sort(key=lambda t: (earliest(t)[0], key(t)))
        t = ready[0]
        who = t["assignee"]
        cap = float(people[who]["hours_per_day"])
        day, used = earliest(t)
        start = day
        left = float(t["hours"])
        while True:
            take = min(left, cap - used)
            used += take
            left -= take
            if left <= 1e-9:
                break
            day, used = cal.next_workday(day), 0.0
        impl_end = day
        cursor[who] = (day, used)
        needs_review = t.get("needs_review", who not in skip_review_for)
        due = cal.add_workdays(impl_end, latency) if needs_review and latency else impl_end
        done[t["id"]] = due
        out.append({"id": t["id"], "name": t.get("name", ""), "assignee": who, "hours": t["hours"],
                    "start": start.isoformat(), "impl_end": impl_end.isoformat(), "due": due.isoformat(),
                    "late": bool(milestone and due > milestone)})
        del remaining[t["id"]]

    summary = {}
    for p in people:
        mine = [o for o in out if o["assignee"] == p]
        summary[p] = {"tasks": len(mine), "hours": round(sum(o["hours"] for o in mine), 1),
                      "last_due": max((o["due"] for o in mine), default=None),
                      "late": sum(1 for o in mine if o["late"])}
    return {"tasks": out, "people": summary, "unscheduled": unscheduled}


def table(result):
    lines = ["| id | assignee | h | start | due | late | name |", "|---|---|---|---|---|---|---|"]
    for o in sorted(result["tasks"], key=lambda o: (o["assignee"], o["start"])):
        lines.append(f"| {o['id']} | {o['assignee']} | {o['hours']:g} | {o['start']} | {o['due']} | "
                     f"{'!' if o['late'] else ''} | {o['name'][:60]} |")
    lines.append("")
    for p, s in result["people"].items():
        lines.append(f"- {p}: {s['tasks']} tasks, {s['hours']} h, last due {s['last_due']}, after milestone {s['late']}")
    for u in result["unscheduled"]:
        lines.append(f"- unscheduled {u['id']}: {u['reason']}")
    return "\n".join(lines)


def self_test():
    base = {"start": "2026-10-16", "holidays": ["2026-10-28"], "people": {"a": {"hours_per_day": 4}, "b": {"hours_per_day": 8}},
            "review": {"latency_days": 1, "skip_for": ["b"]}, "milestone": "2026-10-22"}
    # 1) 10 h at 4 h/day starting Fri 16.10. -> Fri, Mon, Tue (2 h); review +1 workday -> Wed 21.10.
    r = schedule({**base, "tasks": [{"id": "t1", "assignee": "a", "hours": 10, "priority": 2, "status": "Open"}]})
    o = r["tasks"][0]
    assert (o["start"], o["impl_end"], o["due"]) == ("2026-10-16", "2026-10-20", "2026-10-21"), o
    # 2) dependency across people: t3 (b) waits for t2 (a) due incl. review; b skips review
    r = schedule({**base, "tasks": [{"id": "t2", "assignee": "a", "hours": 4, "priority": 1, "status": "Open"},
                                     {"id": "t3", "assignee": "b", "hours": 8, "priority": 1, "status": "Open", "depends_on": ["t2"]}]})
    by = {o["id"]: o for o in r["tasks"]}
    assert by["t2"]["due"] == "2026-10-19" and by["t3"]["start"] == "2026-10-20" and by["t3"]["due"] == "2026-10-20", by
    # 3) holiday skipped: 8 h for b starting Tue 27.10. lands on Thu 29.10. when 28.10. is a holiday and two tasks queue
    r = schedule({**base, "start": "2026-10-27", "tasks": [{"id": "x", "assignee": "b", "hours": 8, "priority": 1, "status": "Open"},
                                                            {"id": "y", "assignee": "b", "hours": 8, "priority": 2, "status": "Open"}]})
    by = {o["id"]: o for o in r["tasks"]}
    assert by["x"]["start"] == "2026-10-27" and by["y"]["start"] == "2026-10-29", by
    # 4) ordering: in-progress before Open, then priority
    r = schedule({**base, "tasks": [{"id": "p", "assignee": "b", "hours": 8, "priority": 1, "status": "Open"},
                                     {"id": "q", "assignee": "b", "hours": 8, "priority": 4, "status": "in progress"}]})
    assert [o["id"] for o in r["tasks"]] == ["q", "p"], r["tasks"]
    # 5) unknown assignee and dependency on it -> both unscheduled; dependency outside the plan is satisfied
    r = schedule({**base, "tasks": [{"id": "u", "assignee": "nobody", "hours": 2},
                                     {"id": "v", "assignee": "b", "hours": 2, "depends_on": ["u"]},
                                     {"id": "w", "assignee": "b", "hours": 2, "depends_on": ["closed-elsewhere"]}]})
    assert {u["id"] for u in r["unscheduled"]} == {"u", "v"} and r["tasks"][0]["id"] == "w", r
    # 5b) gap filling: b's urgent task waits for a's task (due Mon 19.10.), so b does the low-priority task first
    r = schedule({**base, "tasks": [{"id": "dep", "assignee": "a", "hours": 4, "priority": 1, "status": "Open"},
                                     {"id": "urgent", "assignee": "b", "hours": 8, "priority": 1, "status": "Open", "depends_on": ["dep"]},
                                     {"id": "filler", "assignee": "b", "hours": 8, "priority": 4, "status": "Open"}]})
    by = {o["id"]: o for o in r["tasks"]}
    assert by["filler"]["start"] == "2026-10-16" and by["urgent"]["start"] == "2026-10-20", by
    # 5c) not_before: a task that may not start before Thu 12.11. starts then, and b fills the time before with other work
    r = schedule({**base, "tasks": [{"id": "later", "assignee": "b", "hours": 2, "priority": 1, "status": "Open", "not_before": "2026-11-12"},
                                     {"id": "now", "assignee": "b", "hours": 8, "priority": 4, "status": "Open"}]})
    by = {o["id"]: o for o in r["tasks"]}
    assert by["later"]["start"] == "2026-11-12" and by["now"]["start"] == "2026-10-16", by
    # 6) milestone flag
    r = schedule({**base, "tasks": [{"id": "big", "assignee": "a", "hours": 40, "priority": 1, "status": "Open"}]})
    assert r["tasks"][0]["late"] is True and r["people"]["a"]["late"] == 1
    print("self-test OK")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--self-test" in args:
        self_test()
        sys.exit(0)
    src = next((a for a in args if not a.startswith("--")), "-")
    spec = json.load(sys.stdin if src == "-" else open(src))
    res = schedule(spec)
    print(table(res) if "--table" in args else json.dumps(res, indent=2, ensure_ascii=False))
