# DIFF review — docs/pages-workers-table — a side-by-side table of Pages and Workers in `docs/PAGES-OR-WORKERS.md`

Base `be049d7` (the head of #261, on which this branch was stacked; `cf2955b` on main after #261 merged, the same tree) · depth: **Light** (prose in a doc no agent loads as instructions and no one runs; the owner's standing default for such a diff, 2026-10-09) · verdict: **CLEAN** · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A, this session created the worktree and the branch; POST AUTHORITY — atom A once this session opens the PR.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `10f1002` | full, `be049d7...10f1002` | codex-cli 0.162.1, `gpt-6.1-sol`, medium, read-only | 84 s, 35,800 | 0 / 1 / 2 |
| confirmation 1 (prose-only re-gate, not a round) | `9bb6968` | delta since `10f1002` | the same | 75 s, 33,542 | 1 / 0 / 0 (T1 re-raised, no new evidence) |
| confirmation 2 (not a round): the fix of C1, plus T1's settling observation, the table against the saved vendor pages | `c9bb0b8` | delta since `9bb6968`; the 32 pages in `docs/local/vendor-pages-2026-10-11/` | the same | 100 s, 54,386 | 0 / 0 / 0 |
| merge link (not a round) | `a30cd5f` | `merge_link.sh be049d7 c9bb0b8 cf2955b` printed nothing: the merge of #261 changed none of this change's files | no reviewer run, nothing to send | — | — |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| T1 | RISK | codex | 1 | The table's Cloudflare claims lack source text the reviewer could inspect | refuted; externally checked in confirmation 2 | The author's copies of the cited pages (fetched 2026-10-11 as markdown from developers.cloudflare.com) were put on disk for the reviewer. Codex compared each row with them: the twelve vendor rows are supported, and "Fit with the kit" was verified against the kit's files. The copies are the author's, not a live fetch by the reviewer; the table's intro says the Workers column was not tried on a deployment |
| T2 | NIT | codex | 1 | The row "Previews kept out of search engines" claimed an outcome; the docs promise a header | fixed `9bb6968`; locally_verified; externally_reverified in confirmation 1 | The row now reads "A noindex header on previews" |
| T3 | NIT | codex | 1 | "A move touches … every live site": moving the kit does not force a live site to move | fixed `9bb6968`; locally_verified; externally_reverified in confirmation 1 | The table row, the sentence after the kit table and judgment point 2 say "each live site that follows"; one sentence adds that a site can stay on Pages while Pages is offered. Two of those sentences came in with #259 |
| C1 | BUG | codex | confirmation 1 | The fix for T1 wrote "none of it was tried on a deployment", which contradicts the file's own observation on live Pages sites | fixed `c9bb0b8`; locally_verified; externally_reverified in confirmation 2 | The intro now says the Workers column was not tried on a deployment and names the one Pages observation |

Waivers: none. Deferrals: none. Follow-ups: none.

Notes:
- Light gate, one seat by design: the script's "fewer than 2 reviewers" notice is expected. Round 1 found no BUG, so no second round. C1 was a contradiction a closing edit introduced; it was fixed and confirmed once, as the skill's wording-pass rule allows. The owner may still ask for a Normal gate.
- T2 and T3 arrived as UNVERIFIABLE entries; a look confirmed both, so they are findings. Still open as questions only: Cloudflare's behaviour on a real deployment, the 2026-10-05 observations (their hosts stay out of this public repo), and whether the saved pages match the vendor's originals.
- Data check: the diff holds no credentials and no private names. Destination Codex only, on the owner's request in this session (2026-10-05): "an independent review per the repo's conventions".
- Raw reviewer output: in the PR's one review comment.
