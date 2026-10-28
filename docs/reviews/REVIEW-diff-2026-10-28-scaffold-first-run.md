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
