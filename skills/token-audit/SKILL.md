---
name: token-audit
description: Find what actually drives token cost across agent sessions and measure whether a change to how you work reduced it — price-weighted shares, cache rewrites after idle gaps vs model switches, cost by context size, multi-day sessions, tool-result and skill residency, subagents against doing the same work inline — then refute the conclusions in a fresh context and compare against a saved baseline. Use when the user asks "kde mi utíkají tokeny", "jak ušetřit tokeny", "zanalyzuj spotřebu tokenů z logů", "zabralo to?", "přeměř token audit", "where do my tokens go", "why is my usage so high", "did the change reduce token use". Not the general usage dashboard (tokens per project, skill, subagent, top prompts) — that is the `session-report` plugin.
license: MIT
version: 1.1.1
---

# Token audit

The question this answers is not "how many tokens did I use" but "which of my habits cost the most, and what would change it". It reads the agent's own session transcripts, weights usage by relative price, attributes cost to drivers an intervention can act on, and — run again later against a saved baseline — tells whether the intervention worked.

Transcript format: Claude Code JSONL under `<harness-home>/projects/` (`~/.claude/projects/` by default). Other harnesses are not supported by the bundled script.

## 1. Fix the question and the decision rule first

Before running anything, write down what the measurement is for and what result would change a decision. For a first audit, unless the user sets another, use: "act on the largest driver that is a changeable habit, if it carries at least ~10–15 % of cost; below that, report that nothing is worth changing". For a re-measure: the success gate set when the intervention was introduced, e.g. "idle cache rewrites fall below 10 % of cost". A rule written after the number is read is not a rule.

## 2. Run the analyzer

```bash
python3 <skill-dir>/scripts/token_audit.py --since 30d --json <durable-path>/token-audit-<date>.json
```

`--since` / `--until` take `Nd` or an ISO date and filter by **request timestamp** (file modification time only pre-selects files). `--projects` points elsewhere than `~/.claude/projects`. `--baseline <file.json>` prints each metric next to an earlier run and lists metrics present in only one of the two — a baseline from an older script version is not comparable on those, so regenerate it over the original window with the current script rather than reading the delta. (A key collision in the first version of this script turned an 18 % → 23 % rise into a reported 20 % → 2 % fall.)

Save the JSON somewhere that survives the session — a project's notes, the user's memory directory — never a scratch directory: without it there is nothing to compare against later.

## 3. Read the drivers and map each to a lever

Weights relative to uncached input: input 1, 5-minute cache write 1.25, 1-hour cache write 2, cache read 0.1, output 5. The total is **input-equivalent tokens, not money** — models differ in price, so compare runs only over a similar model mix (the script prints it). Every percentage is a share of that one total, and the sections are overlapping slices of it: idle rewrites, the `>400k` bucket and tool-result residency can describe the same tokens, so never add them up. The context-size buckets cover main threads only and sum to the main-thread share the script prints, not to 100 %.

| Driver in the output | What it means | Lever |
|---|---|---|
| cache read dominates, cost concentrated in `>400k` context | every turn re-reads a huge context | shorter sessions — one task or review round per session; a lower auto-compact window is a personal setting, offer it as such, sized as described below the table |
| `idle > 1h` rewrites | resuming a big session after the 1-hour cache TTL writes the whole context again at 2× | compact or end the session before a break; work that keeps its state in files (findings files, PRs, trackers) restarts cheaply. Claude Code hooks can react to compaction but not start it (hooks docs, checked 2026-10-01), so this is a habit, not an automation |
| `model switch` rewrites (incl. `idle + model switch`) | each model has its own cache | switch models only at the start of a session |
| no metric of its own — list, per short time window, how many sessions made their first request after more than an hour idle | many finished sessions woken within minutes of each other — a `/retro` or "commit and push" sweep across every open session, a cross-session message to sessions that are done — each writes its whole context again, and a model switch on the way in makes that certain | run a retro at the end of the session it reviews, while the cache is warm and on the same model; do not wake a finished session just to inform it. Measured 2026-10-02 over one month: four such sweeps came to ~10–14 % of cost (upper bound), about half of it pure rewrites |
| high `later day` share | multi-day sessions carry the cost | same as the first row |
| tool-result residency (with the `Bash by command` breakdown) | a large output stays in context, paid on every later turn and again on every rewrite | delegate long read-only exploration to a subagent when the main context is already large; read files in ranges rather than whole |
| subagent `inline/actual` | estimated cost of doing the same work inline, as a multiple of the subagents' actual cost. Two numbers: with their reads staying in context until compaction (upper bound), and without (lower) — the truth is between | above 1 on both: keep delegating; below ~10 tool calls from a small context they lose |
| skills share | skill listing plus loaded skill bodies | usually small; trimming descriptions costs triggering accuracy for little gain |

**Sizing an auto-compact window.** A lower window is triggered by size alone: it cannot tell a pause or a change of topic from a large task still in progress, so it fires mostly mid-work. Derive it from the data rather than picking a round number — find the largest contexts of sessions that were large for a reason (one task carried through, short gaps between prompts) and set the window just above them, so that only the runaway tail gets compacted. Simulated 2026-10-02 over one month: a 200k window would have compacted ~200 times, about 80 % of them within five minutes of the previous request; a window just above the legitimate single-task maximum (~500k in that data) compacted 44 times and left those sessions alone. A simulation's saving is an upper bound (step 4). Say how reversible each habit is when recommending it: a conversation left with `/clear` stays available to `/resume` at full context, at the cost of the cache rewrite a pause would have caused anyway; `/compact` cannot be undone within the session, and the Claude Code docs suggest `/branch` before it when the full history may be needed again.

**Raising the window for one session.** A user with a lower window will sometimes see a session approach it for a good reason and want more room. Claude Code's `/autocompact <tokens>` (`auto` restores the model default; no argument shows the current value and its source) changes the window from inside a running session — but it writes `autoCompactWindow` into the user's global settings file, so the change outlives the session and, since every session reads that file, very likely reaches parallel ones too. Verified 2026-10-02 on 2.1.287: `/autocompact auto` removed the key from `~/.claude/settings.json` at the moment it ran, although the command's code reads as a session-level override. When recommending it, say that the user has to set the old value back afterwards, or the lower window silently stops applying. The only override truly scoped to one session is the environment variable, which takes precedence over the setting but has to be given at launch: `CLAUDE_CODE_AUTO_COMPACT_WINDOW=<tokens> claude --resume` reopens a session with full context, provided auto-compaction has not run yet. Never export that variable from a shell profile — it would override the setting for every session without any sign of it.

Two traps observed in real data: `hook_success` attachments can make up half of a transcript's bytes but never reach the model — measure from `usage`, not file size; and `<synthetic>` records carry no usage.

## 4. Refute before concluding

Quantitative conclusions are the ones most likely to flatter the analyst. Dispatch a fresh-context subagent with the script, its output and your list of claims — not your reasoning — briefed to **refute** them against the raw transcripts. Known weak points to point it at:

- the subagent counterfactual is an upper bound (inline work might take fewer turns than a subagent does);
- characters-per-token (2.33) was calibrated on one machine's transcripts; to re-check it, take requests that immediately follow a single large tool result and divide that result's characters by the growth in context (`cache_read + cache_creation + input`) between the two requests — the median over a hundred such pairs is the ratio;
- residency counts results from before the window as read in it but not written in it, and ignores residency inside subagent transcripts;
- a cap-and-compact simulation, if you run one, must charge the compacted context's cache write, files re-read after compaction and the summarization request — and it cannot see what compaction loses.

Record which claims survived, and correct the ones that did not before reporting.

## 5. Report

Conclusion first: the one or two drivers worth acting on, each with its share and its lever. Label every number as measured or estimated, give ranges where the refutation pass moved a figure, and end with what would change the recommendation. For a re-measure, read the result against the rule from step 1 — met, not met, or confounded (e.g. the model mix changed).
