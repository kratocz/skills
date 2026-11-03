#!/usr/bin/env python3
"""Report skills deployed under ~/.agents that have drifted from their repo.

`npx skills` deploys skills as COPIES, so editing a deployed skill leaves the
repo behind silently -- and for a GitHub-sourced skill the next
`npx skills update -g` overwrites the edit without a word. This ran as a
SessionStart hook after that happened twice in two days (dm-catchup on
2026-09-04, dependency-diagrams on 2026-09-05).

Silent when everything matches; prints a report only when there is something
to fix. Never fails a session: any unexpected error exits 0 quietly.
"""
import json
import os
import sys

HOME = os.path.expanduser("~")
LIVE = os.path.join(HOME, ".agents", "skills")
# The clone this script lives in (bin/ sits next to skills/); a symlinked
# script resolves to the clone. SKILLS_REPO overrides it.
REPO = os.environ.get("SKILLS_REPO") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "skills")
LOCK = os.path.join(HOME, ".agents", ".skill-lock.json")


def files_under(root):
    """Relative path -> content, for every file in a skill directory."""
    out = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn == ".DS_Store":
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                with open(full, "rb") as fh:
                    out[rel] = fh.read()
            except OSError:
                out[rel] = None
    return out


def main():
    if not os.path.isdir(LIVE) or not os.path.isdir(REPO):
        return 0

    repo_names = {n for n in os.listdir(REPO)
                  if os.path.isdir(os.path.join(REPO, n))}
    live_names = set(os.listdir(LIVE))

    drifted, missing, copies, linked = [], [], [], 0
    for name in sorted(repo_names):
        live_path = os.path.join(LIVE, name)
        if name not in live_names:
            missing.append(name)
            continue
        if os.path.islink(live_path):
            linked += 1
            continue  # a symlink cannot drift
        if files_under(os.path.join(REPO, name)) != files_under(live_path):
            drifted.append(name)
        else:
            copies.append(name)

    # An identical copy is no drift today, but on a machine that otherwise
    # runs live symlinks the next edit to the clone never reaches it.
    # pr-rebase-sweep sat as a copy for three weeks unnoticed (2026-10-31).
    if linked <= len(copies):
        copies = []

    # Deployed, not a symlink, not in the repo and not installed by the CLI:
    # someone hand-wrote a skill straight into the deployment directory.
    try:
        with open(LOCK, encoding="utf-8") as fh:
            locked = set(json.load(fh).get("skills", {}))
    except (OSError, ValueError):
        locked = set()
    unversioned = sorted(
        n for n in live_names - repo_names - locked
        if not os.path.islink(os.path.join(LIVE, n))
        and os.path.isdir(os.path.join(LIVE, n))
    )

    if not (drifted or missing or copies or unversioned):
        return 0

    lines = ["Skill drift detected between ~/.agents/skills (deployed) and "
             "kratocz/skills (versioned)."]
    if drifted:
        lines.append(
            "  Edited in place, repo is behind: " + ", ".join(drifted) + "\n"
            "    These are deployed copies. A GitHub-sourced skill loses the edit "
            "on the next `npx skills update -g`, so recover it now: copy the "
            "~/.agents version into the repo, commit, push.")
    if missing:
        lines.append("  In the repo but not deployed: " + ", ".join(missing))
    if copies:
        lines.append(
            "  Deployed as copies, not live symlinks: " + ", ".join(copies) + "\n"
            "    Identical for now, but edits to the clone will not reach them; "
            "replace each with a symlink into the clone.")
    if unversioned:
        lines.append(
            "  Hand-placed, in neither the repo nor the CLI lock: "
            + ", ".join(unversioned) + "\n"
            "    Nothing overwrites these, but nothing backs them up either.")
    lines.append("Mention this to the user; do not fix it unasked.")

    report = "\n".join(lines)
    json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                      "additionalContext": report}}, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # a broken check must never break a session
        sys.exit(0)
