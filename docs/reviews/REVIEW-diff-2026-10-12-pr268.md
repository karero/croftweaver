# DIFF review — PR #268 — `npm create croftweaver`, a one-line install of the skills
Base `e58d3ae`, and `d382cbe` since the merge of main before round 2 · depth: Normal (an install script: it deletes and moves folders in the place an assistant takes its instructions from, and unpacks a download) · verdict: CLEAN (every row is fixed, refuted or waived; P8 closed on 2026-10-12 by the real run after the owner published) · authority used: POST AUTHORITY — atom A (this session opened #268); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — atom A (codex's chain below, unbroken from round 1 to `5d05bf4`)

Seats: Codex and GLM 5.3 on melious (`SECOND_SEAT=melious`), and in round 1 a fresh-eyes pass on a mid-tier model of the host's family. The owner's OK for both services, given in this session on 2026-10-12 to the question "shall I run the review pair (Codex and GLM 5.3 on melious, Normal depth), then push and open the PR?": "yes to all three, npm half is right".

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `60ae63e` | full: `e58d3ae...60ae63e` without `docs/reviews/`, plus the plan `docs/reviews/SKILL-PLAN-capability-gaps.md`; in front of it, marked as context, `scripts/install.sh`, the zip lines of `scripts/package.sh`, the suite lookup of `new-website`, live facts and the test records | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only · melious HTTP API, glm-5.3, text only · fresh-eyes: a sub-agent on the host family's mid-tier model, read-only by instruction | codex 470 s / 96,694 · melious 500 s / 41,214 · fresh-eyes 185 s / 137,750 | codex 3/3/0 · melious 0/2/4 · fresh-eyes 0/4/6 · after dedup 3/9/6 |
| 2 | `9f5cee7` | merge link (`merge_link.sh e58d3ae 60ae63e d382cbe`: the change's own files since round 1's head, the merge of main included) plus the plan's delta `60ae63e..9f5cee7`, with round 1's dispositions (`--verify`); in front of it, as context, `index.mjs` whole and the test record | codex-cli 0.162.1, gpt-6.1-sol, medium, read-only · melious HTTP API, glm-5.3, text only | codex 249 s / 62,122 · melious 499 s / 50,151 | codex 1/1/0 · melious 0/0/1, and one NIT outside scope · after dedup 1/1/0 |
| 3 | `c52c88c` | delta `9f5cee7..c52c88c` without `docs/reviews/` (two files, 42 lines), with round 2's dispositions (`--verify`); as context, `index.mjs` whole and the test record | same two seats, codex at medium | codex 181 s / 61,935 · melious 128 s / 20,542 | codex 1/0/0 · melious 0/0/0 |
| 4 | `e7249b1` | delta `c52c88c..e7249b1` without `docs/reviews/`, with round 3's dispositions (`--verify`); context as before | same two seats, codex at medium | codex 82 s / 47,111 · melious 31 s / 11,210 | codex 0/0/0 · melious 0/0/1 |
| wording pass | `fdb4da9` | delta `e7249b1..fdb4da9`: two prose lines (a code comment, a README sentence), scoped to contradictions with the code | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only | 177 s / 44,500 | one contradiction (labelled BUG), fixed |
| confirmation | `5d05bf4` | delta `fdb4da9..5d05bf4`: the fix of that contradiction, two prose lines | same | 147 s / 32,777 | 0/0/0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| P1 | BUG | codex, fresh-eyes | 1 | A path that steps sideways (`skills/alpha/../ghost/SKILL.md`) stays inside staging and passes, but names a skill that gets no folder; the install stops after it has removed skills | fixed — locally_verified | `bb52aff`: steps `.`, `..` and empty are refused. Invariant: every file lands in the skill its path names. Variants tested: one sideways step, a `./x/../../late` chain, a colon, a backslash, a climb out; the three new cases failed on `60ae63e` before the fix |
| P2 | BUG | codex | 1 | A folder called `new-website/SKILL.md` passes for the orchestrator, and a working suite is replaced by one that cannot load | fixed — locally_verified | `bb52aff`: `statSync(...).isFile()`; the new case failed on `60ae63e` |
| P3 | RISK | codex | 1 | `scripts/check_clean.sh` does not read `packages/`; a row in `docs/BUGLOG.md` records the gap and does not close it | waived for this pull request — the owner, 2026-10-12 | asked where it should be fixed, the owner chose "Own small PR next (Recommended)"; the row in `docs/BUGLOG.md` stays open until that pull request |
| P4 | RISK | codex, melious (as NIT) | 1 | The README names `npm create croftweaver` while npm still serves the placeholder | waived as it stands — the owner, 2026-10-12 | asked how to order it, the owner chose "Publish before merge (Recommended)": the README lines stay, the owner publishes from the reviewed commit, one real `npm create croftweaver -- --codex` run follows (it also closes P8), then the merge |
| P5 | RISK | codex | 1 | No test installs the real skills on Windows | fixed — locally_verified | `bb52aff`: a test zips the real skills with `git archive --format=zip`, on every system, and compares each installed file with its blob id from `git ls-tree` |
| P6 | BUG | codex | 1 | The Makefile and the workflow call the tests "node only"; one calls git, tar and zip | fixed — locally_verified | `bb52aff`: both now name git, and zip and tar on Linux and macOS. Help text and a comment, so not counted as substantive |
| P7 | RISK | melious | 1 | That `lstat` reports a Windows junction as a link is not shown | refuted | CI run 38277105136, job 114905149569 (windows-latest, Node 24.21.0): both link tests pass, and they create the link as a junction there |
| P8 | RISK | melious | 1 | Nothing runs the installer through npm, so `-- --codex` reaching it is not shown | fixed — shown by the real run, 2026-10-12 | The owner published `create-croftweaver` 0.1.0; its checksum on the registry, `2394930488d0025bdfaede0b7026f2dc2fed251b`, is that of `npm pack` at `b031d27`. `npm create --yes croftweaver@latest -- --codex`, `HOME` set to an empty scratch folder: exit 0, "Croftweaver v0.31 is installed: 34 skills in ~/.agents/skills", and no `~/.claude`. The same without the flag: 34 skills in `~/.claude/skills`. `diff -rq` of each against `git archive v0.31 skills` reports only `.croftweaver.json` as extra |
| P9 | NIT | melious | 1 | A file's mode is cut by the umask, so under one that clears the owner's execute bit scripts land non-executable | refuted | under `umask 0177` the folders themselves cannot be entered: `git clone` and `cp` of an executable file both fail in a probe; no install route works there |
| P10 | NIT | melious, fresh-eyes | 1 | "Nothing was changed" is printed although a skill was removed and the list was rewritten | fixed — locally_verified | `bb52aff`: "No skill was changed", and only when none was copied or removed; tested both ways |
| P11 | NIT | melious, fresh-eyes | 1 | A staging folder left by a killed run stays for good | waived — the owner, 2026-10-12, after the fix was withdrawn | `bb52aff` added a cleanup, which drew P19 and P21; told of the chain and asked what to do with it, the owner chose "Remove the cleanup (Recommended)". The package README names the leftover folder |
| P12 | RISK | fresh-eyes | 1 | The package is published once, and its rule for skill names would stop every install the day a release has a folder named otherwise | fixed — locally_verified | `bb52aff`: any plain, not hidden folder name; a test installs `Odd_Name.v2` |
| P13 | RISK | fresh-eyes | 1 | A site scaffolded from the copies is stamped `suite_commit: unknown`; neither the README nor the plan says so | fixed — locally_verified | `bb52aff`: README's update note and the plan's known limits; `skills/new-website/SKILL.md`, the `else` branch that writes `SUITE-VERSION` |
| P14 | RISK | fresh-eyes | 1 | Its own copies are known by name, so a folder the user puts under such a name is replaced, or removed, without a backup; only the overwritten edit was disclosed | fixed — locally_verified | `bb52aff`: the package README's two bullets and the plan's known limits say it |
| P15 | RISK | fresh-eyes | 1 | The ruleset needs the matrix job's exact check names | fixed | the pull request's text lists the four names as `gh pr checks 268` prints them |
| P16 | NIT | fresh-eyes | 1 | Where the skills folder is a link to another disk, a backup folder beside the link cannot take the rename | fixed — locally_verified | `bb52aff`: beside the real folder; a test with a linked skills folder checks where it lands (the two-disk case itself is not tested) |
| P17 | NIT | fresh-eyes | 1 | The package names its licence and ships no LICENSE file | fixed | the owner chose "Add a copy (Recommended)" on 2026-10-12; `packages/create-croftweaver/LICENSE` is the root file, byte for byte, and `npm pack --dry-run` lists it |
| P18 | NIT | fresh-eyes | 1 | The new BUGLOG row has a sentence where the other rows have one word for Impact | fixed | `bb52aff` |
| P19 | BUG | codex | 2 | The sweep added for P11 removes every other staging folder, so a second run started while a first is installing leaves the first with its skills removed and nothing to rename into place | fixed, then superseded by P21: the sweep is gone | `f07645b`: only a staging folder a day old is removed. Invariant: a run takes nothing another run may still need. Tested: a two-day-old folder goes, a fresh one stays with its files; the fresh-one case fails with round 1's sweep put back. No lock: two runs at once can still end with the second stopped part-way, which a further run finishes. caused-by: P11 (introduced) |
| P20 | RISK | codex, melious (as NIT) | 2 | P12's rule still refused a space, a letter outside ASCII and a leading underscore, against its own comment | fixed — externally_reverified (round 3, both seats) | `f07645b`: any name with no slash, backslash or colon and no dot in front; a test installs `café`, `website tools`, `_helper` and `Odd_Name.v2` and runs twice. A name one system cannot hold fails the real-skills tests on that system's runner |
| P21 | BUG | codex | 3 | Age does not show that a run is dead: after a pause of more than a day or a clock set forward, P19's sweep removes a live run's staging, its own included, and the run then removes skills it cannot replace | fixed — externally_reverified (round 4, both seats) | `b100dff`: the sweep is removed: no run touches a staging folder that is not its own. Tested: an old and a fresh foreign staging folder both survive a run with their files. melious had judged the case outside any real run's length. caused-by: P19 (partial) |
| P22 | NIT | melious | 4 | The comment and the README say a folder is left by a run killed "while it unpacks"; a kill during the renames leaves it too | fixed — locally_verified, then read by the wording pass | `fdb4da9`: "before it finishes" in the README, "once it has begun to unpack" in the comment |
| P23 | wording | codex | wording pass | The comment said such a run "leaves" the folder, though one killed after its own cleanup leaves none; and whether a dot in front hides a folder on Windows was not shown | fixed — externally_reverified (the confirmation) | `5d05bf4`: "can leave", and "hidden" is gone from the comment and the README |

23 findings in 4 rounds, a wording pass and its confirmation: 5 BUG, 10 RISK, 7 NIT and one wording contradiction. 18 fixed, 2 refuted (P7, P9), 3 waived by the owner (P3, P4, P11).

UNVERIFIABLE entries, round 1: 12 asked across the three seats, none became a finding. Looked at: `setup-node` with an empty `node-version` (the Windows job's log: "Resolved skills/new-website/templates/astro/.nvmrc as 24"), the junction claim (P7), npm's dispatch (P8); the rest (GitHub's redirect, the plugin documentation, the proxy sentence) rest on the author's records above and in the plan.

UNVERIFIABLE entries, round 2: 8 asked, none became a finding. Looked at: `npm pack --dry-run` lists `LICENSE`, `README.md`, `index.mjs`, `package.json`; the pull request's text carries the four check names; codex ran the plan's `git grep` itself and got eleven.

UNVERIFIABLE entries, round 4, the wording pass and the confirmation: 9 asked, one confirmed (a dot in front does not hide a folder on Windows: P23). The owner's answers behind the waivers are quoted in the rows; they were given in the authoring session, which a reviewer cannot open.

UNVERIFIABLE entries, round 3: 7 asked, none became a finding. Looked at: the Windows job on `c52c88c` (run 38292842650, job 114956793935) passes "the real skills, zipped by git, arrive file for file" and the test with `café` and `website tools`; the sentence that nothing loads a staging folder is gone with the sweep.

Fix chain: P11 → P19 → P21, three rows on the staging cleanup. The owner was told once, with the option to prove ownership by process id, and chose to remove the cleanup.

Follow-ups:
- (melious, round 2, outside scope) On main, the workflow's header comment says the Cloudflare check's tests "need nothing beyond Node", while their job's own comment says they use openssl. Not this change's text.

Notes:
- Round 4 is the one round past 3. It was earned by P21, the BUG round 3 found in the staging cleanup.
- Round 4 was clean in the sense of stop condition (a2): no BUG, no RISK. Its NIT (P22) was fixed without a further round and read by the wording pass.
- Chains for the stamp: codex saw `e58d3ae...60ae63e` in full, then each delta to `9f5cee7` (a merge link over the merge of main), `c52c88c`, `e7249b1`, `fdb4da9` and `5d05bf4`. melious's chain ends at `e7249b1`, fresh-eyes' at `60ae63e`, by design.
- No final full read: a DIFF gate at Normal depth on a change that is mostly code.
- The commit that brings this file to its final state changes nothing else; the stamp names it, and the reviewed scope is the one at `5d05bf4`.
- The order the owner chose was kept: published from the reviewed commit `b031d27`, then the real run (P8), then the merge of main and the merge link below, and only then the merge.

## Before round 1

Found by the author's own checks and by CI, before any reviewer ran; both are in the reviewed diff:

- A failed first run left an empty skills folder behind, against the README's "changes nothing" (found by the claims sweep; `9b51b4d`).
- That fix removed one folder too many on Windows, where `fs.mkdirSync`'s return value is spelled differently from the destination; the new test failed on the Windows runner (run 38275840632, job 114900979567) and `75b3e19` fixed it. The same run's macOS and Node 22.12.0 legs were cancelled by fail-fast, not failed; `75b3e19` turns fail-fast off.

## Test records

Run at `75b3e198824c67cb26125b73a2a0998b49f99ab8`, the head before the commit that adds this file. That commit takes this file and nothing else.

`make test-create`, the whole output:

```
✔ a first run installs every skill of the latest release, and nothing else from the zip (128.784417ms)
✔ a second run makes the folder match the new release: changed, added and dropped skills (239.600667ms)
✔ a folder someone else put under a skill's name is moved beside the skills folder, not lost and not left to load twice (127.317208ms)
✔ skills linked from a toolkit folder are left alone, and --force swaps the link for a copy without touching that folder (247.581625ms)
✔ a link whose folder is gone is replaced: keeping it would keep a skill that cannot load (127.506625ms)
✔ each assistant gets its own folder, and the two overrides of the shell installers hold here too (498.60125ms)
▶ a download that cannot be used changes nothing in an install that works
  ✔ the server has no such file (158.516583ms)
  ✔ the zip is cut short (131.513584ms)
  ✔ the zip points past its own end (132.105833ms)
  ✔ a file fails its checksum (125.881292ms)
  ✔ a path climbs out of the skills folder (138.211625ms)
  ✔ a path climbs out the Windows way (127.882375ms)
  ✔ a skill name is not a plain name (128.014875ms)
  ✔ the zip holds a link (124.402ms)
  ✔ the zip is not a Croftweaver release (123.879459ms)
  ✔ on a computer without the skills, a failed run leaves no empty folder behind (273.635667ms)
  ✔ nothing answers at the address (104.382375ms)
✔ a download that cannot be used changes nothing in an install that works (1696.7495ms)
✔ an argument it does not know stops it before anything is downloaded or written (230.953625ms)
✔ the real skills, zipped the way a release is, arrive file for file with their executable bits (474.242333ms)
ℹ tests 20
ℹ suites 0
ℹ pass 20
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 3988.047208
exit status: 0
```

`make check`: 1084 lines of output, last line `exit status: 0`. The lines that start with `OK` or `all`, or hold `passed`, and the exit status (a selection by that rule; the same checks run as CI jobs on the pull request):

```
OK — no private names in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs scripts; no contact info or credentials in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs LICENSE
OK — all 11 subjects behave identically with and without an exported CDPATH.
OK — whats-new.sh resolves a relative <project_dir> to the real one, not a CDPATH decoy.
OK — no early-exit pipe under pipefail in 20 scripts (2 exempt, each with a reason in scripts/check_pipefail_pipes.sh).
OK — independent-review stays model-agnostic (no concrete model names/tags in its 23 pipeline files)
OK — all 53 files under skills/new-website/templates/astro are accounted for (TEMPLATE_TRACKED, SITE_OWNED, or SITE_SOURCE).
OK (with warnings) — no skill over a hard budget; see the warn lines above (34 skills checked).
ok   suggest: a path already passed after -- is not suggested again
ok   thinkfailhelp: the flag is not passed
ok   thinklongword: the flag is not passed
all checks passed
all checks passed
all checks passed
test_whats_new_removed_skill: all cases passed
all checks passed
all checks passed
all checks passed
test_clean_denylist: all passed
test_git_stand_hook: all passed
all whats-new missing-file tests passed
all checks passed
exit status: 0
```

CI on `75b3e19` (run 38277105136): `create-croftweaver-tests` passed on ubuntu-latest, macos-latest, windows-latest and on ubuntu-latest with Node 22.12.0. The Windows leg skips, by name, the one test that needs the `zip` tool.

Checked by hand, not by a test:

- Each of 17 guards in `index.mjs` was removed once; `node --test` failed every time. The list is in the pull request's comment.
- `npm pack`, then `npm exec --package=<the tarball> -- create-croftweaver` against the stub, serving the real skills: exit 0, 34 skill folders. The tarball holds `README.md`, `index.mjs`, `package.json`.
- One real run against the v0.31 release on GitHub, `HOME` set to an empty scratch folder: exit 0, 34 skill folders; `diff -rq` against `git archive v0.31 skills` reports only `.croftweaver.json` as extra; 15 executable files on both sides. Run at `963c3be`, not repeated since: the two commits after it list the missing folders before `mkdirSync` and try to remove them, if empty, at the end of every run.
- Not tested: the refusal on a Node older than 22.12.
