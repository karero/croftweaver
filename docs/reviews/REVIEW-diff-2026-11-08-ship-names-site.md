# DIFF gate trail: `npm run ship` names the site and asks for a yes

Plan: `docs/reviews/SKILL-PLAN-ship-names-site.md`. Depth High; seats Codex and GLM 5.3; a fresh-eyes
read in rounds 1 and 2. Gate 20261108T161754Z-60491: 3 rounds, 268,011 tokens logged (fresh-eyes
not counted).

| Round | Reviewed | Findings | Outcome |
|---|---|---|---|
| 1 | whole change at `10f24d84` | 3 BUG, 4 RISK, 7 NIT, 4 UNVERIFIABLE | BUG 1 (the site came from this folder in worktree mode): fixed by the planner's call, Fix A. BUG 2 (host read as owner) and BUG 3 (BUGLOG wording): fixed. RISK 60 s limit refuted by timings; RISK many-sites became a BUGLOG row; the rest fixed or kept as the plan has them. |
| 2 | delta to `38ff65f1` | 1 BUG, 4 NIT | BUG (BUGLOG impact understated): fixed. NITs fixed or refuted (`tokenurl1` covers the accepting direction). |
| 3 | delta to `1226f96f` | 1 BUG (stale comment), 3 NIT | Fixed in `7123b94d` (comments only); not re-reviewed. NITs: coupling of the trap check to source text accepted (commented); no test for the test helper's own guard. |

Mutation check: 28 mutations in a scratch copy each; all killed. `widen-class` and
`sed-without-n-p` survived once, when the host-as-owner guard hid the sed from the old cases; the
cases `oddchars` and `scpnoowner` killed them.
