# Per kind, from runs-81-gates-redacted.tsv alone (option e). A kind's first cut round is the first round whose
# lines carry cut=1 and name it. A round "asks" when it names a kind that an earlier round, after that first cut
# round, named too: its second return after the cut. A round "reminds" when it names a kind cut in an earlier round.
import sys,collections
norm=lambda k:k.lower().replace('.','').replace('_','').replace('-','')
rounds=collections.defaultdict(lambda:collections.defaultdict(list))
for i,line in enumerate(open(sys.argv[1])):
    p=line.rstrip('\n').split('\t')
    if i==0 or not p[3].isdigit(): continue
    rounds[p[7]][int(p[3])].append(p)
tok=lambda q:int(q[5]) if q[5].isdigit() else 0
gates=asks=n=t=multi=obl=rem=remg=0
for g,R in rounds.items():
    fc={}; named=collections.defaultdict(set); first=None; gr=False
    for r in sorted(R):
        ks=set(norm(k) for q in R[r] for k in q[8].split(',') if k!='-')
        due=[k for k in ks if k in fc and any(fc[k]<x<r for x in named[k])]
        if due:
            asks+=1; obl+=len(due); first=first or r
            if len(due)>=2: multi+=1
        if any(k in fc and fc[k]<r for k in ks): rem+=1; gr=True
        for k in ks: named[k].add(r)
        for q in R[r]:
            if q[9]=='1':
                for k in q[8].split(','):
                    if k!='-': fc.setdefault(norm(k),r)
    remg+=gr
    if first is None: continue
    gates+=1; n+=len([r for r in R if r>first]); t+=sum(tok(q) for r in R if r>first for q in R[r])
print('gates that would ask:',gates,' rounds that would ask:',asks,' rounds after the first ask:',n,' tokens:',t)
print('kinds asked about:',obl,' rounds asking about two or more:',multi,' rounds that remind:',rem,' in gates:',remg)
