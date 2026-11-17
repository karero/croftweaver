# Evidence: cut-or-continue plan

For `SKILL-PLAN-review-cut-or-continue.md`. Everything below was run on 2026-11-17 against the
cost log `~/.local/state/independent-review/runs.tsv` and this repo at `origin/main` `5a0b3010`.
The log has 17 columns; columns 15 to 17 are `earned_by`, `cut` and `reason`. It covers every repo
the maintainer reviews. For other repos only counts are given, and only this repo's gates are
named.

## 1. Definitions, as the scripts compute them

- **The window:** whole gates whose id (its start time) is on or after 2026-11-03, with every
  line they logged. Round 3's review found that the first count cut off a gate's lines from before
  that day. Counting whole gates fixed it: 82 gates became 81.
- A **round** is one `--round N` of one gate id, all its seats together.
- A **cut** settles only the kinds on the log line that carries it, as `review_log.sh` counts it.
  Another seat's line in the same round may name a kind the cut was not about. Round 1's review
  found that the first count settled every kind of the round. Recounted per line, the figures did
  not change.
- A **return** is a later round whose `earned_by` names a kind that a cut settled earlier. Kinds
  are compared as the script compares them: lower-cased, without `.`, `_` or `-`. The `earned_by`
  of round N names what round N−1 found. So a return at round N means the round that reviewed the
  cut, or a later one, found that kind again.
- **Rounds from the first return** count the return round and every round after it.
- **The most an option can save** is the rounds after the return round. The return round itself
  still runs, because it reviews whatever the next fix is.

## 2. The scripts (as run)

`scan2.py` finds the gates and their returns, and writes them to a JSON file:

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
# whole gates that started on or after the day (the gate id starts with its start time)
win=[p for p in rows if p[13] not in ('','-') and p[13][:8]>=since.replace('-','')]
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

`scan3.py` gives the ceilings and this repo's listing; it reads the JSON `scan2.py` wrote:

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

`base.py` gives the baseline for the two-week check: every gate that reached round 4. It counts
distinct logged round numbers above 3, so a skipped number is not counted as a round (round 2's
review found the first version counted `max round − 3`):

```python
import os,collections
F=os.path.expanduser('~/.local/state/independent-review/runs.tsv')
rs=collections.defaultdict(set); tk=collections.defaultdict(int)
for line in open(F):
    p=line.rstrip('\n').split('\t')
    if p[0]=='date' or p[13] in('','-') or p[13][:8]<'20261103' or not p[6].isdigit(): continue
    r=int(p[6]); rs[p[13]].add(r)
    if r>3 and p[11].isdigit(): tk[p[13]]+=int(p[11])
el=[k for k in rs if max(rs[k])>=4]
# distinct logged round numbers above 3, so a skipped number is not counted as a round
print('gates reaching round 4:',len(el),' rounds past 3:',sum(len([r for r in rs[k] if r>3]) for k in el),' tokens past round 3:',sum(tk[k] for k in el))
```

## 3. Their output

```text
window from 2026-11-03 logged tokens 257853137
gates with a return after a cut: 81
 rounds from the first return: 203  tokens 17991532  share 7.0%  seat runs no tokens 45
 ended within one more round (last-r1<=1): 50
 ended at r1 itself: 30
gates with a second return: 45  rounds from it 106  tokens 9234510
by gate type Counter({'plan': 44, 'diff': 37})
by depth Counter({'normal': 41, 'high': 39, '-': 1})
last round dist [(5, 20), (6, 17), (7, 14), (8, 15), (9, 8), (10, 2), (11, 2), (12, 3)]
r1 dist [(4, 2), (5, 51), (6, 17), (7, 8), (8, 2), (11, 1)]
past 8 15
opt1 ceiling: rounds after r1 122 tokens 10743852
opt2 ceiling: rounds after r2 61 tokens 5379363
gates where the returning kind came back again after r1: 42
gates reaching round 4: 234  rounds past 3: 574  tokens past round 3: 45976379
```

"Logged tokens" is the sum over every line of the window's gates. Lines with no gate id are left
out.

The brief that started this plan gave 83 gates, 209 rounds, 20.5M tokens (8%), 49 seat runs with
no tokens, and 31 gates that ended within one more round. Those came from another session's count.
The plan uses the figures above. The log grows while sessions run, so a later run may count more.

## 4. This repo's gates with a return

Branch, gate type, depth, first return, returns, last round, tokens from the first return on,
tokens of the whole gate.

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

## 4b. All 81 gates, one line each

Gate ids only, since each is just a start time. That way the sums can be checked without the
log. Columns 6 to 8 sum to 17,991,532, 10,743,852 and 5,379,363.

```text
gate_id	type	first_return	returns	last_round	tokens_from_first_return	tokens_after_first_return	tokens_after_second_return
20261104T074523Z-53735	plan	5	5,7	7	308521	199125	0
20261104T225606Z-2982	plan	5	5,6,7	7	281388	184097	90108
20261105T100835Z-70190	plan	5	5,6,7,8	8	1102516	659847	409775
20261105T153850Z-65131	plan	5	5,6	8	414333	313556	214140
20261105T160524Z-84167	diff	7	7	7	68522	0	-
20261105T221825Z-32137	plan	5	5,6,7,8	8	286080	230124	170897
20261106T085517Z-97743	diff	5	5,6	6	150344	81272	0
20261106T135543Z-62822	diff	6	6,7,8,9	9	313321	223028	171839
20261106T144654Z-70667	plan	5	5	5	118197	0	-
20261106T150219Z-11787	plan	5	5,6	6	238425	173088	0
20261106T220039Z-90198	plan	5	5	6	192074	111956	-
20261106T220059Z-97865	plan	5	5,6,7,8	8	475428	364108	255509
20261106T230622Z-11856	plan	5	5	5	41143	0	-
20261107T142409Z-15102	diff	6	6,7	7	114142	63227	0
20261107T154202Z-65414	diff	6	6	8	414805	266280	-
20261107T173246Z-9392	plan	6	6,7	7	255515	108730	0
20261107T173349Z-13243	plan	5	5,6	6	187015	89207	0
20261107T213936Z-36981	diff	5	5	5	63933	0	-
20261108T105552Z-77609	plan	7	7,8,9	9	472433	311429	148867
20261108T131517Z-32159	diff	5	5	5	37039	0	-
20261108T132019Z-99059	plan	6	6	6	54118	0	-
20261108T201342Z-15892	diff	5	5	5	48341	0	-
20261109T054352Z-87840	plan	5	5,6,7,8,9	12	980517	858052	719908
20261109T054417Z-94020	diff	5	5,6	6	72053	30697	0
20261109T091101Z-2336	plan	5	5,6,7	7	283842	206645	122176
20261109T134544Z-58988	plan	6	6,7,8,9	9	324863	241932	196667
20261109T152009Z-23233	plan	4	4,5	5	106055	28763	0
20261109T153934Z-23371	plan	6	6	6	104288	0	-
20261109T182523Z-40490	plan	5	5	7	247086	132508	-
20261109T210813Z-33270	diff	6	6,7,8,9,10,11	11	379210	248294	202813
20261110T082307Z-11743	plan	5	5,6,7,8,9	9	364830	287991	217683
20261110T083326Z-18084	diff	6	6,7,8,9,10,11,12	12	382952	333243	269860
20261110T090120Z-44034	diff	5	5	5	42332	0	-
20261110T110318Z-12502	plan	5	5,6,7	7	381917	258273	122766
20261110T144651Z-92642	plan	5	5,8	8	303441	229517	0
20261111T080558Z-62896	diff	5	5,8	8	164582	130394	0
20261111T085656Z-80060	plan	5	5,6	6	251798	41728	0
20261111T220604Z-24374	plan	6	6,7,8,9	10	341040	283948	226266
20261111T220753Z-33476	plan	11	11	11	65733	0	-
20261111T222244Z-80750	diff	6	6,7	7	81027	38641	0
20261111T222245Z-81212	diff	5	5	5	30349	0	-
20261112T081641Z-97213	diff	5	5,6	6	127631	56844	0
20261112T093514Z-9164	diff	5	5	5	40025	0	-
20261112T144029Z-11588	plan	5	5,6	6	260830	106217	0
20261112T144708Z-65488	diff	4	4,5	5	105206	45322	0
20261113T061509Z-64268	plan	5	5	6	335634	229499	-
20261113T082208Z-39549	diff	6	6	6	70847	0	-
20261113T104434Z-57834	diff	5	5	5	97567	0	-
20261113T113328Z-72680	plan	7	7,8	8	235276	129153	0
20261113T122303Z-63542	diff	5	5,6,7	7	252655	172540	92926
20261113T125706Z-81784	diff	7	7	8	185954	89302	-
20261113T132653Z-29511	diff	5	5,6,8,9,10	10	553465	467243	374422
20261113T210709Z-95421	diff	5	5	5	48690	0	-
20261113T212811Z-48548	plan	5	5	5	148622	0	-
20261113T223547Z-6551	diff	5	5	5	68350	0	-
20261113T225848Z-37489	diff	5	5	5	59336	0	-
20261114T011932Z-98288	diff	5	5,6,7	8	359590	258559	159926
20261114T013310Z-59643	diff	5	5,6	6	146026	81548	0
20261114T094902Z-75444	diff	7	7	7	45006	0	-
20261114T131115Z-60591	plan	6	6	6	104801	0	-
20261114T140233Z-76445	diff	5	5	6	179247	85523	-
20261114T161942Z-1183	diff	5	5	5	59098	0	-
20261114T162636Z-49941	diff	5	5,6	6	120506	62161	0
20261114T170548Z-12407	plan	6	6,7,8	9	356925	277487	191436
20261114T181821Z-24161	diff	5	5,6,7	7	260289	165579	80698
20261115T132450Z-57162	plan	5	5,7,8	9	414894	330907	178265
20261115T135502Z-67017	plan	6	6	6	122160	0	-
20261115T140512Z-1606	plan	7	7	7	79310	0	-
20261115T164412Z-53581	plan	5	5,6,7,8,9,10,11,12	12	322212	290380	243540
20261115T165801Z-85512	plan	8	8	8	105215	0	-
20261115T184623Z-77781	plan	5	5	5	116283	0	-
20261115T185800Z-9481	plan	6	6,8	8	428038	217908	0
20261115T212939Z-28890	diff	5	5	5	70671	0	-
20261116T061548Z-33385	plan	5	5,7,8	8	393758	276682	82101
20261116T083203Z-43618	plan	5	5	5	114258	0	-
20261116T115619Z-30539	plan	7	7,8	8	171521	91361	0
20261116T134834Z-50369	diff	5	5	5	87733	0	-
20261116T135222Z-97520	plan	5	5,6,7,9	9	520427	428947	334846
20261116T230248Z-74626	diff	6	6,7	9	188359	150990	101929
20261117T062500Z-24029	diff	8	8	8	46218	0	-
20261117T092624Z-56443	plan	7	7	7	43351	0	-
```

## 4c. A redacted copy of those gates' log lines, and a recount from it alone

`evidence-cut-or-continue/runs-81-gates-redacted.tsv` holds every log line of the 81 gates. It
keeps date, gate type, depth, round, seat, tokens, outcome and gate id. Each kind is replaced by
the first 8 hex digits of the SHA-1 of its normalised name, and the cut by `1` or `0`. Repo,
branch, head, model, cut text and reason are dropped. `evidence-cut-or-continue/recount.py` reads
only that file:

```text
$ python3 -I docs/reviews/evidence-cut-or-continue/recount.py docs/reviews/evidence-cut-or-continue/runs-81-gates-redacted.tsv
gates 81 rounds from first return 203 tokens 17991532 seat runs no tokens 45 ended at the return round 30
second return 45 | after first return: rounds 122 tokens 10743852 | after second: rounds 61 tokens 5379363
```

The baseline (234 gates, 574 rounds, 46.0M tokens) covers gates outside these 81, so it has its
own redacted file: `baseline-gates-redacted.tsv`, one line per gate that reached round 4, with the
gate's start day, its distinct round numbers above 3 and their tokens. It holds every such gate
started from 2026-11-03 except this plan's own gate, as the log stood on 2026-11-17 at round 5 of
this gate. `recount_baseline.py` recounts it from that file alone:

```text
$ python3 -I docs/reviews/evidence-cut-or-continue/recount_baseline.py docs/reviews/evidence-cut-or-continue/baseline-gates-redacted.tsv
gates reaching round 4: 234  rounds past 3: 574  tokens past round 3: 45976379
```

## 5. The lastmod gate, round by round (gate `20261116T230248Z-74626`, branch `fix/move-prep-036`)

Codex lines only. The melious seat failed every round ("out of balance") and logged no tokens.

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
(`REVIEW-diff-2026-11-17-move-prep-036.md`, F20 and F21) says the manager session decided after
round 7 to make the scan a warning. That change is `0fcce419`, and round 8 reviewed it.

Lines changed outside `docs/` (`git diff --numstat`), for each fix the next round reviewed:

```text
15342f8..050042c +4 -2   (round 5 reviewed it; --cut given)
050042c..c399d0d +4 -2   (round 6; --cut given)
c399d0d..d481229 +2 -3   (round 7; --cut given)
d481229..0fcce41 +33 -25 (round 8; the warning, the real cut)
```

## 6. The probe: can a seat tell a cut from a patch?

The probe used seven real fixes. The files are in `evidence-cut-or-continue/`: `probe-labels.txt`
(the hand labels), `probe-brief.md` (cases A to F, as sent), `probe-brief-g.md` (case G),
`probe-out.md` and `probe-out-g.md` (Codex's whole output). Two lines were changed in the outputs
before committing: the scratch folder's path (`workdir:`) and the `session id:`.

Each case gave the finding the fix answers, a `--cut` text and the diff (`git diff A..B`, leaving
out `docs/BUGLOG.md` and `docs/reviews`). Cases A to F went in one blind brief. G went in a second
one, because the first had only one cut. Case B is the lastmod round 8. That round had no `--cut`,
since it started a new kind, so its claim was written for the probe from the trail's F21. The
findings for C and E were taken from their `--cut` texts.

Command: `codex exec -s read-only --skip-git-repo-check -c model_reasoning_effort=medium - < brief.md`
(Codex CLI 0.169.0, model gpt-6.1-sol). The verdict lines, as printed:

```text
Case A: PATCH — The replacement adds `(?<![.\w$])return\s+` and two regression examples, but keeps the heuristic scan and its blocking `gaps.push(...)`.
Case B: CUT — The diff removes the scan from `stageOneGaps`, emits it through `say('Warning: ...')`, and tests `r.code === 0`, eliminating its power to block the move.
Case C: PATCH — `receivers.append(cmd)` and `zip(bodies, receivers)` replace global ownership with positional matching, but never validate that association or refuse unsupported forms.
Case D: PATCH — The lookbehind trades `^\s*` for `\breturn\s+` while retaining `gaps.push(...)`, adding another heuristic exception instead of a strict input rule.
Case E: PATCH — `HEREDOC` still accepts tab-prefixed terminators indiscriminately and unclosed bodies through `|\Z`, while `has_option` continues interpreting clusters rather than refusing unsupported input.
Case F: PATCH — Removing the `return` alternative leaves the heuristic scanner feeding `gaps.push(...)`, and deleting the returning-function test merely drops coverage for a known miss.
Case G: CUT — Deleting `site_addrs()` removes the comment scanner; `site_count()` counts every regex match, P6/P7 assert that multiple matches trigger no fetch, and P5 retains an ordinary successful verification test.
```

File times (`ls -lT` in the probe folder, 2026-11-17, local time):

- 11:24:52: `brief.md`, written by the same command that wrote the labels for A to F.
- 11:25:31: Codex's answer, `out.md`.
- 11:25:54: label G appended, and `brief-g.md` written.
- 11:26:10: `out-g.md`.

The times show the order of the files. They cannot prove when the labels were decided.

Tokens: 23,715 (A to F) and 14,882 (G), 38,597 in all. All seven verdicts match the labels.

Limits: seven cases from two gates, one model, one run each. A judge that always says PATCH would
score 5 of 7. So the probe says little about how often a real cut gets called a patch. Tests T1a
and T1b are for that.

## 7. T1a, the backtest (2026-11-17): FAIL

The owner's go covered T1a only. The 22 cases are in `t1a/cases.tsv`, and their labels in
`t1a/labels.txt`. Both were committed (e67b8c6d, 14:24 +01:00) before any call ran. There are 9
plan rounds (5 cuts, 4 patches) and 13 diff rounds (6 cuts, 7 patches), all from this repo's own
gates. They include S1's round-5 fix (D7) and S4's round-5 fix (D9). D6 is the lastmod warning
round, which had no `--cut`; its text is the probe's case B.

`t1a/make_briefs.py` builds each brief from git alone: `t1a/block.txt` filled in, then the diff
(less `docs/BUGLOG.md`, `docs/buglog` and `docs/reviews`), or for a plan the plan at the round's
head and its diff since the previous round. Each brief was one call:
`codex exec -s read-only --skip-git-repo-check -c model_reasoning_effort=medium - < <id>.md`
(Codex CLI 0.169.0, model gpt-6.1-sol), run from an empty folder. Outputs are in `t1a/out/`, with
the `workdir:` and `session id:` lines replaced and the echoed prompt cut out (it held old plan
text naming people; `make_briefs.py` rebuilds it). Every case gave a valid verdict. Tokens: 350,196.

```text
$ python3 -I docs/reviews/evidence-cut-or-continue/t1a/score.py   (last three lines)
real cuts not called CUT: 3 of 11 ['P2', 'P5', 'D5'] (bar: at most 1)
patches called PATCH: 8 of 11 = 73% (bar: at least 80%)
T1a FAIL
```

Patches called CUT: P7 and P8, two rounds of the plan regex chain (the host had called each a
strict rule), and D12, the join rewrite in the refusal check.

The labels are one person's judgment, and some of Codex's reasons have weight: D5's reader still
takes a `url:` line inside a block comment, and P5's `--cut` text covers only one of its two
kinds. Even with all three disputed cuts relabelled PATCH, the patch bar still fails: 11 of 14,
79%. Passing would need patches relabelled as cuts, including rounds whose kind came back right
after.

## 8. Option (e), counted per kind (2026-11-17)

`evidence-cut-or-continue/recount_per_kind.py` reads the redacted file of §4c alone. Per gate, it
keeps for each normalised kind the set of distinct rounds whose lines carry `cut=1` and name that
kind. A round asks when a kind in its `earned_by` already has two such rounds. Seats share a round,
so two seat lines count as one cut round.

```text
$ python3 -I docs/reviews/evidence-cut-or-continue/recount_per_kind.py docs/reviews/evidence-cut-or-continue/runs-81-gates-redacted.tsv
gates that would ask: 39  rounds that would ask: 78  rounds after the first ask: 57  tokens: 4989208
rounds that would ask about two or more kinds: 17  closing reminders: 172  in gates: 81
```

A closing reminder is counted after a round whose cut lines name a kind that, this round
included, has two cut rounds. "Rounds after the first ask" leaves out the asking round itself,
which still reviews what the manager chose.

S2, gate `20261110T083326Z-18084` (branch `fix/move-analytics-gap-035`), Codex tokens per round
(the melious seat logged none from round 4): rounds 1 to 3 with both seats 72,862, 69,229,
64,884; then 63,798, 50,926, 49,709, 63,383, 76,956, 44,118, 46,534, 47,851, 54,401. One kind
carries `cut=1` from round 5 to round 12, so the first ask comes at the start of round 7, printed
at the end of round 6. Rounds 7 to 12: 333,243 tokens; rounds 8 to 12, after the round that
reviews the manager's choice: 269,860.
