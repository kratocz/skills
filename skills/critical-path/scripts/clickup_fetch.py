#!/usr/bin/env python3
"""Fetch a whole ClickUp list, dependencies included, over the REST API.

    clickup_fetch.py --whoami
    clickup_fetch.py <list_id> -o tasks.json

One request per 100 tasks (subtasks and closed tasks included), and every task
carries its `dependencies` array — no per-task calls. REST is metered per token
per minute, separately from the MCP integration's daily call cap.

The personal token (`pk_...`) comes from the CLICKUP_API_TOKEN environment
variable, else from the macOS Keychain item named by --keychain-service
(default `clickup-api-token`). It is read inside this process, sent only in the
Authorization header, and never printed.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.clickup.com/api/v2"


def read_token(service):
    tok = os.environ.get("CLICKUP_API_TOKEN", "").strip()
    if not tok:
        try:
            tok = subprocess.run(
                ["security", "find-generic-password", "-s", service, "-w"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            tok = ""
    if not tok:
        # An empty Keychain item is the usual cause: `security ... -w` typed
        # through an agent's non-interactive shell stores an empty password.
        sys.exit(f"no ClickUp token: set CLICKUP_API_TOKEN or store it in Keychain "
                 f"service '{service}' from a real terminal")
    return tok


def get(path, tok):
    req = urllib.request.Request(API + path, headers={"Authorization": tok})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            budget = f'{resp.headers.get("X-RateLimit-Remaining")}/{resp.headers.get("X-RateLimit-Limit")}'
            return json.load(resp), budget
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {path}: {e.read()[:300]!r}")


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("list_id", nargs="?")
    ap.add_argument("-o", "--out", help="where to write the raw task array (JSON)")
    ap.add_argument("--whoami", action="store_true", help="only verify the token")
    ap.add_argument("--keychain-service", default="clickup-api-token")
    args = ap.parse_args()
    tok = read_token(args.keychain_service)

    if args.whoami:
        data, budget = get("/user", tok)
        print(f'token OK: {data["user"]["username"]} | rate budget left this minute: {budget}')
        return
    if not (args.list_id and args.out):
        ap.error("list_id and --out are required unless --whoami")

    tasks, page, calls = [], 0, 0
    while True:
        data, budget = get(f"/list/{args.list_id}/task?subtasks=true&include_closed=true&page={page}", tok)
        calls += 1
        tasks += data["tasks"]
        if data.get("last_page", True) or not data["tasks"]:
            break
        page += 1
    with open(args.out, "w") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
        f.write("\n")

    open_tasks = [t for t in tasks if t["status"]["type"] != "closed"]
    print(f"{len(tasks)} tasks ({len(open_tasks)} not closed) in {calls} request(s) "
          f"-> {args.out} | rate budget left this minute: {budget}")
    print(f'with dependencies: {sum(1 for t in tasks if t.get("dependencies"))} | '
          f'not closed with time_estimate: {sum(1 for t in open_tasks if t.get("time_estimate"))}, '
          f'with start+due: {sum(1 for t in open_tasks if t.get("start_date") and t.get("due_date"))}')


if __name__ == "__main__":
    main()
