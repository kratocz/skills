---
name: anonymize-output
description: Rewrite a captured output so it can be shown to people who must not see who it belongs to — one consistent pseudonym per identifier across every place it hides, replacements length-matched so column alignment survives, derived values re-derived rather than renamed, and a mechanical leak check before anything is quoted. Use when the user wants to share terminal output, a log, a config file, a JSON dump, a screenshot's text or a bug-report snippet and says "anonymizuj to", "změň názvy projektů", "ať tam nejsou vidět firmy", "chci to ukázat kamarádům", "anonymize this", "sanitize this before I post it", "redact the names", or asks for a demo of a tool whose real output names a client. Not for stripping credentials out of diagnostic output — a token or password is removed, never given a plausible fake.
argument-hint: "[what to anonymize — a command to run, or a path to a captured file]"
version: 1.0.0
license: MIT
---

# Anonymize Output

Renaming what you notice is easy and produces a leak. This skill renames what is
*there*, keeps the result looking like real output, and proves the leak is gone
before anyone sees it.

## Why it exists

A `imp status` table was anonymized on 2026-09-04 to show a tmux-session
manager to friends. The employer's name sat in one column — and its four-letter
internal shorthand also sat in a tmux window name, in a ticket prefix inside a
worktree branch (`task-INVC-02`), and in a session title. Two colleagues were
named in worktree branches and two more only in titles. Renaming the obvious
column would have left the client identifiable in four other places.

The second trap was cosmetic but fatal to the purpose: a replacement one
character longer than the original breaks the column alignment, and a table with
ragged columns no longer reads as genuine tool output — which was the whole point
of showing it.

## Scope

Pseudonymization for readability, not redaction. A secret — API key, token,
password, session cookie — is **removed** and written `<REDACTED>`, never
replaced with a realistic-looking fake: a fake suggests the value still means
something, and a leaked secret needs rotating rather than disguising. For
secret-stripping inside diagnostic output see `diagnosing-bugs`.

Renaming also does not hide *structure*. Row counts, timings and the shape of the
work stay legible; if the audience must not learn that a piece of work exists at
all, cut those rows rather than renaming them.

## Steps

1. **Capture to a file; quote nothing yet.** Run the command with its output
   redirected into the scratchpad, or read the file the user pointed at. The raw
   text must not appear in your reply at any point — pasting it first and
   anonymizing afterwards has already leaked it, and an edit does not unsend it.

2. **Inventory the identifiers across the whole capture.** Sweep every column and
   every line, not the one field that obviously names someone. Usual hiding
   places:

   | Where | Example (founding case, shown in its anonymized form) |
   |---|---|
   | Org / owner field | `AcmeGroup` |
   | Repository and directory names | `billing-system-ACC` |
   | Internal shorthand inside a compound token | `INVC` in `task-INVC-02` |
   | Window, pane, session, branch names | `2:LGR`, `questions-dvorak` |
   | Free text: titles, commit subjects, log lines | `Náměty od Davida Dvořáka` |
   | Handles and mentions | `@jan-svoboda` |
   | Domains and e-mail addresses | `bazar.example-shop.cz` |
   | Hostnames and machine names | `macbook-02.local` |
   | Absolute paths carrying a username or client | `/Users/x/clients/acme/...` |
   | IPs, ports and internal URLs | `10.x.x.x`, `git.client.internal` |

   Identity hides *inside* tokens. Rename the token, not the string it happens to
   sit in.

3. **Write the mapping table before changing anything.** One row per original →
   replacement, and every occurrence of that original — in any column, in any
   compound, in any case — gets that one replacement. Renaming ad hoc line by
   line is how the same name ends up as two different pseudonyms on two rows,
   which a reader notices immediately.

   Apply the mapping case-insensitively and carry the original's case transform:
   if `billing-system-ACC` appears lowercased in a derived column, the
   replacement is lowercased there too.

4. **Length-match every replacement.** A column is as wide as its longest value.
   A longer replacement widens the column and the output stops matching what the
   tool really prints. Same character count is the safe default; anything shorter
   than the current column maximum is fine as long as you regenerate the widths.
   Check the value that *sets* the width before shortening it.

5. **Re-derive derived values; never rename them separately.** A session name
   built from repo plus worktree, a slugged domain, a branch echoed in a title —
   all are computed from a replacement, not mapped on their own. Two of these in
   the founding case (`NAME` from `REPO`, `www-example-shop-cz-3b` from the
   domain) would each have been an inconsistency.

6. **Regenerate the layout; do not hand-edit spaces.** Emit the table from the
   anonymized data with computed padding. Pad by **display width**, not
   `len()` — an emoji is one character and two terminal columns, and hand-counting
   spaces is where alignment dies.

   ```python
   import unicodedata

   def dw(s):  # display width
       return sum(2 if unicodedata.east_asian_width(c) in 'WF' or ord(c) > 0x1F000
                  else 1 for c in s)

   widths = [max(dw(r[i]) for r in [header] + rows) for i in range(len(header))]
   for r in [header] + rows:
       print("".join(c + " " * (widths[i] - dw(c) + 2)
                     for i, c in enumerate(r)).rstrip())
   ```

7. **Keep what carries no identity.** Change anything naming a third party — their
   organisation, their projects, their internal shorthand, their people, their
   domains and hosts. Keep what only the user owns and that reveals nobody else:
   the tool being demonstrated, the user's own public handle, genuinely generic
   personal repo names. Keeping some real names is what makes the result readable
   instead of alphabet soup.

8. **Run the leak check.** Grep the finished text for every original from the
   mapping table; zero hits is the pass condition. This is the step that makes
   the result reliable rather than dependent on how carefully you read.

   ```bash
   grep -o -i -F -f originals.txt anonymized.txt | sort -u   # must print nothing
   ```

   Run it over **everything the job produces**, not just the pasted block: the
   summary you write about it, a ticket describing the change, a commit message,
   a skill or note recording the case. Prose written *about* an anonymization is
   where the originals come back, because there they look like explanation rather
   than data.

9. **Report the keep/change decision with the output.** List what you renamed and
   what you deliberately left. The user knows things you do not — that a
   "generic" repo name is a client codename, or that a colleague's first name is
   identifying in their circle. Make the decision easy to override.

## Common mistakes

| Mistake | What it costs |
|---|---|
| Quoting the raw output first, "to show the before" | The leak has happened; the anonymized version is theatre |
| Renaming the org column only | Internal shorthand survives in branches, windows and titles |
| A replacement one character longer | Column widths shift; the demo stops looking like real output |
| Renaming a derived column independently | `REPO` and `NAME` disagree on the same row |
| Giving a secret a plausible fake | Reads as a real value; the real one still needs rotating |
| Trusting your own reading instead of grepping | The occurrence you missed is the one still in the text |
| Grepping only the output, not the write-up around it | Real names re-enter through the summary, ticket or commit message |
| Changing timings, versions or row counts too | The demo stops being representative of anything |
