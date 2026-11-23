# DIFF review — bug sweep 4 of 2026-11-23 (three BUGLOG rows)

Base `738a8aa2` (origin/main) · depth: Normal (shipped scripts, so not Light) · seats: Codex alone (REVIEW-RULES; no
High-row topic) and a fresh-eyes sub-agent (Claude Sonnet, read-only, round 1) · made by a sub-agent of the Croftweaver
manager's session. Artifact per round: the diff against the base (round 1) or since the last reviewed head (rounds 2 and
3, `--verify`), with the brief as evidence.

Rows fixed: `run_agy` with a failing `mktemp` (2026-10-09), the base check's failed-fetch refusal (2026-10-23),
`diff_headers.pl` text after the last hunk (2026-10-25).
Rows left: `codex_tokens()` (2026-11-08: deferred by the owner; where the footer may sit is a heuristic choice) and
`melious_stream.pl` balance code (2026-10-27: the row says fix if one turns up, with a capture; none exists, so the
reply's shape would be guessed).

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex (base `738a8aa2`, head `a6409a60`); fresh-eyes | 2 / 0 / 0 (Codex); 0 / 2 / 2 (fresh-eyes) | a fake `From <sha>` line after a record hid prose; a test comment contradicted bash 5 |
| 2 | Codex (`--verify`, base `a6409a60`, head `cf94859e`) | 2 / 0 / 0 | the comment still wrong for bash 3.2; prose after a `-- ` signature passed |
| 3 | Codex (`--verify`, base `cf94859e`, head `87f86c14`) | 1 / 0 / 0 | the version line after a signature took any parenthesised prose; a second signature reset the state |
| 4 | Codex (`--verify`, base `87f86c14`, head `aff015d1`; manager's session, `--earned-by diff-tail-parsing`) | 1 / 0 / 0 | the manager's `\S*` (kept for Git for Windows) let prose with no spaces through |
| 5 | Codex (`--verify`, base `aff015d1`, head `ca1b3f20`; `--earned-by diff-tail-parsing --cut`) | 0 / 0 / 0 | clean; Codex ran 14 parser checks through `parse()` |

Tokens and time: round 1 Codex 53,399 (137 s); round 2 41,552 (85 s); round 3 40,429 (87 s); round 4 38,366 (56 s); round 5 32,955 (64 s); fresh-eyes 117,219 tokens
(79 s). Codex alone (REVIEW-RULES); the script's warning that the standard pair was not met applies.

## Findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | BUG | Codex | a `From <40 hex> ` line after a record opened a message block that swallowed the prose after it | fixed: such a line counts only outside a record; test T3p fake From |
| R1-02 | BUG | Codex | test comment said agy would run in the caller's folder; false under bash 5 (`cd ""` fails) | fixed with R2-01 |
| R1-03 | RISK | fresh-eyes | a mailer that strips the signature's trailing space, or CRLF, now refuses after the last hunk | not fixed: rare, loud, names `--evidence` |
| R1-04 | RISK | fresh-eyes | the fetch error, now whole, may carry a remote URL | not fixed: git hides credentials in URLs it prints; cut at 400 characters |
| R1-05 | NIT | fresh-eyes | control characters other than newline and tab are not stripped from the fetch error | not fixed |
| R2-01 | BUG | Codex | the comment was wrong for bash 3.2 (`cd ""` succeeds there) | fixed: comment names both shells |
| R2-02 | BUG | Codex | after a signature line a `From` line plus prose passed | fixed: only a version line may follow a signature; a `From` after records of a non-mailbox diff is refused; tests t3s, t3t, control t3u |
| R3-01 | BUG | Codex | the version line took any parenthesised prose; a second signature reset the state | fixed: a second signature is refused; tests t3v, t3w, controls t3x (Apple), t3y (Windows); reverting the Perl failed t3v and t3w |
| R4-01 | BUG | Codex | `\S*` after the version accepted `2.43.0(Reviewer-note:…)` | fixed: the line is digits and dots, then optionally `.windows.N`, then optionally ` (Apple Git-N)`; test t3z. A git release candidate's line (`2.47.0.rc1`) is now refused: rare, loud, names `--evidence`. A real `git format-patch` signature from git 2.54.0 (Apple Git-157) passes |

Test evidence: with the three fixes reverted, T3p (3 checks), T5's new cause check and `agynomktemp`'s naming check failed
(that case's "agy never ran" check passes before the fix under bash 5, where `cd ""` fails); with R1-01 reverted the fake
From case failed; with R2-02's Perl reverted t3s and t3t failed. All restored and passing (`test_base_check.sh` PASS,
`test_failed_tier_report.sh` all checks passed up to round 1's head). Claims about those runs were UNVERIFIABLE for a
read-only seat. The suites of round 3's head other than `test_base_check.sh` were not run again.
Rounds 4 and later ran in the manager's session, which also re-ran every suite listed above on head `e256cb2f` (all exit 0).
