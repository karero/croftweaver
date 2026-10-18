# DIFF review — branch feat/wordpress-redirects — wordpress-inspector writes a move's redirects (make_redirects.py) and checks them against the decisions (check_move.py --moves)
Base `89f965b5` · depth: Normal (shipped code; no auth, payments, personal data or deploy) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A: this session created the worktree and the branch

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `d83746cb` | full, since `89f965b5` | Codex gpt-6.1-sol (config effort, read-only); GLM 5.3 on melious; fresh-eyes Claude Sonnet (read-only, ran 58 mutants on a copy) | 286 s 94,997; 339 s 48,122; 734 s 164,453 | 5/6/6 |
| 2 | `821a6fe2` | delta since `d83746cb` | Codex (medium); GLM 5.3 | 160 s 58,247; 596 s 60,934 | 2/3/5 |
| 3 | `ffe2b82a` | delta since `821a6fe2` | Codex (medium); GLM 5.3 | 138 s 67,979; 484 s 46,080 | 1/1/4 |
| 4 | `9cbeeea6` | delta since `ffe2b82a` | Codex (medium); GLM 5.3 | 131 s 51,631; 292 s 22,858 | 1/1/3 |
| re-gate | `94f5d183` | delta since `9cbeeea6` (the owner-decided H1 fix and the H3–H5 test NITs) | Codex (medium) | 91 s 43,178 | 0/1/0 |
| wording | `94f5d183` + the release-note row | the row only | Codex (medium) | 86 s 51,380 | 0/0/0 |
| merge link | `d3b20404` (merge of origin/main `9ce0f906`; BUGLOG conflict resolved by keeping both sides' rows) | `merge_link.sh 89f965b5 598e4fd4 9ce0f906`: README.md and docs/BUGLOG.md only | Codex (medium) | 78 s 55,008 | 0/0/0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| D1 | BUG | Codex | 1 | `--moves` took the first of two conflicting rows; loops passed | fixed, externally_reverified r2 | `gather()` shared; `test_a_sheet_with_two_decisions_for_one_page_or_a_loop_stops_the_run` |
| D2 | BUG | Codex | 1 | a redirect to another port compared as the decided path | fixed, externally_reverified r3 | `observed()` compares origins; the test fails against the old comparison (mutant run) |
| D3 | BUG | Codex | 1 | a line break in a quoted cell was joined into a valid path | fixed, externally_reverified r2 | `csv.reader(io.StringIO(text, newline=""))`; `test_a_line_break_inside_a_cell_is_not_understood` |
| D4 | BUG | GLM | 1 | `KeyError` when a missing address appeared twice | fixed, externally_reverified r2 | `test_the_same_missing_address_twice_is_a_finding_not_a_crash` |
| D5 | BUG | fresh-eyes | 1 | `SENT_HOME_REASON` used by one script only | fixed, externally_reverified r2 | check_move's sent-home rows carry it; asserted in `TheHomePage` |
| D6 | RISK | fresh-eyes | 1 | tracebacks exit 1 (bad address, unwritable output) | fixed, externally_reverified r2 | exit 2; tests |
| D7 | RISK | fresh-eyes | 1 | `/search -> /search?lang=de` written | fixed, externally_reverified r2 | refused as "cannot be written"; test |
| D8 | RISK | fresh-eyes | 1 | 12 kinds of mutant survived the tests | fixed, externally_reverified r2 | a test per kind (listed in the round 2 prior-findings) |
| D9, D10, E5, G2, H2 | RISK | Codex, GLM | 1–4 | Cloudflare's matching, slash forwarding and query handling unverifiable in the repo | refuted | limits cited from Cloudflare's docs next to the constants; matching measured with read-only curl on two live kit sites, 2026-10-18 (slash exact, case exact, `%5F` not decoded, `/page/` → 308 `/page`, a rule matches whatever the query and passes it on). The site names are on `scripts/.clean-denylist`; the measurements are recorded in the private feature tracker. Re-raised without new evidence |
| D11 | RISK | GLM | 1 | `StopIteration` arm dead | refuted | `read_addresses` calls `next()` over `reader.fieldnames` |
| D12–D17 | NIT | GLM, fresh-eyes | 1 | `--site` with `--draft`/without `--moves`; header heuristic; off-site slash conflict; chain to a self-move; credentials and query escaping; line numbers | fixed (D13 refuted: the rule `read_addresses` already uses), externally_reverified r2 | tests |
| E1 | BUG | Codex | 2 | `/a\nb` in an old address became `/ab` | fixed, externally_reverified r3 (superseded by G1's cut) | test |
| E3 | BUG | Codex | 2 | check_move crashed on a malformed address in the list (outside scope, old code) | fixed, externally_reverified r3 | exit 2; test |
| E4 | RISK | GLM | 2 | the two sides of `--moves` escaped a query differently | fixed, externally_reverified r3 | `escaped()` shared; test |
| E6–E8 | NIT | GLM | 2 | loop through a query; unread rows dropped; dead guard | fixed, externally_reverified r3 | tests |
| E9, E10 | RISK, NIT | GLM | 2 | slash and escape case in `--moves` | refuted | `page_form` drops the slash and uppercases escapes |
| G1 | BUG | GLM | 3 | control characters guarded for the old address only | fixed by a cut, externally_reverified r4 | the rule moved into `ask_of`, the one entry point for every address |
| G3–G6 | NIT | Codex, GLM | 3 | overflow line; docstring; strictness comment; dead test branch | fixed, externally_reverified r4 | — |
| H1 | BUG | Codex | 4 | a plain-text list split one address in two on a vertical tab (`splitlines`); a trailing tab trimmed | first part fixed (the owner's decision), locally_verified, externally_reverified by the re-gate; trailing trim refuted (cells are trimmed by design) | `94f5d183`; the test fails against `splitlines` (mutant run) |
| H3–H5 | NIT | GLM | 4 | stub parses twice; query appended with `?`; other-port test could hit 65536 | fixed, externally_reverified by the re-gate | `94f5d183` |
| I1 | RISK | Codex | re-gate | the test stub joins an incoming query to a target that has its own with `&`; unmeasured on Cloudflare | follow-up | no test sends a query to a rule whose target has one, so the branch is unexercised |

Waivers and deferrals: none. The owner, 2026-10-18, on H1: "Fix it now (Recommended)".

Follow-ups: I1 (measure Cloudflare's `Location` for a query sent to a rule whose target has its own query, then match the stub to it). The first real WordPress move is the first real-host run (`%c3%bc` against `%C3%BC` is still unmeasured).

Notes:
- Round 4 was earned by round 3's BUG G1 (`--earned-by control-characters`); `--cut`: per-reader checks replaced by one strict rule in `ask_of`.
- Round 4's BUG H1 was the same kind after its cut, so patching stopped and the owner decided; no round 5.
- Tests: 180 pass on Python 3.9.6 and the default; `make check` passes, before and after the merge of origin/main.
- The plan passed its own PLAN gate (5 rounds and a final full read), recorded in the private tracker.
