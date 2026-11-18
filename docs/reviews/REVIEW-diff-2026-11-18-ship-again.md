# DIFF review — fix/clean-plate-workers-ship — the starter speaks Workers; `ship` offers one "ship again"

Base `f38a8262` (origin/main when the branch was cut) · depth: High (the starter's publish script and its
tests) · verdict: no BUG and no earning RISK open after round 3; round 3's fixes were not re-verified (see
Notes) · 3 rounds, 32 findings after dedup · authority used: WORKTREE-WRITE and BRANCH-COMMIT. This
session was started by the coordinator for the maintainer's go "Both in 0.36"; it created the worktree and the branch.

Artifact: round 1 `git diff f38a8262..53fdd80b`; round 2 the delta `53fdd80b..9b24e21f`; round 3 the delta
`9b24e21f..45ba2d39`, each `-- . ':(exclude)docs/reviews/'`. Evidence file per round (author's commands
and outputs, quoted): `make check`, the full harness `SHIP_TEST_TTY=1 bash tests/check_ship_push.sh`, the same
harness against the old `ship.sh` (new cases must fail there), the Workers Builds capture
`tests/fixtures/workers-builds-2026-11-08.txt`, and (round 2 on) Cloudflare's build-image and
build-watch-paths pages, fetched by the author on 2026-11-18. Gate id 20261118T151837Z-58366.
Design decision between rounds 1 and 2, from the owner's manager: the retry commit changes one tracked line in
`SHIP-AGAIN.txt` instead of being empty.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `53fdd80b` | full | Codex (gpt-6.1-sol, config effort, read-only); melious (glm-5.3, HTTP API); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 105,425 tokens; melious 47,546; fresh-eyes 142,056 (seconds not recorded) | 2 / 5 / 6 after dedup |
| 2 | `9b24e21f` | the round 1 fixes, `--base 53fdd80b`, `--verify` | Codex; melious (first run failed at 954 s, curl 28; rerun 614 s); fresh-eyes | codex 244 s, 82,750; melious 614 s, 56,998; fresh-eyes 150,366 (seconds not recorded) | 1 / 4 / 3 after dedup |
| 3 | `45ba2d39` | the round 2 fixes, `--base 9b24e21f`, `--verify` | Codex; melious; fresh-eyes | codex 156 s, 117,232; melious 437 s, 51,179; fresh-eyes 301 s, 154,699 | 1 (comment) / 3 / 7 after dedup |

The cost log's round 3 row for melious carries the label "round 3" for round 2's rerun; the real round 3
rows are the ones above. Gate total after round 3: 908,251 seat tokens by the script plus fresh-eyes 447,121
logged by the host (rounds 1 to 3).

Round 1 findings (full list with the author's fixes: round 2's `--verify` file): a refused worktree-mode retry
printed the retry commit as GitHub's main (BUG, three seats); `--no-verify` left prepare-commit-msg hooks
running in folder mode (BUG, Codex); an empty commit may start no Cloudflare build (RISK, three seats; fixed by
design: the commit changes `SHIP-AGAIN.txt`); the curl stub never exercised the "build arrived while you answered"
recheck (RISK); the 3-minute threshold was unguarded (RISK); the `.nvmrc` claim had no citation (RISK);
Ctrl-C between the yes and the push said "Nothing was published" (RISK, fixed in code); five NITs of wording,
one refuted (`check_deploy` marker cases run after the fixture guard: the guard fails the file either way).

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| R2-1 | BUG | Codex | 2 | A retry interrupted during a push that landed exited before `main_what` was set; the last line called the retry commit "GitHub's main as of the fetch". | fixed in `45ba2d39` | T17 (worktree, TERM during the retry push): exit 1, last line "(GitHub's main with the 'ship again' commit: <12>.)". Fails on the old script (RUN 3). |
| R2-2 | RISK | melious | 2 | The question's exit trap stays armed after the answer, so a stop between yes and push claims "nothing more was done", and `push_and_report`'s stop branch could never fire. | refuted | `ship.sh` re-arms `trap 'stop_asked=1'` straight after `read`. T18 (folder, TERM at ship_again's `date`) asserts "the 'ship again' push was not made. The 'ship again' commit is taken off 'main' again.", main and production unchanged. Codex and fresh-eyes confirmed in round 3. |
| R2-3 | RISK | Codex | 2 | A tracked link or an ignored `SHIP-AGAIN.txt` could be overwritten, and the failure cleanup could delete the owner's file. | fixed in `45ba2d39` | Guard before any write. T14c (ignored file, folder), T14b (no prior file: removed again), and in round 3 T14d (tracked link) and T14e (worktree, `.gitignore`). |
| R2-4 | RISK | Codex, melious | 2 | Cloudflare facts had no checked support (`.nvmrc` for Workers; watch paths). | support added | READ 2: build-image page row "Node.js … .nvmrc, .node-version"; watch-paths page: any changed file triggers a build by default, include paths filter. That a retry commit starts a build is not shown: BUGLOG open row. |
| R2-5 | RISK | fresh-eyes | 2 | The CI no-TTY step grepped "T1 to T8". | fixed | The grep is now "skipped: SHIP_TEST_TTY is not set", with no case count. |
| R2-6 | NIT | melious | 2 | Watch-path wording inverted in the commit message, a comment and the BUGLOG row. | fixed | "Build watch paths that do not list that file skip this commit." |
| R2-7 | NIT | melious | 2 | `restore_again_file`'s absent-file branch had no test. | fixed | T14b. |
| R2-8 | NIT | fresh-eyes | 2 | A refused retry after a first run that pushed nothing said "The first publish did go out". | fixed | `first_n`; T19 asserts "The first run pushed nothing ('production' already had <12>)". |
| R3-1 | BUG (comment) | Codex; melious, fresh-eyes NIT | 3 | The workflow's comment said "T1 to T16 now", the harness says more. | fixed | The comment names no count. Documentation only; the executable grep was right. |
| R3-2 | RISK | fresh-eyes | 3 | The link half of the new guard (`[ -L … ]`) and the worktree-mode guard had no case: deleting either left every test green. | fixed | T14d (folder, a tracked link to a file outside the site: the file is untouched, production unchanged); T14e (worktree, the site's `.gitignore` lists the file). |
| R3-3 | RISK | fresh-eyes | 3 | The stop branch for a first run that pushed nothing (`first_n=0`) had no case. | fixed (that text); rest follow-up | T20 asserts the exact sentence. Still untested: the question-time stop text when production already had the commit, "still on 'main' here, not pushed" (needs a `main` that moved), and the "(counted from 'ship again')" wording. BUGLOG row. |
| R3-4 | RISK | fresh-eyes | 3 | If `rev-parse` fails right after the retry commit, the commit stays on `main` in folder mode, unannounced. | re-sorted: rare | Ordinary use does not make `rev-parse HEAD` fail right after a commit. One cheap loud message: "could not read the new commit's id", and for folder mode that the commit is on `main`, not pushed. BUGLOG sentence. |
| R3-5 | NIT | fresh-eyes | 3 | Two comments said "the first publish is already out", false when the first run pushed nothing. | fixed | Reworded to "the first run". |
| R3-6 | NIT | fresh-eyes | 3 | The T13 probe could not tell that the hook caused the refusal. | fixed | The hook touches a file; the probe asserts the file exists. |
| R3-7 | NIT | fresh-eyes | 3 | PUBLISHING.md and the BUGLOG row did not say a link or an ignored `SHIP-AGAIN.txt` refuses the retry. | fixed | One clause each. |
| R3-8 | NIT | fresh-eyes | 3 | "the next npm run ship says what to do" is not true in folder mode (it says `git push`, which a protected `main` refuses). | fixed | The tail is dropped: "still on 'main' here, not pushed." |
| R3-9 | NIT | melious | 3 | The BUGLOG row did not name the third outcome (undo fails, the commit stays on a moved `main`). | fixed | Row says so. |
| R3-10 | NIT | melious | 3 | Evidence RUN 2's note dated two test fixes (`--folder-moves`, T16's second question) to the round 2 delta. | accepted | They landed before `9b24e21f`; the note was carried over from the round 2 evidence. No code change. |
| R3-11 | NIT | fresh-eyes | 3 | "T1–T8" in the test file and the BUGLOG row 362 are stale. | refuted | Those name the publish question's cases T1 to T8 (an earlier change), which are still T1 to T8. |

Notes:
- R2-1, R2-3 and R2-4 were each raised by two or three seats; R3-1 by all three.
- UNVERIFIABLE, round 3: Codex 3 (Cloudflare matching rules, the reported runs, real-terminal and Bash 3.2
  execution); melious 5, of which it asked to read `undo_again`'s worktree branch (it returns 1 at once:
  `[ "$from_github" = 0 ] || return 1`, so no false "taken off" note) and whether the push's `tee` carries
  git's error (T14 asserts it); fresh-eyes 4 (the evidence runs, Cloudflare, Bash 3.2, a real Ctrl-C).
- Not tested, accepted: a real terminal and a real Ctrl-C (T17 and T18 send TERM under `script(1)`); a real
  Cloudflare build after a retry (BUGLOG open row); the "dropped" and "maybe" messages of the retry push;
  Bash 3.2 execution of the new code (`bash -n` passes on 3.2.57 and 5.3).
- Round 3 raised no substantive BUG and no earning RISK, so no round 4 was earned. Its fixes (tests, message
  text, one added message, docs) were checked by the harness and `make check`, not by a reviewer: "last round
  not re-verified".
- Fresh-eyes is read-only (Claude Sonnet sub-agent, Explore); its findings were weighed like a seat's.
