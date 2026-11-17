# Evidence: cut-or-continue plan

For `SKILL-PLAN-review-cut-or-continue.md`. Everything below was run on 2026-11-17, against the
cost log `~/.local/state/independent-review/runs.tsv` (17 columns; 15 to 17 are `earned_by`, `cut`,
`reason`) and this repo at `origin/main` `5a0b3010`. The log covers every repo the maintainer
reviews; only aggregate counts are given for other repos, and only this repo's gates are named.

## 1. Definitions, as the script computes them

- A **round** is one `--round N` of one gate id (all seats of that round together).
- A **cut** settles only the kinds on the log line that carries it, as `review_log.sh` counts it
  (another seat's line in the same round may name a kind the cut was not about). Round 1's review
  pointed out that the first count settled every kind of the round; recounted per line, every figure
  below came out the same.
- A **return** is a later round whose `earned_by` names a kind (compared as the script does:
  lower-cased, without `.`, `_`, `-`) that an earlier cut round named. The `earned_by` of round N
  names what round N−1 found, so a return at round N means the round reviewing the cut, or a
  later one, found that kind again.
- **Rounds from the first return** count the round of the return and every round after it.
- **The most it can save:** the rounds after the return round. The return round itself still runs,
  because it reviews whatever the next fix is.

## 2. The measurement script (as run)

```python
import sys,re,collections
import os; F=os.path.expanduser('~/.local/state/independent-review/runs.tsv')
rows=[]
for line in open(F):
    p=line.rstrip('\n').split('\t')
    if p[0]=='date': continue
    p+=['-']*(17-len(p)); rows.append(p)
norm=lambda k: re.sub(r'[._-]','',k.lower())
since=sys.argv[1]
win=[p for p in rows if p[0][:10]>=since]
tot=sum(int(p[11]) for p in win if p[11].isdigit())
gates=collections.defaultdict(list)
for p in win:
    if p[13] not in ('','-'): gates[p[13]].append(p)
out=[]
for g,ps in gates.items():
    rounds=collections.defaultdict(list)
    for p in ps:
        if p[6].isdigit(): rounds[int(p[6])].append(p)
    K=lambda r:set(norm(k) for q in rounds[r] for k in q[14].split(',') if k not in('','-'))
    C=lambda r:any(q[15] not in('','-') for q in rounds[r])
    cutk=set(); returns=[]
    for r in sorted(rounds):
        if K(r)&cutk: returns.append(r)
        # a cut settles only the kinds on the row that carries it (review_log.sh does the same)
        cutk|=set(norm(k) for q in rounds[r] if q[15] not in('','-') for k in q[14].split(',') if k not in('','-'))
    if not returns: continue
    r1=returns[0]; last=max(rounds)
    after=[r for r in rounds if r>=r1]
    toks=sum(int(q[11]) for r in after for q in rounds[r] if q[11].isdigit())
    nt=sum(1 for r in after for q in rounds[r] if not q[11].isdigit())
    toks2=0; after2=[]
    if len(returns)>=2:
        after2=[r for r in rounds if r>=returns[1]]
        toks2=sum(int(q[11]) for r in after2 for q in rounds[r] if q[11].isdigit())
    # did a round past 8 exist? did the rounds end with no kind (clean)?
    out.append(dict(g=g,branch=ps[0][2],gate=ps[0][4],depth=ps[0][5],r1=r1,last=last,n=len(after),toks=toks,nt=nt,ret=returns,toks2=toks2,n2=len(after2)))
print('window from',since,'logged tokens',tot)
print('gates with a return after a cut:',len(out))
print(' rounds from the first return:',sum(o['n'] for o in out),' tokens',sum(o['toks'] for o in out),' share %.1f%%'%(100*sum(o['toks'] for o in out)/tot),' seat runs no tokens',sum(o['nt'] for o in out))
print(' ended within one more round (last-r1<=1):',sum(1 for o in out if o['last']-o['r1']<=1))
print(' ended at r1 itself:',sum(1 for o in out if o['last']==o['r1']))
two=[o for o in out if len(o['ret'])>=2]
print('gates with a second return:',len(two),' rounds from it',sum(o['n2'] for o in two),' tokens',sum(o['toks2'] for o in two))
print('by gate type', collections.Counter(o['gate'] for o in out))
print('by depth', collections.Counter(o['depth'] for o in out))
print('last round dist', sorted(collections.Counter(o['last'] for o in out).items()))
print('r1 dist', sorted(collections.Counter(o['r1'] for o in out).items()))
print('past 8', sum(1 for o in out if o['last']>8))
import json; json.dump(out,open(sys.argv[2],'w'))
```

Then, for the ceilings and this repo's listing (reads the gates `scan2.py` wrote):

```python
import json,re,collections
import os; F=os.path.expanduser('~/.local/state/independent-review/runs.tsv')
out=json.load(open('%s/out.json'%__import__('sys').argv[1]))
rows=collections.defaultdict(list)
for line in open(F):
    p=line.rstrip('\n').split('\t')
    if p[0]=='date': continue
    p+=['-']*(17-len(p)); rows[p[13]].append(p)
def rt(g,pred):
    return sum(int(q[11]) for q in rows[g] if q[6].isdigit() and pred(int(q[6])) and q[11].isdigit())
s1=sum(rt(o['g'],lambda r,o=o:r>o['r1']) for o in out)
two=[o for o in out if len(o['ret'])>=2]
s2=sum(rt(o['g'],lambda r,o=o:r>o['ret'][1]) for o in two)
n1=sum(len({int(q[6]) for q in rows[o['g']] if q[6].isdigit() and int(q[6])>o['r1']}) for o in out)
n2=sum(len({int(q[6]) for q in rows[o['g']] if q[6].isdigit() and int(q[6])>o['ret'][1]}) for o in two)
print('opt1 ceiling: rounds after r1',n1,'tokens',s1)
print('opt2 ceiling: rounds after r2',n2,'tokens',s2)
# per gate: did the rounds after r1 keep the same kind?
same=0
for o in out:
    g=o['g']
    ks=lambda r:set(re.sub(r'[._-]','',k.lower()) for q in rows[g] if q[6]==str(r) for k in q[14].split(',') if k not in('','-'))
    if o['last']>o['r1'] and any(ks(r)&ks(o['r1']) for r in range(o['r1']+1,o['last']+1)): same+=1
print('gates where the returning kind came back again after r1:',same)
for o in sorted(out,key=lambda o:o['g']):
    repo=rows[o['g']][0][1]
    print(o['g'],repo,o['branch'],o['gate'],o['depth'],'r1',o['r1'],'ret',o['ret'],'last',o['last'],'tok_from_r1',o['toks'],'tok_gate',rt(o['g'],lambda r:True))
```

And the baseline for the two-week check (every gate that reached round 4):

```python
import os,collections
F=os.path.expanduser('~/.local/state/independent-review/runs.tsv')
g=collections.defaultdict(lambda:collections.defaultdict(int)); mx=collections.defaultdict(int)
for line in open(F):
    p=line.rstrip('\n').split('\t')
    if p[0]=='date' or p[0][:10]<'2026-11-03' or p[13] in('','-') or not p[6].isdigit(): continue
    r=int(p[6]); mx[p[13]]=max(mx[p[13]],r)
    if p[11].isdigit(): g[p[13]][r]+=int(p[11])
el=[k for k in mx if mx[k]>=4]
print('gates reaching round 4:',len(el),' rounds past 3:',sum(mx[k]-3 for k in el),' tokens past round 3:',sum(v for k in el for r,v in g[k].items() if r>3))
```

## 3. Its output (2026-11-03 to 2026-11-17)

```text
window from 2026-11-03 logged tokens 286135779
gates with a return after a cut: 82
 rounds from the first return: 204  tokens 18065017  share 6.3%  seat runs no tokens 45
 ended within one more round (last-r1<=1): 51
 ended at r1 itself: 31
gates with a second return: 45  rounds from it 106  tokens 9234510
by gate type Counter({'plan': 45, 'diff': 37})
by depth Counter({'normal': 42, 'high': 39, '-': 1})
last round dist [(5, 20), (6, 17), (7, 14), (8, 16), (9, 8), (10, 2), (11, 2), (12, 3)]
r1 dist [(4, 2), (5, 51), (6, 17), (7, 8), (8, 3), (11, 1)]
past 8 15
opt1 ceiling: rounds after r1 122 tokens 10743852
opt2 ceiling: rounds after r2 61 tokens 5379363
gates where the returning kind came back again after r1: 42
gates reaching round 4: 236  rounds past 3: 584  tokens past round 3: 46161657
```

The figures in the brief that started this plan were 83 gates, 209 rounds, 20.5M tokens (8%), 49
seat runs with no tokens, and 31 gates that ended within one more round. They came from another
session's count and differ slightly from these. The plan uses the figures above. The log grows
while sessions run, so a rerun gives a slightly larger total.

## 4. This repo's gates with a return

Branch, gate type, depth, first return, returns, last round, tokens from the first return on, tokens of the whole gate.

```text
main plan high r1 5 ret [5, 6, 7] last 7 tok_from_r1 281388 tok_gate 1083548
fix/refusal-check-first-person diff normal r1 7 ret [7] last 7 tok_from_r1 68522 tok_gate 548432
plan/glm-marker-and-failed-reason plan normal r1 6 ret [6, 7] last 7 tok_from_r1 255515 tok_gate 856452
fix/035-d-whats-new-imports plan normal r1 6 ret [6] last 6 tok_from_r1 54118 tok_gate 477112
fix/move-refusal-words-035 diff normal r1 5 ret [5] last 5 tok_from_r1 48341 tok_gate 440358
plan/live-analytics-check plan high r1 5 ret [5] last 7 tok_from_r1 247086 tok_gate 553882
plan/live-analytics-check diff normal r1 6 ret [6, 7, 8, 9, 10, 11] last 11 tok_from_r1 379210 tok_gate 609285
fix/move-analytics-gap-035 diff normal r1 6 ret [6, 7, 8, 9, 10, 11, 12] last 12 tok_from_r1 382952 tok_gate 704651
fix/ship-commented-site-035 diff normal r1 5 ret [5, 6] last 6 tok_from_r1 127631 tok_gate 453711
fix/agy-release-test-misreads diff normal r1 5 ret [5, 6, 7] last 7 tok_from_r1 260289 tok_gate 674651
fix/move-prep-036 diff high r1 6 ret [6, 7] last 9 tok_from_r1 188359 tok_gate 468929
```

## 5. The lastmod gate, round by round (gate `20261116T230248Z-74626`, branch `fix/move-prep-036`)

Codex lines only; the melious seat failed every round ("out of balance") and logged no tokens.

```text
round 1 head 1234683 80375 tokens earned_by=- cut=-
round 2 head 8aeea76 65005 tokens earned_by=- cut=-
round 3 head f773cbb 38959 tokens earned_by=- cut=-
round 4 head 15342f8 44090 tokens earned_by=lastmod-scan-regex-literal cut=-
round 5 head 050042c 52141 tokens earned_by=lastmod-scan-regex-literal cut=dropped the line-start regex-literal case from the lookbehind
round 6 head c399d0d 37369 tokens earned_by=lastmod-scan-regex-literal cut=return counts as a keyword only when not a property name
round 7 head d481229 49061 tokens earned_by=lastmod-scan-regex-literal cut=removed the return alternative; a regex literal after return is a miss
round 8 head 0fcce41 59628 tokens earned_by=lastmod-warning-not-gap cut=-
round 9 head e6d6545 42301 tokens earned_by=advisory-scan-read-failure cut=-
```

Rounds 6 and 7: 37,369 + 49,061 = 86,430 tokens. The trail
(`REVIEW-diff-2026-11-17-move-prep-036.md`, F20 and F21) says the scan became a warning by the
manager session's decision after round 7, in `0fcce419`, which round 8 reviewed.

Lines changed outside `docs/` (`git diff --numstat`), for each fix the next round reviewed:

```text
15342f8..050042c +4 -2   (round 5 reviewed it; --cut given)
050042c..c399d0d +4 -2   (round 6; --cut given)
c399d0d..d481229 +2 -3   (round 7; --cut given)
d481229..0fcce41 +33 -25 (round 8; the warning, the real cut)
```

## 6. The probe: can a seat tell a cut from a patch?

Seven real fixes. The labels were written to a file before either run:

```text
A PATCH  lastmod round 6 (050042c..c399d0d)
B CUT    lastmod round 8 (d481229..0fcce41)
C PATCH  agy round 5 (78e14af..d476e99)
D PATCH  lastmod round 5 (15342f8..050042c)
E PATCH  agy round 6 (d476e99..13cad51)
F PATCH  lastmod round 7 (c399d0d..d481229)
G CUT    ship.sh comment scanner (5328e7d3^..5328e7d3)
```

Each case held the finding the fix answers, a `--cut` text and the diff (`git diff A..B`, without
`docs/BUGLOG.md` and `docs/reviews`). Cases A to F went in one blind brief; G went in a second
one, because only one cut was in the first. Case B's lastmod round 8 had no `--cut` (it started a
new kind), so its claim text was written for the probe from the trail's F21. The findings for C
and E were taken from their `--cut` texts. The prompt's head, as sent:

```text
You judge fixes made during a code review. For each case below you get: the finding the fix answers, the author's claim (its --cut text) and the diff. The review's rule, quoted:

"Cut, don't patch: where a kind earned an earlier round of the gate too, the fix since then must be a cut, not another patch: take the feature out, or replace it by a strict rule that accepts only the input it names and refuses the rest, with a test that ordinary input still passes. Refusing the one input the last BUG used is a patch."

For each case answer one line: `Case X: CUT` or `Case X: PATCH`, then one sentence why, naming the lines that decide it. Judge the diff, not the claim. Read only what is given; do not run anything.

```

Command: `codex exec -s read-only --skip-git-repo-check -c model_reasoning_effort=medium - < brief.md`.
Codex's verdict lines, as printed:

```text
Case A: PATCH — The replacement adds `(?<![.\w$])return\s+` and two regression examples, but keeps the heuristic scan and its blocking `gaps.push(...)`.
Case B: CUT — The diff removes the scan from `stageOneGaps`, emits it through `say('Warning: ...')`, and tests `r.code === 0`, eliminating its power to block the move.
Case C: PATCH — `receivers.append(cmd)` and `zip(bodies, receivers)` replace global ownership with positional matching, but never validate that association or refuse unsupported forms.
Case D: PATCH — The lookbehind trades `^\s*` for `\breturn\s+` while retaining `gaps.push(...)`, adding another heuristic exception instead of a strict input rule.
Case E: PATCH — `HEREDOC` still accepts tab-prefixed terminators indiscriminately and unclosed bodies through `|\Z`, while `has_option` continues interpreting clusters rather than refusing unsupported input.
Case F: PATCH — Removing the `return` alternative leaves the heuristic scanner feeding `gaps.push(...)`, and deleting the returning-function test merely drops coverage for a known miss.
Case G: CUT — Deleting `site_addrs()` removes the comment scanner; `site_count()` counts every regex match, P6/P7 assert that multiple matches trigger no fetch, and P5 retains an ordinary successful verification test.
```

Tokens: 23,715 (A to F) and 14,882 (G), 38,597 in all. All seven verdicts match the labels. Limits:
seven cases from two gates, one model, one run each. A judge that always says PATCH would score 5
of 7, so the probe says little about wrongly calling a real cut a patch. That is what test T1 is
for.
