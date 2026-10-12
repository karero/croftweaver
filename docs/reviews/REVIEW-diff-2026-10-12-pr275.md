# DIFF review — PR #275 — website-tagline: an opt-in test for the line on the page
Base `6905a21`, after one merge of the base branch (`714516a`) · depth: Normal (a test that is copied into users' sites, a new CI job, and an instruction file) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened #275); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — atom A (the chain below, unbroken for Codex)

Normal gate: Codex and GLM 5.3 on melious.ai as the pair, and a fresh-eyes pass on a mid-tier host-family model in round 1.

Data check before round 1: the diff holds no key, token or password (searched for `api key`, `secret`, `token`, `passw`, `PRIVATE`; no hit). Destinations: Codex and melious.ai, as for #270 earlier in this session, where the owner approved a plan naming both; the owner then asked for this PR to be merged after being told the Normal review with the same pair came first.

Test records:
- The new CI job's three steps, read out of the workflow file as committed, run on a Mac against a fresh site built from the starter, once before round 1 and once after each set of fixes that touched the test or the job (five runs). The last, at `d0ff5ac`: 4 skipped (unconfigured); type check 0 errors, the whole suite 71 passed and 1 skipped (a correct site, with two decoys); nine times "red as expected", one per mistake; exit status 0. That log is in a comment on the PR.
- At `809bce9`, whose one change is a guard inside the test: type check 0 errors and 0 warnings, the test file 4 passed, on the same site.
- On a scratch copy, with one expected decoding changed on purpose: 1 failed, in "the line is typed once", naming the pair.
- The decoding itself, in Chromium, for eleven spellings; the list and what each returned are in round 4's record in the PR comment.
- CI on the first head `7dbc7e1`: 39 checks passed, among them `tagline-skill` (on Linux, Node 24) and `template-tests-ok`. CI on the final head is named in the PR comment.
- `make check` on a tree identical to `7dbc7e1`: exit status 0. Its output was not kept; the same guards run in CI.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `9e45a5c` | full: `origin/main...9e45a5c` without `docs/reviews/`, 5 files | codex-cli 0.162.1, gpt-6.1-sol, config.toml's effort, read-only · melious: glm-5.3, HTTP API, text only · fresh-eyes: host sub-agent, sonnet, read-only | 400 s / 81,404 · 358 s / 31,971 · 118 s / 117,788 | 3/3/6 |
| 2 | `df759ab` | delta `9e45a5c..df759ab`, with round 1's dispositions (`--verify`) | codex as above at medium · melious as above | 109 s / 32,818 · 589 s / 47,213 | 2/0/1 |
| 3 | `a7fcea3` | delta `df759ab..a7fcea3` | codex at medium · melious | 101 s / 36,410 · 475 s / 36,882 | 1/0/2 |
| 4 | `ffda4d0` | delta `a7fcea3..ffda4d0` | codex at medium · melious | 138 s / 46,230 · 311 s / 21,551 | 0/1/2 |
| confirmation, not a round | `d0ff5ac` | delta `ffda4d0..d0ff5ac`, the test file | codex at medium | 141 s / 31,446 | 1/0/0 |
| second confirmation | `809bce9` | delta `d0ff5ac..809bce9`, one guard | codex at medium | 92 s / 24,172 | 0/0/0 |
| merge link, not a round | `f749bb8` | `merge_link.sh 6905a21 809bce9 714516a`: hunks in `README.md`, all the base branch's (PR 268) | codex at medium | 109 s / 54,107 | 0/0/0 for this change; one finding on the base branch's text, below |

Round 1's count is after merging duplicates; as filed: Codex 3/2/0, melious 0/1/3, fresh-eyes 0/1/4. Round 4 was earned by B8, the BUG round 3 found.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| B1 | BUG | codex | 1 | "typed once" missed a copy written with an escaped quote | fixed — externally_reverified (round 2, both seats) | `df759ab`: a backslash before a quote is removed before the search; a CI case types the copy that way |
| B2 | BUG | codex; fresh-eyes as NIT | 1 | Characters were counted as code points, against the comment | fixed — externally_reverified (round 2) | `df759ab`: `Intl.Segmenter`, grapheme |
| B3 | BUG | codex | 1 | The job's comment said the fixture places the line as the skill's §6 says; the starter has no header | fixed — externally_reverified (round 2) | `df759ab`: the comment says where the line sits |
| R1 | RISK | fresh-eyes, codex | 1 | The job's name check matched the reporter's progress lines, so it accepted a test that passed | fixed — externally_reverified (round 2) | reproduced first; `df759ab`: only the numbered failure lines are read, and the job tests the check against a test that passed |
| R2 | RISK | codex | 1 | One fixture broke both limits | fixed — externally_reverified (round 2) | `df759ab`: nine short words, six long words, each with its message |
| R3 | RISK | melious | 1 | The placeholder in the test and the starter's value could drift apart | fixed — externally_reverified (round 2) | `df759ab`: step 1 compares them |
| N1 | NIT | fresh-eyes | 1 | The new comment sat between the last job and that job's own comment | fixed — externally_reverified (round 2) | `df759ab` |
| N2 | NIT | fresh-eyes | 1 | "typed once" was a raw substring match | fixed, reopened in part as B5 | `df759ab`: whole-word match, a decoy in the fixture |
| N3 | NIT | fresh-eyes, melious | 1 | An empty line made "typed once" list every file | fixed — externally_reverified (round 2) | `df759ab`: that test skips on an empty line |
| N4 | NIT | fresh-eyes | 1 | A tagline per language cannot be expressed | no change to the test; the skill's §7 says the test covers one line | `df759ab` |
| N5 | NIT | melious | 1 | README read as if the test were copied to every site | fixed — externally_reverified (round 2) | `df759ab` |
| N6 | NIT | melious | 1 | The QA row left out the fourth check | fixed — externally_reverified (round 2) | `df759ab` |
| B4 | BUG | codex; melious as RISK | 2 | The skill said "an HTML entity"; the test decoded eight spellings. `caused-by: B1 (partial)` | fixed in part in round 3, in full as B8 | `a7fcea3`, `ffda4d0` |
| B5 | BUG | codex | 2 | The whole-word check read half of a character outside the basic plane. `caused-by: N2 (partial)` | fixed — externally_reverified (round 3: Codex checked 97,880 such characters) | `a7fcea3`: whole characters; a second decoy |
| N7 | NIT | melious | 2 | The job held its own copy of the placeholder | fixed — externally_reverified (round 3) | `a7fcea3` |
| B8 | BUG | codex; melious as NIT | 3 | References with many leading zeros were not decoded. `caused-by: B4 (partial)` | fixed — externally_reverified (round 4, both seats) | `ffda4d0`: the decoding table is gone; the browser decodes each reference once |
| N8 | NIT | melious | 3 | `&#38;amp;` was decoded twice | fixed — externally_reverified (round 4) | `ffda4d0`: one pass |
| N9 | NIT | melious | 3 | An out-of-range reference was clamped, where HTML gives U+FFFD | fixed — externally_reverified (round 4) | `ffda4d0`: the browser's answer |
| R4 | RISK | codex, melious | 4 | What the browser decodes was shown only by one manual run | fixed — externally_reverified (confirmation) | `d0ff5ac`: nine pairs checked on every run; a changed pair turned the test red |
| N10 | NIT | melious | 4 | A malformed answer from the browser switched decoding off silently | fixed in part, in full as B9 | `d0ff5ac`, `809bce9` |
| N11 | NIT | melious | 4 | "the way it decodes them on a page" overstated | fixed — externally_reverified (confirmation) | `d0ff5ac`: "in a page's text" |
| B9 | BUG | codex | confirmation | The guard counted strings, so a missing answer made up for by an extra one passed. `caused-by: N10 (partial)` | fixed — externally_reverified (second confirmation) | `809bce9`: length, then type |

22 findings in 4 rounds and a confirmation (7 BUG, 4 RISK, 11 NIT): 21 fixed, 1 answered by a sentence in the skill. No waiver, no deferral, nothing refuted.

A fix chain, named once as the review rules ask: B1, B4 and B8 were three holes in one hand-written decoder, found in three rounds running. After the third the decoder was replaced by the real component, the browser (`ffda4d0`), and round 4 found no BUG.

Outside this change, found by the merge link: Codex reads the base branch's `README.md` (the npm installer's text, PR 268) as wrong where it says that running `npm create croftweaver` again replaces the installed skills. The host checked the installer: it keeps a working symbolic link unless `--force` is given (`packages/create-croftweaver/index.mjs`, the lines that test `isSymbolicLink()`). This change neither wrote nor touches that text; it is reported to the owner and not fixed here.

Follow-ups:
- The README sentence above.
- A site with a tagline per language (N4).
- The first full run of the job on the merged head is CI's, not a local one.

Notes:
- Rounds 2 to 4 were owed by fixes to the test and the CI job. Round 4 ran past round 3 because round 3 found B8.
- Chain for the stamp: Codex saw the full pair in round 1, each delta since up to `809bce9`, and the merge link to `f749bb8`. The melious chain ends at `ffda4d0`; the fresh-eyes chain ends at round 1, by design at Normal depth.
- The commits that write this file change nothing else; the reviewed scope is the one at `f749bb8`.
