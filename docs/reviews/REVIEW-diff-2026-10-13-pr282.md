# DIFF review — PR #282 — BUGLOG: one row on the ruleset recipe, after its first run on a real site
Base `f7c3ef4` · depth: started Light (a row in a log that nobody runs and no assistant loads as instructions), moved to Normal after the extra Light round still found a BUG · verdict: PENDING — Normal round 1 found no BUG, 2 RISKs and 7 NITs, all answered in `c274170`; Normal round 2 has not run yet · authority used: POST AUTHORITY — atom A (this session opened #282); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — atom A (the rounds below)

Why the depth changed: the owner's rule for the Light gate is one round, one more if it found a BUG, and Normal from its round 1 if that extra round still finds one. It did. Both BUGs were wrong pointers in the row's own text (which section holds a recipe, which plan step probes a rule), not faults in any code.

Data check: the diff holds no key, token or password. Destinations: Codex in every round; in the Normal round also GLM 5.3 on melious, the repo's standing second seat.

| Round | Head | Artifact | Reviewer: CLI version, model, effort, sandbox | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| Light 1 | `4e68c2b` | full: `origin/main...4e68c2b`, 1 file | codex-cli 0.162.1, gpt-6.1-sol, medium, read-only | 137 s / 62,331 | 1/1/0 |
| Light 2 (the extra round) | `7ab51d4` | delta `4e68c2b..7ab51d4`, with the author's record of round 1 | the same | 89 s / 35,934 | 1/1/0; M1 confirmed fixed, M2 fixed in two of its three parts |
| Normal 1 | `0ba6cd2` (content of `366b81c`) | full: `origin/main...0ba6cd2` without `docs/reviews/`, 1 file | codex (config effort); melious glm-5.3 (HTTP API, text only); fresh-eyes: a sub-agent of the host's model family, one size down, read-only, allowed to fetch the two GitHub pages the row cites | codex 140 s / 66,848; glm 223 s / 17,008; fresh-eyes 169 s / 124,574 | codex 0/0/0; glm 0/0/2; fresh-eyes 0/2/5 · 7 after dedup |
| Normal 2 | pending | delta `0ba6cd2..HEAD` without `docs/reviews/`, with the author's record of Normal round 1 | pending | pending | pending |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| M1 | BUG | codex | Light 1 | the row said "§5-A's two rule sets"; the `production` rule set is specified in §3's settings table | fixed `7ab51d4` — locally_verified, externally_reverified (Light 2) | the Where cell and the first sentence name §3 for `production` and §5-A for `main` |
| M2 | RISK | codex | Light 1 | three claims went past the evidence: that the four keys are defaults and stay, that the Copilot key is the documented option, that each merge costs every other pull request a CI run | fixed `7ab51d4` and `366b81c` — locally_verified, externally_reverified (Light 2 for two parts; Normal 1, where no seat raised it again) | the keys are "Seen, in that one answer"; the mapping is "A reading, not checked"; the cost is listed under "Not checked" |
| M3 | BUG | codex | Light 2 | the row called step A2 of the capability-gaps plan "the probe" for the `production` rule set; A2 is about a required check on `production`, a different rule | fixed `366b81c` — locally_verified, externally_reverified (Normal 1: no seat raised it again) | the pointer is gone; the row says only that no ship has run on that site since |
| M4 | RISK | codex | Light 2 | the cost of "up to date" still rested on the skill's own words, not on GitHub's behaviour or a probe, and it argued for switching the requirement off | fixed `366b81c` — locally_verified, externally_reverified (Normal 1: no seat raised it again) | the row gives the skill's sentence as the skill's, says the cost "was not probed here", lists the probe under "Not checked", and no longer argues for a choice |
| P1 | RISK | fresh-eyes | Normal 1 | "nothing points that owner to §5" was a universal negative with no check behind it; the skill's own description names a second assistant | fixed `c274170` — locally_verified | the row sets `new-website`'s sentence beside the skill's description and says what was counted: five mentions of the skill in `new-website`, none for that owner |
| P2 | RISK | fresh-eyes | Normal 1 | "Not checked: that the four keys are defaults (a second call that leaves them out…)" was muddled: the first call already left them out; the open question is what the read-back's PUT does | fixed `c274170` — locally_verified | "Shown once, on that repo: sent without them, the create answer carried four keys…"; the page's "enabled by default" is quoted; "Not checked" starts with the PUT |
| P3 | NIT | fresh-eyes | Normal 1 | "the first of these" and "the third key" could each be read two ways | fixed `c274170` — locally_verified | "run the PUT check"; the key is written out |
| P4 | NIT | fresh-eyes | Normal 1 | the Where cell listed the `production` row, but nothing in the fix touched it | fixed `c274170` — locally_verified | the fix ends with a sentence for §3b's `production` row |
| P5 | NIT | fresh-eyes, glm | Normal 1 | the settings table with the `production` row is §3b, not §3 | fixed `c274170` — locally_verified | "§3b" in the Where cell and twice in the text; the "Update branch" sentence stays with §3 |
| P6 | NIT | fresh-eyes, glm | Normal 1 | "(the names match …)" overstated the basis of the reading | fixed `c274170` — locally_verified | "(the wording overlaps; the page names no key, and the REST reference does not list this one)" |
| P7 | NIT | fresh-eyes | Normal 1 | the row did not say why "up to date" was switched off; the paragraph in `new-website` was misnamed | fixed `c274170` — locally_verified | the reason is given in the second sentence; the Where cell says the "Sibling skills" paragraph |

Check records: `bash scripts/check_clean.sh` OK with exit status 0 on `4e68c2b`, on `7ab51d4`, on `366b81c` and on `c274170`; `git diff --check origin/main` reports nothing; the row has the table's seven cells.

Waivers: none. Deferrals: none.
