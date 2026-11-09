# DIFF review — robots.txt and the search-console steps name `sitemap-0.xml`

Plan: `sitemap-0/PLAN.md` in the private hub (PLAN gate passed in round 1, no BUG). Depth: Normal
(a served file and a test that ships to sites; no box, user data, login, money, deletion or
schema). Seats: Codex gpt-6.1-sol and GLM 5.3 on melious in one command
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`). Gate 20261109T114446Z-56319.

## Rounds

| Round | Head | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|
| 1 | `8f081dba` | Codex 101 s, 38,127 · melious 157 s, 12,481 | 1 / 2 / 2 |
| 2 | `fe561a1c` | Codex 130 s, 45,835 · melious 214 s, 14,939 | 0 / 2 / 3 |

Two rounds, 12 findings, 111,382 tokens. Wording-only fixes after round 2 got no third round:
no BUG was open, and they change a failure message and a checklist line.

## Round 1

| Seat | Kind | Finding | Disposition |
|---|---|---|---|
| Codex | BUG | A trailing comment on the Sitemap line hid it from the test | Fixed: comments are stripped first; checked with a trailing comment, a comment-only line, two lines and the index named |
| Codex | RISK | `@astrojs/sitemap` file names and the 45,000 split lack evidence | Refuted: locked 3.7.4 has `entryLimit: 45e3`, `filenameBase: "sitemap"`; a real build wrote `sitemap-0.xml` and `sitemap-index.xml`; the test checks both at run time |
| GLM | RISK | The Sitemap host is checked nowhere | Refuted: `cloudflare-check.mjs:1054` and `:1060` compare it with the live site; Codex marked the comment VERIFIED |
| GLM | NIT | Step 4 says "submit `sitemap-0.xml`" twice | Fixed |
| GLM | NIT | The Bing anecdote reads as general behaviour | Fixed: "once … on one site" |

## Round 2

| Seat | Kind | Finding | Disposition |
|---|---|---|---|
| Codex | RISK | After the S4 fallback, console submissions should change too | Fixed: the test's message says to submit the index in Search Console and Bing |
| GLM | RISK | The host is checked nowhere (again) | Refuted as in round 1 |
| GLM | NIT | A relative Sitemap value throws a bare TypeError | Re-sorted: rare; the test still fails loudly |
| GLM | NIT | The name `sitemap-0.xml` is never asserted, so a renamed child gets the wrong advice | Re-sorted: rare, and the test still fails; it belongs to a later `@astrojs/sitemap` that renames files |
| GLM | NIT | The checklist lost "robots.txt accurate" | Fixed: "`robots.txt` (naming it) + `llms.txt` accurate" |

Unverifiable, not counted: Bing's report of 2026-11-09 (Daniel's screenshots of 22 and 15 pages
for two sites; plan S2) and that `#` ends a line in robots.txt (RFC 9309).
