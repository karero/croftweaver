# DIFF review — docs/architecture-429-scope — `WEBSITE_ARCHITECTURE.md`: the 429 reason for staying on Pages holds only if code stays in front of every request

Base `origin/main` (`b8daa7e`; `6905a21` after the merge of #270, which main's up-to-date rule required) · depth: **Normal** (the file is a skill reference that agents load, so the Light default for prose does not apply) · verdict: **CLEAN** · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A, this session created the worktree and the branch; POST AUTHORITY — atom A once this session opens the PR.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `2b73b63` | full, `origin/main...2b73b63` | codex-cli 0.162.1, `gpt-6.1-sol`, config effort, read-only · melious `glm-5.3`, HTTP API, text only · fresh-eyes: Claude Sonnet sub-agent, read-only, no shared context | codex 91 s, 58,498 · melious 10 s, 2,610 · fresh-eyes 161 s, 117,381 | 0 / 1 / 3 |
| wording pass (not a round) | `f90e680` | delta since `2b73b63`, prose only | codex, medium, read-only | 74 s, 34,425 | 0 / 1 / 0 |
| merge link (not a round) | `077a206` | `merge_link.sh b8daa7e f90e680 6905a21` printed nothing: the merge of #270 changed none of this change's files | no reviewer run, nothing to send | — | — |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| M1 | RISK | melious | 1 | The paragraph cites `docs/PAGES-OR-WORKERS.md`, which the diff does not contain (the seat reads only the diff) | refuted | The file is on main; line 7 reads "Owner decision, 2026-10-11: stay on Pages for now". Codex and fresh-eyes both opened it |
| M2 | NIT | melious | 1 | The year 2026 could not be confirmed | refuted | The same line; commit `0d77902` is dated 2026-10-11 |
| E1 | NIT | fresh-eyes | 1 | The bare path `docs/PAGES-OR-WORKERS.md` does not resolve from an installed skill | fixed `f90e680`; locally_verified; externally_reverified by the wording pass | Now "`docs/PAGES-OR-WORKERS.md` in the Croftweaver folder", as `search-console-setup/SKILL.md:95` and `CLOUDFLARE_FIRST_DEPLOY.md:212` write it |
| E2 | NIT | fresh-eyes | 1 | "Holds only for a move that keeps the middleware" read as settled; the move without it is untested | fixed `f90e680`; locally_verified; externally_reverified by the wording pass | Now "holds only for a move that keeps code in front of every request, as the middleware does; a move without it is untried" |
| W1 | RISK | codex | wording pass | "As the middleware does" asserts that Cloudflare runs it before every request; handler code and tests do not show platform routing | refuted | Cloudflare's middleware page: a `functions/_middleware.js` at the root runs "in front of static files" (read 2026-10-11, linked from `CLOUDFLARE_FIRST_DEPLOY.md`). Seen on two live sites on 2026-10-05 (`docs/PAGES-OR-WORKERS.md`, "Seen on live sites"). Main already states it in both files |

Waivers: none. Deferrals: none. Follow-ups: none.

Notes:
- Round 1 found no BUG and no RISK that called for a fix, so no second round was owed. The two NIT fixes went to the wording pass; its one RISK is refuted, so the head did not move again.
- Second seat: GLM 5.3 on melious, the owner's standing choice. The owner's OK for this repo's diff to go there, given in this session on 2026-10-12: "Yes, Codex + melious".
- UNVERIFIABLE entries (questions, not findings): each seat asked whether Cloudflare's quota and routing behaviour is as the paragraph assumes. None became a finding beyond W1: the vendor pages behind it are cited in `docs/PAGES-OR-WORKERS.md` and `CLOUDFLARE_FIRST_DEPLOY.md`, and that file says the move without middleware is untried.
- Data check: the diff holds no credentials and no private names. Destinations: Codex and melious.
- Raw reviewer output: in the PR's one review comment. Fresh-eyes raw output is not attached (a Claude sub-agent); its findings are E1 and E2.
