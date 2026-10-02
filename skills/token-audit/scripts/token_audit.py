#!/usr/bin/env python3
"""Where do the tokens go? Cost-driver analysis of Claude Code session transcripts.

Reads <projects>/<slug>/<session>.jsonl (main threads) and
<projects>/<slug>/<session>/subagents/agent-*.jsonl, weights usage by relative
price, and attributes cost to drivers an intervention can act on.

  token_audit.py [--projects DIR] [--since 30d|YYYY-MM-DD] [--until YYYY-MM-DD]
                 [--json OUT.json] [--baseline BASE.json]

Weights are relative to uncached input: input 1, 5-minute cache write 1.25,
1-hour cache write 2, cache read 0.1, output 5. The result is "input-equivalent
tokens", not money: models are not priced alike, so compare runs over a similar
model mix.
"""
import argparse, collections, datetime as dt, glob, json, os, statistics, sys

W_IN, W_CW5, W_CW1H, W_CR, W_OUT = 1.0, 1.25, 2.0, 0.1, 5.0
CHARS_PER_TOKEN = 2.33   # measured from context growth after single large tool results
REWRITE_MIN = 30_000     # a cache write this large on one request is a rewrite, not growth
IDLE_TTL_S = 3600


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--projects', default=os.path.expanduser('~/.claude/projects'))
    ap.add_argument('--since', default='30d')
    ap.add_argument('--until', default=None)
    ap.add_argument('--json', dest='json_out')
    ap.add_argument('--baseline')
    return ap.parse_args()


def parse_when(s, default):
    if s is None:
        return default
    if s.endswith('d') and s[:-1].isdigit():
        return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(s[:-1]))
    d = dt.datetime.fromisoformat(s)
    return d if d.tzinfo else d.astimezone()


def ts_of(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00')) if s else None


def cost(u):
    cw5 = (u.get('cache_creation') or {}).get('ephemeral_5m_input_tokens', 0) or 0
    cw = u.get('cache_creation_input_tokens', 0) or 0
    return ((u.get('input_tokens', 0) or 0) * W_IN + cw5 * W_CW5 + max(0, cw - cw5) * W_CW1H
            + (u.get('cache_read_input_tokens', 0) or 0) * W_CR + (u.get('output_tokens', 0) or 0) * W_OUT)


def ctx(u):
    return (u.get('input_tokens', 0) or 0) + (u.get('cache_creation_input_tokens', 0) or 0) + (u.get('cache_read_input_tokens', 0) or 0)


def result_chars(c):
    rc = c.get('content')
    if isinstance(rc, list):
        return sum(len(x.get('text', '')) for x in rc if isinstance(x, dict)) + \
            sum(6000 for x in rc if isinstance(x, dict) and x.get('type') == 'image')
    return len(str(rc or ''))


def read_file(path, since, until):
    """One transcript -> ordered events. Requests are deduplicated by requestId,
    keeping the record with the largest output_tokens (the streamed final one)."""
    reqs, order, pending = {}, [], {}
    for line in open(path, errors='replace'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get('type')
        m = d.get('message') or {}
        if t == 'system' and d.get('subtype') == 'compact_boundary':
            order.append(('compact',))
        elif t == 'attachment':
            a = d.get('attachment') or {}
            if a.get('type') == 'skill_listing':
                order.append(('res', 'skill listing', len(a.get('content') or '') / CHARS_PER_TOKEN))
        elif t == 'assistant':
            u, rid = m.get('usage'), d.get('requestId')
            if u and rid and m.get('model') != '<synthetic>':
                when = ts_of(d.get('timestamp'))
                if rid not in reqs:
                    reqs[rid] = dict(u=u, ts=when, model=m.get('model'))
                    order.append(('req', rid))
                elif (u.get('output_tokens') or 0) > (reqs[rid]['u'].get('output_tokens') or 0):
                    reqs[rid]['u'] = u
            for c in m.get('content') or []:
                if isinstance(c, dict) and c.get('type') == 'tool_use':
                    pending[c.get('id')] = (c.get('name') or '?', c.get('input') or {})
        elif t == 'user':
            cont = m.get('content')
            if d.get('isMeta') and isinstance(cont, list):
                for c in cont:
                    if isinstance(c, dict) and c.get('text', '').startswith('Base directory for this skill'):
                        order.append(('res', 'skill body', len(c['text']) / CHARS_PER_TOKEN))
            if isinstance(cont, list):
                tur = d.get('toolUseResult')
                for c in cont:
                    if isinstance(c, dict) and c.get('type') == 'tool_result':
                        name, inp = pending.get(c.get('tool_use_id'), ('?', {}))
                        key = '__'.join(name.split('__')[:2]) if name.startswith('mcp__') else name
                        if name == 'Bash':
                            words = (inp.get('command') or '').replace('&&', ' ').split()
                            words = [w for w in words if '=' not in w and w not in ('cd', 'command', 'sudo', 'env')]
                            key = 'Bash: ' + (' '.join(words[:2]) if words[:1] in (['git'], ['gh']) else (os.path.basename(words[0]) if words else '?'))
                        order.append(('res', key, result_chars(c) / CHARS_PER_TOKEN))
                        if name in ('Agent', 'Task') and isinstance(tur, dict) and tur.get('agentId'):
                            order.append(('agent', tur['agentId'], inp.get('subagent_type') or 'general-purpose'))
    out, seen_window = [], False
    for e in order:
        if e[0] == 'req':
            r = reqs[e[1]]
            if r['ts'] and since <= r['ts'] < until:
                out.append(('req', r)); seen_window = True
        elif e[0] == 'res':
            out.append(e + (seen_window,))
        else:
            out.append(e)
    return out


def main():
    a = parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    since, until = parse_when(a.since, now - dt.timedelta(days=30)), parse_when(a.until, now)
    mains = [f for f in glob.glob(f'{a.projects}/*/*.jsonl') if os.path.getmtime(f) >= since.timestamp()]
    total = 0.0
    comp = collections.Counter()
    by_model, sub_cost, n_req = collections.Counter(), 0.0, 0
    buckets = collections.Counter()
    main_ctx = []
    rewrite = collections.Counter()
    later_day = 0.0
    sess_cost = collections.Counter()
    resid = collections.Counter()
    sub_actual = sub_inline = sub_inline_nores = 0.0
    sub_runs = sub_wins = 0
    main_cost = 0.0

    def account(r, is_sub):
        nonlocal total, n_req, sub_cost
        u = r['u']; c = cost(u); total += c; n_req += 1
        cw5 = (u.get('cache_creation') or {}).get('ephemeral_5m_input_tokens', 0) or 0
        cw = u.get('cache_creation_input_tokens', 0) or 0
        comp['cache read'] += (u.get('cache_read_input_tokens', 0) or 0) * W_CR
        comp['cache write 1h'] += max(0, cw - cw5) * W_CW1H
        comp['cache write 5m'] += cw5 * W_CW5
        comp['output'] += (u.get('output_tokens', 0) or 0) * W_OUT
        comp['input'] += (u.get('input_tokens', 0) or 0) * W_IN
        by_model[r['model']] += c
        if is_sub:
            sub_cost += c
        return c

    for mf in mains:
        sess = os.path.basename(mf)[:-6]
        ev = read_file(mf, since, until)
        reqs = sorted((e[1] for e in ev if e[0] == 'req'), key=lambda r: r['ts'])
        linked = set()
        if not reqs:
            continue
        start_day = min(r['ts'] for r in reqs).astimezone().date()
        prev = None
        for r in reqs:
            c = account(r, False)
            sess_cost[sess] += c
            main_cost += c
            x = ctx(r['u']); main_ctx.append(x)
            buckets['<100k' if x < 100e3 else '100-200k' if x < 200e3 else '200-400k' if x < 400e3 else '>400k'] += c
            if r['ts'].astimezone().date() > start_day:
                later_day += c
            cw = r['u'].get('cache_creation_input_tokens', 0) or 0
            if prev and cw >= REWRITE_MIN and (r['u'].get('cache_read_input_tokens', 0) or 0) < 0.5 * x:
                gap = (r['ts'] - prev['ts']).total_seconds()
                switched = prev['model'] != r['model']
                cause = ('idle > 1h + model switch' if switched else 'idle > 1h (cache expired)') if gap > IDLE_TTL_S else \
                    'model switch' if switched else 'other (prefix changed, < 1h)'
                cw5 = (r['u'].get('cache_creation') or {}).get('ephemeral_5m_input_tokens', 0) or 0
                rewrite[cause] += cw5 * W_CW5 + (cw - cw5) * W_CW1H
            prev = r
        # residency: a result costs a write once, a read on every later request, and a
        # fresh write on every later full rewrite, until the next compaction
        later, rewrites_after = 0, 0
        for e in reversed(ev):
            if e[0] == 'req':
                later += 1
                u = e[1]['u']
                if (u.get('cache_creation_input_tokens', 0) or 0) >= REWRITE_MIN and \
                        (u.get('cache_read_input_tokens', 0) or 0) < 0.5 * ctx(u):
                    rewrites_after += 1
            elif e[0] == 'compact':
                later, rewrites_after = 0, 0
            elif e[0] == 'res' and later:
                first_write = 1 if e[3] else 0
                resid[e[1]] += e[2] * W_CW1H * (first_write + rewrites_after) + e[2] * W_CR * later
        # subagents: actual cost vs. doing the same work inline in this thread
        sdir = mf[:-6] + '/subagents'
        if os.path.isdir(sdir):
            pos_ctx, remaining = 0, len(reqs)
            for e in ev:
                if e[0] == 'req':
                    pos_ctx = ctx(e[1]['u']); remaining -= 1
                elif e[0] == 'agent':
                    sf = f'{sdir}/agent-{e[1]}.jsonl'
                    if not os.path.exists(sf):
                        continue
                    linked.add(sf)
                    sev = read_file(sf, since, until)
                    sreqs = [x[1] for x in sev if x[0] == 'req']
                    if not sreqs:
                        continue
                    act = sum(account(r, True) for r in sreqs)
                    sess_cost[sess] += act
                    payload = sum(x[2] for x in sev if x[0] == 'res')
                    out5 = sum((r['u'].get('output_tokens', 0) or 0) * W_OUT for r in sreqs)
                    inline = len(sreqs) * pos_ctx * W_CR + payload * (W_CW1H + W_CR * remaining) + out5
                    nores = len(sreqs) * pos_ctx * W_CR + payload * W_CW1H + out5
                    sub_actual += act; sub_inline += inline; sub_inline_nores += nores
                    sub_runs += 1; sub_wins += inline > act
            # subagent transcripts no tool result links to still cost: count them, outside the comparison
            for sf in glob.glob(f'{sdir}/agent-*.jsonl'):
                if sf not in linked:
                    for x in read_file(sf, since, until):
                        if x[0] == 'req':
                            sess_cost[sess] += account(x[1], True)
    if not total:
        sys.exit('no requests in the window')

    pct = lambda v: v / total * 100
    m = dict(window=f'{since:%Y-%m-%d %H:%M}..{until:%Y-%m-%d %H:%M} UTC', requests=n_req, sessions=len(sess_cost), total_M=round(total / 1e6, 1))
    m.update({f'share_{k.replace(" ", "_")}': round(pct(v), 1) for k, v in comp.items()})
    m.update({f'ctx_{k}': round(pct(v), 1) for k, v in buckets.items()})
    m['ctx_median_k'] = round(statistics.median(main_ctx) / 1e3) if main_ctx else 0
    slug = {'idle > 1h (cache expired)': 'idle', 'idle > 1h + model switch': 'idle_and_model_switch',
            'model switch': 'model_switch', 'other (prefix changed, < 1h)': 'other'}
    m.update({f'rewrite_{slug[k]}': round(pct(v), 1) for k, v in rewrite.items()})
    m['later_day_share'] = round(pct(later_day), 1)
    m['top10_sessions_share'] = round(pct(sum(v for _, v in sess_cost.most_common(10))), 1)
    m['subagent_share'] = round(pct(sub_cost), 1)
    m['tool_result_residency_share'] = round(pct(sum(v for k, v in resid.items() if not k.startswith('skill'))), 1)
    m['skills_share'] = round(pct(resid['skill listing'] + resid['skill body']), 1)
    m['subagent_inline_ratio'] = round(sub_inline / sub_actual, 2) if sub_actual else None
    m['subagent_inline_ratio_no_residency'] = round(sub_inline_nores / sub_actual, 2) if sub_actual else None
    m['main_thread_share'] = round(pct(main_cost), 1)

    print(f"window {m['window']}: {n_req} requests, {m['sessions']} sessions, {m['total_M']}M input-equivalent tokens")
    print('every % below is a share of this one total; the sections are overlapping slices of it, not addends')
    print('\ncost components:')
    for k, v in comp.most_common():
        print(f'  {k:16s} {pct(v):5.1f} %')
    print('\nby model:')
    for k, v in by_model.most_common(6):
        print(f'  {str(k):30s} {pct(v):5.1f} %')
    print(f"\nmain-thread context: median {m['ctx_median_k']}k; cost by context size (main threads = {m['main_thread_share']} % of total):")
    for k in ('<100k', '100-200k', '200-400k', '>400k'):
        print(f'  {k:9s} {pct(buckets[k]):5.1f} %')
    print('\ncache rewrites (>=30k written on one main request), by cause:')
    for k, v in rewrite.most_common():
        print(f'  {k:32s} {pct(v):5.1f} %')
    print(f"\nrequests on a later local day than their session started: {m['later_day_share']} %")
    print(f"top 10 sessions: {m['top10_sessions_share']} %")
    print(f"subagents: {m['subagent_share']} %; {sub_runs} linked runs, estimated cheaper than inline in {sub_wins}; "
          f"inline/actual = {m['subagent_inline_ratio']} (upper bound: their reads stay in context until compaction), "
          f"{m['subagent_inline_ratio_no_residency']} without that residency")
    print(f"\nresidency-weighted cost (write + reads + rewrites until compaction):")
    print(f"  tool results {m['tool_result_residency_share']} %, skills {m['skills_share']} %; top items:")
    bash = collections.Counter()
    for k, v in resid.items():
        (bash.__setitem__(k[6:], bash[k[6:]] + v) if k.startswith('Bash: ') else None)
    merged = collections.Counter({k: v for k, v in resid.items() if not k.startswith('Bash: ')})
    merged['Bash'] = sum(bash.values())
    for k, v in merged.most_common(8):
        print(f'    {k:32s} {pct(v):5.1f} %')
    print('  Bash by command:')
    for k, v in bash.most_common(6):
        print(f'    {k:32s} {pct(v):5.1f} %')

    if a.baseline:
        b = json.load(open(a.baseline))
        print(f"\ncompared with baseline {b.get('window')}:")
        for k, v in m.items():
            if isinstance(v, (int, float)) and isinstance(b.get(k), (int, float)) and k not in ('requests', 'sessions'):
                print(f'  {k:32s} {b[k]:>8} -> {v:>8}  ({v - b[k]:+.1f})')
        only = sorted(set(b) ^ set(m))
        if only:
            print('  not comparable (present in only one run — different script version?): ' + ', '.join(only))
    if a.json_out:
        json.dump(m, open(a.json_out, 'w'), indent=1)
        print(f'\nmetrics written to {a.json_out}')


if __name__ == '__main__':
    main()
