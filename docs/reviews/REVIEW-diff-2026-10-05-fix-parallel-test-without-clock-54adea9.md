# DIFF review — branch `fix/parallel-test-without-clock` — the parallel test proves overlap by order, not by clock

Base `1a62629` · depth: Light (a test-only change: one test script, no user data, no production path) · verdict: **CLEAN** · authority used: WORKTREE-WRITE and BRANCH-COMMIT — this session's worktree, and this session created the branch; POST — this session opens the pull request; GATED-THIS-DIFF — `/code-review` saw `1a62629...54adea9` in full.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `54adea9` | full, `1a62629...54adea9` | `/code-review` at medium, host-family model (claude-opus-5-5), inline in the authoring session | ~15 s, not reported for an inline seat | 0 / 0 / 0 |

No findings. The seat checked that nothing writes `ollama-ran` before the tiers launch (`ollama list` and `ollama run --help` exit before the stub reaches its mark), that codex runs only inside its tier, and that the codex stub's removed `slow` mode had no other user.

Notes: Light is same-family by design (the owner's standing choice, 2026-09-26); no cross-model seat ran and no content left the machine. The seat ran in the authoring session, not a fresh one. Evidence beyond the review, by hand on the same head: the check fails when both tier launches lose their `&` (only this check fails); with a 3 s pause between the two launches, `origin/main`'s check fails ("took 6s") and the new one passes; the script passed alone at a load average of 16, and `make check` passed at 193–203.
