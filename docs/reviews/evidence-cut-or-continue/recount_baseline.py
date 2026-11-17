# Recount the two-week baseline (gates that reached round 4) from baseline-gates-redacted.tsv alone.
import sys
rows=[l.rstrip('\n').split('\t') for l in open(sys.argv[1])][1:]
print('gates reaching round 4:',len(rows),' rounds past 3:',sum(len(r[1].split(',')) for r in rows),
      ' tokens past round 3:',sum(int(r[2]) for r in rows))
