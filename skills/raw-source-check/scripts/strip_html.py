#!/usr/bin/env python3
"""Strip a fetched HTML page to plain text for quotation checking.

Usage: strip_html.py page.html [page.txt]

Drops <script>/<style>, turns block boundaries (<br>, </p>, </div>, </h1-6>, </li>)
into newlines, removes the remaining tags, unescapes entities, collapses runs of
spaces and blank lines. Prints the output path and word count so a suspiciously
small page (index, login wall, bot block, parked domain) is noticed at once.
"""
import html
import re
import sys


def strip(markup: str) -> str:
    markup = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', markup, flags=re.S | re.I)
    markup = re.sub(r'<br\s*/?>', '\n', markup, flags=re.I)
    markup = re.sub(r'</(p|div|h[1-6]|li|tr|blockquote)>', '\n', markup, flags=re.I)
    markup = re.sub(r'<[^>]+>', ' ', markup)
    text = html.unescape(markup)
    text = text.replace(' ', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    return text.strip() + '\n'


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    src = argv[1]
    dst = argv[2] if len(argv) > 2 else re.sub(r'\.html?$', '', src) + '.txt'
    with open(src, encoding='utf-8', errors='replace') as f:
        text = strip(f.read())
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(text)
    words = len(text.split())
    print('%s: %d words -> %s' % (src, words, dst))
    if words < 400:
        print('  WARNING: small page — index, login wall, bot block or parked domain? Read its first lines.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
