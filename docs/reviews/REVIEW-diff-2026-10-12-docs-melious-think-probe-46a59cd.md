# DIFF review — branch `docs/melious-think-probe` — R-MELIOUS-THINK measured on the two models the Melious seat may run
Base `b8daa7e` · depth: Light (one row of the open-findings tracker and this trail: prose no agent loads as instructions and no person runs) · verdict: CLEAN, two RISKs fixed · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY — none yet, no PR

Light gate, by the owner's standing rule for prose-only diffs: Codex alone, one round, one more only if it finds a BUG. It found none.

Data consent: the owner asked for this measurement on 2026-10-12 ("then this: The think-tag test on GLM 5.3 and Flash", including Flash through the new script against the real Melious). What went to Melious was a nine-line made-up plan, eight times; what went to Codex was the tracker row's diff and those plans. No secret in either; the request bodies carry no key (the script sends it as a header).

| Round | Head | Artifact | Reviewer: CLI version, model, effort, sandbox | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `46a59cd` | full: `origin/main...46a59cd`, one file, plus the two plans as context | codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only | 119 s / 50,053 | 0/2/0 |

| id | Sev | Source | Finding | Status | Evidence |
|---|---|---|---|---|---|
| T1 | RISK | Codex | The row stated a mechanism (tags not seen as typed, text missing from what the model reviewed) that the replies do not establish; one failing run's reasoning holds the word | fixed, locally_verified, not externally re-verified: the row now says what the reviews said, that the cause is not established, and that the runs neither confirm nor rule out the rewrite tried earlier | the diff |
| T2 | RISK | Codex | The measurement's support was only in files git ignores | fixed in part: the row says the eight replies are in a comment on the PR that adds it, and why the request bodies are not committed (they hold the tags, which this repo's files avoid). Open until the PR exists and the comment is posted | — |

What Codex verified against the captured runs: the counts (glm-5.3 3 of 3, glm-5.3-flash 1 of 3, both controls), that each tagged request body holds the tag pair around the word, that the saved reviews match the raw streams, and that every run ended `reviewers: melious OK`.

The measurement itself, for the record: `MELIOUS_MODEL=<model> independent_review.sh <plan> --plan --seat melious --depth <normal for glm-5.3, light for glm-5.3-flash>`, the installed script at `4e5ff23`, 2026-10-12, eight runs, 4 to 29 s and 995 to 1,845 tokens each.
