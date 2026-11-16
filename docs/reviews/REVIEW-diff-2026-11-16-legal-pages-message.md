# DIFF review — branch fix/legal-pages-message — the legal-pages test's message stands on its own

Base `07211892` · depth: Normal (a starter test's failing message and one AGENTS.md instruction; no
user data, auth or deploy path) · verdict: CLEAN after round 4 and a wording pass · authority used: WORKTREE-WRITE and
BRANCH-COMMIT. This session (the small BUGLOG sweep) created the worktree and the branch.

Artifact: round 1 `git diff 07211892...3db8dc0e -- . ':(exclude)docs/reviews/'`; round 2 `git diff
3db8dc0e..f4a7c52a` (same exclusion), with `--base 3db8dc0e`. Round 3 `git diff f4a7c52a..065874bb`, with `--base f4a7c52a`. Round 4 `git diff 065874bb..2e2e687b`, with `--base 065874bb` and `--earned-by impressum-adoption --cut "removed the recipe for a site with neither Impressum file: it is set up by hand"`. Wording pass `git diff 2e2e687b..ff2ce1f8` (the BUGLOG Status cell), with `--base 2e2e687b`. Evidence: round 1
the starter's `tests/placeholders.spec.ts` run whole on a scratch copy of the starter, and the new
unit test run with origin/main's message put back. Gate id 20261116T145245Z-81881.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `3db8dc0e` | full, merge base with origin's HEAD | Codex (gpt-6.1-sol, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 113 s, 33,683; melious 165 s, 11,314; fresh-eyes 54 s, 117,564 | 0 / 1 / 3 after dedup |
| 2 | `f4a7c52a` | delta from `3db8dc0e`, verify of F1-F4 | Codex (medium); melious | codex 149 s, 71,314; melious 119 s, 7,806 | 1 / 0 / 1 |
| 3 | `065874bb` | delta from `f4a7c52a`, verify of F5-F6 | Codex (medium); melious | codex 165 s, 41,937; melious 203 s, 13,218 | 1 / 2 / 1 |
| 4 | `2e2e687b` | delta from `065874bb`, verify of F1-F8 | Codex (medium); melious | codex 84 s, 26,893; melious 68 s, 6,048 | 0 / 0 / 0 |
| wording | `ff2ce1f8` | the BUGLOG Status cell | Codex (medium), `--wording-pass` | codex 58 s, 28,965 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | fresh-eyes, melious (NIT) | 1 | The new AGENTS.md clause, "a site made before that file existed takes it from the latest Croftweaver starter first", had no support and named no place to take the file from. | fixed in `f4a7c52a` | `git log` shows the German page routed as `src/pages/impressum.astro` from 13c4516a (first in v0.15) until 6d99b398 (v0.35) renamed it `_impressum.astro`. The clause now says a 0.15 to 0.34 site already has the page, and one with neither file copies it from `skills/new-website/templates/astro/src/pages/` in the download, which `scripts/package.sh` zips (`skills` is in its list). |
| F2 | NIT | melious | 1 | The three answers appear twice in the message, as prose and as README forms, and only one case asserts the prose. | refuted | One function writes the message for every case, so the two cannot drift apart by case; the prose is the question, the forms are what to record. |
| F3 | NIT | fresh-eyes | 1 | The message words the answers differently from section 5's options. | no change | Section 5's options are in the owner's voice ("I use my own texts"); the message speaks of the owner. |
| F4 | NIT | fresh-eyes | 1 | The test comment's claim that a site can lack AGENTS.md has no support in the diff. | no change | BUGLOG row 328 records it, found in three sites' updates to 0.35. |
| F5 | BUG | Codex | 2 | A site with neither file followed the copied page's header, which says the footer needs no edit; a site made before 0.15 has a footer that links only `/privacy`, so the Impressum stayed unlinked. | fixed in `065874bb` | That site also adds the footer link. `git show v0.14:…/Base.astro` has only the privacy link; v0.15 and v0.34 link `/impressum`; `impressum.astro` first ships in v0.15 (13c4516a). |
| F6 | NIT | melious | 2 | The sentence named where to copy from, not where to; "first" had no clear referent. | fixed in `065874bb` | It names the site's own `src/pages/` and drops "first". |
| F7 | BUG | Codex, melious (RISK) | 3 | F5 came back: the copied page's steps replace `/legal-notice` entries and trust a footer a site made before 0.15 does not have, so on such a site the page stayed out of the tests and `llms.txt`. | fixed in `2e2e687b` (a cut) | The recipe is gone: on a site with neither file the agent does not follow the header's steps (they assume a site made from 0.35 on; `legal-notice.astro` first ships in v0.35, 6d99b398) and tells the owner the page needs setting up by hand. |
| F8 | RISK | Codex, melious (NIT) | 3 | "Made before 0.15" left out a later site that deleted the German page. | fixed in `2e2e687b` | The same cut covers every site with neither file. |

Mutation check on `ff2ce1f8` (playwright, `tests/placeholders.spec.ts -g 'draft notice rules pick'`): 3
mutations of the message on `placeholders.spec.ts` line 150, all 3 killed, and both baselines
passed.
