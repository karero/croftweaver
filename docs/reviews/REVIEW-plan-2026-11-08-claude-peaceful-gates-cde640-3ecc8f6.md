# PLAN review — branch `claude/peaceful-gates-cde640` — `npm run ship` names the site and asks at a terminal

Artifact: `docs/reviews/SKILL-PLAN-ship-names-site.md`. Base `6859448c` · depth: High (the
starter's publish script; the High row names deploy code) · verdict: in progress; round 9 granted by the owner ("Yes, round 9", 2026-11-08), one round only · authority used:
WORKTREE-WRITE and BRANCH-COMMIT (the app made this worktree and branch for this session). No PR.
Seats: Codex and GLM 5.3 on melious in one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`,
`CODEX_EFFORT=config`), fresh-eyes Opus 5.5 in rounds 1 to 3.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `3ecc8f63` | full plan; evidence `evidence-r1.md` (scratchpad: `ship.sh` whole, the test file's stub, harness and real-git helpers, five READs of 2026-11-08) | Codex (gpt-6.1-sol), GLM 5.3, fresh-eyes Opus 5.5 | Codex 353 s, 95,508; GLM 427 s, 74,647; fresh-eyes 427 s, 203,605 | 4/6/13 |
| 2 | `57ff1c7f` | `--verify` of A1–A23; evidence `evidence-r2.md` (r1 plus READ 7 URL parse, READ 8 the 11-07 run, READ 9 GitHub's push record); fresh-eyes on the delta `3ecc8f63..57ff1c7f` | Codex, GLM 5.3, fresh-eyes Opus 5.5 | Codex 226 s, 80,098; GLM 289 s, 75,011; fresh-eyes 280 s, 154,719 | 5/3/12 |
| 3 | `98f42cee` | `--verify` of B1–B20; evidence `evidence-r3.md` (r2 plus READ 10, match counting and query refusal on both bashes); fresh-eyes on the delta `57ff1c7f..98f42cee` | Codex, GLM 5.3, fresh-eyes Opus 5.5 | Codex 206 s, 79,493 (clean); GLM 370 s, 82,124; fresh-eyes 310 s, 165,235 | 1/0/7 |
| 4 | `33335678` | `--verify` of C1–C8, `--earned-by harness-file-paths`; evidence `evidence-r4.md` (r3 plus READ 11, process group under `script`); no fresh-eyes (High: rounds 1 to 3) | Codex, GLM 5.3 | Codex 197 s, 78,817; GLM 308 s, 73,191 | 1/1/1 |
| 5 | `e9d0bf64` | `--verify` of D1–D3, `--earned-by spec-consistency,ci-wiring`; evidence `evidence-r5.md` (r4 plus READ 12, every place the test file runs) | Codex, GLM 5.3 | Codex 103 s, 74,016; GLM 329 s, 76,073 | 1/2/3 |
| 6 | `ea329892` | `--verify` of E1–E6, `--earned-by ci-wiring,allowlist-needle,tool-behaviour --cut "removed the macOS leg from the skip-only caller list…"`; evidence `evidence-r6.md` (r5 plus READ 13 util-linux `script`, READ 14 BSD `script` on TERM, READ 15 tiny gate and lock lines) | Codex, GLM 5.3 | Codex 138 s, 70,243; GLM 496 s, 91,661 | 2/2/1 |
| 7 | `36dfd5b9` | `--verify` of F1–F6, `--earned-by ci-wiring,refactor-drift --cut "removed the prepare-any-shell push claim and the second slash strip"`; evidence `evidence-r6.md` with READ 16 (stdout through npm, `bsdutils`) and READ 17 (`ship.sh` 753–758, pushes in the workflow) | Codex, GLM 5.3 | Codex 201 s, 71,831; GLM 412 s, 89,173 | 1/3/2 |
| 8 | `ec668df1` | `--verify` of G1–G6, `--earned-by comment-claim,ci-wiring,test-placement --cut "the T cases no longer run in site pre-push hooks or site CI; the llms clause is dropped from the moved comment"`; evidence `evidence-r6.md` with READ 18 (starter config, llms strip, `run_ship` PATH) | Codex, GLM 5.3 | Codex 177 s, 85,009; GLM 337 s, 77,553 | 1/2/1 |
| 9 | `c0d61833` | granted by the owner ("Yes, round 9"); `--verify` of H1–H4, `--earned-by output-order,stub-path,ci-wiring --cut "no claim that ubuntu-latest has script; the build PR's own CI is the check"`; evidence `evidence-r6.md` | Codex (clean), GLM 5.3 | Codex 98 s, 61,400; GLM 393 s, 87,467 | 0/1/3 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex | 1 | `get-url origin` names the fetch address; `git push origin` uses `pushurl` when set | fixed `e4ddaf08`: `get-url --push --all`, more than one line gives the fallback | READ 7 (git 2.54: with `pushurl` set, `--push --all` prints it, two lines for two) |
| A2 | BUG | Codex | 1 | a token in a query string is printed | fixed `e4ddaf08`: only `owner/name` of `[A-Za-z0-9._-]` is printed | READ 7 (`…/site.git?token=s3cret` → empty) |
| A3 | BUG | Codex | 1 | the `site:` read can return a commented-out old address | fixed `e4ddaf08`: `site_lines` counts matches; more than one gives a fallback; the line-753 read stays word for word | READ 7 (two-line file counts 2) |
| A4 | BUG | Codex | 1 | PUBLISHING.md "when you run it yourself it asks" contradicts the stdout check | fixed `e4ddaf08`: the sentence names a terminal window with output on screen, and the not-asked case | plan §Also |
| A5 | RISK | Codex | 1 | the feeder's 60 s limit does not stop a hung child | fixed `e4ddaf08`: pid wrapper and a watchdog that terminates ship.sh and `script` and fails the case | plan §fake terminal |
| A6 | RISK | GLM | 1 | the `exec </dev/null` reason is wrong: nested runs already send output to logs, so none is asked | fixed `e4ddaf08`: line and the build-time `script` run dropped; the plan says why none is needed | test file 236, 1009, 1030 |
| A7 | NIT | GLM | 1 | `get-url`'s error reaches the output | fixed `e4ddaf08`: `2>/dev/null \|\| true` | READ 7 (`error: No such remote 'origin'`, exit 2) |
| A8 | NIT | GLM | 1 | in worktree mode the question names this folder's address, not the published copy's | refuted, wording clarified `e4ddaf08`: the two differ only when the address changed on GitHub's `main` and not here; the push address, which decides what goes live, is exact | plan §B |
| A9 | NIT | GLM | 1 | T7's output file inside the clone breaks the folder-unchanged check | fixed `e4ddaf08`: `$G/t7.out` | test file 968-970 |
| A10 | NIT | GLM | 1 | a `get-url \| sed` pipe would trip the pipefail checker | fixed `e4ddaf08`: here-string | `check_pipefail_pipes.sh` 40-50 |
| A11 | RISK | fresh-eyes | 1 | `[^/:]` lets a user part through (`s3cret@host…/site` printed) | fixed `e4ddaf08`: the safe class; cases `tokenurl1`, `tokenurl2` | READ 7 |
| A12 | RISK | fresh-eyes | 1 | a second run meets the lock while the first waits at the question and is told to let it finish | fixed `e4ddaf08`: the line gains "(it may be waiting for a yes in another window)"; the lock cases at 1169 and 1209 check it | ship.sh 163 |
| A13 | RISK | fresh-eyes | 1 | an assistant shell with a terminal that cannot type would wait | fixed `e4ddaf08`, in "Not covered": the wait ends at the tool's limit with "Nothing was published"; no AGENTS.md line, since telling assistants to feed `/dev/null` adds nothing safer | plan §Not covered |
| A14 | RISK | fresh-eyes | 1 | the incident's path is unsupported: from an assistant's shell the question would not have fired | refuted: the owner typed it by hand at a terminal; the output pasted into the session shows the shell prompt in the wrong folder. The same output and GitHub's record also show the run pushed nothing new; the plan now says both | READ 8, READ 9 |
| A15 | NIT | fresh-eyes | 1 | the `exec </dev/null` reason | fixed with A6 | — |
| A16 | NIT | fresh-eyes | 1 | T7's file path, and T7 needs its own feeder mode | fixed `e4ddaf08` | plan T7 |
| A17 | NIT | fresh-eyes | 1 | strip the trailing `/` before `.git` | fixed `e4ddaf08` | READ 7 (`…/site.git/` → `owner/site`) |
| A18 | NIT | fresh-eyes | 1 | `${answer,,}` fails on bash 3.2 | fixed `e4ddaf08`: `case` pattern | — |
| A19 | NIT | fresh-eyes | 1 | the first-line mutation is not caught by S2 | fixed `e4ddaf08`: `noorigin` stops at the fetch | plan §Mutation |
| A20 | NIT | fresh-eyes | 1 | T5 needs ship.sh's pid | fixed `e4ddaf08`: the `start_bg` wrapper, `kill -0` poll | test file 236 |
| A21 | NIT | fresh-eyes | 1 | the expected line 1 must be per case | fixed `e4ddaf08`: `expect` takes it as an argument | plan §Stub |
| A22 | NIT | fresh-eyes | 1 | read the address with `git show "$id:astro.config.mjs"` for the question | refuted with A8 | — |
| A23 | NIT | fresh-eyes | 1 | fixture names are lowercase (`t1/origin`) | fixed `e4ddaf08` | test file 949 |
| B1 | BUG | Codex | 2 | A2 reopened: a query token holding `/` still prints (`?token=/s3cret/value` → `s3cret/value`) | fixed `98f42cee`: an address with `?` or `#` gives the fallback; cases `queryurl`, `fragurl` | READ 10 |
| B2 | BUG | Codex | 2 | A3 reopened: counting lines misses an old address in a comment on the live line's own line | fixed `98f42cee`: `site_count` counts matches; case `twosite2` | READ 10 (`/* site: old */ … site: new` → many) |
| B3 | BUG | Codex | 2 | T7's `$G` is not exported, so the inner shell writes `/t7.out` | fixed `98f42cee`: the path is passed as an argument | test file 834, 861 |
| B4 | BUG | Codex | 2 | A8's "only if the address changed on GitHub" is false: an unsaved edit here differs too | fixed `98f42cee`: the line says it reads this folder's file; both directions named | ship.sh 249–270, 391–409 |
| B5 | RISK | Codex | 2 | the watchdog's wait is unbounded when a run ignores terminate | fixed `98f42cee`: 5 s of `kill -0` polls, then an outright kill, `wait` on `script` only; T8 tests the watchdog | plan §fake terminal |
| B6 | RISK | Codex | 2 | the assistant-timeout outcome is claimed, not checked | fixed `98f42cee`: both outcomes named (trap, or a kill that leaves the lock), "not checked" said | plan §Not covered |
| B7 | NIT | GLM | 2 | the pid wrapper is `expect`'s (line 236), not `start_bg`'s | fixed `98f42cee` | test file 236, 1024–1031 |
| B8 | NIT | GLM | 2 | the watchdog's wait is unbounded | fixed with B5 | — |
| B9 | BUG | fresh-eyes | 2 | `twosite` reaches the live check, which reads the old address, and its file would break every later case | fixed `98f42cee`: `twosite1`/`twosite2` carry the `noorigin` marker and remove their file | test file 21, 181–182, 294–297 |
| B10 | RISK | fresh-eyes | 2 | PUBLISHING.md says an assistant's run is never asked; the plan's own "Not covered" says one with a terminal is | fixed `98f42cee`: the sentence and the BUGLOG row speak of "no terminal window", not of assistants | plan §Also |
| B11 | NIT | fresh-eyes | 2 | the pid wrapper's credit | fixed with B7 | — |
| B12 | NIT | fresh-eyes | 2 | `wait` on ship.sh fails: it is `script`'s child, not the test shell's | fixed `98f42cee`: polled with `kill -0` | — |
| B13 | NIT | fresh-eyes | 2 | T7 has no pid for the watchdog | fixed `98f42cee`: the wrapper in T7's command | — |
| B14 | NIT | fresh-eyes | 2 | an empty count breaks `[ -gt ]` | fixed `98f42cee`: `case` on the match list | READ 10 (no file → none) |
| B15 | NIT | fresh-eyes | 2 | the push-versus-fetch case is in no list; no mutation for several push addresses | fixed `98f42cee`: the stub refuses any other `remote` form, so every case kills a fetch-address read; `twopush` mutation listed | plan §Mutation |
| B16 | NIT | fresh-eyes | 2 | the "only if" claim | fixed with B4 | — |
| B17 | NIT | fresh-eyes | 2 | a hard kill skips the prompt-time trap | fixed with B6 | — |
| B18 | NIT | fresh-eyes | 2 | T5 without the trap ends at the watchdog, not when the feeder closes | fixed `98f42cee` | — |
| B19 | NIT | fresh-eyes | 2 | "would have stopped it" is a judgment | fixed `98f42cee`: "would have named that site and waited for a yes" | — |
| B20 | NIT | fresh-eyes | 2 | "Let it finish" after "waiting for a yes" | fixed `98f42cee`: "answer or stop it there" | — |
| C1 | BUG | GLM, fresh-eyes | 3 | the wrapper's `> pid` writes into the clone: every T case fails the folder-unchanged check, and T6 stops as unsaved | fixed `33335678`: the pid path is an argument, `$G/<case>.pid` | test file 236, 940–955, 968–970 |
| C2 | NIT | GLM | 3 | the line-1 check is a wording check with no escape for a translated ship.sh | fixed `33335678`: `SHIP_GATE_SKIP_WORDING` skips it and the no-terminal check; T cases say they are skipped under it | test file 262–280, 777 |
| C3 | NIT | fresh-eyes | 3 | T8 does not fit `run_tty`, and a timeout that sets `fail` cannot be expected | fixed `33335678`: `--none`, `--prog`, `--limit`; `run_tty` returns 124 and sets no `fail`; 15 s bound | — |
| C4 | NIT | fresh-eyes | 3 | "T8 then hangs" is wrong: BSD `script` exits on terminate | fixed `33335678`: the mutation leaves the stand-in running, which T8 checks | — |
| C5 | NIT | fresh-eyes | 3 | `queryurl` no longer kills "widen the class" or "print the raw address" | fixed `33335678`: dropped from those two lists | READ 10 |
| C6 | NIT | fresh-eyes | 3 | `fragurl` must have `/` after `#` to kill "drop the refusal" | fixed `33335678`: spelled out | — |
| C7 | NIT | fresh-eyes | 3 | the B4 fix still reads as a full list, and "says only that" is unclear | fixed `33335678`: "for example …", committed edits included; "the line does not say which copy it read" | — |
| C8 | NIT | fresh-eyes | 3 | the outright kill reaches one process, not ship.sh's children | fixed `33335678`: the group is killed; T8's stand-in starts a child; mutation listed | READ 11 (pid = pgid under BSD `script`) |
| D1 | BUG | Codex | 4 | T8 calls `run_tty --none …` with no case name, against the helper's own signature | fixed `e9d0bf64`: `run_tty t8 --none …` | plan §fake terminal |
| D2 | RISK | GLM | 4 | `SHIP_TEST_REQUIRE_TTY` is credited to CI steps, but no change to the workflow is planned, so the guard cannot fire; the file also runs in more places than the plan named | fixed `e9d0bf64`: `template-tests.yml` added to step 4 (lines 94 and 303–311 set it); every other place the file runs is named, with a skip printing there; the time T cases add to a push goes in the PR | `template-tests.yml` 88, 94, 303–311, 319; `templates/astro/.github/workflows/ci.yml` 129; `scripts/hooks/pre-push` 92 |
| D3 | NIT | GLM | 4 | T8's stand-in, if a file in the clone, repeats C1 | fixed `e9d0bf64`: an inline `bash -c` | — |

# Round 5 findings and how each was handled (plan now at ea329892)

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| E1 | BUG | Codex | 5 | the caller list puts the macOS leg of prepare-any-shell among the runs where a skip only prints; that leg holds the direct bash 3.2 step | fixed `24b17b7e`: the macOS leg removed from that list; it is named as the second direct step | `template-tests.yml` 303–311 (`if: runner.os == 'macOS'`) |
| E2 | RISK | GLM | 5 | the pipefail allow-list needle ends in `)"`; a function body with a bare pipeline would not hold it, and the entry fails as stale | fixed `24b17b7e`: the form is pinned, `s="$(grep … \| head -1 \|\| true)"` inside `site_of`, so the entry matches its one line | `scripts/check_pipefail_pipes.sh` 49 |
| E3 | RISK | GLM | 5 | the claim that the feeder does not depend on util-linux `script` was unmeasured | fixed `24b17b7e`: measured (READ 13); the util-linux form is `script -qec 'exec …'`, the watchdog kills `script` itself as well as the group | READ 13 (2.38.1: input forwarded, EOF on close, both streams a terminal; without `exec` the group is the shell's; `script` outlives TERM; KILL ends all); READ 14 (BSD `script` exits on TERM, a child ignoring it survives) |
| E4 | NIT | GLM | 5 | T1 asserts "Going live" without advancing its fixture | fixed `24b17b7e`: `advance 1` | plan §fake terminal |
| E5 | NIT | GLM | 5 | "no new exposure" is too broad: early stops now print the site and repo | fixed `24b17b7e`: narrowed to the owner's own screen or log | — |
| E6 | NIT | GLM | 5 | `--prog CMD` cannot go through the wrapper, which execs a script path | fixed `24b17b7e` and `ea329892`: `--prog FILE` takes the place of `scripts/ship.sh` in the wrapper; the stand-in is a file under `$G` | — |

# Round 6 findings and how each was handled (plan now at 36dfd5b9)

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 6 | prepare-any-shell has no pushes, so "prepare-any-shell's pushes on each system" overstates the hook-run callers | fixed `36dfd5b9`: removed; the hook runs are verify-windows' pushes and owners' own | READ 17 (no `git push` in 236–318; verify-windows 365, 403, 410) |
| F2 | BUG | Codex | 6 | keeping the call-site strip after `site_of` strips once strips twice: `site: 'https://a//'` would ask for `https://a/build.txt`, not today's `https://a//build.txt` | fixed `36dfd5b9`: line 758 goes and its comment moves into `site_of`, one strip as today | READ 17 (753–758) |
| F3 | RISK | GLM | 6 | stdout being a terminal through `npm run` was never measured; if not, the question never appears for the owner | refuted by measurement: through `npm run` both streams stay terminals, and only `> file` turns stdout off; the plan now cites it | READ 16 |
| F4 | RISK | GLM | 6 | site CI on Ubuntu is said to have `script`, not shown | fixed `36dfd5b9`: site CI runs on `ubuntu-latest`, the playwright job's image, whose required step shows `script` there on every run; `bsdutils` is essential on Debian (Ubuntu not checked here) | READ 16 |
| F5 | NIT | GLM | 6 | a call-site strip with nothing to do is dead code | fixed with F2 | — |
| F6 | NIT | GLM | 6 (outside scope) | the no-terminal line's cause list misnames a run whose input alone is not a terminal | fixed `36dfd5b9`: "(input or output is not a terminal window)" | — |

# Round 7 findings and how each was handled (plan now at ec668df1)

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| G1 | BUG | Codex | 7 | the comment moved into `site_of` says the strip is the llms guard's, but that guard strips every trailing slash and this one strips one | fixed `ec668df1`: the clause is dropped in the move | READ 18 (`llms-coverage.spec.ts:30`) |
| G2 | RISK | Codex | 7 | the shared `ubuntu-latest` label does not show `script` in later site CI runs, where a skip only prints | fixed `ec668df1` with G4: the T cases no longer run in site CI at all | — |
| G3 | RISK | GLM | 7 | "the starter has one" was not shown | fixed `ec668df1`: measured, `one`, `https://example.com`; no test pins it, since an owner may set `site` from a variable | READ 18 |
| G4 | RISK | GLM | 7 | the T cases run in every site's pre-push hook on `script` versions never measured, so a quirk could refuse an owner's real push | fixed `ec668df1`, a cut: the T cases run only with `SHIP_TEST_TTY=1`, set on the toolkit's two direct CI steps; elsewhere they print a skip line; the cost (a hand-edited `ship.sh` in a site loses their cover) is in Not covered | `template-tests.yml` 94, 303–311 |
| G5 | NIT | GLM | 7 | "the mode line becomes the second line" is not always so | fixed `ec668df1`: it follows the first line; `mode_has` finds it wherever it sits | — |
| G6 | NIT | GLM | 7 | `run_tty`'s stub `PATH` is unstated | fixed `ec668df1`: the same stub `bin` first on `PATH` as `run_ship` (line 1009) | READ 18 |

# Round 8 findings and how each was handled (plan now at c0d61833, not yet confirmed by a round)

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| H1 | BUG | Codex | 8 | the G5 rewording puts the leftovers warning before the mode line, but `report_leftovers` runs after it | fixed `c0d61833`: leftovers named as still after it (line 539 since round 9) | `ship.sh` 537–539 |
| H2 | RISK | Codex | 8 | with the stub `bin` first on `PATH`, T8's `sleep 40` returns at once, so the stand-in ends before the watchdog fires | fixed `c0d61833`: the stand-in and the watchdog sleep through `$SHIP_T_REAL_SLEEP`, exported for every run (line 870) | `check_ship_push.sh` 893–898, 870 |
| H3 | RISK | GLM | 8 | `ubuntu-latest` having `script` is not shown; if it lacks one the whole file goes red with no clue why | fixed `c0d61833`: the failure is one line naming the T cases and `SHIP_TEST_TTY`, as S10 (e) does (line 841); the build PR's own CI shows it before any merge | `check_ship_push.sh` 840–841 |
| H4 | NIT | GLM | 8 | "the answer rests on what goes" is half wrong in worktree mode: the address is this folder's copy | fixed `c0d61833`: the repo and the commits are what goes; the address is this folder's copy | plan §B |

# Round 9 findings and how each was handled (plan now at 83747653)

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| I1 | RISK | GLM | 9 | the feeder's waits are unnamed while the stub `sleep` is first on `PATH`; a feeder on it would write the answer before the read, and BSD `script` drops it | fixed `ebe1a364`: the feeder waits on `$SHIP_T_REAL_SLEEP` | READ 1 (an answer before the read is lost); `check_ship_push.sh` 893–898 |
| I2 | NIT | GLM | 9 | "`mode_has` already finds it": the helper is new | fixed `ebe1a364`: "the new `mode_has` helper (below)" | — |
| I3 | NIT | GLM | 9 | `report_leftovers` is line 539, not 538 | fixed `ebe1a364` | `ship.sh` 537–539 |
| I4 | NIT | GLM | 9 | the playwright step's comment says the file "fails within a minute or so", untrue with T cases | fixed `83747653`: the clause is dropped, since a hung T case takes its 60-second limit | `template-tests.yml` 86–93 |
