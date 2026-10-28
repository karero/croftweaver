# DIFF review — new-website: a scaffold that asks nothing, keeps its .gitignore, and passes its first test

Branch `fix/scaffold-first-run`, karero/croftweaver#435. Depth: **Normal**: the diff edits a
SKILL.md and the starter's README, never Light; no secret, permission or legal text changes,
so not High. Seats: Codex and GLM 5.3 on melious (`SECOND_SEAT=melious`, one command), plus a
fresh-eyes pass (Sonnet) in round 1.

`make check` passed before round 1 (exit 0). Real runs before round 1, sent to the reviewers as
`--evidence`: the new command with stdin closed over a committed starter `.gitignore`
(create-astro 5.3.1: exit 0, no prompt, ` M .gitignore`); the new steps 0 and 1 end to end with
the domain set in all four files, `tests/seo.spec.ts` "robots.txt stays open and llms.txt
exists" passed, and failed with only the two old files set.

## Round 1 — `22b23b1d`, base `origin/main` (`3fad0752`)
`codex` 157s (42,300 tokens) · `melious` 75s (13,763 tokens) · fresh-eyes (Sonnet) 64s
(114,163 tokens).

| id | sev | seat | status | why |
|---|---|---|---|---|
| C1 | BUG | codex | fixed | `templates/astro/README.md` step 4 still set the domain in two files; it now names `robots.txt` and `llms.txt` too (fresh-eyes F1, the same point, as a RISK) |
| C2 | RISK | codex | fixed | Measured: under a terminal (`script`) with no keyboard input, npm asked "Ok to proceed? (y)" before an uncached create-astro (5.2.0) and exited 1 on end of input; with `npm create --yes astro@…` (5.1.0, uncached) it went straight through. Both files now give npm's `--yes` too |
| C3 | RISK | codex | fixed | The release-notes row told existing sites to copy the starter's `.gitignore` in, which would drop their own lines; it now says to add the missing lines and keep their own (fresh-eyes F4, the same point) |
| C4 | BUG | codex | fixed | The release-notes row said a hidden folder is never taken, against SKILL.md's owner-named exception; it now names the exception |
| M1 | RISK | melious | fixed | Measured: with only `llms.txt` on example.com, `seo.spec.ts` and `llms-coverage.spec.ts` fail 2 tests. No run shows `astro.config.mjs` or `src/config.ts` alone being caught, so the sentence now says the test fails while `robots.txt` or `llms.txt` still names example.com |
| M2 | NIT | melious | fixed | Both files name the checked version, create-astro 5.3.1 |
| M3 | NIT | melious | fixed | An owner-named hidden folder: the assistant says it may not show in Finder or File Explorer and asks once |
| M4 | NIT | melious | fixed | One clause says `git checkout` restores the file step 0 committed. No fallback copy: a skipped step 0 makes it fail loudly, which is wanted (fresh-eyes said the same) |
| F2 | NIT | fresh-eyes | fixed | The hidden-folder check came after "ask whether it is their websites folder", so the assistant could still offer the hidden folder and take a "yes" as the owner naming it. The check now comes first, and the long line is wrapped |
| F3 | NIT | fresh-eyes | fixed | Step 1 says nothing is installed yet and README step 3 runs `npm install` |
| F5 | NIT | fresh-eyes | fixed | The websites-folder row's closing says the rule is an instruction no assistant run has tested yet |

## Round 2 — `2b1ad04e`, base `22b23b1d` (verification)
`codex` 109s (53,579 tokens) · `melious` 246s (26,059 tokens). Both seats: every round-1 fix
landed and covers its whole finding. Gate total so far: 4 seat runs, 135,701 tokens logged, plus
fresh-eyes 114,163.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C5 | RISK | codex | fixed | Settled by a run: the exact final command with an empty npm cache under a terminal (npm 11.20.0, create-astro 5.3.1): exit 0, no question, `.gitignore` restored. Both files now name those two versions |
| C6 / M9 | RISK | both, outside scope | fixed | Settled by a run: the starter's whole first `npm test` on a scaffold made by the new steps with all four domain files set: 114 passed, 1 skipped (the positioning test, which waits for the positioning step by design) |
| M5 | NIT | melious | fixed | The owner-named warning now covers a tool's scratch or temp folder too |
| M6 | NIT | melious | fixed | The release-notes row points at `templates/.gitignore` to compare with, naming `.env`, `.wrangler/` and the rest as examples |
| M7 | NIT | melious | fixed | The version note is scoped: the exact command was checked with npm 11.20.0 and create-astro 5.3.1 |
| M8 | NIT | melious | fixed | The robots row quotes both `llms.txt` errors |

No BUG in round 2. The round-3 change is wording and evidence only; it gets a wording pass,
not another round.

## Wording pass — `817cab81`, base `2b1ad04e`
`codex` 79s (36,131 tokens): no findings · `melious` 128s (17,884 tokens): two NITs, both fixed:
`.env.example` is named as the one `.env.*` file the starter keeps; "this exact command was
checked" became "checked … run fresh with no keyboard input", since the run used an empty npm
cache and closed input. Gate closed: 2 rounds and a wording pass, 0 BUG open, 19 findings in all
(2 BUG, 5 RISK, 12 NIT; the two fresh-eyes points Codex also raised counted once), all fixed.
