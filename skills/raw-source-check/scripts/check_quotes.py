#!/usr/bin/env python3
"""Check that every quotation in a note is a verbatim substring of a stripped source.

Usage:
  check_quotes.py --note NOTE.md --sources a.txt b.txt ... [options]

Options:
  --require-chars CHARS   only check quotations containing at least one of CHARS
                          (e.g. Czech diacritics) — skips English glosses
  --min-len N             ignore quoted spans shorter than N chars (default 8)
  --max-len N             ignore quoted spans longer than N chars (default 2000);
                          raise it when a long quotation is reported missing
  --quotes-file FILE      check these quotations (one per line) instead of
                          extracting them from the note
  --context N             for each hit, print N chars of source before and after
  --bisect                for each miss, print the longest matching prefix and
                          where the note and the source diverge

Every quotation is split on ellipses ("...", "…") and on "**" markers, editorial
brackets are removed, whitespace/NBSP normalized and case folded on both sides;
each fragment must occur in at least one source. Exit code 1 if any fragment is
missing, so the check can gate a commit.
"""
import argparse
import io
import re
import sys


def norm(text: str) -> str:
    text = text.replace(' ', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def load_sources(paths):
    out = {}
    for p in paths:
        with io.open(p, encoding='utf-8', errors='replace') as f:
            out[p] = norm(f.read())
    return out


def extract_quotes(note_text, min_len, max_len):
    spans = re.findall(r'"([^"]{%d,%d})"' % (min_len, max_len), note_text)
    spans += re.findall(r'„([^“”]{%d,%d})[“”]' % (min_len, max_len), note_text)
    spans += re.findall(r'“([^”]{%d,%d})”' % (min_len, max_len), note_text)
    return spans


def fragments(quote):
    parts = re.split(r'\s*(?:\.\.\.|…|\*\*)\s*', quote)
    return [re.sub(r'\[|\]', '', p) for p in parts if len(p.strip()) > 6]


def longest_prefix(needle, hay):
    lo, hi = 0, len(needle)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if needle[:mid] in hay:
            lo = mid
        else:
            hi = mid - 1
    return lo


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--note', required=True)
    ap.add_argument('--sources', nargs='+', required=True)
    ap.add_argument('--require-chars', default='')
    ap.add_argument('--min-len', type=int, default=8)
    ap.add_argument('--max-len', type=int, default=2000)
    ap.add_argument('--quotes-file')
    ap.add_argument('--context', type=int, default=0)
    ap.add_argument('--bisect', action='store_true')
    args = ap.parse_args()

    sources = load_sources(args.sources)
    if args.quotes_file:
        with io.open(args.quotes_file, encoding='utf-8') as f:
            quotes = [l.rstrip('\n') for l in f if l.strip()]
    else:
        with io.open(args.note, encoding='utf-8') as f:
            quotes = extract_quotes(f.read(), args.min_len, args.max_len)

    checked = missing = 0
    for q in quotes:
        if args.require_chars and not any(ch in q for ch in args.require_chars):
            continue
        checked += 1
        for frag in fragments(q):
            needle = norm(frag)
            hits = [name for name, hay in sources.items() if needle in hay]
            if hits:
                print('ok(%s) %s' % (','.join(hits), frag[:70]))
                if args.context:
                    hay = sources[hits[0]]
                    i = hay.find(needle)
                    print('    <<< %s' % hay[max(0, i - args.context):i])
                    print('    >>> %s' % hay[i + len(needle):i + len(needle) + args.context])
            else:
                missing += 1
                print('MISS   %s' % frag[:150])
                if args.bisect:
                    best = max(sources.items(), key=lambda kv: longest_prefix(needle, kv[1]))
                    n = longest_prefix(needle, best[1])
                    print('    longest matching prefix in %s: %d/%d chars' % (best[0], n, len(needle)))
                    print('    note  : ...%s|%s...' % (needle[max(0, n - 40):n], needle[n:n + 40]))
                    k = best[1].find(needle[max(0, n - 40):n]) if n else -1
                    if k >= 0:
                        print('    source: ...%s' % best[1][k:k + 90])
    print('\nquotations checked: %d, fragments missing: %d' % (checked, missing))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
