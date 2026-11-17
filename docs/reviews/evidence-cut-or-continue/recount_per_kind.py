# Per kind, from runs-81-gates-redacted.tsv alone: a round "asks" when its earned_by names a kind that two earlier rounds settled with a cut (option e).
import sys,collections
norm=lambda k:k.lower().replace('.','').replace('_','').replace('-','')
rounds=collections.defaultdict(lambda:collections.defaultdict(list))
for i,line in enumerate(open(sys.argv[1])):
    p=line.rstrip('\n').split('\t')
    if i==0 or not p[3].isdigit(): continue
    rounds[p[7]][int(p[3])].append(p)
tok=lambda q:int(q[5]) if q[5].isdigit() else 0
gates=asks=n=t=multi=rem=remg=0
for g,R in rounds.items():
    cutr=collections.defaultdict(set); first=None; gr=False
    for r in sorted(R):
        ks=set(norm(k) for q in R[r] for k in q[8].split(',') if k!='-')
        if any(len(cutr[k])>=2 for k in ks):
            asks+=1; first=first or r
        if sum(len(cutr[k])>=2 for k in ks)>=2: multi+=1
        for q in R[r]:
            if q[9]=='1':
                for k in q[8].split(','):
                    if k!='-': cutr[norm(k)].add(r)
        # Design 2's closing reminder: this round carries a cut for a kind that now has two cut rounds.
        cks=set(norm(k) for q in R[r] if q[9]=='1' for k in q[8].split(',') if k!='-')
        if any(len(cutr[k])>=2 for k in cks): rem+=1; gr=True
    remg+=gr
    if first is None: continue
    gates+=1; n+=len([r for r in R if r>first]); t+=sum(tok(q) for r in R if r>first for q in R[r])
print('gates that would ask:',gates,' rounds that would ask:',asks,' rounds after the first ask:',n,' tokens:',t)
print('rounds that would ask about two or more kinds:',multi,' closing reminders:',rem,' in gates:',remg)
