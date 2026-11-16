#!/usr/bin/env python3
"""Turn the approved Markdown text of an e-mail into Gmail htmlBody.

Usage:
    python3 md2html.py <file.md> [--section "## Email text"] [-o out.html]

Without --section the whole file is the e-mail body. With --section only the
part after that heading line is used, up to the next heading of the same or
higher level. A leading "**Subject:** …" (or "**Předmět:** …") line is
dropped: the subject goes to the tool's `subject` parameter.

Supported Markdown: paragraphs (lines inside one paragraph are joined with
<br>, e.g. a signature), "### " headings (rendered as a bold paragraph),
numbered and "- " lists, **bold**, *italic* and [text](url) links.

Every bare domain in the visible text (example.com, Example.ORG …) is broken
with <span>.</span> so Gmail does not linkify it, and the script fails if one
survives or if a link's visible text is itself a URL or a domain.

Runs on Python 3.9 and later.
"""
import argparse
import html
import re
import sys
from pathlib import Path

TLD = r"(?:cz|sk|com|org|net|io|ai|eu|de|pl|uk|info|dev|app)"
DOMAIN = re.compile(r"\b([\w-]+(?:\.[\w-]+)*)\.(" + TLD + r")\b", re.I)
SUBJECT = re.compile(r"^\*\*(?:Subject|Předmět):\*\*")
NUMBERED = re.compile(r"^\d+\. ")


def section(text, heading):
    if not heading:
        return text
    level = len(heading) - len(heading.lstrip("#"))
    lines = text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == heading.strip())
    except StopIteration:
        sys.exit(f"heading not found: {heading}")
    out = []
    for l in lines[start + 1:]:
        m = re.match(r"^(#+) ", l)
        if m and len(m.group(1)) <= level:
            break
        out.append(l)
    return "\n".join(out)


def break_domains(s):
    return DOMAIN.sub(lambda m: m.group(1) + "<span>.</span>" + m.group(2), s)


def inline(s):
    links = []

    def keep(m):
        label, url = m.group(1), m.group(2)
        if re.match(r"^\w+://", label) or DOMAIN.search(label):
            sys.exit(f"link text looks like a URL or domain, Gmail would rewrite it: {label}")
        links.append((label, url))
        return f"\x00{len(links) - 1}\x00"

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", keep, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    s = break_domains(s)

    def restore(m):
        label, url = links[int(m.group(1))]
        return f'<a href="{html.escape(url)}">{break_domains(html.escape(label, quote=False))}</a>'

    return re.sub(r"\x00(\d+)\x00", restore, s)


def items(rows, strip):
    return "".join("<li>" + inline(strip(r)) + "</li>" for r in rows)


def convert(body):
    lines = body.strip("\n").split("\n")
    if lines and SUBJECT.match(lines[0]):
        lines = lines[1:]
    out = []
    for block in "\n".join(lines).strip("\n").split("\n\n"):
        block = block.strip("\n")
        if not block:
            continue
        rows = block.split("\n")
        if re.match(r"^#{1,6} ", block):
            out.append("<p><b>" + inline(re.sub(r"^#+ ", "", block)) + "</b></p>")
        elif all(NUMBERED.match(r) for r in rows):
            out.append("<ol>" + items(rows, lambda r: NUMBERED.sub("", r)) + "</ol>")
        elif all(r.startswith("- ") for r in rows):
            out.append("<ul>" + items(rows, lambda r: r[2:]) + "</ul>")
        else:
            out.append("<p>" + "<br>".join(inline(r) for r in rows) + "</p>")
    result = "".join(out)
    visible = re.sub(r"<[^>]+>", " ", result.replace("<span>.</span>", "․"))
    left = DOMAIN.findall(visible)
    if left:
        sys.exit(f"bare domain left in visible text: {left}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--section")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    result = convert(section(Path(a.file).read_text(encoding="utf-8"), a.section))
    if a.output:
        Path(a.output).write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
