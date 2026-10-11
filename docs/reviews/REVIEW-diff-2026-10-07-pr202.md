# DIFF review — karero/website-builder#202 — SECOND_SEAT=melious: Melious in the second seat, ollama as its fallback

Base `b02c165` · depth: **Normal** (review tooling: seat dispatch and its tests; no key handling, no new
destination) · verdict: **CLEAN** · authority used: POST AUTHORITY, WORKTREE-WRITE, BRANCH-COMMIT,
atom A (this session created the branch, its worktree and the PR; the owner: "Yes" to push and open
it); GATED-THIS-DIFF, atom A (Codex and Melious glm-5.3 each hold an unbroken chain: round 1 full
`b02c165...99ec37e`, then each delta to `4288aee`); MERGE: not given.

**Data release consent:** the repo is public; Melious already reviews it (#165, #179). Seats: Codex +
Melious glm-5.3, run through this PR's own switch (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3
OLLAMA_MODEL=glm-5.3:cloud`); ollama-cloud was at its session usage limit when round 1 began.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `99ec37e` | full `b02c165...99ec37e` (15 KB) | codex gpt-6.1-sol (config effort, read-only); Melious glm-5.3 (HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only, tools, ran the suite) | codex 163 s/66,355; glm 141 s/28,695; fe 211 s | 1/4/9 |
| 2 `--verify` | `9aeaf82` | delta since `99ec37e`, with round 1's dispositions | codex (medium); Melious glm-5.3 | codex 122 s/49,493; glm 155 s/16,884 | 0/2/1 (codex clean) |
| 3 `--verify` | `4288aee` | delta since `9aeaf82`, with round 2's dispositions | codex (medium); Melious glm-5.3 | codex 41 s/25,716; glm 27 s/6,747 | 0/0/0 |

| id | Sev | Source | Rnd | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| C1 | BUG | codex | 1 | `SECOND_SEAT=gpt` exits 2 under `--seat`/`--local-only`, though the env block said they ignore it | fixed, ext. reverified | the refusal stays (a typo is caught in every mode); the env block says so; `sbadseat`, `sbadlocal` |
| C2 | RISK | codex | 1 | "credits out included" is unchecked provider behaviour | fixed, ext. reverified | the words are gone; any non-counted Melious outcome hands over |
| C3 | RISK | codex | 1 | "one run in four" in a test comment has no support in the repo | fixed, ext. reverified | deleted |
| M1 | NIT | glm | 1 | the swapped Melious attempts have no inline `MELIOUS_MODEL` gate | refuted | `run_melious` returns 3 without a model; validation exits 2 before any tier |
| M2 | NIT | glm | 1 | `SECOND_SEAT=""` is read as ollama | refuted | empty means unset, as for `CODEX_EFFORT` |
| M3 | NIT | glm | 1 | `MELIOUS_RAN` set but unread in the swapped path | fixed, ext. reverified | removed |
| F1 | RISK | fe | 1 | no test that a stop reaches the late ollama fallback | fixed, ext. reverified | ollama stub `stubborn`; `sstop`, with a mark that proves the stub was killed; a foreground-fallback mutant fails it |
| F2 | RISK | fe | 1 | the fallback starts only after Melious ends, so a slow failure delays the round | refuted | the default mode has the same shape; nothing promises otherwise |
| F3 | NIT | fe | 1 | rationale.md lacks `SECOND_SEAT` | fixed, ext. reverified | one sentence |
| F4 | NIT | fe | 1 | as C1 | fixed | C1 |
| F5 | NIT | fe | 1 | "Unset = no Melious call at all" omits the refusal | fixed, ext. reverified | added |
| F6 | NIT | fe | 1 | the no-reviewer heredoc line is terse | no change | fe: accurate as is |
| F7 | NIT | fe | 1 | the "overlap in the default parallel run" comment | refuted | codex overlaps the second seat in both modes |
| F8 | NIT | fe | 1 | test gaps: a skipped Melious, both seats failing, a reused raw dir | fixed in part, ext. reverified | `sboth`, `sreuse`; no skipped-Melious case: `melious_counted` treats every non-0 status alike, and 429 pins that path |
| R1 | RISK | glm | 2 | "refused in every mode" untested under `--local-only` | fixed, ext. reverified (r3) | `sbadlocal` |
| R2 | RISK | glm | 2 | no test that `SECOND_SEAT=melious` without a model refuses | refuted | `snomodel` (round 1, outside the round-2 delta); codex reproduced it |
| R3 | NIT | glm | 2 | `sstop`'s 5 s pid poll | refuted | the same budget as `mstop`; a timeout fails loudly |

Tests: `test_failed_tier_report.sh` passes in full and `make check` passes at `4288aee`. Mutants, one run
each, each failing only its own test: no fallback (`sfall`), Melious started after codex
(`sparallel`), `--first-success` order swapped (`sfirstsucc`), validation removed (`snomodel`,
`sbad`), a foreground fallback (`sstop`).

Waivers and deferrals: none.

Notes: round 3 was clean from both seats. The trail commit changes only `docs/reviews/`, so the
diff-scope is the one round 3 read.
