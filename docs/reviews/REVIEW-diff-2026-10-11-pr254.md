# DIFF review — PR #254 — buglog: two ai-seo sweep follow-ups that had no row
Base `26f304b` · depth: Light (the diff is two log rows, prose no agent loads and no person runs; Codex alone at medium effort, one round, one more after a BUG, as the owner's rule for such diffs says) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened PR #254); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — captured reviewer input against the `(base, head)` pairs below; adding the rows — atom B (the owner's "Add them", 2026-10-11)

Data consent: the owner's standing instruction names Codex for correctness review. The artifact is a public diff of two log rows. Nothing was sent to melious or ollama (Light gate).

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `7a86066` | full: `26f304b...7a86066`, 1 file | codex-cli 0.162.0, gpt-6.1-sol, medium, read-only, cwd the worktree | codex 92 s / 39,458 | 1/0/0 |
| 2 | `819dc7a` | delta `7a86066..819dc7a`, 1 file | codex medium, read-only | codex 47 s / 41,392 | 0/0/0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex | 1 | The second row put "Where to Start" under `skills/ai-seo/SKILL.md`; it is in `references/platform-ranking-factors.md` | fixed, externally_reverified (r2) | `819dc7a`: the anchor moved into the reference file's parenthesis; round 2 confirmed the path and the line |

1 finding (1 BUG): fixed. No waiver, deferral or follow-up. Verified by Codex against the tree: both test names and all six line numbers, the 4.93 s run against the #249 record, and each place the Bingbot and Copilot advice is marked unchecked.

Waivers and deferrals: none.

Follow-ups: none from this gate. The Microsoft claims themselves stay UNVERIFIABLE; that is what the second row logs.

Notes: Light gate, so no pair and no fresh-eyes seat; the owner's rule names the diff kinds it covers and sends a found BUG to a second round, which is how round 2 ran. Codex called the brief's scope sentence prompt injection (low); it is the author's own and was treated as data. The claims sweep ran before round 1.
