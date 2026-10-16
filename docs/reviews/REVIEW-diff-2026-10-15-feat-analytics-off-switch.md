# Review trail: the starter's analytics off switch (`feat/analytics-off-switch`)

Base `688164f` (after merging `origin/main` as `98fbf7f`) · depth: High (runtime code in the starter, a CI step, and the claim that a site without analytics sends nothing the page does not need) · verdict: CLEAN (2026-10-15). Five rounds, a parallel round 1 by another session on `98fbf7f`, a final full read and a wording pass; 45 findings before merging duplicates (2 BUG in code fixed, 1 BUG in wording fixed, none open) · seen pair: base `688164f`, head `e7b6b04`; the commit after it adds only this trail

## Rounds

| Round | Head | Scope | Seats | Time, tokens | Findings (BUG / RISK / NIT) |
|---|---|---|---|---|---|
| 1 | `e698261` | full | Codex (gpt-6.1-sol, config effort); Melious (glm-5.3); fresh-eyes (Claude Opus) | Codex 341 s, 96,490 · Melious 476 s, 21,587 · fresh-eyes 270 s, 157,513 | 0 / 4 / 7 |
| 2 | `7344fda` | fixes since `e698261` | same | Codex 261 s, 90,343 · Melious 168 s, 14,291 · fresh-eyes 86 s, 99,884 | 0 / 3 / 1 |
| 3 | `bfebd60` | fixes since `7344fda` (the artifact also carried main's merge `98fbf7f`; only the fix was triaged) | same | Codex 226 s, 82,579 · Melious 215 s, 20,888 · fresh-eyes 124 s, 107,494 | 0 / 3 / 3 |
| 1 (parallel) | `98fbf7f` | full, run by another session while this one was unreachable after an app restart | Codex, Melious (glm-5.3), fresh-eyes (Claude Opus) | Codex 164 s, 75,836 · Melious 350 s, 32,826 | 1 / 3 / 6 |
| final full read (not a round) | `242a96d` | full (`origin/main...HEAD`) | ollama (kimi-k3:cloud), not yet on this artifact | 349 s | 0 / 0 / 1 |
| 4 (earned by `csp-host-match`) | `7073ecb` | fixes since `242a96d` | Codex (config effort); Melious (glm-5.3) | Codex 354 s, 91,166 · Melious 222 s, 21,533 | 1 / 4 / 4 |
| 5 (earned by `host-link-check`, cut) | `ef71213` | the cut since `7073ecb` | same | Codex 217 s, 72,008 · Melious 191 s, 18,406 | 1 (wording) / 2 / 1 |
| wording pass (not a round) | `e7b6b04` | prose and comments since `7073ecb` | Codex | 159 s, 66,372 | 0 / 0 / 0 |

## Findings

| Id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | Codex, Melious | 1 | CI off-step named `analytics.example.com` instead of reading it | fixed | host read from `scriptHost` (G1 widened the reader) |
| F2 | RISK | Melious | 1 | the off path runs only three builds | refuted | `build empty set ""` sits after `fi`; the off run printed four build lines and "4 builds, off in every one" |
| F3 | NIT | Melious | 1 | off mode passed a `_headers` with no CSP | fixed | `csp_host_left` reports it; fixture `p_nocsp:bad` |
| F4 | NIT | Melious | 1 | error message narrower than the parser | fixed | names the tolerated `//` comment |
| F5 | NIT | fresh-eyes | 1 | "the gate then checks" though a site's CI does not run it | fixed | Q5, `config.ts`, `_headers` say to run it by hand |
| F6 | NIT | fresh-eyes | 1 | starter README did not name the switch | fixed | file list and step 4 |
| F7 | NIT | fresh-eyes | 1 | no type check with the switch off | fixed | `npm run check` in the off-step; locally 0 errors |
| F8 | NIT | fresh-eyes | 1 | `else` body of the gate not indented | refuted (style) | reindenting would rewrite unchanged lines |
| F9 | RISK | fresh-eyes, Codex r3 | 1 | the starter ships with analytics on, so a site that never answers Q5 writes the placeholder script on its live build | follow-up | older than the change; the owner decides whether the starter should ship off |
| F10 | RISK | Codex | 1 | Q5's "search & referral traffic" for Search Console | follow-up | sentence older than the change |
| G1 | RISK | Codex | 2 | CI host reader took single quotes only | fixed | same regex as the gate, trailing slash stripped |
| G2 | RISK | Codex | 2 | `sed` removal also matched lookalike hosts | fixed | perl `\Q…\E`, whole token only; tested with `analytics-example.com` and `.com.au` |
| G3 | NIT | Melious | 2 | guard message said "no line" for a format mismatch | fixed | names the expected form |
| T1 | RISK | Codex, fresh-eyes (NIT) | 3 | the substring guard after the removal failed on a lookalike the removal keeps | fixed | guard dropped; the gate reports a left token |
| T2 | RISK | Codex, fresh-eyes (NIT) | 3 | removal missed a tab before the host, or a host at the end of a line with no newline | fixed | `[ \t]+…(?=[;\s]|$)`; tested |
| H1 | BUG | Codex (parallel) | 1p | with analytics off, a path-qualified source `https://host/js/` was not counted as the host | fixed, externally_reverified (round 4) | sources cut to `scheme://host[:port]` before matching; fixtures `p_path:bad`, `p_lookalike:ok`, `p_default:bad` |
| H2 | RISK | fresh-eyes (parallel) | 1p | CI did not assert the starter ships `USE_ANALYTICS = true` | fixed | the off-step fails unless the line reads `true` |
| H3 | RISK | fresh-eyes (parallel) | 1p | the off check would miss a preconnect link to the host | documented limit | a link search was added in `7073ecb` and cut in `ef71213` (R4-1); the gate's "cannot check" list names it; `Base.astro:174` is the starter's only use of `scriptHost` |
| H4–H8 | NIT | fresh-eyes, Melious (parallel) | 1p | pointer to the right comment; lookalike fixture; Q5 "That means" read as sufficient; `default-src` unchecked; CI hard-coded `production` | fixed | as described in `7073ecb` |
| K1 | NIT | Kimi (final full read) | full | "no `USE_ANALYTICS` line counts as on" overstated | fixed | wording, then corrected again by R5-1 |
| R4-1 | BUG | Codex | 4 | the new host-link search matched commented-out links and `data-src` | fixed by a cut | the search is removed (`ef71213`) |
| R4-2, R4-4–7 | RISK/NIT | Codex, Melious | 4 | the link search's case, site-host skip, follower class, fixtures, comment | moot | removed with the search |
| R4-3 | RISK | Melious | 4 | the path cut assumes one source per line | refuted | `csp_tokens` prints one token per line (`print t[j]` in its loop) |
| R4-8 | NIT | Melious | 4 | CI regexes hard-code single spaces | refuted | the gate's own readers take the same exact form; a reformat fails loudly |
| R4-9 | RISK | Melious | 4 | with analytics on, a path-qualified source is still matched exactly | follow-up | on-path behaviour older than the change |
| R4-10 | NIT | Melious | 4 | the CI removal cannot strip a path-qualified source | follow-up | the starter's `_headers` has none; fails loudly |
| R5-1 | BUG (wording) | Codex | 5 | "names it only in a comment fails" is wrong: a commented-out line in the gate's form is still read | fixed | "names it but has no line in the gate's form fails" (gate header, BUGLOG) |
| R5-2 | RISK | Melious | 5 | the off guarantee now rests on what `Base.astro` writes | refuted | `grep` over `src` and `public`: the only `scriptHost` use is the gated script tag |
| R5-3 | NIT | Melious | 5 | lookalike fixture stripped `https://` only | fixed | `${host#*://}` |

## Checks run by the author

- `bash tests/check_analytics_gate.sh` with analytics on: green, 28 CSP fixtures.
- The CI off-step rehearsed on macOS: `astro check` 0 errors, the gate "4 builds, off in every one", `tests/email.spec.ts` on a `CF_PAGES_BRANCH=production` build 9 passed.
- Negative cases: switch off with the host left in `_headers` fails; a switch that `enabled:` ignores fails (`expect_off` on the live build).
- Starter suite: 69 passed, 1 skipped (the positioning test waiting for a filled map).
- `make check`: green except `scripts/test_mktemp_guard.sh`, which fails the same way on a clean `origin/main` on this Mac and passes in CI on Linux; not part of this change.
