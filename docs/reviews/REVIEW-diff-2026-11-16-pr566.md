# DIFF review — karero/croftweaver#566 — First deploy: set the production branch after the import, in Settings → Builds

Base `36229c9d` · depth: Normal (instructions an owner follows for a first deploy and an assistant
follows from `SKILL.md`; no code, auth, data or deploy wiring changes) · verdict: CLEAN after round 3
(3 rounds, 11 findings after dedup; gate total 321,543 seat tokens logged, fresh-eyes included) · authority used:
WORKTREE-WRITE and BRANCH-COMMIT. This session (the bug sweep before 0.36) created the worktree and
the branch `fix/first-deploy-production-branch`.

Artifact: round 1 `git diff 36229c9d...8bd5b17b -- . ':(exclude)docs/reviews/'`; round 2 the delta
`8bd5b17b...e0fe6b82`; round 3 the delta `e0fe6b82...ab4e3063`. Evidence file, the same every round,
READs 1 to 3 from round 1 and READ 4 added in round 3: Cloudflare's build-branches docs page
(https://developers.cloudflare.com/workers/ci-cd/builds/build-branches/), the release-candidate site's
import record (trimmed, names replaced), launch's commit check and the analytics gate, and ship's
no-push case with the move guide's order. Gate id 20261115T230657Z-54437.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `8bd5b17b` | full, merge base with origin's HEAD | Codex (gpt-6.1-sol, config effort, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 169 s, 75,118; melious 97 s, 14,973; fresh-eyes 38 s, 113,350 | 1 / 2 / 5 after dedup |
| 2 | `e0fe6b82` | the round 1 fixes, `--base 8bd5b17b`, `--verify` | Codex (effort medium); melious (glm-5.3) | codex 105 s, 37,951; melious 119 s, 20,504 | 0 / 2 / 1 after dedup |
| 3 | `ab4e3063` | the round 2 fixes, `--base e0fe6b82`, `--verify` | Codex (effort medium); melious (glm-5.3) | codex 70 s, 44,138; melious 67 s, 15,509 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 1 | Path B's "attach the domain only after the branch is set, as launch does" says launch sets or checks the production branch; it compares only the commit the Worker serves with the head of `production`. | fixed in `e0fe6b82` | READ 3: `cloudflare-setup.mjs` launch compares `state.sha` with `prodSha`. The guide now says "The domain is attached later, at launch", and that launch checks the commit, not the branch that built it. Round 2 confirmed. |
| F2 | RISK | Codex, melious | 1 | After the branch change no step makes a build from `production`, so the Worker keeps `main`'s build (no analytics) and launch accepts it, the commit being the same. | fixed in `e0fe6b82` and `ab4e3063` | `src/config.ts:102` turns analytics on only for a `production` build (READ 3). All three texts say the live build comes with the next push to `production`, before launch; R2-1 then added "after a new commit on `main`". |
| F3 | RISK | fresh-eyes | 1 | Checklist §1 has no warning that a route already in `wrangler.jsonc` would publish `main`'s build. | fixed in `e0fe6b82`, then R2-2 | The push-before-launch sentence covers the starter. Round 2 raised the routed case again as R2-2. |
| F4 | NIT | melious, fresh-eyes | 1 | "the repository's default branch, `main`" assumes the default branch is `main`. | fixed in `e0fe6b82` | Now "(`main` on a starter site)"; READ 1: Workers defaults to the repository's default branch. |
| F5 | NIT | fresh-eyes | 1 | "Settings → Builds" differs from the docs' "Settings > Build > Branch control". | refuted | READ 1: the same docs page says "Settings > Builds" (line 49). The record's screenshots say "Settings → Builds". Path B also names the docs' "Build → Branch control". |
| F6 | NIT | fresh-eyes | 1 | "connecting builds it straight away" vs the 2026-11-08 fixture, a connect-time build on `production`. | refuted | READ 2: the first build ran at the import, from `main`. How the fixture's site was connected is the open question the BUGLOG row keeps. |
| F7 | NIT | fresh-eyes | 1 | `docs/MOVE-TO-WORKERS.md:68` points to path B. | refuted | Path B still holds the steps it points to; the finding asks for no change. |
| F8 | NIT | fresh-eyes | 1 | The checklist's Pages form line is not updated. | refuted | Out of scope: the row is about the Workers import only. |
| R2-1 | RISK | Codex, melious | 2 | SKILL.md and the checklist said only "the next `npm run ship`"; with no new commit on `main`, ship pushes nothing, so no build runs from `production`. | fixed in `ab4e3063` | READ 4: `scripts/ship.sh` prints "Nothing to push: 'production' already has this commit" when `live_n` is 0, and pushes `$id:refs/heads/production` otherwise. All three texts now say "after a new commit on `main`". Round 3 confirmed. |
| R2-2 | RISK | Codex | 2 | A site connected with a route already in `wrangler.jsonc` would serve `main`'s build on it. | follow-up (re-sorted: rare) | No path reaches B with a route: the starter's `wrangler.jsonc` has none, and the move writes its route commit at the move, after the Worker is connected (READ 4; Codex in round 3: `CLOUDFLARE_MOVE.md` stage 1, `move-to-workers.mjs:1573-1576`). BUGLOG row 2026-11-16. |
| R2-3 | NIT | melious | 2 | BUGLOG row 319's What cell still says "(attach the domain after, as launch does)". | refuted | The What cell is the row as filed; its status cell says what was fixed, and the guide an owner follows no longer says it. Round 3 agreed. |

Notes:
- F2 and R2-1 were each raised by both seats.
- UNVERIFIABLE, round 1: Codex 1, melious 2, 0 confirmed (Cloudflare's import form and build triggers,
  answered from READs 1 and 2). Round 2: Codex 1, melious 2; melious's ship question was answered by
  READ 4 in round 3, and confirmed as R2-1's cause. Round 3: Codex 1, melious 2; Codex's own reads
  answered melious's two (the move's route order, the starter's `wrangler.jsonc`).
- Not tested: a site connected with a route (R2-2), and whether a build that deployed to no address
  sets the version launch reads. The push-before-launch step holds either way.
- No wording pass: round 3 read every change since round 2, the BUGLOG rows included.
- `make check` passed before each round and after the last edit.
