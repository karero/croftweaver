# Recount the plan's figures for the 82 gates from runs-82-gates-redacted.tsv (no other input).
import sys,collections
rounds=collections.defaultdict(lambda:collections.defaultdict(list))
for i,line in enumerate(open(sys.argv[1])):
    p=line.rstrip('\n').split('\t')
    if i==0 or not p[3].isdigit(): continue
    rounds[p[7]][int(p[3])].append(p)
tok=lambda q:int(q[5]) if q[5].isdigit() else 0
g_n=r_n=t=nt=end=two=n1=t1=n2=t2=0
for g,R in rounds.items():
    K=lambda r:set(k for q in R[r] for k in q[8].split(',') if k!='-')
    cut=set(); ret=[]
    for r in sorted(R):
        if K(r)&cut: ret.append(r)
        cut|=set(k for q in R[r] if q[9]=='1' for k in q[8].split(',') if k!='-')
    if not ret: continue
    g_n+=1; last=max(R)
    after=[r for r in R if r>=ret[0]]
    r_n+=len(after); t+=sum(tok(q) for r in after for q in R[r]); nt+=sum(1 for r in after for q in R[r] if not q[5].isdigit())
    end+=last==ret[0]
    n1+=len([r for r in R if r>ret[0]]); t1+=sum(tok(q) for r in R if r>ret[0] for q in R[r])
    if len(ret)>1:
        two+=1; n2+=len([r for r in R if r>ret[1]]); t2+=sum(tok(q) for r in R if r>ret[1] for q in R[r])
print('gates',g_n,'rounds from first return',r_n,'tokens',t,'seat runs no tokens',nt,'ended at the return round',end)
print('second return',two,'| after first return: rounds',n1,'tokens',t1,'| after second: rounds',n2,'tokens',t2)
