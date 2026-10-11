# DIFF review — PR #255 — AGENTS.md template: the assistant merges when the person says "merge"
Base `78ead07` · depth: Light, named by the owner's message "Do a light review" (2026-10-09); the diff holds instruction files agents load (`AGENTS.md` template, `website-team-setup/SKILL.md`), which the owner's rule sends to Normal at least, so a depth named in the owner's own message is what put it at Light; Codex alone at medium effort, one round, one more after a BUG, then one wording pass on the last commit · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened PR #255); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — captured reviewer input against the `(base, head)` pairs below; push and PR — atom B (the owner's "Yes to" the four steps, 2026-10-11)

Data consent: the owner asked for a light review in this session, and his standing rule for Light names Codex alone; no quoted "OK" for Codex was asked for in this session. The artifact is a public diff of three public text files. Nothing was sent to melious or ollama (`--seat codex`).

Heads below are as reviewed. The first commit's message was reworded afterwards (it still named the dropped Codex-cloud claim), which changed all three SHAs; the tree is identical (`5af48e5`). Before round 1 the claims sweep (`sweep_claims.sh`) listed 16 sentences in 3 files; the two worth checking by hand were the `gh pr checks` exit codes and the Codex-cloud sentence, which Codex then raised.

| Round | Head (as reviewed → now) | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 (2026-10-09) | `a2fb94f` → `41af23f` | full: `78ead07...a2fb94f`, 3 files | codex-cli 0.162.0, gpt-6.1-sol, medium, read-only, run from the worktree root | codex 142 s / 52,049 | 2/1/0 |
| 2 (2026-10-09) | `f478d32` → `9a7e7e7` | delta `a2fb94f..f478d32`, with round 1's dispositions (`--verify`) | codex medium, read-only (`--seat codex`) | codex 117 s / 48,958 | 0/2/0 |
| wording pass (2026-10-11) | `e1a105c` → `7d6f763` | delta `f478d32..e1a105c`, with round 2's dispositions (`--verify`); the one commit no reviewer had read | codex medium, read-only (`--seat codex`) | codex 54 s / 26,480 | 0/0/0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex | 1 | A site made earlier keeps "The assistant never merges" in its own §2, while the new guide and handover promise assistant merging; setup migrated §5 only | fixed — externally_reverified (round 2) | `9a7e7e7`: `website-team-setup` §7 replaces that old bullet with the template's "Merging" bullet |
| F2 | BUG | codex | 1 | "the preview is rebuilding, or the live site is" contradicts the token-deployed case, where a merge publishes nothing until the deploy command runs | fixed — externally_reverified (round 2) | `9a7e7e7`: the bullet points at "What a merge means" and names all three outcomes |
| F3 | RISK | codex | 1 | "exit code 0 = all green, 1 = red" for `gh pr checks` is not traced (skipped, cancelled, absent checks); asked for a fixture test of the exit codes | reworded, then raised again as F4; the fixture test refuted: it would test GitHub's CLI, not this repo, and the rule no longer depends on those codes | `9a7e7e7` (reworded), `7d6f763` (see F4) |
| F4 | RISK | codex | 2 | the reworded claim (skipped checks count as on the green tick) still lacks traced evidence | fixed by removing the claim — externally_reverified (wording pass) | `7d6f763`: "must exit 0 and list no failing or pending check; exit 8 means still running: wait; anything else: do not merge" |
| F5 | RISK | codex | 2 | "Codex in the cloud cannot" reach GitHub replaced the removed authentication claim with an unsupported connectivity claim | fixed by removing it — externally_reverified (wording pass) | `7d6f763`: the fallback rests on `gh` actually failing |

5 findings (2 BUG, 3 RISK, 0 NIT) in 2 rounds and a wording pass: all fixed; one part of F3 (the fixture test) refuted with a reason.

Waivers and deferrals: none.

Follow-ups:
- The release-note row for existing sites is in `docs/BUGLOG.md` (added with this trail).
- `templates/claude/settings.json` does not allow `gh pr merge`, so Claude Code asks for approval at each merge. Left as it is on purpose; allowing it is the owner's call.
- Not exercised: saying "merge" in a real Claude Code or Codex session. Exit code 8 comes from `gh pr checks --help` only; no run produced it.

Notes: Light gate, so no pair and no fresh-eyes seat. The round-1 record sent to Codex said three PRs with "25 to 28 passing and 5 skipped" checks exit 0; exactly, PR 234 had 25 passing and 5 skipped, PR 230 had 27 passing and 5 skipped, PR 212 had 28 passing and none skipped, all exit 0. The wording pass called that record unproven; the instruction no longer relies on it. The extra round found no BUG, so the change stayed at Light.
