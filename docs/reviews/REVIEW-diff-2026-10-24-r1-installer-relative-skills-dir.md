# DIFF review — installers: resolve a relative skills dir — round 1

Branch `fix/installer-relative-skills-dir` at `d2231921`, base `11a13e2d`. Depth: **Normal** (an
installer change; the run itself named no depth, which the script flagged). Seats: codex
(gpt-6.1-sol, read-only) and melious (glm-5.3). `reviewers: codex OK, melious OK`.
`timings: codex 201s (39861 tokens), melious 156s (16921 tokens)`. The owner consented to sending
this repo's content to melious in chat, this session.

## Findings

| id | sev | seat | status | why |
|---|---|---|---|---|
| M1 | RISK | melious | refuted | The parity comment holds: `create-croftweaver/index.mjs:265` is `path.resolve(ASSISTANTS[assistant].dir())`, which never consults CDPATH. The author read it before the fix; codex traced and measured it independently. |
| M2 | NIT | melious | refuted | An empty DEST cannot be reached: both installers run `set -euo pipefail`, so a failed substitution in the assignment exits. Tested with a directory without permissions: stopped at line 25, nothing created. |
| M3 | NIT | melious | refuted | The output check is not vacuous: it failed on the unfixed installers alongside the pin check. The installers only `cd` through the decoy and never write into it, so a "decoy stays pristine" check would pass on broken code too. |

Codex: no findings.

## Verification

- The new `relative_dest` cases failed on `origin/main` (pin re-pointed, decoy path in output), in both installers, and pass with the fix.
- Mutation check: reverting either installer's line alone fails the suite.
- `make check` exit 0, normally and with an exported CDPATH.

Zero open BUGs or RISKs after round 1, so no further round.
