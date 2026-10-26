# DIFF review — ship.sh's line for a pages.dev address (#413)

Branch `fix/ship-preview-wording`. Depth: **Normal** (shipped code: `scripts/ship.sh`). Seats: codex
(gpt-6.1-sol, read-only) and GLM 5.3. melious failed both rounds on credit ("Insufficient balance
… Available: 0"), so GLM 5.3 ran on ollama (`glm-5.3:cloud`) in its place, as the script does.

## Round 1 — `d4fb5ff6`, base `428b7ba1`
`reviewers: codex OK, melious FAILED (quota), ollama-cloud OK` · `timings: codex 181s (49649 tokens), melious 0s, ollama-cloud 449s` · gate `20261026T061941Z-99160`

| id | sev | seat | status | why |
|---|---|---|---|---|
| C1 | BUG | codex | fixed | `PAGES.DEV` or a final dot kept "✓ LIVE"; the host is now trimmed of one final dot and lowercased; case P5 (`https://Ship-Test.PAGES.DEV.`), shown to fail without the fix |
| C2 | RISK | codex | fixed | "the site isn't live there" claimed a domain state the script never saw (the middleware sends `<project>.pages.dev` to `CANONICAL_URL` when that is set); the note now says only "the site is live on your domain only once that's connected" |
| O1 | RISK | ollama | fixed | "preview address": `<project>.pages.dev` serves production, and the starter's docs keep "preview" for `main.<project>.pages.dev` (PUBLISHING.md, CLOUDFLARE_FIRST_DEPLOY.md:452); now "the pages.dev address" and "Cloudflare's address for the site" |
| O2 | RISK | ollama | refuted | `update-index -q --refresh` under `set -e`: P3 and P4 ran green three times (bash 5 twice, /bin/bash 3.2 once), and run_ship's "index unchanged" check passed each time |
| O3 | NIT | ollama | fixed | "there" could read as the pages.dev address; fixed with C2 |
| O4 | NIT | ollama | left | The newer-publish warning (worktree mode, two publishes racing) still says "the live site"; untouched to keep the change to the success line |
| O5 | NIT | ollama | fixed | Same as C1 |

## Round 2 — `b47d9151`, delta from `d4fb5ff6` (`--verify` round 1)
`reviewers: codex OK, melious FAILED (quota), ollama-cloud OK` · `timings: codex 156s (46797 tokens), melious 0s, ollama-cloud 289s`

Both seats verified C1, C2, O1 and O3 fixed. No BUG.

| id | sev | seat | status | why |
|---|---|---|---|---|
| O6 | RISK | ollama | refuted | `<<<` is not POSIX sh: ship.sh is `#!/usr/bin/env bash`, runs as `bash scripts/ship.sh`, and already uses `<<<` (line 50) |
| C3/O7 | RISK | both | refuted | O2 raised again; same evidence as O2 |
| C4/O8 | NIT | both | left | O4 raised again |
| O9 | NIT | ollama | left | The branch name still says "preview"; it goes with the merge |

Totals: 2 rounds, 9 distinct findings (1 BUG, 5 RISK, 3 NIT); seat tokens 96,446 logged (ollama
gives no figure).
