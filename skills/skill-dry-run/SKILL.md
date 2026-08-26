---
name: skill-dry-run
description: Prove an already-written skill actually works by executing it end to end against real data, in a clean context, with writes made structurally impossible rather than merely forbidden — fingerprint the target, deny the credential path, dispatch a neutral-prompted fresh-context agent, diff the fingerprint, and re-verify every finding it reports. Use when the user says "/skill-dry-run", "ověř ten skill", "otestuj skill nanečisto", "does this skill actually work", "dry-run the skill", "verify my skill against real data", or has just changed a skill that writes somewhere and wants proof before trusting it. Not for authoring a skill or pressure-testing whether an agent complies with its wording — that is superpowers:writing-skills.
argument-hint: "<skill-name> [-- <args to pass through>]"
version: 1.0.0
license: MIT
---

# Skill Dry Run

Reading a skill proves only that it reads well. This skill runs one, safely, and
reports what actually happened.

It answers a different question from its neighbours:

| Skill | Question |
|-------|----------|
| `superpowers:writing-skills` | Does an agent comply with what I wrote? |
| `plugin-dev:skill-reviewer` | Is this skill well-formed and well-described? |
| **`skill-dry-run`** | **Does running it produce correct results on real data?** |

## Why it exists

Five runs of one skill on 2026-08-26 each surfaced defects the previous runs had
not, and the two most damaging — a coverage diff broken hours earlier, and a
matching rule that contradicted its own worked example — appeared only once the
skill ran in a context that had never seen it written. An author re-reading their
own text supplies the intent the text is missing.

## Arguments

- `<skill-name>` (required): the skill to exercise.
- `-- <args>` (optional): everything after `--` is passed to the skill verbatim.
  Prefer arguments that narrow the run — a four-day window instead of a month —
  so a verification pass stays cheap.

## Steps

1. **Locate the source, not the install.** Resolve where the skill's `SKILL.md`
   actually lives: an installed copy may lag the working clone. Compare the
   `version:` (or a `git log -1` on the source) against the installed path the
   harness will load. If they differ, say so and refresh the install before
   running — otherwise the run tests yesterday's skill and the result is
   worthless. This is the single most common way a verification pass silently
   proves nothing.

2. **Determine what the skill can write to.** Read its steps and list every
   outward effect: HTTP writes, MCP tools that mutate, files outside a
   scratchpad, git operations. If there are none, note that and skip to step 5 —
   the rest of this skill is about containing writes.

3. **Fingerprint each writable target — before the run.** Capture something
   small that changes if anything is written: a record count plus the highest
   record id, a file's checksum, `git rev-parse HEAD`. Store it. A count alone
   is too weak — a create-plus-delete leaves it unchanged.

   ```bash
   # example: a time tracker reached over HTTP
   printf 'user = "%s:api_token"\n' "$KEY" | curl -sS --config - \
     "https://api.example.com/v9/me/time_entries?start_date=<s>&end_date=<u>" \
   | python3 -c 'import json,sys; d=json.load(sys.stdin); \
       ids=sorted(e["id"] for e in d); print(len(ids), max(ids, default=0))'
   ```

4. **Remove the credential path — do not merely forbid the write.** Telling an
   agent "do not write" is a request; taking away what it would need in order to
   write is a property of the run. Identify the file or env var holding the
   credential and forbid *reading it* in the dispatch prompt. A skill that posts
   with an API key it must first read cannot post if it never gets the key, no
   matter how it misreads its own instructions.

   Where read-only MCP tools already carry their own auth, say so explicitly —
   the agent needs to know it does not need the key, or it will go looking.

5. **Dispatch a fresh-context agent.** Never run the verification yourself: you
   have read the skill, and that is precisely the contamination being controlled
   for. In the prompt:
   - name the skill and how to invoke it, with the pass-through arguments;
   - list the prohibitions from step 4 as absolute, above the task itself, and
     name the specific tools and endpoints that are off limits;
   - say where to stop (a dry-run flag is a request the skill makes of itself;
     the stopping point is an instruction you give from outside);
   - state **what to check without stating the expected answer.** "Report how
     many blocks came back covered" surfaces a defect; "confirm the count is no
     longer zero" invites agreement. If a previous defect is being re-checked,
     describe the symptom, never the verdict;
   - ask for **verbatim output** — the rendered result, exact label strings,
     exact warnings — not a summary. Paraphrase hides the bug;
   - ask what in the skill text was ambiguous or self-contradictory. A clean
     context hits every ambiguity an author has long since resolved in their
     head, and this question is often the highest-yield part of the run.

6. **Diff the fingerprint — after the run.** Re-capture step 3's values and
   compare. Report the comparison, never the agent's own statement that it wrote
   nothing. If anything moved, that is the finding; stop and surface it.

7. **Re-verify every reported finding against the file.** Treat the report as
   claims, not results. Read the lines it names and confirm the defect exists as
   described. A report in one such run named a broken `awk` line that was in fact
   correct in the source — the agent had mangled it while substituting
   placeholders. Marking a false positive as a bug costs a real fix.

8. **Execute the embedded snippets separately.** Prose can be reviewed; code
   cannot. Extract every code block the skill tells an agent to run, compile it,
   and execute it against real data — including the emit path, not only the
   early-exit path. Two live bugs found this way read as obviously right: a
   field named `content` where the data calls it `aiTitle`, so every row lost
   its description; and `date -u -j -f`, which parses its input *as UTC* on
   macOS and shifted a whole window by the zone offset.

   ```bash
   # extract a fenced snippet from the SKILL.md, compile it, run it on real input
   python3 - <<'PY'
   import re, io, textwrap, subprocess, sys
   s = io.open('<path>/SKILL.md', encoding='utf-8').read()
   code = textwrap.dedent(re.search(r"<<'PY'\n(.*?)\n   PY\n", s, re.S).group(1))
   compile(code, '<skill>', 'exec')          # syntax first
   print(subprocess.run([sys.executable, '-c', code, '<real-arg>'],
                        capture_output=True, text=True).stdout[:500])
   PY
   ```

9. **Report.** Per checked item: confirmed defect / behaved correctly / could not
   reach. Then the fingerprint comparison, and separately the ambiguities from
   step 5 — those are usually fixes waiting to happen rather than bugs.

## What this cannot tell you

- **Paths the run never took.** A branch that needs a different config, a
  different sink, or an interactive answer stays untested however many times you
  run the default path. Name those explicitly as unexercised rather than letting
  a clean report imply full coverage.
- **Whether the fix is right, only that the symptom is gone.** Re-run after
  fixing: two of the defects found on 2026-08-26 were regressions introduced by
  the fix for an earlier one, hours before.
