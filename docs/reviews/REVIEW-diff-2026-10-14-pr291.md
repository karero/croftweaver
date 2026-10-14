# DIFF review — karero/croftweaver#291 — BUGLOG: two rows from the review of PR 281

Base `034472d` · depth: Light (two rows in the bug log, prose no agent follows; Codex alone, one round and one more after a BUG) · verdict: CLEAN · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `6ceae76` | full (6,094 bytes) | Codex: codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only sandbox | 184 s, 53,101 tokens | 2 / 0 / 0 |
| 2 | `171043e` | delta since `6ceae76` (7,235 bytes), round 1's findings as `--verify` | the same | 148 s, 44,396 tokens | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| L1 | BUG | Codex | 1 | the facts-check row said entities "expand without end"; nested entities grow enormously but finitely, a recursive one is refused | fixed, externally_reverified (round 2) | the row now says a few hundred bytes grow into gigabytes and names expat 2.4.0 (CVE-2013-0340) for the limit |
| L2 | BUG | Codex | 1 | the same row said the new skill's reader stops at "its document-type event", leaving out its one exception | fixed, externally_reverified (round 2) | the row names the exception (an html document type that declares nothing, read past to the first element; PR 281 trail row F56) and why the facts check needs none |

Waivers and deferrals: none.

Follow-ups: none. Round 2 left two UNVERIFIABLE entries as questions: the gigabyte scale (the mechanism was reproduced, not a gigabyte run) and "normally the owner's own site" behind the row's low impact, which is a judgment the row states.

Notes: Light gate as the owner's standing rule allows for prose no agent follows; both findings were wording, so the change stayed Light.
