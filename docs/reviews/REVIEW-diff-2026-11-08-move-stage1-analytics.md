# DIFF review: branch `fix/move-stage1-analytics-035`, stage 1's analytics line (row 242)

No plan: a docs fix that restores intended behaviour (the release manager's scope, 2026-11-08).
Base `a2365d4e` (origin/main, with #491 merged as `cc07629e`) · depth: Normal (a guide an owner's
assistant follows step by step) · no red team (docs only; no box, user data, login, money,
deletion or schema). Seats: Codex and GLM 5.3 on melious in one command
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet in round 1. Round 1 ran without
`--base`, so the script's stale-diff check was on; round 2 took `--base 8ddc6f3b`, the head round 1
reviewed, as a verification round must. The artifact leaves out `docs/reviews/`.

**Verdict: CLEAN at round 2** (no BUG; its one RISK refuted). Gate `20261108T221906Z-88084`:
2 rounds, 9 findings, 238,879 tokens logged over 5 seat runs (fresh-eyes included).

## Evidence checked before round 1

- RUN 1: the 0.35 `tests/check_analytics_gate.sh`, on a copy of the template with
  `USE_ANALYTICS = true` and the old line (`process.env.CF_PAGES_BRANCH === PROD_BRANCH`), exits 1:
  "the enabled: line in src/config.ts must read process.env.WORKERS_CI_BRANCH … it reads: none."
- `src/` is SITE_SOURCE (`scripts/check_template_coverage.sh` line 67): an update never rewrites
  the site's `src/config.ts`.
- `record` compares each page's body hash on the domain with the Worker's version URL
  (`move-to-workers.mjs` line 1119) and stops on an unknown difference (lines 1386 to 1401). Read,
  not run on a real move; Codex ran `compare()` on differing body hashes and got an unknown body
  difference.
- Workers Builds runs `npm run build` (template `package.json` line 12), which runs no test.

## Rounds

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `8ddc6f3b` | whole change; evidence (6,894 bytes) | Codex; melious glm-5.3; fresh-eyes Sonnet | Codex 145 s, 62,126 · melious 117 s, 16,951 · fresh-eyes 33 s, 99,800 | 1 / 3 / 4 (Codex 1/1/1, melious 0/1/1, fresh-eyes 0/2/4; shared ones counted once) |
| 2 | `67ed9668` | round 1's fixes | Codex; melious glm-5.3 | Codex 99 s, 49,763 · melious 64 s, 10,239 | 0 / 1 / 0 (Codex) |

## Round 1 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| F1 | BUG | Codex | The quoted 0.35 form leaves out `USE_ANALYTICS &&`: pasted in, it switches analytics on with them off | Fixed: the whole line in a `ts` block, as the template's line 117 |
| F2 | RISK | melious, fresh-eyes | "`record` stops on a body difference on every page" is not settled: a Worker deployed by hand with `CF_PAGES_BRANCH` has the tag; a build might fail first | Fixed: the stop is said only of a Worker that Workers Builds builds, "every page" dropped. Workers Builds runs `npm run build`, not the tests |
| F3 | RISK | Codex | The Workers Builds claim rests on the repo's own capture | Refuted in part: the capture is a real run from #491, says how it was made, and the gate test reads it. The guide now says "seen on real runs" |
| F4 | RISK | fresh-eyes | "All of it is merged to the live branch" reads as covering only analytics; nothing says how the edit ships | Fixed: the analytics step is its own paragraph, ending "ship it with the rest of stage 1" |
| F5 | NIT | fresh-eyes | Nothing says what to do with analytics off | Fixed: "With analytics off, leave the line alone." |
| F6 | NIT | fresh-eyes | One long run-on sentence | Fixed: short sentences |
| F7 | NIT | fresh-eyes | Step 5's note sits oddly beside "Workers Builds does not set `CF_PAGES_BRANCH`" | Fixed: "this build sets `CF_PAGES_BRANCH`, which the old `enabled:` line and the 0.35 one both read" |
| F8 | NIT | Codex, melious, fresh-eyes | `#PRNUM` placeholders | Fixed: the PR number, once the PR was open |

## Round 2 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| G1 | RISK | Codex | F3 again: the capture is the only support for what Workers Builds sets | Refuted: the guide claims only what was seen, and a wrong name cannot pass silently: `record` stops when the Worker's pages lack the tag the domain's have. Nothing changed after round 2, so no round 3 is owed |
