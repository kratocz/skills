---
name: wireguard-diagnose
description: Diagnose a WireGuard tunnel that is up but carries no traffic — read the server's own `wg show` BEFORE restarting anything, branch on what the two sides disagree about, and identify the phase from packet sizes on the wire. Use when the user says "VPN nefunguje", "nejde mi WireGuard", "tunel stojí ale nic neprojde", "wg show ukazuje 0 B received", "my VPN is up but nothing works", "WireGuard handshake fails", or reports that a tunnel interface exists and has an address but pings through it time out. Not for setting a tunnel up from scratch, and not for a tunnel that was never configured.
---

# Diagnosing a WireGuard tunnel that is up but dead

The symptom this skill is for: the interface exists, is `UP`, has its address, the route to the tunnel subnet points at it — and nothing passes. `wg show` on the client reports `transfer: 0 B received` and, crucially, **no `latest handshake` line at all**.

## The one thing to get right

**`0 B received` does NOT mean the server is not answering.** It means the answer did not arrive. Those are different faults with different fixes, and you cannot tell them apart from the client alone. Everything below follows from that.

## Rule zero: read the server before you restart anything

Restarting the client and the server within a few minutes of each other **merges two independent changes into one and destroys the evidence**. If the tunnel then works, nobody learns why, and it can come back. So:

1. Get `wg show` from the server first (`ssh root@<endpoint>`), while the tunnel is still broken.
2. Compare the two sides.
3. Only then change anything — one side at a time, checking after each.

If the user has already restarted both sides, say plainly that the cause cannot now be determined, and record what to capture next time rather than inventing a cause.

## The branch that decides everything

| Server's view of your peer | Meaning | Where to look |
|---|---|---|
| fresh `latest handshake`, client has none | **Return path is lost** — server replies, replies don't arrive | NAT/router on the client's side |
| no handshake, no traffic counted | Packets never arrive | outbound path, firewall, or the server itself |
| peer absent from `wg show` | Server does not know this key | server config; client key changed |

Two notes on reading `wg show`: the `transfer` counters count **data packets only**, not handshake packets, so a peer can have a known endpoint and still show `0 B received`. And a suspiciously low `transfer` on an interface that has been up for months means the peer state was recently reset — distinguish a real service restart from a mere `wg syncconf` with `systemctl show wg-quick@<iface> -p ActiveEnterTimestamp -p ActiveState`.

## Reading the wire

Packet sizes identify the phase without decrypting anything:

- **148 B** — handshake initiation (client → server)
- **92 B** — handshake response (server → client)
- **128 B** — a default `ping` encapsulated in the tunnel
- **32 B** — keepalive

Bidirectional pairs of equal size mean the tunnel works. Only initiations going out, nothing back, means you are in the first row of the table above.

`tcpdump` may not need root: on macOS, installing Wireshark adds `org.wireshark.ChmodBPF` and puts the user in group `access_bpf` — check with `id -Gn | command grep access_bpf`. Sniff **one interface at a time** (`-i any` fails without root on macOS with `ioctl(SIOCIFCREATE)`) and pick the one the default route actually uses (`route -n get default`) — on a multihomed machine that need not be Wi-Fi, and a machine can hold several addresses in the same subnet.

## Causes worth ruling out early, in this order

1. **Is the endpoint's address still current?** `wg-quick` resolves the endpoint **once, at startup**. Compare `dig +short <endpoint-host>` against the `endpoint` in `wg show`; a dynamic-DNS server that moved leaves the tunnel talking to an address nobody answers on. A boot-time DNS failure also leaves the tunnel never started at all — check the daemon's log.
2. **Routing stolen by another VPN.** If connectivity is **asymmetric** (server → client works, client → server does not), some other tunnel has taken the route. Tailscale with `accept-routes` installs host routes `/32` that outrank a `/24`. Do not check the subnet, check the address: `route -n get <gateway-ip>` must leave via the interface holding your tunnel address.
3. **A second client using the same private key.** A server keeps one endpoint per peer, so whoever handshakes last wins and the other goes dark. Compare the keys in each machine's config — never assume two configs differ just because they sit in different files.
4. **NAT mapping collisions behind a cheap router.** When several WireGuard clients share one public IP and two of them report the *same* source port on the server, the router is mapping them onto one entry and only one gets replies. Fix: give every client behind that router its own fixed `ListenPort`. `PersistentKeepalive` does **not** help here — keepalives only flow after a handshake is established, and that is exactly what never happened.
5. **A client whose signature expired.** A tunnel started by a signed GUI client can be `UP` with an address and never handshake, because the OS detached the network extension. Look in the system log for the extension's own complaints before blaming the network.

## Restart detection

A restart performed outside the service manager leaves **no trace in the daemon's log**, so an empty log does not prove the tunnel was not restarted. Real evidence: the mtime of the runtime socket (`/var/run/wireguard/*.sock`), `ps -o pid,lstart,etime -p $(pgrep -f wireguard-go)`, and a changed `listening port` between two `wg show` runs.

## Before you report a cause

State which claim is a measurement and which is an inference, and say what would change your mind. If both sides were restarted, the honest answer is that the cause is undetermined — with the capture list for next time. A correlation across two networks (same server, same config, only the router differs) is good evidence, but it is still correlation; say so.
