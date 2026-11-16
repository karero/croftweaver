# DIFF review — karero/croftweaver#565 — Starter: Node floor to November's security releases, and patch bumps

Base `36229c9d` · depth: Normal (the starter's `package.json` and lockfile: shipped template
configuration, no auth, data or deploy wiring) · verdict: CLEAN after round 1 and the wording pass (1 round, 6 findings; gate total 257,043 seat tokens logged, fresh-eyes included) ·
authority used: WORKTREE-WRITE and BRANCH-COMMIT. This session (the bug sweep before 0.36) created the
worktree and the branch `fix/node-floor-nov`.

Artifact: `git diff 36229c9d...07791390 -- . ':(exclude)docs/reviews/'`. Evidence file with READs 1 to
11 (Node's release index, Astro's engines, the advisory, the guard's run, `npm audit`, the lockfile
changes, the old-version grep, `make check`, an install and build from an archive copy, the
advisory's issue list, CI's Playwright job). Gate id 20261115T223402Z-59673.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `07791390` | full, merge base with origin's HEAD | Codex (gpt-6.1-sol, config effort, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 109 s, 57,046; melious 97 s, 29,881; fresh-eyes 34 s, 128,431 | 1 / 2 / 3 after dedup |
| wording pass | `8706fe8a` | the fix commit only, `--base 07791390`, `--wording-pass` | Codex (gpt-6.1-sol, read-only), alone, as the wording pass allows | codex 110 s, 41,685 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| N1 | BUG | Codex | 1 | The BUGLOG row calls every bump a patch release, but Wrangler goes from 4.161.0 to 4.162.0, a minor. | fixed in `8706fe8a` (wording) | The row now reads "patch releases, and a minor one for Wrangler". |
| N2 | RISK | Codex | 1 | Unchecked that the Playwright preview server still starts under Astro 7.4.12 (`ASTRO_PREVIEW_BACKGROUND`, `playwright.config.ts:80`). | refuted | READ 11: CI's `playwright` job on the merge of `07791390` ran `npm ci`, then `playwright test`, whose `webServer` builds and previews: 98 tests, 97 passed, 1 skipped (the positioning test, skipped by design until terms are filled). |
| N3 | RISK | Codex | 1 | `sitemap` moves from 9.0.1 to 10.0.0 under @astrojs/sitemap 3.7.5, and the sitemap tests had not run. | refuted | READ 11: `tests/seo.spec.ts:167` "sitemap matches PAGES" and `:196` "robots.txt names the one sitemap file, sitemap-0.xml" passed in that run. |
| N4 | NIT | melious, fresh-eyes | 1 | "most of them in HTTP/2 and TLS" had no support in the evidence. | refuted | READ 10: the advisory lists 17 CVEs; 12 are in HTTP/2 or TLS/HTTPS, all 7 rated High among them. |
| N5 | NIT | melious, fresh-eyes | 1 | "same majors" hides the transitive `sitemap` 9 to 10. | fixed in `8706fe8a` (wording) | The row now says `sitemap` moves from 9 to 10 under @astrojs/sitemap 3.7.5, and that the starter's sitemap tests pass on it. |
| N6 | NIT | fresh-eyes | 1 | `scripts/check_node_floor.sh:5` calls 7.4.2's raise "the last time". | refuted | The comment lists Astro's raises of its Node floor. 7.4.12 keeps `>=22.23.4` (READ 2), so 7.4.2's is still the last one. The file is not in this diff. |

Notes:
- UNVERIFIABLE: 7 asked (Codex 4, melious 3), 0 confirmed. Answered from evidence: the advisory's
  contents (READ 10), the sitemap's output (READ 11). The guard compares Astro's range only, as its
  G1 says. That npm warns and does not stop on an `engines` mismatch is covered by
  `scripts/test_node_floor.sh`'s install case, which `make check` runs (READ 8). Not checked here:
  which Node Cloudflare's builders pick from `.nvmrc`. This PR does not change `.nvmrc`.
- No round 2 (stop condition (a2)): N1 and N5 changed only the BUGLOG row's wording, and nothing that
  runs. The wording pass read that row.
- The Playwright suite was not run on this Mac (the machine was under heavy load, and Playwright
  1.65.1 needs a browser build not yet installed here); CI's run is the evidence for N2 and N3.
