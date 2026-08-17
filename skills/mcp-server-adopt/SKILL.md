---
name: mcp-server-adopt
description: Find, compare, security-vet, install and verify a third-party MCP server for a device or service — candidate sweep, metadata table, source reading, static audit before any build, credential setup outside the client config, registration and a real MCP handshake check. Use when the user asks for an MCP server for something ("najdi mi MCP server pro X", "nainstaluj MCP server", "is there an MCP server for my Hue lights", "which MCP server should I use for X", "vyber MCP server"), or wants a third-party MCP server vetted before installing it.
license: MIT
---

# Adopting a third-party MCP server

Picking an MCP server is a security decision wearing a convenience costume: you are granting unreviewed third-party code a long-lived credential and a seat inside the agent loop. Most candidates have single-digit stars, so community vetting does not exist — you are the review.

Work the phases in order. **Phase 4 must complete before Phase 5.** That ordering is the whole point of this skill.

## Phase 0 — Establish what the user actually has

Never shortlist before you know the target. Device generation and API version eliminate candidates outright — a server requiring a newer hub than the user owns is disqualified no matter how good it looks.

Discover the device on the local network (adapt to the domain):

```bash
curl -s -m 8 https://discovery.meethue.com/            # vendor discovery service, if one exists
dns-sd -B _<service>._tcp local                        # mDNS browse
arp -an | head -30                                     # MAC OUI identifies the vendor
```

Then read the device's own identity endpoint — model, firmware, API version — and check which API generations answer. Record it; you will cite it when recommending.

Also check the local toolchain (`go version`, `node -v`, `uv --version`, `python3 -V`) and free disk space. A server in a language the user does not have installed carries a real cost you must state, not hide.

## Phase 1 — Sweep for candidates

Search the web and the MCP registries. Cast wide — include toys and abandoned projects, because the comparison table is what makes the recommendation credible.

## Phase 2 — One metadata pass, not nine

Pull comparable metadata for every candidate in a single loop:

```bash
for r in owner/repo1 owner/repo2 …; do
  gh api "repos/$r" --jq '[.full_name, (.stargazers_count|tostring), (.forks_count|tostring),
    (.language // "?"), (.license.spdx_id // "NONE"), (.archived|tostring), .pushed_at,
    (.open_issues_count|tostring)] | @tsv' 2>/dev/null || echo -e "$r\tERR"
done | column -t -s$'\t'
```

Report forks alongside stars. A high fork-to-star ratio means people actually run and modify the thing; stars alone are a bookmark. `pushed_at` older than a year plus an unmaintained dependency is usually disqualifying.

## Phase 3 — Read the source, never trust the README

READMEs overstate. Verify each shortlisted candidate's claims against its code:

- **Which API generation?** Check the dependency manifest and grep for endpoint paths. A legacy-API wrapper works today but forecloses every newer feature — that alone can decide the comparison.
- **How many tools, and what are they?** Grep the registration calls. Cross-check against the README's promises; features listed there and absent in code are a maintenance signal.
- **Transport** — stdio is what a CLI client wants. Rich inline UI resources (`ui://…`) only render in some clients; in a terminal they are dead weight.
- **Credential handling** — env vars are good, a config file the server writes itself is worse, credentials in code disqualify.

Where two candidates differ in kind rather than quality, say so: one may be a compact controller, the other a platform. Name the axis and let the user choose against their own use.

## Phase 4 — Recommend one, with falsification

State a single recommendation, the reasoning, the residual risks, and explicitly what would change your mind (a failing build, a flaky tool list — both cheap to test in Phase 6). Name the uncomfortable part out loud: recommending a one-star project means the user is trusting your reading, not a community.

## Phase 5 — Audit BEFORE building

**`go test` / `npm test` / `cargo test` execute the third-party code.** A plain `go build` does not, unless the repo has `cgo` (`import "C"`, `#cgo`) or `//go:generate`. Do the static pass first — this is the step people skip and regret.

If the `ai-security-skills:mcp-server-review` skill is available, invoke it for the MCP-specific dimensions (tool permission matrix, injection surface, data exposure, sandboxing, supply chain). Add the language-level checks it does not cover — for Go:

```bash
grep -rn 'os/exec\|exec.Command\|syscall.Exec\|plugin.Open' --include='*.go' .   # command execution
grep -rn 'unsafe\.\|go:linkname\|import "C"\|#cgo' --include='*.go' .            # native / type-system escape
grep -rn '^func init()\|go:generate' --include='*.go' .                          # runs at import or build time
grep -rhoE '"https?://[^"]*"|Sprintf\("https?://[^"]*"' --include='*.go' . | sort -u   # every network target
grep -rn 'os.WriteFile\|os.Create\|os.MkdirAll\|os.Getenv' --include='*.go' .    # disk writes, env reads
grep -rn 'log\.\|Printf' --include='*.go' . | grep -i 'username\|token\|apikey'  # credential leaks to logs
grep -rnE 'base64\.(Std|URL)Encoding\.DecodeString|hex\.DecodeString' --include='*.go' .  # obfuscation
grep -rn 'http.Get\|net.Dial\|httptest\|exec.Command' --include='*_test.go' .    # what the tests will do
go mod verify                                                                     # checksums vs sum.golang.org
go run golang.org/x/vuln/cmd/govulncheck@latest ./...                             # called vs merely present CVEs
```

The network-target list is the highest-value check: every host the code can reach, in one screen. Anything beyond the device and the vendor's discovery service is a red flag.

Report the audit as a table of check → result, then state the residual risks plainly. Typical ones worth naming: TLS verification disabled for a self-signed device certificate (normal for LAN hubs, still real), the confused-deputy exposure of any MCP server to prompt injection, and the fact that you audited *this commit* — not future ones.

## Phase 6 — Install

Fork first when the project is small: a fork protects against the upstream vanishing or rewriting history, and gives you somewhere to land the fixes you will find while reading the code. Follow the user's clone convention (typically: clone upstream to `<projects>/github.com/<upstream-author>/<repo>`, `origin` stays upstream, the fork is a second remote named `fork` over SSH).

Build, then run the project's tests — now that the audit has cleared them. A build that fails or tests that fail is the falsification from Phase 4 firing; go back to the runner-up.

Pair or authenticate. When pairing needs a physical button press, run a **background** retry loop with a generous window rather than a single attempt, and tell the user to press it whenever:

```bash
for i in $(seq 1 200); do
  RESP=$(curl -s -m 5 -X POST http://<device>/api -H "Content-Type: application/json" -d '{"devicetype":"…"}')
  KEY=$(echo "$RESP" | python3 -c "import sys,json; …" 2>/dev/null)
  if [ -n "$KEY" ]; then umask 077; printf '%s' "$KEY" > "$OUT"; chmod 600 "$OUT"; exit 0; fi
  sleep 3
done
```

Never print the credential into the transcript — write it to a `chmod 600` file and echo only a masked prefix.

## Phase 7 — Keep the credential out of the client config

`claude mcp add --env SECRET=…` writes the secret in plaintext into the client's config, which gets read, copied and pasted routinely. Prefer an env file plus a wrapper:

```sh
#!/bin/sh
# Runs the MCP server with credentials loaded from outside the client config.
set -a
. "$HOME/.config/<tool>/env"
set +a
exec "$HOME/.local/bin/<tool>" "$@"
```

`chmod 600` the env file, `chmod 755` the wrapper, and delete any scratch copy of the key afterwards. The client config then contains only a path — safe to commit.

## Phase 8 — Register

Ask for the scope rather than assuming: user scope for anything the user wants everywhere (home automation, personal accounts), project scope for repo-bound tooling. Project scope writes a `.mcp.json` into the repository root — flag that it is untracked and let the user decide whether it belongs in git; do not commit it for them.

```bash
claude mcp add <name> --scope <user|project> -- /absolute/path/to/wrapper
```

## Phase 9 — Verify the handshake, not just the process

"It starts" is not verification. Drive the stdio protocol and assert on the tool list:

```python
import json, subprocess
p = subprocess.Popen(["<wrapper>"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.DEVNULL, text=True, bufsize=1)
def send(o): p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
def read():
    for line in p.stdout:
        if line.strip().startswith("{"): return json.loads(line)
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05",
     "capabilities":{},"clientInfo":{"name":"check","version":"1"}}})
init = read()
send({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
send({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
tools = read().get("result", {}).get("tools", [])
print(init["result"]["serverInfo"], len(tools))
p.terminate()
```

Then exercise one real read-only call against the device and show the user the actual result — the list of their own lights, files, or records is the proof they can check.

Tell the user the server only becomes active after the client reloads (a new project `.mcp.json` needs their approval), and give them something usable in the meantime — most of these projects ship a CLI alongside the MCP server.

## Phase 10 — Write it down

Record in the project's knowledge file or memory: which server, which commit was audited, where the credential lives, the verification command, and any upstream bugs you found — those are ready-made PR candidates for the fork. Note explicitly that the credential is machine-local and never enters the repository.
