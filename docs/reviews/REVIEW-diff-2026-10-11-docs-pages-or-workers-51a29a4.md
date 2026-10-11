# DIFF review — docs/pages-or-workers — an assessment of what moving the kit from Cloudflare Pages to Workers would change

Base `origin/main` (`35e9b42`; `e9e0a19` after the merge of #258) · depth: **Light** (both changed files are prose that no agent loads as instructions and no one runs: an assessment for the maintainer in `docs/` and a row in the README's file map; the owner's standing default for such a diff, 2026-10-09) · verdict: **CLEAN** · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A, this session created the worktree and the branch; POST AUTHORITY — atom A once this session opens the PR.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `51a29a4` | full, `origin/main...51a29a4` | codex-cli 0.162.1, `gpt-6.1-sol`, medium, read-only | 88 s, 49,161 | 1 / 1 / 0 |
| 2 | `e1cd8b6` | delta since `51a29a4` | the same | 117 s, 39,757 | 0 / 1 / 0 |
| confirmation (prose-only re-gate, not a round) | `23ed584` | delta since `e1cd8b6` | the same | 50 s, 14,990 | 0 / 0 / 0 |
| merge link (not a round) | `b9b944d` | `merge_link.sh 35e9b42 23ed584 e9e0a19`: this change's own files since `23ed584`, merge effects included; normal scope, since the README hunk sits in a fenced listing | the same | 89 s, 34,040 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex | 1 | The file said the site's navigation tests would show a difference in how Workers serves URLs; those tests never reach Cloudflare | fixed `e1cd8b6`; locally_verified; externally_reverified r2 | `playwright.config.ts` sets `baseURL` to `http://localhost:<port>` and starts `npm run build && npm run preview`; `tests/middleware.spec.ts` calls `onRequest()` directly. The table row now says the tests cannot confirm it, and trial item 4 asks the deployed Preview directly |
| F2 | RISK | codex | 1 | The Cloudflare claims lack independently checked vendor text (the reviewer had no network and marked the group UNVERIFIABLE) | refuted for the quoted sentences; two trial checks added `e1cd8b6` | 2026-10-11: each cited page fetched as markdown from developers.cloudflare.com, and each of the 11 quoted phrases found in it as a literal substring. Pages and read date are under "Sources". The file labels route B untested and makes any move wait for the trial. Added as the reviewer suggested: URL and redirect requests against the Preview (item 4), and what the dashboard counts against the daily limit (item 8) |
| F3 | RISK | codex | 2 | Trial item 4 named `/about` and an entry from `public/_redirects`; the starter ships neither | fixed `23ed584`; locally_verified; externally_reverified by the confirmation | `src/pages/` holds `privacy.astro` and no `about`; `public/` holds no `_redirects`. The item names `/privacy` and says to add a redirect entry for the trial |

Waivers: none. Deferrals: none. Follow-ups: none.

Notes:
- Light gate, one seat by design: the script's "fewer than 2 reviewers" notice is expected. No fresh-eyes pass at this depth. Round 2 ran because round 1 found a BUG; it found none, so the rounds ended there.
- The merge: #258 moved the base and rewrote the README's `docs/` map (the two maintainer trackers are now repo only). Main was merged in (`b9b944d`); the one conflict was resolved by taking main's lines and adding this branch's row. The row and the file's first line no longer say "maintainer-internal" (`7ee155a`), a label that since #258 goes with "repo only". The merge link confirmed that the file ships in the zip under main's `package.sh`.
- UNVERIFIABLE entries (questions, not findings): round 2 asked three, the confirmation one, the merge link three. None became a finding: the vendor quotations are F2's evidence, the starter's own `tests/_helpers.ts` lists `/privacy`, and a complete package run is `make smoke`, run on the merged head before the push.
- Data check before round 1: the diff holds no credentials and no private names. Destination Codex only, on the owner's request in this session (2026-10-05): "an independent review per the repo's conventions".
- Not checked by any reviewer: Cloudflare's behaviour itself, and the 2026-10-05 observations on two live sites, whose hosts stay out of this public repo. Raw reviewer output: in the PR's one review comment.
