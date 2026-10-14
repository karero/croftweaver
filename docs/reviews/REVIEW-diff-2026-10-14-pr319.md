# DIFF review — karero/croftweaver#319 — Checklist: Bot Preference Sync is `bot_preference_sync_enabled`
Base `6c4c38d` · depth: Normal (a step in a document a person and an assistant follow: the field an assistant writes; not Light, since it edits a step a person follows) · verdict: OPEN until karero/croftweaver#320 merges (B1); no other finding open. Rounds ended after round 3: its findings were re-raises and one NIT · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`. Raw reviewer output is in the pull request's review comment.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `17d0e1c` | full | Codex CLI, gpt-6.1-sol, config effort, read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, sonnet, read-only | Codex 94 s, 48,535 · Melious 47 s, 3,135 · fresh-eyes 80 s, 103,856 | 0 / 2 / 2 after merging duplicates (Codex 0/1/0, Melious clean, fresh-eyes 0/2/2) |
| 2 | `34ec2e2` | delta since round 1, as a verification round | Codex CLI, gpt-6.1-sol, medium, read-only · Melious HTTP API, glm-5.3 | Codex 44 s, 46,583 · Melious 85 s, 7,688 | 1 / 2 / 2 after merging duplicates (Codex 1/1/1, Melious 0/1/1) |
| 3 | `0b45ab8` | delta since round 2, as a verification round | the same two seats | Codex 74 s, 27,471 · Melious 111 s, 8,277 | 1 / 1 / 2: B1 and B2 again with no new evidence, B3 again, and C1 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | RISK | fresh-eyes, Codex | 1 | The row says the update call writes `bot_preference_sync_enabled`, with no support that a write is accepted | fixed, locally_verified | the paragraph says the trial set it with the Bot Management update call; the plan's "Seen in the second trial" (karero/croftweaver#320) cites the accepted PUT (T2-063) |
| A2 | RISK | fresh-eyes, Codex | 1 | How the field was set, what the refusal was, and that it was one zone are unsaid; the captures are not in the repository | fixed, locally_verified | the paragraph names the call, code 10400 and one spare domain, and points to the plan's table. The captures are committed, cleaned, as fixtures in the plan's step 6 |
| A3 | NIT | fresh-eyes | 1 | The plan still names `is_robots_txt_managed` | fixed elsewhere | karero/croftweaver#320 |
| A4 | NIT | fresh-eyes | 1 | "Only the Transform Rules call on live sites" sits above a paragraph on a Bot Management trial | fixed, locally_verified | "and the Bot Management call on one spare domain" |
| B1 | BUG | Codex | 2 | The paragraph points to "Seen in the second trial" and T2-063, which are not on this branch | open until karero/croftweaver#320 merges | the section comes with #320; this branch is brought up to date after it, and the merge link shows the section present |
| B2 | RISK | Codex | 2 | The trial's claims lack captures in the repository | refuted | re-raise of A1, A2 without new evidence; the plan keeps captures outside the repository until its step 6 commits them cleaned |
| B3 | NIT | Codex | 2 | The plan in this checkout still names `is_robots_txt_managed` | fixed elsewhere | karero/croftweaver#320, as B1 |
| B4 | RISK | Melious | 2 | A4's fix reads as exempting the Bot Management call from the read-back | fixed, locally_verified | "for every call the assistant should read each setting back" |
| B5 | NIT | Melious | 2 | "Accepts it as `false`" generalises one trial | fixed, locally_verified | "accepted it as `false`"; the trial's PUTs sent it `false` and were accepted (T2-061, T2-063) |
| C1 | NIT | Melious | 3 | "and none of them often" can read as "none of the calls were run" | fixed, locally_verified (closing edit, not externally re-verified) | "and we have not run any of them often" |

Waivers and deferrals: none.

Follow-ups: none.

Notes:
- The paragraph points to a section that karero/croftweaver#320 adds; merge #320 first.
