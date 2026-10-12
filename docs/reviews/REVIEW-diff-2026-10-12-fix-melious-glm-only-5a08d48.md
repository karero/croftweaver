# DIFF review — branch `fix/melious-glm-only` — the Melious seat refuses every model its list does not allow
Base `896e3c5` · depth: Normal (the diff changes the logic of the gate script and of a check script, and an instruction file agents load) · verdict: CLEAN for artifact 2 at head `5d7b4dd`, with one RISK waived by the owner (A1) and nothing open; artifact 1 stopped after round 5 and was replaced (the owner's decisions, below) · authority used: WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); POST AUTHORITY — none yet: no PR, and the owner's task says not to push or open one without his OK

Data consent: the owner's task for this change (2026-10-12) names the gate: "the review gate is Normal at least (Codex + GLM 5.3 on melious via the independent-review skill)". The repo is public. A grep of the round-1 artifact for keys, tokens, passwords and secrets found only the tests' stub values (`stub-msecret`, `stub-stopkey`, `real-curl-key`). ollama-cloud received nothing (Melious counted in all five rounds); Antigravity was not used. The script was run from this worktree (`grep -c SECOND_SEAT` found 16), so each round also exercised the changed script with the allowed model.

## Artifact 1 — the model's name in the script, with an exception in the model-name check (replaced)

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `5a08d48` | full: `origin/main...5a08d48`, 7 files (docs/reviews excluded), plus unchanged source excerpts marked as context for the text-only seat | codex-cli 0.162.1, gpt-6.1-sol, effort high (config.toml), read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction | codex 327 s / 90,507; melious 290 s / 49,587; fresh-eyes 157 s / 133,123 | 2/2/5 after dedup |
| 2 | `fe47e13` | delta `5a08d48..fe47e13`, `--verify` with round 1's dispositions | codex as above at effort medium; melious glm-5.3 | codex 180 s / 46,052; melious 283 s / 24,928 | 2/0/0 new; F9 re-raised |
| 3 | `467e658` | delta `fe47e13..467e658`, `--verify` | same pair | codex 233 s / 55,066; melious 405 s / 35,343 | 1/1/2 |
| 4 | `f9806ae` | delta `467e658..f9806ae`, `--verify` | same pair | codex 200 s / 45,722; melious 272 s / 29,185 | 1/0/2 |
| 5 | `f135570` | delta `f9806ae..f135570`, `--verify` | same pair | codex 277 s / 47,351; melious 344 s / 31,216 | 1/0/2 |

In all: 5 rounds, 21 findings (7 BUG, 3 RISK, 11 NIT). Every BUG is in `scripts/check_model_agnostic.sh`'s let-through for the model name; none is in the refusal in `independent_review.sh`, which Codex and GLM confirmed in each round.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex; fresh-eyes as RISK | 1 | The let-through's second pass piped the filter into grep: a filter that died read as a clean scan | fixed `fe47e13`, locally_verified, externally_reverified (rounds 2 to 5) | A perl wrapper that works for the self-test and then exits 1: the fixed script prints its filter-failure FAIL; round 1's printed OK |
| F2 | BUG | Codex; GLM as NIT | 1 | "Bare id only" was false: `glm-5.3._preview`, `..preview`, `+flash`, `/latest`, `~x` passed | fixed `fe47e13`, externally_reverified (round 2). Invariant: only the bare id passes; variants in the self-test's bad list | the self-test |
| F3 | RISK | GLM | 1 | The let-through applied anywhere in the skill, so the same id as another seat's default would pass | fixed in part `fe47e13`; superseded by G1 and G2 | — |
| F4 | NIT | GLM, fresh-eyes | 1 | A second check inside `run_melious` could not fire, and returned 1 where the rule calls for a stop | fixed `fe47e13` (removed), externally_reverified | section 32c still passes |
| F5 | NIT | GLM | 1 | Section 32c uses `kimi-k3`, a real model name the check's pattern cannot see | refuted | The owner's task names that value; `git grep -n kimi-k3 896e3c5 -- skills/independent-review` finds it in two scanned files on the base (Codex ran it in rounds 2, 4 and 5) |
| F6 | NIT | fresh-eyes, GLM | 1 | A prose colon after the id is flagged | fixed by saying so in the comment and pinning it in the self-test | — |
| F7 | NIT | fresh-eyes | 1 | `SKILL.md`: an over-long line in the Independence rule | fixed `fe47e13` | — |
| F8 | NIT | fresh-eyes | 1 | `README.md`: the exception read as part of the next clause | fixed `fe47e13` | — |
| F9 | RISK | Codex (as UNVERIFIABLE), re-raised each round | 1 | The one model the seat may run has no measurement of how Melious hands it a prompt holding think tags (tracker row R-MELIOUS-THINK measured three models the seat now refuses) | OPEN, for the owner: the tracker row says so (`fe47e13`); the probe needs a direct call to Melious this session may not make | `OPEN-FINDINGS-independent-review.md`, R-MELIOUS-THINK |
| G1 | BUG | Codex; GLM as NIT | 2 | Scoped to lines that name Melious, the let-through hid `OLLAMA_MODEL=glm-5.3` on a line that also set `MELIOUS_MODEL` | fixed `467e658` (one shape: the value of a named variable), externally_reverified (round 3). caused-by: F3 (partial) | reproduced on `fe47e13`; bad list |
| G2 | BUG | Codex | 2 | The `file:line:` prefix parser rejected spaces, so a file name holding "melious" counted as text | fixed `467e658` (no prefix parsing), externally_reverified. caused-by: F3 (partial) | reproduced on `fe47e13`; bad list |
| H1 | BUG | Codex | 3 | A quote after the value passed: `MELIOUS_MODEL=glm-5.3"-flash"` | fixed `f9806ae`, externally_reverified (round 4). caused-by: G1 (introduced) | reproduced on `467e658`; bad list |
| H2 | RISK | GLM | 3 | The let-through keyed on any `MELIOUS_` variable name | fixed `f9806ae` (three named variables), externally_reverified | bad list |
| H3 | NIT | GLM | 3 | Comment: "what the file is called never matters" overstated | fixed `f9806ae` | — |
| H4 | NIT | GLM | 3 | Three copies of the name must change together | fixed `f9806ae` (comments name each other) | — |
| J1 | BUG | Codex | 4 | A backtick after the value passed, and bash reads ``MELIOUS_MODEL=glm-5.3` printf -- -flash` `` as `glm-5.3-flash` | fixed `f135570` (no punctuation tail; two exact shapes); the cited case externally_reverified (round 5), the wider claim not (K1). caused-by: H1 (partial) | reproduced on `f9806ae`, with `bash -c` |
| J2 | NIT | GLM | 4 | Any non-word character could stand before the variable | fixed `f135570`; K2 says a colon still can | bad list |
| J3 | NIT | GLM | 4 | `independent_review.sh`: "two more places" undercounted | fixed `f135570`, externally_reverified | — |
| K1 | BUG | Codex | 5 | The space-or-end shape also matches inside a backtick command: `` `echo MELIOUS_MODEL=glm-5.3 x` `` is hidden, against the comment's "whole content of one pair of backticks" | OPEN. caused-by: J1 (partial) | not yet reproduced by the author |
| K2 | NIT | Codex, GLM | 5 | Any colon before the variable passes, not only grep's prefix | OPEN | — |
| K3 | NIT | GLM | 5 | A single quote or `(` before the assignment is flagged, which over-fires on ordinary shell lines | OPEN | — |

Waivers and deferrals: none.

Notes:
- Stopped: not converging, on the let-through alone. F3, G1, H1, J1, K1 are one chain: each fix to the pattern exposed the next shape. Five rounds; rounds 4 and 5 were earned by H1 and J1. The open items go to the owner as one decision.
- The requirement moved during the gate: the owner's instructions (his `~/.claude` commit `86cb4eb`, 2026-10-12 11:54 CEST) now allow GLM 5.3 Flash on Melious in a Light review. The branch refuses it in every mode. Also for the owner's decision.
- Melious's reply in round 1 came with its final-review marker at the end, so the script printed the whole reply with its "no usable marker" notice; it reads as a finished review and was counted.
- Codex could not run the check script or the test file in its sandbox (here-strings need temp files); it ran their cases through pipes. The author's full runs (`make check`: exit 0, 1062 ok lines, at each head) are not externally reproduced.
- Raw reviewer output of these five rounds: not posted (no PR); copies are kept as the last note of artifact 2 says.

## The owner's decisions, 2026-10-12, after artifact 1's round 5

Asked in this session with the round-5 state and the changed rule in front of him; his answers, as he picked them:
- Where the list of models Melious may run lives: "List file in the repo (Recommended)". The option read: one short file inside the review skill lists the allowed models, the script reads it and refuses the rest, and the check skips that one file, the way it already skips the setup guide.
- How the script treats GLM 5.3 Flash, which his instructions allow in a Light review since that day: "Only with --depth light (Recommended)". The option read: with normal, high, or no depth stated, it is refused.
- F9, the missing think-tag measurement: "Accept for now, keep it listed (Recommended)". This is the waiver for F9 on this change; the tracker row R-MELIOUS-THINK stays open and says so.

So artifact 1's let-through is gone and K1, K2 and K3 with it: `scripts/check_model_agnostic.sh` is the base's file plus one more exact-path exclusion, and no file it scans holds a model's name. Artifact 2 is a new artifact with a new round count.

## Artifact 2 — the allowed models in `scripts/melious_models.txt`, a light-only mark, the check skips that file

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `91e58fe` | full: `origin/main...91e58fe`, 8 files (docs/reviews excluded), plus unchanged source excerpts marked as context for the text-only seat | codex-cli 0.162.1, gpt-6.1-sol, effort high (config.toml), read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction | codex 301 s / 96,067; melious 328 s / 53,069; fresh-eyes 322 s / 149,448 | 2/4/5 after dedup |
| 2 | `99e4e53` | delta `91e58fe..99e4e53`, `--verify` with round 1's dispositions | codex at effort medium; melious glm-5.3 | codex 133 s / 62,579; melious 282 s / 28,918 | 0/1/2 |
| not a round: the closing edits, and the tracker row | `7ec02a6` | delta `99e4e53..7ec02a6` plus this change's diff of `OPEN-FINDINGS-independent-review.md`, `--verify` | same pair | codex 119 s / 58,579; melious 268 s / 21,668 | 0/1/0 |
| not a round: confirmation of C1's fix | `5d7b4dd` | delta `7ec02a6..5d7b4dd`, `--verify`, `--seat codex` | codex at effort medium | codex 111 s / 37,966 | 0/0/0 |

Artifact 2: 2 rounds, 15 findings (2 BUG, 6 RISK, 7 NIT). One BUG was a README sentence; the other was refuted, and both seats confirmed the refutation in round 2. The whole gate, both artifacts: 7 rounds, 36 findings.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | RISK | Codex | 1 | Neither listed model has a measurement of how Melious hands it a prompt holding think tags (it is F9 again) | waived by the owner (below); tracker row R-MELIOUS-THINK stays open | — |
| A2 | BUG | Codex | 1 | `README.md` said the skill is free of concrete model names outside two files; the tests hold `kimi-k3`, which the check's pattern does not see | fixed `99e4e53` as wording (the README now says what the pattern covers), externally_reverified (round 2). The literal stays: the owner's task names it, and it is in two scanned files on the base | `git grep -n kimi-k3 896e3c5 -- skills/independent-review` |
| A3 | RISK | Codex | 1 | The refusal tests compared a sentence naming every listed model, so a longer list would fail them | fixed `99e4e53`, externally_reverified | Codex reproduced the substrings on a longer list |
| A4 | BUG | GLM | 1 | The gate would refuse a Light run because the parser "stores the whole token `--depth:light`" | refuted; both seats confirmed in round 2 | `case "$a:$1" in --depth:light\|…) DEPTH="$1"`: the colon is only in the string matched on. Tests `lseat`, `lsecond` (run at `--depth light`), `lnormal`, `lhigh` (refusal text) pass. GLM had been shown one arm of the parser, not the `case` line |
| A5 | RISK | GLM | 1 | The two-word form `--depth light` may have no parser branch | refuted, as A4 | — |
| A6 | RISK | GLM | 1 | Nothing shows that Melious serves the two ids | fixed in part `99e4e53`, then corrected by B1 | the any-depth id answered in every round of this gate |
| A7 | NIT | GLM | 1 | An id listed as `light` and again bare was named twice in the refusal | fixed `99e4e53`, externally_reverified | test `ltwice` |
| A8 | NIT | fresh-eyes | 1 | The sentence about Kimi and ollama ended every refusal, also where it did not fit | fixed `99e4e53`, externally_reverified | test `lnodepth` |
| A9 | NIT | fresh-eyes | 1 | A test comment overstated what the check keeps out | fixed `99e4e53` | — |
| A10 | NIT | fresh-eyes | 1 | Two over-long lines | fixed `99e4e53` | — |
| A11 | NIT | fresh-eyes | 1 | Nothing said the script cannot check that a review is Light | fixed `99e4e53` (setup guide) | — |
| B1 | RISK | Codex | 2 | The list's header claimed both ids "answered on Melious on 2026-10-12" with no record, least for the light-only id | fixed `7ec02a6` (the sentence is gone), externally_reverified | — |
| B2 | NIT | GLM | 2 | An id with a glob character would match another id already seen | refuted; Codex confirmed | `bash -c` on the pattern prints `kept`; test `lglob` (after C1) |
| B3 | NIT | GLM | 2 | `ltwice` covered one order only | fixed `7ec02a6` (`ltwice2`), externally_reverified | — |
| C1 | RISK (GLM), NIT (Codex) | both | closing edits | `lglob` as first written could not fail: its wildcard stood in the id already seen | fixed `5d7b4dd`, externally_reverified (Codex's confirmation) | With the id unquoted in a scratch copy, the test file fails on `lglob` alone |

Waivers and deferrals: A1 (and F9 of artifact 1), the missing think-tag measurement: waived for this change by the owner on 2026-10-12, in this session, with the risk described to him: "Accept for now, keep it listed (Recommended)". No deferral.

Follow-ups: none.

Notes on artifact 2:
- Stop (a2) after round 2: no BUG and no RISK that called for a change to what runs. The closing edits held a test hunk, so they were read once by the pair instead of going to a prose-only pass; that read's one finding (C1) got one confirmation from Codex.
- Seen pair: base `896e3c5`, head `5d7b4dd`. Codex holds an unbroken chain to that head; GLM's ends at `7ec02a6`; fresh-eyes' at round 1, by design. `origin/main` has since moved to `e58d3ae` (PR #264), which touches none of this change's files; the merge-base is unchanged.
- Author's runs at `5d7b4dd`: `make check` exits 0 with 1094 ok lines. It skips, here as on the base, the Perl minimum-version check (no Perl::MinimumVersion on this machine; CI runs it) and six pre-push-hook cases that need `/proc`. With the startup check cut from a scratch copy, 28 checks of sections 32c to 32e fail.
- Codex could not run the test file or the check script in its sandbox (they write temp files) and ran their cases through pipes instead; the full runs above are the author's.
- Raw reviewer output: not posted (no PR yet). Copies of every round's output and prior-findings file are in this worktree under `docs/local/review-raw-fix-melious-glm-only/`, which git ignores.

