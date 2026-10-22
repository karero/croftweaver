# DIFF review — deps/astro-7-4-2-node-floor — Astro 7.4.2 in the starter, and the Node floor it now needs
Base `9acc3b9` · depth: Normal (dependencies and instructions an assistant follows are never Light; no data, login or money is touched, so not High — a judgment) · verdict: CLEAN (2 rounds, a wording pass and its confirmation; 15 findings, 2 BUG, both found in round 1 and fixed; 2 RISKs waived by the owner and taken by a second PR) · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created this worktree and branch); POST AUTHORITY — not used, no PR yet

Seats: Codex CLI 0.163.0 (gpt-6.1-sol, read-only; config effort in round 1, medium after), GLM 5.3 on melious, a fresh-eyes Sonnet sub-agent in round 1 (by design at Normal depth). The change is a public repo's text and a lockfile; the data check found no secret.

| Round | Head | Artifact | New findings (BUG/RISK/NIT) | Seats |
|---|---|---|---|---|
| 1 | `f7db0ab` | full, `9acc3b9...f7db0ab` | 2/4/5 | codex 385 s / 136,330; melious 148 s / 27,175; fresh-eyes 758 s / 197,215 |
| 2 | `7d95437` | delta since `f7db0ab` | 0/1/2 | codex 159 s / 54,937; melious 189 s / 22,272 |
| wording pass | `5e9afe1` | delta since `7d95437`, prose only | 0/1/0 (R3-01) | codex 111 s / 47,913 |
| confirmation | `ee928fb` | the fix alone, `5e9afe1..ee928fb` | 0/0/0 | codex 77 s / 50,011 |

Round 1:
- R1-01 BUG (Codex; GLM as NIT) FIXED, `externally_reverified` in round 2: "24.22.1 on Node 24" was stated as part of Astro's own floor. Astro's check is `engines = '>=22.23.4'` with `skipSemverCheckIfAbove = 23` (`astro/bin/astro.mjs:27-39`, read by the host and by Codex), so 24.22.1 and 26.12.1 are Node's security fixes, not Astro's floor. The four texts now give the two separately.
- R1-02 BUG (Codex) FIXED, re-verified: the lockfile root `engines.node` still said `>=22.12.0`. Regenerated with `npm install --package-lock-only`; the one changed line is that value.
- R1-03 NIT (Codex) FIXED, re-verified: SETUP.md said the install commands above satisfy the floor; never checked, now cut.
- R1-04 RISK (fresh-eyes) WAIVED by the owner, to be fixed in the second PR: nothing ties `engines.node` to Astro's floor. A new script, so it needs a plan first. Owner, 2026-10-22, answering the question "Waive … for THIS PR?": "Waive, plan it for 0.34 (Recommended)"; the same day he asked for "another PR to fix the remaining issues" and to "Hold 0.33 until it is merged". BUGLOG row added.
- R1-05 RISK (fresh-eyes) FIXED, re-verified: `docs/UPGRADING.md` named `^7.3.8` as the floor and had no Node step; now `^7.4.2` and a Node paragraph.
- R1-06 RISK (fresh-eyes; Codex re-raised it in round 2 as BUG) WAIVED by the owner, to be fixed in the second PR: the installer's comment calls its floor the template's. The comment sits in `packages/create-croftweaver`, and a change there asks for a new npm version. Owner, same question set: "Waive, fix at the next installer change (Recommended)"; later "Yes, include it" in the second PR (0.2.1, he publishes). Rated RISK by the host: it is a comment, not behaviour. BUGLOG row added; the root README now says building a site needs Node 22.23.4.
- R1-07 RISK (fresh-eyes) FIXED as advice-only, re-verified: the 24.22.1 and 26.12.1 advice has no signal behind it, since `engines` admits older 24 and 26. `dependabot.yml` now says so. Owner, same set: "Not in this PR: advice only (Recommended)"; the stricter `engines` goes into the second PR.
- R1-08 to R1-11 NIT (fresh-eyes) FIXED, re-verified: ci.yml and SETUP.md say "the Astro this starter ships"; brand-kit comments say "an existing site may still allow" 22.12; website-motion names Playwright 1.64.1; SETUP.md names the 22, 24 and 26 lines and says to update Node the way it was installed.

Round 2 (verification, 0 BUG):
- R2-01 RISK (GLM) FIXED: the BUGLOG rows pointed at the maintainer's private release routine, which a reader of the public repo cannot see. They now say what the maintainer does.
- R2-02 NIT (GLM) FIXED: dependabot.yml said the advice is "in SETUP.md only"; it names the files.
- R2-03 NIT (GLM) FIXED: the starter README's step 2 said "Astro's own floor"; it scaffolds `astro@latest`, so it now says "the Astro this starter ships".
- Re-raised, not new: R1-04 and R1-06 (the two waivers above).

Checked by the host and not left as UNVERIFIABLE: Node's advisory page, read raw (10 CVEs, 4 High, fixed 22.23.4, 24.22.1, 26.12.1); `npm view astro@7.4.0 engines.node` is `>=22.22.0` and 7.3.8's `>=22.12.0`; `npm audit --package-lock-only` finds 0, with and without dev dependencies; a clean `npm ci` installs Astro 7.4.2, `astro check` reports 0 errors and `npm run build` completes. Not run here: the Playwright suite (CI runs it), and npm's behaviour on an engines mismatch ("only warns", from npm's documented default).

Wording pass:
- R3-01 RISK (Codex) FIXED: the BUGLOG row for the guard said "the maintainer reads both values at every release", a manual safeguard the public release procedure does not contain. It now says that nothing compares them and how to compare by hand.

Cost: about 536k reviewer tokens in all. A first confirmation run was refused by the review script's base check (the diff did not match the `--base` given); it was redone from the right base, and nothing was reviewed on the wrong one.

Follow-ups: the guard and the installer comment (R1-04, R1-06) in the second PR; the stricter `engines` (R1-07) there too.
Notes:
- Round 2's fixes (R2-01 to R2-03) are `locally_verified`; no round 3 was earned (round 2 had no BUG), and the wording pass is the last read.
- The first PR replaces Dependabot's #371, which stops at Astro 7.4.0 and would have moved the floor twice.
- Rounds ran on the review script from the checkout of `main` at `9acc3b9` (with `base:` lines).
