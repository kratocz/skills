---
name: geo-page-audit
description: Audit whether a site's pages are actually visible to search and AI crawlers — collapsed/tabbed content in server HTML, robots.txt and per-bot responses, cloaking, canonical/meta/JSON-LD/hreflang across a sitemap sample, sibling market domains, and a real LLM fetch — then have the conclusion adversarially refuted before it reaches anyone. Use when someone asks "vidí roboti náš obsah?", "jsou sbalené sekce vidět pro AI?", "proč nás AI necituje", "zkontroluj GEO/SEO našeho webu", "are our tabs visible to Googlebot", "can ChatGPT read this page", "audit the site for AI search", or claims that a redesign guaranteed hidden content stays crawlable.
---

# GEO page audit

Answer one question with evidence: **does the content a stakeholder cares about
reach a crawler, and does a real LLM actually come back with it?** The two are
different questions with different failure modes, and conflating them is how an
audit ends up reassuring people about the wrong thing.

The output is a dated document with numbers someone else can re-measure, plus
whatever unrelated defect the audit stumbles over — that by-catch is often
worth more than the question you were asked.

## Steps

### 1. Write the pass/fail criteria before measuring

Decide and write down, before the first request:

- **PASS for crawlers:** the text is in the server's HTTP response with no
  JavaScript executed. CSS hiding (`display:none`) is fine — crawlers do not
  apply CSS, and Google indexes content hidden behind tabs.
- **FAIL:** the content is absent from the raw HTML and arrives by JS after a
  click. LLM crawlers (GPTBot, ClaudeBot, PerplexityBot) do not execute JS, so
  for them it does not exist.
- **Second, independent condition:** those bots must not be blocked, by
  `robots.txt` or by the server.

Rules read after the result are not rules. Write them in the document first.

### 2. Fetch without a browser

`curl -sSL -A '<a real browser UA>' <url> -o page.html`. Then find the
component: grep the HTML for the classes of the collapsing widget
(`accordion`, `collapse`, `switchable`, `tab-pane`, `details`), and extract each
section's text.

Parse with `python3`, not shell regex — `grep -E` over a 600 KB HTML line hits
"exceeds complexity limits", and HTML parsers choke on real-world markup. Pair
`<div>` opens and closes with a counter to slice each panel, strip tags, and
report character counts per section. Do this for **three or four products from
different categories**, not one.

Then prove the hiding is cosmetic:

- download the stylesheet and find the rule (`.x--off .y{display:none}`);
- download the JS bundle and read the click handler — it should only
  `classList.add/remove`. If it contains `fetch`, that panel is lazy-loaded and
  the answer for it is different. Watch for a *second* kind of panel in the same
  widget (a size guide, a related-products strip) that is an AJAX link while its
  neighbours are static — check whether its content is nonetheless prerendered
  elsewhere in the page before calling it a failure.

Confirm in a real browser: snapshot each panel's `textContent` length before
clicking, click every trigger, snapshot again. Identical numbers mean expanding
adds nothing.

### 3. robots.txt and per-bot responses

Fetch `robots.txt`. Then fetch one product page under each UA that matters —
GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Googlebot — and record status
and size.

Two traps:

- **Do not conclude "nothing is blocked" from five user agents.** Sites carry UA
  denylists (Bytespider commonly gets 403) and nginx concurrency limits (three
  parallel connections from one IP can start returning 429 with no
  `Retry-After`). Test a couple of extra bots, and write the calibrated
  sentence — "the crawlers we care about are not blocked" — not "nothing is
  blocked".
- **Byte-equal whole pages are weak evidence against cloaking** and will
  embarrass you: a randomised recommended-products carousel makes the browser
  and bot responses differ in size while nothing is cloaked. The strong evidence
  is that **the content section itself is byte-identical** between bot and
  browser — slice it out of both responses and compare md5.

Be considerate: sequential requests with a small sleep. This is someone's
production site.

### 4. Sample the sitemap for structural SEO defects

Pull the sitemap index → the product sitemap. **`<loc>` values are often wrapped
in `<![CDATA[…]]>`** — a regex that keeps the wrapper produces a run of
`curl: (3) bad range in URL` and, if you suppress stderr, a silent page of
zeros. Strip it.

Take every Nth URL (30–50 pages is plenty), fetch sequentially with a delay, and
record per page: `rel="canonical"`, `meta name="description"`, `og:url`, the
JSON-LD blocks and their keys, `hreflang`, and whether the content component is
present at all.

What this reliably surfaces:

- **`canonical` pointing at the homepage** on a fraction of pages — usually an
  empty admin field falling back to root. This is the finding that can hollow
  out the whole effort while the content is demonstrably in the HTML, so look
  for it even when nobody asked.
- Empty `meta description` / `og:description`, `og:url` pointing at the
  homepage.
- JSON-LD `Product` with **no `description` key at all** (different from an
  empty one — different fix), and missing `FAQPage`.
- `Organization.sameAs` pointing at the agency's own social profiles instead of
  the client's. Genuinely common, genuinely embarrassing.
- Missing `hreflang` between market domains.

Report frequencies as `n/N (x %)`, name the affected URLs, and separate the
measured tag from the inferred impact. Check the counter-hypothesis before
claiming harm — if a page with a homepage canonical still ranks for its own
product name in a web search, the risk is real but **not yet realised**, and
saying so is what makes the rest of the report credible.

### 5. Sibling market domains

Find the other market domains from the page itself — analytics/GTM config blocks
often list them — rather than guessing TLDs. Guessing is how an audit reports
that a client's Slovak shop "does not exist" when the real address was sitting
in the HTML already downloaded, and the guessed domain belongs to a stranger.

For each: is it the same platform (same component, content in HTML) or a
different system? A different e-commerce platform means nothing built for the
main domain propagates there — a material finding for anyone planning
multi-market content.

When comparing content volume across platforms, compare **like with like**: the
main content region (`<main>`, the product block), not whole-page text. Whole
pages are 80 % navigation and footer, and the ratio you publish will be wrong.

### 6. Verify with a real LLM, not just with the HTML

The HTML answers "what does the server hand out". It does not answer "what does
the assistant come back with", which is what a user actually experiences.

Pick **markers**: 8–10 concrete values that occur *only* inside the collapsed
sections and nowhere else on the page (verify that programmatically —
`marker in accordion and marker not in rest`). Then ask, as the end user would:
*"Open <url> and list what is in sections X and Y; add nothing from other
sources; if you cannot see a section, say so."* Score markers found / total.

Run it two ways where possible — the provider API with a web-search tool, and
the chat UI the actual users have. They fetch and truncate differently.

Two behaviours worth knowing in advance:

- Asked for a **verbatim** transcription, an assistant may refuse on copyright
  grounds and return a ~25-word excerpt *while stating it can see the
  sections*. Ask for **"structured data (field: value)"** and it returns
  everything. A report that concludes "the model cannot read the page" from the
  first phrasing is simply wrong.
- Long pages can be truncated by raw-byte limits. Measure where the component
  sits: percentage through the HTML, and how many characters of *plain text*
  precede it. A page can be 600 KB of HTML but only 13 000 characters of text,
  which changes the conclusion completely.

For browser automation of a chat UI: the user logs in, never you. In a fresh
composer, typed input may drop ASCII characters — insert via
`document.execCommand('insertText', …)` on the contenteditable and submit by
clicking the send button. Keep batched waits under ~30 s and re-read the
conversation URL to get the completed answer.

### 7. Write it down, then have it refuted

Write `<docs>/test-<topic>-<date>.md`: the criteria from step 1, the result with
numbers, the mechanism (CSS rule, JS handler), the blocking caveat, the
by-catch findings, the sibling domains, and what is explicitly **not** covered.
Label fact vs inference per claim.

Then dispatch **one subagent whose brief is to refute it** — hand it the
document and the contract it must satisfy (who reads it, what decision rides on
it), never your reasoning. Tell it to re-measure every number itself, to hunt
for a counter-example in a wider sample, and to say plainly if it finds nothing.

Verify its critical findings with your own commands before accepting them — it
can be wrong too — and record the outcome in the document header
(`- **Ověření:** …`). Expect it to find something real: in the session this
skill came from, the refutation caught a sibling domain declared missing that
was in the downloaded HTML, an overbroad "nothing is blocked", and a
`rel="canonical"` defect the original pass never looked at.

## Reporting to a non-technical stakeholder

Lead with the answer to the question that was asked. Put the by-catch in its own
paragraph or a separate document — merging "yes, this works" with "but I found
something else broken" in one breath reads as evasion. Say which part is not
yours to fix and who owns it.
