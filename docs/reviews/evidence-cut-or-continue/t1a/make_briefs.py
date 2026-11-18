# Build one T1a brief per case from cases.tsv, block.txt and git alone; writes <out>/<id>.md.
import subprocess, sys, os
here = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1]
block = open(os.path.join(here, 'block.txt')).read()
HEAD = ("You are a reviewer in one round of a review. Answer only the CUT-CHECK below. Read only "
        "what is given; do not run anything.\n\n")
def git(*a): return subprocess.run(['git', *a], capture_output=True, text=True, check=True).stdout
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(here, 'cases.tsv'))][1:]
for cid, typ, br, rnd, a, b, pf, kinds, cut in rows:
    s = HEAD + block.replace('{kinds}', kinds).replace('{cut}', cut) + '\n'
    if typ == 'plan':
        s += ('--- BEGIN PLAN (as sent this round) ---\n' + git('show', f'{b}:{pf}') +
              '--- END PLAN ---\n\n--- BEGIN PLAN DIFF SINCE THE PREVIOUS ROUND ---\n' +
              git('diff', a, b, '--', pf) + '--- END PLAN DIFF ---\n')
    else:
        s += ('--- BEGIN DIFF ---\n' + git('diff', a, b, '--', '.', ':(exclude)docs/BUGLOG.md',
              ':(exclude)docs/buglog', ':(exclude)docs/reviews') + '--- END DIFF ---\n')
    open(os.path.join(out, cid + '.md'), 'w').write(s)
print(len(rows), 'briefs')
