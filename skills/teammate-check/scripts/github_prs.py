#!/usr/bin/env python3
"""One-call GitHub snapshot for teammate-check.

Fetches, in a single GraphQL request per page, every open pull request by a
teammate together with everything §3 and §4 of the skill need: labels, review
requests, the reviewer's latest review and whether the head moved since,
unresolved review threads whose last word is the author's, the author's
comments after that review, changed files and the CI rollup. Optional task
ids are searched in the same request, to catch a follow-up someone else
opened on the teammate's task.

Requires the GitHub CLI (`gh`), authenticated. Read-only.

Usage:
  github_prs.py --repo OWNER/NAME [--repo ...] --author LOGIN --reviewer LOGIN
                [--task-id ID ...] [--json]
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime

PR_FIELDS = """
  number title url isDraft createdAt updatedAt headRefName headRefOid
  author { login }
  repository { nameWithOwner }
  labels(first: 20) { nodes { name } }
  reviewDecision
  mergeable
  reviewRequests(first: 20) {
    nodes { requestedReviewer { ... on User { login } ... on Team { name } } }
  }
  reviews(last: 50) {
    nodes { author { login } state submittedAt commit { oid } }
  }
  reviewThreads(first: 100) {
    nodes {
      isResolved
      comments(last: 1) { nodes { author { login } createdAt url body } }
    }
  }
  comments(last: 30) { nodes { author { login } createdAt url body } }
  files(first: 100) { nodes { path } }
  commits(last: 1) {
    nodes { commit { committedDate statusCheckRollup { state } } }
  }
"""


def gh_graphql(query, variables):
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        cmd += ["-f", f"{key}={value}"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh api graphql failed: {out.stderr.strip()}")
    data = json.loads(out.stdout)
    if data.get("errors"):
        sys.exit(f"GraphQL errors: {json.dumps(data['errors'])[:500]}")
    return data["data"]


def fetch(repos, author, task_ids):
    repo_q = " ".join(f"repo:{r}" for r in repos)
    searches = {"mine": f"{repo_q} is:pr is:open author:{author}"}
    for i, tid in enumerate(task_ids):
        searches[f"t{i}"] = f"{repo_q} is:pr {tid} in:title,body"
    prs, by_task = {}, {}
    cursors = {alias: None for alias in searches}
    while cursors:
        parts, variables = [], {}
        for alias, cursor in cursors.items():
            var = f"after_{alias}"
            parts.append(
                f'{alias}: search(query: "{searches[alias]}", type: ISSUE, first: 25, after: ${var}) '
                f"{{ pageInfo {{ hasNextPage endCursor }} nodes {{ ... on PullRequest {{ {PR_FIELDS} }} }} }}"
            )
            if cursor:
                variables[var] = cursor
        decl = ", ".join(f"$after_{a}: String" for a in cursors)
        data = gh_graphql(f"query({decl}) {{ {' '.join(parts)} }}", variables)
        nxt = {}
        for alias in cursors:
            block = data[alias]
            for node in block["nodes"]:
                if not node:
                    continue
                key = (node["repository"]["nameWithOwner"], node["number"])
                prs[key] = node
                if alias != "mine":
                    by_task.setdefault(task_ids[int(alias[1:])], []).append(key)
            if block["pageInfo"]["hasNextPage"]:
                nxt[alias] = block["pageInfo"]["endCursor"]
        cursors = nxt
    return prs, by_task


def login(node):
    return ((node or {}).get("author") or {}).get("login")


def summarise(pr, author, reviewer):
    mine = [r for r in pr["reviews"]["nodes"] if login(r) == reviewer and r["state"] != "PENDING"]
    last = mine[-1] if mine else None
    last_at = last["submittedAt"] if last else ""
    requested = [
        (n["requestedReviewer"] or {}).get("login") or (n["requestedReviewer"] or {}).get("name")
        for n in pr["reviewRequests"]["nodes"]
    ]
    open_replies = [
        c for t in pr["reviewThreads"]["nodes"] if not t["isResolved"]
        for c in t["comments"]["nodes"] if login(c) == author
    ]
    author_comments = [c for c in pr["comments"]["nodes"] if login(c) == author and c["createdAt"] > last_at]
    head = pr["commits"]["nodes"][0]["commit"] if pr["commits"]["nodes"] else {}
    rollup = (head.get("statusCheckRollup") or {}).get("state")
    return {
        "repo": pr["repository"]["nameWithOwner"],
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["url"],
        "author": login(pr),
        "draft": pr["isDraft"],
        "created": pr["createdAt"],
        "updated": pr["updatedAt"],
        "branch": pr["headRefName"],
        "labels": [l["name"] for l in pr["labels"]["nodes"]],
        "review_decision": pr["reviewDecision"],
        "mergeable": pr["mergeable"],
        "ci": rollup,
        "review_requested_from_reviewer": reviewer in requested,
        "reviewer_last_review": (
            {"state": last["state"], "at": last["submittedAt"], "on_head": (last.get("commit") or {}).get("oid") == pr["headRefOid"]}
            if last else None
        ),
        "author_open_thread_replies": [{"at": c["createdAt"], "url": c["url"], "text": c["body"][:200]} for c in open_replies],
        "author_comments_after_review": [{"at": c["createdAt"], "url": c["url"], "text": c["body"][:200]} for c in author_comments],
        "files": [f["path"] for f in pr["files"]["nodes"]],
    }


def local(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")


def render(rows, by_task, author, task_ids):
    out = [f"read at {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %z')}; open PRs by {author}: "
           f"{sum(1 for r in rows if r['author'] == author)}"]
    for r in rows:
        if r["author"] != author:
            continue
        rv = r["reviewer_last_review"]
        rv_txt = f"{rv['state']} {local(rv['at'])} {'on head' if rv['on_head'] else 'HEAD MOVED since'}" if rv else "none"
        out.append(f"\n#{r['number']} {r['title']}  {r['url']}")
        out.append(f"  labels={r['labels']} decision={r['review_decision']} ci={r['ci']} mergeable={r['mergeable']}"
                   f"{' DRAFT' if r['draft'] else ''}")
        out.append(f"  review requested from reviewer: {r['review_requested_from_reviewer']}; reviewer's last review: {rv_txt}")
        for c in r["author_open_thread_replies"]:
            out.append(f"  unresolved thread, author's reply last ({local(c['at'])}): {c['text']!r} {c['url']}")
        for c in r["author_comments_after_review"]:
            out.append(f"  author comment after review ({local(c['at'])}): {c['text']!r} {c['url']}")
        out.append(f"  files ({len(r['files'])}): {', '.join(r['files'][:12])}{' …' if len(r['files']) > 12 else ''}")
    for tid in task_ids:
        found = [f"#{n} ({repo})" for repo, n in by_task.get(tid, [])]
        out.append(f"\ntask {tid}: PRs mentioning it in title or body: {', '.join(found) or 'none'}")
    out.append("\n(mergeable=UNKNOWN only means GitHub has not computed it yet)")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", action="append", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--task-id", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    prs, by_task = fetch(a.repo, a.author, a.task_id)
    rows = sorted((summarise(p, a.author, a.reviewer) for p in prs.values()), key=lambda r: (r["repo"], r["number"]))
    if a.json:
        print(json.dumps({"prs": rows, "by_task": {k: [list(x) for x in v] for k, v in by_task.items()}}, indent=1))
    else:
        print(render(rows, by_task, a.author, a.task_id))


if __name__ == "__main__":
    main()
