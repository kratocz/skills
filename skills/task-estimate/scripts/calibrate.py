#!/usr/bin/env python3
"""Build an effort calibration from a GitHub repository's pull requests and, optionally, a time-tracker export.

Two kinds of evidence, never mixed:
  * people WITHOUT time tracking (--commit-authors): effort per PR is inferred from their commit days.
    Each working day with commits is split across the PRs committed to that day (--weighting count:
    by commit count, equal: evenly). Variant B also spreads working days without any commit over the
    PRs "in flight" that day (a commit before and after). Units are person-days of capacity.
  * people WITH time tracking (--time-entries): tracked hours are tied to a PR when the entry text names
    "#123" / "PR 123" / "PRs #10-#12" (ranges split evenly), otherwise to a task key (--key-regex).
    Entries matching --review-regex are reviewer cost of that PR.

PR size ("core lines") = additions + deletions outside tests, migrations, docs and generated files.
Output: a JSON dump (--out) and a Markdown summary on stdout. Read-only: it only calls `gh` GET endpoints.

Time-entry JSON: a list of {"description": str, "start": ISO-8601 with offset, "seconds": int}.
"""
import argparse, collections, json, re, subprocess, time
import concurrent.futures as cf
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

GEN_DEFAULT = r"(\.min\.(js|css)$|tailwind\.css$|\.po$|\.mo$|(^|/)(uv|poetry|Cargo|Gemfile)\.lock$|package-lock\.json$|yarn\.lock$|pnpm-lock\.yaml$|\.(svg|png|jpe?g|gif|ico|pdf|drawio)$)"
# Defaults fit Python/Django and JavaScript projects; other stacks pass their own patterns.
TEST_DEFAULT = r"(/tests/|(^|/)(test_[^/]+|[^/]+_test)\.py$|\.(spec|test)\.[jt]sx?$)"
MIG_DEFAULT = r"/migrations/"
SIZES = [(10, "XXS <10 (i18n/test/CI-only)"), (50, "XS 10-50"), (200, "S 50-200"), (600, "M 200-600"),
         (2000, "L 600-2000"), (10**12, "XL 2000+")]


def expand_keys(text, keyre):
    """Task keys in text, expanding shorthand lists: 'ABC-15/16/17' and 'ABC-08..11' / 'ABC-08–11' / 'ABC-08-ABC-11'."""
    keys = set(keyre.findall(text))
    for m in re.finditer(r"\b([A-Z]{2,6})-(\d{1,4})((?:\s*/\s*\d{1,4})+)", text):
        width = len(m.group(2))
        for n in [m.group(2)] + re.findall(r"\d{1,4}", m.group(3)):
            keys.add(f"{m.group(1)}-{int(n):0{width}d}")
    for m in re.finditer(r"\b([A-Z]{2,6})-(\d{1,4})\s*(?:\.\.|–|—|-)\s*(?:\1-)?(\d{1,4})\b", text):
        lo, hi, width = int(m.group(2)), int(m.group(3)), len(m.group(2))
        if lo < hi <= lo + 20:
            keys.update(f"{m.group(1)}-{n:0{width}d}" for n in range(lo, hi + 1))
    return sorted(k for k in keys if keyre.fullmatch(k))


def gh(args):
    for attempt in range(5):
        try:
            return subprocess.check_output(["gh"] + args, stderr=subprocess.DEVNULL).decode()
        except subprocess.CalledProcessError:
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"gh failed: {args}")


def bucket(path, gen, mig, test):
    if gen.search(path): return "gen"
    if mig.search(path): return "mig"
    if path.startswith("docs/") or path.endswith(".md"): return "docs"
    if test.search(path): return "test"
    return "core"


def size_class(core):
    return next(label for limit, label in SIZES if core < limit)


def q(values, p):
    v = sorted(values)
    if not v: return None
    return round(v[min(len(v) - 1, max(0, int(round(p * (len(v) - 1)))))], 2)


def quantile_row(label, values):
    if not values: return f"| {label} | 0 | | | | | | |"
    mean = sum(values) / len(values)
    return (f"| {label} | {len(values)} | {q(values, .25)} | {q(values, .5)} | {round(mean, 2)} | {q(values, .8)} | "
            f"{q(values, .9)} | {round(max(values), 2)} |")


QHEAD = ["| {} | n | P25 | P50 | mean | P80 | P90 | max |", "|---|---|---|---|---|---|---|---|"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD; PRs created before are ignored")
    ap.add_argument("--commit-authors", default="", help="comma-separated forge logins without time tracking")
    ap.add_argument("--tz", default="UTC")
    ap.add_argument("--holidays", default="", help="comma-separated YYYY-MM-DD")
    ap.add_argument("--weighting", choices=["count", "equal"], default="count")
    ap.add_argument("--time-entries", help="JSON export of the tracked person's entries")
    ap.add_argument("--key-regex", default=r"\b[A-Z]{2,6}-\d{1,4}\b", help="task key pattern in entry text and PR titles")
    ap.add_argument("--review-regex", default=r"\b(CR|review|re-review|code review)\b")
    ap.add_argument("--generated-regex", default=GEN_DEFAULT)
    ap.add_argument("--test-regex", default=TEST_DEFAULT,
                    help="paths counted as tests, not core; e.g. Go '_test\\.go$', JVM '(^|/)src/test/'")
    ap.add_argument("--migration-regex", default=MIG_DEFAULT,
                    help="paths counted as migrations, not core; e.g. Rails '(^|/)db/migrate/'")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    tz = ZoneInfo(a.tz)
    holidays = {date.fromisoformat(h) for h in a.holidays.split(",") if h}
    gen = re.compile(a.generated_regex)
    mig, test = re.compile(a.migration_regex), re.compile(a.test_regex)
    keyre = re.compile(a.key_regex)
    prs = json.loads(gh(["pr", "list", "-R", a.repo, "--state", "all", "--limit", "1000", "--json",
                         "number,title,state,author,createdAt,mergedAt,headRefName"]))
    prs = [p for p in prs if p["createdAt"][:10] >= a.since]

    def detail(n):
        files = gh(["api", "--paginate", f"repos/{a.repo}/pulls/{n}/files", "--jq", ".[] | [.filename, .additions, .deletions] | @tsv"]).splitlines()
        commits = gh(["api", "--paginate", f"repos/{a.repo}/pulls/{n}/commits", "--jq",
                      ".[] | [.sha, .commit.author.date, (.author.login // \"\")] | @tsv"]).splitlines()
        return n, [l.split("\t") for l in files], [l.split("\t") for l in commits]

    rows = {}
    with cf.ThreadPoolExecutor(3) as ex:
        for n, files, commits in ex.map(detail, [p["number"] for p in prs]):
            rows[n] = {"files": files, "commits": commits}
    for p in prs:
        r = rows[p["number"]]
        loc = collections.Counter()
        for f in r["files"]:
            if len(f) == 3: loc[bucket(f[0], gen, mig, test)] += int(f[1]) + int(f[2])
        r.update(number=p["number"], title=p["title"], state=p["state"], author=p["author"]["login"],
                 created=p["createdAt"], merged=p["mergedAt"], core=loc["core"], loc=dict(loc),
                 keys=expand_keys(p["title"] + " " + p["headRefName"], keyre))

    out = {"params": vars(a), "people": {}, "prs": {}}
    md = [f"# Calibration for {a.repo} since {a.since}", ""]

    # ---- commit-day attribution per author ----
    for login in [x for x in a.commit_authors.split(",") if x]:
        mine = {n: r for n, r in rows.items() if r["author"] == login}
        per_day = collections.defaultdict(collections.Counter)
        seen = set()
        for n, r in mine.items():
            for c in r["commits"]:
                if len(c) < 3 or c[0] in seen or (c[2] and c[2] != login): continue
                seen.add(c[0])
                d = datetime.fromisoformat(c[1].replace("Z", "+00:00")).astimezone(tz).date()
                per_day[d][n] += 1
        if not per_day: continue
        eff_a = collections.defaultdict(float)
        for d, cnt in per_day.items():
            tot = sum(cnt.values()) if a.weighting == "count" else len(cnt)
            for n, k in cnt.items():
                eff_a[n] += (k if a.weighting == "count" else 1) / tot
        span = {}
        for d, cnt in per_day.items():
            for n in cnt:
                lo, hi = span.get(n, (d, d)); span[n] = (min(lo, d), max(hi, d))
        eff_b = collections.defaultdict(float, eff_a)
        d0, d1 = min(per_day), max(per_day)
        work = gap = idle = 0
        d = d0
        while d <= d1:
            if d.weekday() < 5 and d not in holidays:
                work += 1
                if d not in per_day:
                    gap += 1
                    flight = [n for n, (lo, hi) in span.items() if lo < d < hi]
                    if flight:
                        for n in flight: eff_b[n] += 1 / len(flight)
                    else:
                        idle += 1
            d += timedelta(days=1)
        out["people"][login] = {"window": [d0.isoformat(), d1.isoformat()], "working_days": work, "commit_days": len(per_day),
                                "gap_days": gap, "idle_days": idle, "availability": round((work - idle) / work, 3)}
        md += [f"## {login} — person-days per merged PR (weighting: {a.weighting})", "",
               f"Window {d0}..{d1}: {work} working days, {len(per_day)} with commits, {gap} without, {idle} with no PR in flight "
               f"→ availability ≈ {(work - idle) / work:.0%}.", "",
               QHEAD[0].format("size (core lines)"), QHEAD[1]]
        merged = [n for n, r in mine.items() if r["merged"]]
        for _, label in SIZES:
            g = [n for n in merged if size_class(rows[n]["core"]) == label]
            md.append(quantile_row(f"{label} (A)", [eff_a[n] for n in g]))
            md.append(quantile_row(f"{label} (B)", [eff_b[n] for n in g]))
        md += ["", QHEAD[0].format("month created"), QHEAD[1]]
        for m in sorted({rows[n]["created"][:7] for n in merged}):
            md.append(quantile_row(m + " (B)", [eff_b[n] for n in merged if rows[n]["created"][:7] == m]))
        md += ["", "Calendar lead time, PR opened → merged (days; what a due date must allow on top of effort):", "",
               QHEAD[0].format("size"), QHEAD[1]]
        lead = {n: (datetime.fromisoformat(rows[n]["merged"].replace("Z", "+00:00")) -
                    datetime.fromisoformat(rows[n]["created"].replace("Z", "+00:00"))).total_seconds() / 86400 for n in merged}
        for _, label in SIZES:
            md.append(quantile_row(label, [lead[n] for n in merged if size_class(rows[n]["core"]) == label]))
        months = collections.defaultdict(lambda: [0, 0])
        d = d0
        while d <= d1:
            if d.weekday() < 5 and d not in holidays:
                months[d.strftime("%Y-%m")][0] += 1
                if d not in per_day and not any(lo < d < hi for lo, hi in span.values()):
                    months[d.strftime("%Y-%m")][1] += 1
            d += timedelta(days=1)
        md += ["", "Availability by month (working days not idle; idle = no commit and no PR in flight — absence, other work, "
               "or work that left no commit). Use a recent month minus announced absences, not the blended figure:", ""]
        md += [f"- {m}: {(w - i) / w:.0%} ({w - i}/{w})" for m, (w, i) in sorted(months.items())]
        out["people"][login]["availability_by_month"] = {m: round((w - i) / w, 3) for m, (w, i) in months.items()}
        # velocity: class-mean (variant B) estimates of the PRs merged per working day, by month of merge
        class_mean = {}
        for _, label in SIZES:
            g = [eff_b[n] for n in merged if size_class(rows[n]["core"]) == label]
            class_mean[label] = sum(g) / len(g) if g else None
        md += ["", "Velocity — sum of class-mean estimates (variant B, person-days) of the PRs merged per working day, by month "
               "of merge. The window figure is the baseline; a recent month far above or below it means the working day "
               "changed, so schedule at the recent velocity rather than at day length × availability:", ""]
        for m in sorted(months):
            done_m = [n for n in merged if rows[n]["merged"][:7] == m and class_mean.get(size_class(rows[n]["core"]))]
            est_m = sum(class_mean[size_class(rows[n]["core"])] for n in done_m)
            md.append(f"- {m}: {est_m:.1f} person-days of estimates in {months[m][0]} working days = {est_m / months[m][0]:.2f} per day")
        tot_est = sum(class_mean[size_class(rows[n]["core"])] for n in merged if class_mean.get(size_class(rows[n]["core"])))
        md.append(f"- whole window: {tot_est:.1f} / {work} = {tot_est / work:.2f} per day")
        out["people"][login]["class_mean_days"] = class_mean
        open_ = [n for n, r in mine.items() if r["state"] == "OPEN"]
        md += ["", f"Open (right-censored, not in the tables): {len(open_)} PRs, effort so far {sum(eff_b[n] for n in open_):.1f} days.", ""]
        for n in mine:
            out["prs"].setdefault(n, {})["days_a"] = round(eff_a[n], 3)
            out["prs"][n]["days_b"] = round(eff_b[n], 3)

    # ---- tracked time ----
    if a.time_entries:
        entries = json.load(open(a.time_entries))
        prre = re.compile(r"(?:PRs?\s*#?|#)(\d{1,5})(?:\s*[–-]\s*#?(\d{1,5}))?")
        revre = re.compile(a.review_regex, re.I)
        pr_h, rev_h, key_h, rev_unattributed = (collections.defaultdict(float) for _ in range(4))
        total = 0.0
        for e in entries:
            h = e["seconds"] / 3600; total += h
            text = e["description"] or ""
            nums = []
            for m in prre.finditer(text):
                lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else lo
                if lo <= hi <= lo + 20: nums += list(range(lo, hi + 1))
            nums = [x for x in dict.fromkeys(nums) if x in rows]
            if nums:
                for x in nums:
                    pr_h[x] += h / len(nums)
                    if revre.search(text): rev_h[x] += h / len(nums)
                continue
            if revre.search(text): rev_unattributed[e["start"][:7]] += h
            keys = expand_keys(text, keyre)
            for k in keys: key_h[k] += h / len(keys)
        md += ["## Tracked time", "", f"{total:.0f} h in {len(entries)} entries: {sum(pr_h.values()):.0f} h name a PR "
               f"({sum(rev_h.values()):.0f} h of it review-worded), {sum(key_h.values()):.0f} h only a task key, "
               f"{total - sum(pr_h.values()) - sum(key_h.values()):.0f} h neither.", "",
               "Reviewer hours per merged PR of the commit authors, by size:", "",
               QHEAD[0].format("size (PRs with time)"), QHEAD[1]]
        authored = [n for n, r in rows.items() if r["author"] in a.commit_authors.split(",") and r["merged"]]
        for _, label in SIZES:
            md.append(quantile_row(label, [rev_h[n] for n in authored if size_class(rows[n]["core"]) == label and rev_h[n] > 0]))
        md += ["", "Per-PR attribution misses review booked without a PR number (batch reviews, posting rounds). "
               "Aggregate review cost per merged PR of the commit authors, by month of merge "
               "(review-worded hours on their PRs + review-worded hours naming no PR) / merged PRs:", ""]
        merged_by_month = collections.Counter(rows[n]["merged"][:7] for n in authored)
        rev_by_month = collections.defaultdict(float)
        for n in authored:
            rev_by_month[rows[n]["merged"][:7]] += rev_h[n]
        for m in sorted(merged_by_month):
            tot_m = rev_by_month[m] + rev_unattributed[m]
            md.append(f"- {m}: {tot_m:.1f} h / {merged_by_month[m]} PRs = {tot_m / merged_by_month[m]:.2f} h per PR")
        md += ["", "Tracked hours per task key (entries without a PR number):", ""]
        for k, h in sorted(key_h.items(), key=lambda kv: -kv[1]):
            md.append(f"- {k}: {h:.1f} h")
        for n in rows:
            out["prs"].setdefault(n, {})["tracked_h"] = round(pr_h[n], 2)
            out["prs"][n]["review_h"] = round(rev_h[n], 2)
        out["key_hours"] = {k: round(v, 2) for k, v in key_h.items()}

    for n, r in rows.items():
        out["prs"].setdefault(n, {}).update(title=r["title"], author=r["author"], state=r["state"], created=r["created"],
                                             merged=r["merged"], core=r["core"], loc=r["loc"], size=size_class(r["core"]), keys=r["keys"])
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print("\n".join(md))


if __name__ == "__main__":
    main()
