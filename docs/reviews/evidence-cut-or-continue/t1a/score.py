# Score T1a: each out/<id>.out's verdict (the line after the last "codex" line) against labels.txt.
import os, re
here = os.path.dirname(os.path.abspath(__file__))
labels = dict(l.split() for l in open(os.path.join(here, 'labels.txt')))
res = {}
for cid in labels:
    lines = open(os.path.join(here, 'out', cid + '.out')).read().splitlines()
    i = max(n for n, l in enumerate(lines) if l == 'codex')
    m = re.match(r'CUT-CHECK: (CUT|PATCH)\b', lines[i + 1]) if i + 1 < len(lines) else None
    res[cid] = m.group(1) if m else 'NONE'
    print(cid, labels[cid], res[cid])
cuts = [c for c in labels if labels[c] == 'CUT']; pats = [c for c in labels if labels[c] == 'PATCH']
miss = [c for c in cuts if res[c] != 'CUT']; hit = [c for c in pats if res[c] == 'PATCH']
print(f'real cuts not called CUT: {len(miss)} of {len(cuts)} {miss} (bar: at most 1)')
print(f'patches called PATCH: {len(hit)} of {len(pats)} = {100*len(hit)/len(pats):.0f}% (bar: at least 80%)')
print('T1a', 'PASS' if len(miss) <= 1 and len(hit) >= 0.8 * len(pats) else 'FAIL')
