---
name: mikrotik-audit
description: Read-only security audit of Mikrotik RouterOS devices via SSH. Detects signs of compromise (VPNFilter IoCs, CVE-2018-14847, scheduler/script persistence, DNS hijacking, rogue users, exfiltration tunnels). Use when the user wants to check their Mikrotik routers for security issues, or when they provide a path to an audit output directory for analysis.
---

# Mikrotik security audit

Read-only audit of Mikrotik RouterOS devices over SSH. Searches for signs of compromise across VPNFilter IoCs, Meris, CVE-2018-14847 (Winbox RCE), unauthorized users, persistence via `/system scheduler` and `/system script`, DNS hijacking, exfiltration tunnels, and exposed management services.

## When to invoke

- User asks to audit / check security of their Mikrotik router(s).
- User suspects a compromise of their network or router.
- User provides a path to an existing `./audit-results/…` directory and wants analysis.

## Resolving SSH targets

Targets may be supplied directly by the user, or discovered from project documentation:

1. **Direct input.** User tells you SSH targets — aliases from `~/.ssh/config`, or `user@host[:port]`.
2. **From project docs.** Check these conventional paths in the current repo, in order:
   - `infrastructure/mikrotik-routers.md`
   - `infrastructure/routers.md`
   - `docs/mikrotik.md`
   - Hints in `AGENTS.md` / `CLAUDE.md` / top-level `README.md`
3. **Fallback:** ask the user which routers to audit and how to reach them over SSH.

When a project file documents routers, extract for each: IP or SSH alias, role (main / backup / bridge), SSH username, non-default port. Confirm with the user before connecting if anything is ambiguous or incomplete. Skip devices that the docs mark as non-routers (e.g. L2 bridges / signal extenders).

## Mode A: full audit (collect + analyze)

1. Verify connectivity for each target:
   ```bash
   ssh -o BatchMode=yes <target> "/system identity print"
   ```
   Authentication must be via SSH key — no password prompts. If auth fails, help the user check `~/.ssh/config` and installed keys. Ideally the router has a dedicated read-only user (group `read`) with the public key installed via `/user ssh-keys import`.
2. Run collection (script is on PATH via plugin `bin/`):
   ```bash
   mikrotik-audit <target> [<target> …]
   ```
   Output lands in `./audit-results/<timestamp>/<target>/<section>.txt` plus a `summary.md` with heuristic flags.
3. Proceed to Mode B for the generated directory.

## Mode B: analyze existing outputs

1. Read `<dir>/summary.md` first — automated heuristic. Treat as a starting point, not a verdict.
2. Walk each router's files systematically using the checklist below. Cite exact lines in findings.
3. Final report per router, categorized:
   - 🚨 **CRITICAL** — clear IoC or known CVE. Immediate action required.
   - ⚠️ **WARN** — suspicious or bad security practice. Fix recommended.
   - ℹ️ **INFO** — configuration the user must confirm (if expected).
   - ✅ **OK** — checked, no issue.
4. For each finding, include:
   - What exactly (quoted line, file path).
   - Why it's suspicious (reference to known IoC / CVE / best practice).
   - Recommended fix — **but do not execute it**. The skill is read-only.

Respond in the user's preferred language (infer from project CLAUDE.md / AGENTS.md; default English).

## Per-file checklist

### `system.txt`
- **RouterOS version.** 6.x < 6.42 → **CRITICAL (CVE-2018-14847)**. Any 6.x → WARN (EOL branch, should move to 7.x). 7.x far behind latest stable → WARN.
- **Uptime.** Extremely long uptime implies no updates applied.
- **Identity.** Unusual name (default is `MikroTik`).

### `users.txt`
- **User list.** Enumerate all. User other than `admin`? Does the user recognize them? Be alert for suspicious names like `ssh`, `service`, `backup`, `support` — VPNFilter and similar families used such patterns.
- **SSH keys.** Unknown fingerprints = potential backdoor.
- **Groups.** `/user group` — custom group with extended rights = suspicious.
- **Active sessions.** Unknown source IPs?

### `scripts.txt` — ⚠️ MOST CRITICAL section
- Any script or scheduler containing:
  - `fetch` (downloading from internet) → highly suspicious
  - `:import` (running a remote `.rsc`) → highly suspicious
  - Hardcoded URL / IP to a C2-style host
  - Name starting with `.` (hidden) or impersonating a system name
- Schedulers running very frequently (every minute) that invoke scripts → red flag.

### `services.txt`
- **SOCKS `enabled=yes`** → 🚨 classic VPNFilter IoC.
- **Telnet / FTP** enabled → WARN (old unencrypted protocols).
- **Winbox (8291) accessible from WAN** → CRITICAL on < 6.42 due to CVE.
- **UPnP `enabled=yes`** → WARN (usually unwanted in home networks).
- **`/ip cloud`** — if user doesn't use MikroTik cloud DNS, shouldn't be active.

### `firewall.txt`
- **NAT dst-nat** rules (port forwards) → verify each is expected.
- **Mangle** rules with unusual actions → injected traffic manipulation.
- **Input chain** accepting from WAN without filtering → open management surface.

### `network.txt`
- **DNS servers.** Anything other than `1.1.1.1` / `8.8.8.8` / user's ISP / user's VPN → **DNS hijacking risk**.
- **Static DNS entries** for popular domains (google, microsoft, banking) → MITM indicator.
- **Routes** to unknown subnets.
- **DHCP client** with a lease from an unexpected source.

### `tunnels.txt`
- **Any active outbound tunnel** (L2TP, PPTP, OpenVPN, SSTP, Wireguard, GRE, EoIP, IPIP) to an unknown endpoint → potential exfiltration / C2.
- Expected tunnels (user's VPN, site-to-site) are OK — confirm with user.

### `wifi.txt`
- **Security profile** with weak auth (WEP, open) → WARN.
- **Unknown SSIDs** (hidden or visible).

### `files.txt`
- `autorun.rsc`, `.auto.rsc`, unknown `.npk` packages in root → persistence indicators.

### `logs.txt`
- Repeated `login failure` from foreign IPs → brute-force.
- `critical` / `error` events.
- Unexpected `dhcp` / `dns` / `account` activity.

### `snmp.txt`
- Community `public` or `private` → WARN (default, weak).
- SNMP accessible from WAN → CRITICAL.

### `tool.txt`
- **bandwidth-server enabled** and accessible from WAN → reflection-abuse risk.
- **RoMON** enabled without need → adds attack surface.
- **mac-server** on WAN-facing interfaces → L2 discovery exposure.

### `certs.txt`
- Unknown root CA certificates → potential MITM setup.
- Expired certificates used for management.

## Threat reference

| IoC / CVE | Manifestation | Where to look |
|---|---|---|
| **CVE-2018-14847** (Winbox path traversal) | RouterOS < 6.42 | `system.txt` |
| **VPNFilter** | SOCKS proxy enabled, rogue user (often `ssh`), custom scripts with `fetch`, unexpected tunnels | `services.txt`, `users.txt`, `scripts.txt`, `tunnels.txt` |
| **Meris botnet** (2021) | RouterOS < 6.49 + Winbox exposed to WAN, `/system scheduler` persistence | `system.txt`, `services.txt`, `scripts.txt` |
| **DNS hijacking** | Custom DNS servers, static entries on popular domains | `network.txt` |
| **Brute-force** | Repeated `login failure` from a single IP | `logs.txt` |

## Principles

- **Read-only.** Neither the skill nor the script makes any changes to the router. A fix is a separate manual step by the user.
- **Don't exfiltrate dumps.** Never upload raw outputs to pastebins, gists, or chat platforms — they contain sensitive network information.
- **When in doubt, escalate.** Is user `admin2` an attacker or another real user? Ask, don't guess.
