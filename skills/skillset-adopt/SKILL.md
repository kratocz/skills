---
name: skillset-adopt
description: Evaluate a named third-party skill collection against what is already installed, then adopt the parts worth having — inventory first, name-collision and trigger-overlap detection, coupling check, a per-skill verdict of install / borrow the idea / skip, then a verified install. Use when the user points at a skills repository and asks whether it is worth taking ("hodilo by se mi doinstalovat něco z <repo>?", "stojí za to tyhle skilly?", "should I install any of these skills", "is this skill collection worth adding", "porovnej to s tím, co už mám"). Not capability-driven discovery of an unknown skill — that is `find-skills`; the MCP-server counterpart is `mcp-server-adopt`.
license: MIT
---

# Adopting a third-party skill collection

The question is never "is this collection good?" — it is "what does this collection add to *this* setup?". A skill's value is relative to the inventory it lands in: an excellent skill whose trigger phrases collide with one already installed makes the setup worse, because two competing descriptions route by whichever the model reaches first and the user sees only the wrong result.

So the inventory comes first. Work the phases in order; **Phase 0 before Phase 1** is the ordering that carries the whole skill.

## Phase 0 — Inventory what is already installed

Before reading a single candidate, establish what the user has and where it came from. Doing this second turns the whole review into guesswork about novelty.

```bash
python3 -c "
import json;d=json.load(open('$HOME/.agents/.skill-lock.json'))['skills']
for k,v in sorted(d.items()): print(f\"{k:28s} {v.get('source','?'):45s} {v.get('installedAt','')[:10]}\")"
ls ~/.agents/skills/ ~/.claude/skills/
find ~/.claude/plugins/cache -maxdepth 4 -name SKILL.md 2>/dev/null | sed 's|.*/skills/||;s|/SKILL.md||' | sort -u
```

Three things to take from this, each of which changed a verdict in practice:

- **Part of the candidate repo may already be installed.** The lock file records the source repo per skill, so check it for the candidate's own name — a user who cherry-picked from this collection months ago will not remember. Report those as already-held rather than proposing them again.
- **Plugin skills do not appear in the lock file.** They live in the marketplace cache and are usually the largest overlap, because plugin bundles cover whole workflows.
- **The user's own collection is the strongest competitor.** A skill they wrote and maintain beats an equivalent stranger's skill even when the stranger's is longer.

## Phase 1 — Read the collection, not its README

Shallow-clone the candidate into a scratch directory and read the frontmatter of every `SKILL.md`, plus its size and bundled assets:

```bash
git clone --depth 1 -q https://github.com/<owner>/<repo>.git cand && cd cand
for d in <skills-dir>/*/; do n="${d%/}"; f="$n/SKILL.md"; [ -f "$f" ] || continue
  echo "### ${n##*/}  ($(wc -l < "$f") lines, $(find "$n" -type f | wc -l | tr -d ' ') files)"
  awk '/^---$/{c++;next} c==1{print} c==2{exit}' "$f"; echo; done
```

A README lists what the author is proud of; the frontmatter is what will actually compete for invocation, and the line count is the honest measure of how much is really there. Read the bodies of the shortlisted ones in full — a twelve-line skill and a three-hundred-line skill both look like one table row.

Also record the licence and the date of the last commit. The licence decides whether Phase 4's "borrow the idea" is available; a stale repo is not disqualifying for a prose skill the way it is for code, but say so.

## Phase 2 — Collisions and overlaps

Two different failures, two different remedies. Separate them explicitly.

- **Name collision** — the candidate and an installed skill share a `name`. Both resolve to the same path (`~/.agents/skills/<name>`), so installing silently replaces the incumbent; where the incumbent is a symlink into the user's own working clone, the replacement is a copy and the link is gone. Always report a collision by name, never install one without saying so first, and if the incumbent is the user's own, default to keeping it.
- **Trigger overlap** — different names, but descriptions that fire on the same request. This is the quieter failure: nothing is overwritten, and the two simply compete, so the outcome varies run to run. The remedy is a **swap, not an addition** — recommend one, and say plainly that keeping both means accepting that either may fire.

Compare descriptions, not titles. Read each candidate's `description` next to the installed one it resembles and ask which phrases could belong to either; a phrase assignable to both is the collision.

## Phase 3 — Coupling

Some collections are a toolbox of independent skills; others are a workflow spine whose parts assume a shared per-repo setup file, a configured issue tracker, or a fixed document layout. Grep the candidates for references to a setup skill or a config path they all read.

Taking two skills out of a coupled system gives the user almost nothing and a broken flow. Say which candidates are standalone and which are only worth taking as a set — and treat "adopt the whole spine" as its own decision, because a spine competes with whatever process the user already runs.

Watch for the sharper form of this: a collection carrying an **always-on discipline** (a session hook, a mandatory gate). Two such disciplines in one setup will contradict each other, and the loser is decided by the harness's instruction hierarchy rather than by the user. Name the conflict rather than letting it be discovered later.

## Phase 4 — A verdict per skill

Every candidate gets exactly one of three, each with a one-line reason:

- **Install** — no collision, no overlap, no coupling; it does something the setup cannot do today.
- **Borrow the idea** — the skill is not worth installing (it collides, or the incumbent is better) but it contains one mechanism worth porting into an existing skill. Name the mechanism concretely and check the licence permits it; this verdict is often the most valuable output.
- **Skip** — redundant, thin, or coupled to a system the user is not adopting.

Present these as a table, then a short recommendation naming the two or three that actually matter. Resist a long install list: every installed skill costs description context in every session, for every one of the user's projects, and dilutes routing for the skills already there.

## Phase 5 — Install

Only the approved ones, and never the whole repo by reflex:

```bash
npx skills add <owner>/<repo> -g -y -a '*' -s <first> -s <second> -s <third>
```

`-s` selects **one skill per flag**. A comma-separated list is read as a single name: nothing installs, and the command prints `No matching skills found for: a,b,c` followed by every skill in the repo — a tail that looks exactly like a successful listing.

## Phase 6 — Verify from the filesystem, not the output

The command's own report is not evidence. Confirm each approved skill by its installed path and its lock entry, and confirm nothing else moved:

```bash
ls -l ~/.agents/skills/<name> ~/.claude/skills/<name>
python3 -c "
import json;d=json.load(open('$HOME/.agents/.skill-lock.json'))['skills']
print([k for k,v in d.items() if v.get('source')=='<owner>/<repo>'])"
```

Then say which harnesses picked them up and which need a restart, and report any install error verbatim — some are benign (harnesses that do not support global installs refuse individually while the rest succeed) and reading them as failure re-runs an install that already worked.
