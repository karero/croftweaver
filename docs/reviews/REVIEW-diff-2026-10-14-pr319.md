# DIFF review — karero/croftweaver#319 — Checklist: Bot Preference Sync is `bot_preference_sync_enabled`
Base `6c4c38d` · depth: Normal (a step in a document a person and an assistant follow: the field an assistant writes; not Light, since it edits a step a person follows) · verdict: OPEN, round 2 under way · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`. Raw reviewer output is in the pull request's review comment.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `17d0e1c` | full | Codex CLI, gpt-6.1-sol, config effort, read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, sonnet, read-only | Codex 94 s, 48,535 · Melious 47 s, 3,135 · fresh-eyes 80 s, 103,856 | 0 / 2 / 2 after merging duplicates (Codex 0/1/0, Melious clean, fresh-eyes 0/2/2) |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | RISK | fresh-eyes, Codex | 1 | The row says the update call writes `bot_preference_sync_enabled`, with no support that a write is accepted | fixed, locally_verified | the paragraph says the trial set it with the Bot Management update call; the plan's "Seen in the second trial" (karero/croftweaver#320) cites the accepted PUT (T2-063) |
| A2 | RISK | fresh-eyes, Codex | 1 | How the field was set, what the refusal was, and that it was one zone are unsaid; the captures are not in the repository | fixed, locally_verified | the paragraph names the call, code 10400 and one spare domain, and points to the plan's table. The captures are committed, cleaned, as fixtures in the plan's step 6 |
| A3 | NIT | fresh-eyes | 1 | The plan still names `is_robots_txt_managed` | fixed elsewhere | karero/croftweaver#320 |
| A4 | NIT | fresh-eyes | 1 | "Only the Transform Rules call on live sites" sits above a paragraph on a Bot Management trial | fixed, locally_verified | "and the Bot Management call on one spare domain" |

Waivers and deferrals: none.

Follow-ups: none.

Notes:
- The paragraph points to a section that karero/croftweaver#320 adds; merge #320 first.
