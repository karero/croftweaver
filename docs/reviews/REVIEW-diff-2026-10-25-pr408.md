# DIFF review — karero/croftweaver#408 — Pages or Workers: timing trial step, sources re-checked

Base `13b61bde` · depth: Normal (adds a command to steps a person follows, so not Light; no High-row item) · verdict: CLEAN · authority used: POST AUTHORITY, WORKTREE-WRITE, BRANCH-COMMIT — atom A, this session created the PR, the worktree and the branch; GATED-THIS-DIFF — atom A, the chain below

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `7d89b3ee` | full, base `13b61bde`; evidence 4,499 bytes | codex-cli 0.164.0 gpt-6.1-sol (config effort, read-only); melious glm-5.3 (HTTP API, text only); fresh-eyes sonnet sub-agent (read-only) | codex 98 s, 32,030; melious 79 s, 10,285; fresh-eyes 42 s, 99,018 | 2 / 1 / 4 |
| 2 | `13791fcd` | delta since `7d89b3ee`; evidence 9,122 bytes | codex (medium), melious glm-5.3 | codex 390 s, 33,508; melious 110 s, 16,082 | 1 / 1 / 0 |
| 3 | `8ff118b0` | delta since `13791fcd`; evidence 11,134 bytes | codex (medium), melious glm-5.3 | codex 521 s, 29,249; melious 48 s, 9,415 | 0 / 0 / 1 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex; fresh-eyes RISK; glm NIT | 1 | A failed or non-200 run counted as a timing sample | fixed `13791fcd`, completed by F8 (locally_verified, externally_reverified r3) | 404, no-DNS (000) and redirect URLs each exit 1 with the message |
| F2 | BUG | codex; fresh-eyes NIT | 1 | "Median" was the 10th of 20 values | fixed `13791fcd`: 21 runs, 11th value (locally_verified, externally_reverified r2) | stub 1..21 prints 11; codex reproduced |
| F3 | RISK | codex, glm, fresh-eyes | 1 | "Every claim still matched" was wider than the evidence | fixed in evidence A2: raw-copy lines for every other Cloudflare fact (externally_reverified r2, glm) | address shapes, build variables, 404 setting, 307, limits, DNS, branch control, matrix rows |
| F4 | NIT | glm | 1 | "(TTFB)" label did not match the post-handshake figure | fixed `13791fcd` (externally_reverified r2) | label removed |
| F5 | NIT | glm | 1 | Re-check date implied the kit was re-read | fixed `13791fcd` (externally_reverified r2) | "(not read again on 2026-10-25)" |
| F6 | NIT | fresh-eyes | 1 | A cold first run could skew the figure | refuted | one slow run moves the median of 21 by at most one rank; codex reproduced (r2, r3) |
| F7 | NIT | fresh-eyes | 1 | Awkward wrap in the header | fixed `13791fcd` (externally_reverified r2) | reflowed |
| F8 | BUG | codex; glm NIT | 2 | curl's exit code was ignored: a 200 then a failed transfer counted | fixed `8ff118b0`: `%{exitcode}` as field 2, bad on non-zero (locally_verified, externally_reverified r3) | forced 200-then-abort (`--max-filesize`, "200 56") exits 1; stub with one exit-18 row exits 1; good URL exits 0 in zsh and bash |
| F9 | RISK | codex | 2 | No evidence for "plain files are free and run no code" | fixed in evidence A3 (externally_reverified r3, glm) | binding, billing and Pages Functions pricing pages quoted |
| F10 | NIT | glm | 3 | `%{exitcode}` needs curl 7.75.0 or later, not said | fixed after round 3 (locally_verified; wording pass) | sentence added after the block; man curl: "Added in 7.75.0" |

UNVERIFIABLE entries: round 1, 5 asked (codex 3, glm 2), 1 confirmed (folded into F3); round 2, 6 asked, 0 confirmed; round 3, 4 asked, 0 confirmed. All concern the vendor pages, the live runs and the check logs, which the text-only seat could not open.

Waivers and deferrals: none.

Follow-ups: none.

Notes: the evidence files (raw-copy greps of Cloudflare's pages fetched 2026-10-25, the command's test runs, the check logs) stayed local and were sent with each round. Round 3 was clean (a2); F10 was fixed without another round. `make check` passed on `7d89b3ee`; `scripts/check_clean.sh` passed on `8ff118b0`.
