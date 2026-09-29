---
name: raw-source-check
description: Verify every quotation in a note or draft against the raw source page — fetched with curl and stripped to text, never through a summarizer — fragment by fragment across ellipses, then read what surrounds each hit, because a verbatim quote can still misrepresent its source. Records bot blocks, login walls and parked mirrors as what the sourcing cost. Use when the user says "/raw-source-check", "ověř citace", "zkontroluj citace proti zdroji", "sedí ty citáty?", "check the quotes against the source", "verify quotations", "is that quote really there", or before a note that quotes a web page is called done.
version: 1.0.0
license: MIT
---

# Raw source check — quotations against the page they came from

## Overview

Two failures hide behind a quotation that looks verified. The cheap one: the words are not on the page (paraphrase remembered as quote, a dropped clause, a changed subject, an ellipsis that was never written). The expensive one: the words are on the page, character for character, and the quote is still wrong — cut two sentences before the argument turns, lifted from a paragraph that points the other way, or a concession that the next sentence reveals as the premise of a *tu quoque*. A summarizing fetch hides both; a mechanical substring check catches the first; only reading the surroundings catches the second. This skill does all three in order, and it writes down what it could not fetch.

Real case (2026-09-14/17): an apologetics chapter was quoted verbatim in a philosophical note as evidence that it "levels" science and faith. Both quotations passed a character-level check. The first pass had cut a geophysicist's argument two sentences before "for me modern palaeoscience is no credible source"; the "levelling" sentences closed a paragraph that was one-way from its first line. The note's own correction had to be retracted.

## Steps

### 1. Collect what has to be checked

- Extract every quotation in the note: double-quoted spans, plus block quotes and `> ` lines if the note uses them. Note the language(s) the sources are in — the checker can restrict itself to quotations containing that language's characters (e.g. Czech diacritics) so that English glosses are not flagged.
- List the pages each quotation is attributed to. One page per URL; a chapter "index" page usually holds no body text, so follow the links to the actual sections.

### 2. Fetch raw, strip, and look at the size

For each URL, from the scratchpad:

```bash
curl -sL --max-time 40 -A "Mozilla/5.0" "<url>" -o page.html
python3 <this skill's scripts/>strip_html.py page.html page.txt
```

`strip_html.py` drops `<script>`/`<style>`, turns `<br>`, `<p>`, `<div>`, `<h*>`, `<li>` boundaries into newlines, strips the rest of the tags, unescapes entities and collapses whitespace. Then **read the word count and the first lines** before trusting the text:

- a few hundred words on a page that should carry an article → an index/landing page, a login wall ("only for registered users"), or a cookie/consent shell; find the real URL or record the wall;
- an error page in the body → bot protection (seen: IIS "HTTP Error 999.0 – AW Special Error" from augustinus.it, which refuses non-browser clients outright);
- content unrelated to the topic → a parked or resold domain (seen: stephenjaygould.org serving gambling spam where the NOMA essay used to be).

Never fetch through a summarizing tool for load-bearing wording: a summarizer returned a paraphrase of Ezekiel 29:17–20 that dropped the very clause an argument rested on.

### 3. Mechanical check — every fragment a verbatim substring

```bash
python3 <this skill's scripts/>check_quotes.py --note <note.md> --sources page1.txt page2.txt … [--require-chars "áéěíóúůýčďňřšťž"] [--min-len 8] [--max-len 2000]
```

What it does: normalizes whitespace and NBSP on both sides, lowercases, splits each quotation on ellipses (`...`, `…`) and on `**` emphasis markers, strips `[…]` editorial brackets, and requires every fragment longer than a few characters to be a substring of at least one source. Output is one line per fragment: `ok(<source>)` or `MISS`.

Reading the output:

- A `MISS` from a source you did not fetch (scripture verified elsewhere, a book) is expected — list those as "not in corpus", do not let them hide real misses.
- A `MISS` on a long quotation whose short fragments all pass usually means the quote marks in the note pair differently from the source (nested `"věda"` in the source rendered as `'věda'` in the note — an accepted convention, but say so) or a word was silently dropped: bisect the quotation (`--bisect` prints the longest matching prefix and the point of divergence).
- Spurious spans: quote characters pair sequentially through the file, so an unpaired `"` in prose makes the extractor join the end of one quotation to the start of the next. Raise `--max-len` and re-run, or pass `--quotes-file` with the quotations listed one per line.
- Watch the three silent edits the checker cannot see: an ellipsis missing where words were dropped ("věda historická … o původu" for "věda historická nebo věda o původu"), a truncation with no ellipsis at the end ("pouhou vírou" for "pouhou vírou a velmi spekulativní hypotézou"), and a subject swapped in the gloss around the quote ("dating methods" for "dating methods used by evolutionists"). Compare each `ok` fragment's boundaries against the source by eye once.

### 4. Context check — read around every hit

For each quotation that passed, print its surroundings and read them:

```bash
python3 <this skill's scripts/>check_quotes.py --note <note.md> --sources … --context 400
```

Questions to answer for each one, in writing if the quotation carries weight:

- **Where does the passage actually end?** If the quotation stops before the paragraph does, read to the end. The sentence that reverses the sense is usually the next one.
- **What is the paragraph doing?** A symmetric-sounding sentence can close a paragraph that is one-way from its first line. Read from the paragraph's start.
- **Is a concession a concession?** "Our side has no answers to everything" followed by "but anyone who thinks the other side is better off is mistaken" is a *tu quoque* premise, not an admission. Do not credit it as one.
- **Whose claim is it?** "According to some creationist scientists there are dozens of dating methods…" is reported, not asserted; the note must not write "the chapter claims".
- **Is the gloss faithful?** The paraphrase before and after the quotation must keep the source's subject, hedge ("I think that…") and scope ("on theologically sensitive questions").

### 5. Record what the sourcing cost

In the note's Sources (or wherever the note keeps its receipts), write down:

- which pages were read raw and when — "fetched as HTML and stripped to text, not through a summarizer, YYYY-MM-DD";
- every blocked, gated or dead source, with what was tried: "two fetches refused by the host (IIS 999), YYYY-MM-DD", "bibliography behind a login — the chapter's numbered references cannot be followed without an account", "the usual mirror is now a parked spam domain" — and what the argument does without it (a position used "as a position, not as a citation");
- quotations deliberately altered in form (nested quote marks, a bracketed case ending) so the next checker does not re-flag them;
- what the check changed: restored ellipses, re-subjected glosses, quotations extended to the end of their argument — and, when the context check overturned a reading, the retraction itself, visibly, not by editing around it.

### 6. Re-run until clean

After every edit round, re-run step 3. The check is clean when the only `MISS` lines are the declared not-in-corpus quotations. Keep the fetched `.txt` files for the note's next adversarial pass — a reviewer briefed to refute the note should get them, so it can verify quotations character by character rather than re-fetch.

## Gotchas

- The same text fetched twice can differ (consent banners, A/B layouts); keep the copy the check ran against.
- `<br>` inside a sentence puts a newline mid-clause in the stripped text — that is why the checker normalizes whitespace; never grep the raw `.txt` for a multi-word phrase without doing the same.
- Diacritics: match on the original characters, never on an ASCII-folded copy — "vira" would match "víra" and also "vira" (virus) in a different sentence.
- In a worktree-isolated agent session the harness refuses loops and heredocs in one Bash line; write the fetch list as a small script and run it as one command.
