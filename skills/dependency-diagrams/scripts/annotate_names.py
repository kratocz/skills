#!/usr/bin/env python3
"""Add task names as a second, smaller line inside the generated diagram nodes.

Runs between gen_diagrams.py and autolayout.py, in place, on the
`<prefix>-*.json` files that gen_diagrams.py wrote:

    python3 gen_diagrams.py model.json --outdir .
    python3 annotate_names.py model.json --outdir .
    for f in <prefix>-*.json; do python3 autolayout.py "$f" -o "${f%.json}.drawio"; done

Node styles carry `html=1`, so labels accept markup. Names come from the model:

    {"tasks":  [{"id": "t1", "label": "INFRA-01", "name": "K3s cluster & networking", ...}],
     "groups": {"INFRA": "Infrastructure & baseline"}}

`groups` is optional and only feeds the overview diagram; `gen_diagrams.py`
ignores both keys, so one model.json drives the whole pipeline. A task with no
`name` is left exactly as generated — that is how nodes whose label is already
a sentence (uncoded follow-ups) stay untouched.

The full graph is skipped by default: at ~90 nodes the second line stops
helping and the file doubles in size. Pass --include-graph to annotate it too.
"""
import argparse
import glob
import html
import json
import math
import os

# Detail nodes and the grey dashed ghost nodes are styled one step apart, and
# their height bases differ because gen_diagrams.py emits them at 38 and 32 px.
DETAIL = {"size": 9, "color": "#5a6672", "width": 190, "base": 38}
GHOST = {"size": 8, "color": "#9aa3ab", "width": 165, "base": 34}
LINE_PX = 14          # added height per wrapped line of the name
OVERVIEW = {"width": 200, "height": 74, "count_color": "#78838d"}


def sub(text, size, color):
    return '<br><font style="font-size:%dpx;color:%s">%s</font>' % (
        size, color, html.escape(text, quote=False))


def main():
    ap = argparse.ArgumentParser(
        description="Add task names as a second, smaller line inside diagram nodes.")
    ap.add_argument("model", help="the same model.json gen_diagrams.py consumed")
    ap.add_argument("--outdir", default=None,
                    help="directory holding the generated JSONs (default: the model's)")
    ap.add_argument("--wrap", type=int, default=26,
                    help="characters per wrapped line, used to size node height (default: 26)")
    ap.add_argument("--include-graph", action="store_true",
                    help="also annotate <prefix>-graph.json (off by default: too dense)")
    args = ap.parse_args()

    model = json.load(open(args.model, encoding="utf-8"))
    outdir = args.outdir or os.path.dirname(os.path.abspath(args.model))
    prefix = model.get("prefix", "deps")
    names = {t["id"]: t["name"] for t in model["tasks"] if t.get("name")}
    descs = model.get("groups") or {}
    counts = {}
    for t in model["tasks"]:
        counts[t["group"]] = counts.get(t["group"], 0) + 1

    def lines(text):
        return max(1, math.ceil(len(text) / args.wrap))

    for path in sorted(glob.glob(os.path.join(outdir, prefix + "-*.json"))):
        base = os.path.basename(path)[len(prefix) + 1:-len(".json")]
        if base == "graph" and not args.include_graph:
            continue
        g = json.load(open(path, encoding="utf-8"))
        touched = 0
        for n in g["nodes"]:
            nid = n["id"]
            if base == "overview":
                # Overview nodes are one per group; gen_diagrams.py labels them
                # "GROUP\n(N tasks)", which we replace with a three-line block.
                if nid not in counts:
                    continue
                c = counts[nid]
                label = nid
                if descs.get(nid):
                    label += sub(descs[nid], DETAIL["size"], DETAIL["color"])
                label += '<br><font style="font-size:%dpx;color:%s">%d task%s</font>' % (
                    DETAIL["size"], OVERVIEW["count_color"], c, "" if c == 1 else "s")
                n["label"] = label
                n["width"], n["height"] = OVERVIEW["width"], OVERVIEW["height"]
                touched += 1
                continue
            spec, key = (GHOST, nid[4:]) if nid.startswith("ext_") else (DETAIL, nid)
            name = names.get(key)
            if not name:
                continue
            n["label"] += sub(name, spec["size"], spec["color"])
            n["width"] = spec["width"]
            n["height"] = spec["base"] + LINE_PX * lines(name)
            touched += 1
        json.dump(g, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("annotated %-14s nodes=%d touched=%d" % (base, len(g["nodes"]), touched))


if __name__ == "__main__":
    main()
