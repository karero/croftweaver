# DIFF review — feat/website-launch-check — the launch check moves into Croftweaver

Depth: **Normal** (skill text agents load, a script and its tests, a CI job). Seats: codex
(gpt-6.1-sol, read-only) and melious (glm-5.3), and a fresh-eyes pass (Claude Sonnet, Agent tool)
in round 1. The owner consented in chat, this session (2026-10-25), to "send the PR A and PR B
diffs (public Croftweaver code, no secrets) to Codex and to GLM 5.3 on melious.ai, plus a Sonnet
fresh-eyes pass in round 1": "Yes, for both PRs (Recommended)". The behaviour trial is recorded in
`docs/reviews/TRIAL-website-launch-check-2026-10-25.md` (run before round 1; its fixes are in the
reviewed head).

## Round 1 — `ab20e044`, base `8ec4cb88`
`reviewers: codex OK, melious OK` · `timings: codex 399s (112150 tokens), melious 393s (57534
tokens)` · fresh-eyes 1079 s, 203,833 tokens · gate `20261025T064840Z-71964`. melious's reply had
no final-review marker; its findings were read from the end, as the script advises.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C2 | BUG | codex | fixed | A redirect line alone was taken as proof; now its target must be the decided address and an internal target must exist in `dist/` (`relaunch.md` §2) |
| C5 | BUG | codex | fixed | Escaped and decoded addresses were merged; now counted as `check_move.py`'s `page_form` does, nothing decoded (`/a%2Fb` and `/a/b` stay two) |
| C6, G4 | BUG (G: NIT) | codex, melious | fixed | A target with parentheses was cut short and `![x](y)` became a link; the LINK pattern takes one balanced pair, an image is text; tests added |
| C7 | BUG | codex | fixed | The comparison's E-E-A-T table had two of the five rows |
| E1 | BUG | fresh-eyes | fixed | Built pages are files (`build.format: 'file'`): `dist/about.html` is `/about` |
| E2 | BUG | fresh-eyes | refuted | "The tests use another port, so a running preview cannot collide": the trial measured Astro refusing a second preview ("Another astro preview server is already running"); the instruction now also says how to read the console |
| E3 | BUG | fresh-eyes | fixed | The docstring overclaimed; it now says what is shown as text, and that emphasis does not reach across a link |
| C1 | RISK | codex | fixed | The consent sentence now speaks of § 25 consent only and leaves the privacy page's legal basis to the owner |
| C3 | RISK | codex | refuted | Passing titles certify edited tests: the plan's decision D2 (PLAN gate rounds 3–5, redesigned) trusts the site's tests "as they stand", and the report says so in those words |
| C4 | RISK | codex | fixed | A config filter could hide `placeholders.spec.ts`; every spec must now show a line, a missing placeholders spec is a 🔴 blocker |
| G1 | RISK | melious | fixed | A test in the skill's suite now fails when the starter renames a test title or warning the mapping names (`LAUNCH_CHECK_REQUIRE_STARTER=1` in `make test-launch-check`, so it cannot skip there; mutation: renaming `seo — head contract on` fails it) |
| G2 | RISK | melious | fixed by citing | The query claim is `make_redirects.py`'s own header ("an address with a query (/?p=12) cannot be matched by _redirects"); `relaunch.md` now cites it |
| E4 | RISK | fresh-eyes | fixed | Four escaping mutations survived the tests (title, unsafe link fallback, th, blockquote); one hostile payload through every construct now fails each of them (mutation-checked) |
| E5 | RISK | fresh-eyes | refuted | The style test pins the constant to itself: D7 narrowed that claim in the PLAN gate; the test asserts no `url(` and no `@import` and makes no other claim; the new CSP meta (E7) is what the browser enforces |
| E6 | RISK | fresh-eyes | fixed | `seo — head contract on /` is a substring of the other pages' titles; the title must end with the page |
| E7 | RISK | fresh-eyes | fixed | A `Content-Security-Policy` meta (`default-src 'none'; style-src 'unsafe-inline'`) now tells the browser to load nothing; tested |
| G3 | NIT | melious | fixed | `--rebuild` rebuilds pages that exist; SKILL.md says so |
| G5 | NIT | melious | fixed | An ordered list keeps its start number |
| G6 | NIT | melious | fixed | A `---` under a line with a pipe made a table; a rule line now needs a pipe |
| E8 | NIT | fresh-eyes | fixed | `mkdir -p docs/launch` before the first write |
| E9 | NIT | fresh-eyes | fixed | "Both legal pages": now the imprint where the site has one, and the privacy or Datenschutz page |
| E10 | NIT | fresh-eyes | fixed | `python3` is not in the site's permission list: SKILL.md says Claude Code asks |
| E11 | NIT | fresh-eyes | fixed | `# C#` lost its `#`; a closing hash sequence needs a space before it; tested |
| E12 | NIT | fresh-eyes | fixed | A relative link may carry a `#fragment` |
| E13 | NIT | fresh-eyes | fixed | WHAT-THE-SKILLS-RUN now names the preview and the scratch file of test output |

Not changed: an `HTTPS://` (upper-case) link stays text, on purpose (the strict pattern); a `|` in
a code span inside a table cell still splits the cell (rare in reports). Substantive BUGs: C2, C5,
C6, C7, E1. Round 2 owed. Fixes in `56f1c789`; `make check` exit 0 there, `make test-plugin` 19
passed and 1 skipped (the release-tag test, run only at a release).

## Round 2 — verification of `56f1c789` against `ab20e044`
`reviewers: codex OK, melious OK` · `timings: codex 257s (111862 tokens), melious 287s (35949 tokens)`

| id | sev | seat | status | why |
|---|---|---|---|---|
| C8 | BUG | codex | fixed | C2's fix compared a redirect line with the literal decision; `make_redirects.py` follows chains (its header: `/a -> /b -> /c` writes `/a -> /c`), so the target is now where the decisions lead, counted as in §1 (also G8's NIT) |
| C9, G9 | BUG (G: NIT) | codex, melious | fixed | E6's "page at the title's end" cannot match the image test's title; now the page goes in place of `<page>` and the whole title is matched |
| C10 | BUG | codex | fixed by a cut | E3's docstring still overclaimed (`![a `code`](i.png)` renders code inside the shown text); the claim is now only what is true: it writes no image and no raw HTML |
| C11 | RISK | codex | refuted | Cloudflare's query matching: `relaunch.md` relays `make_redirects.py`'s own header, which states it from measurements on two live kit sites (October 2026); the launch check makes no claim of its own and writes no redirect |
| C12 | RISK | codex | fixed by narrowing | Browser enforcement of the CSP meta is untested; the comment now says the tests check the tag, not a browser |
| C13 | RISK | codex | refuted | Astro's file-per-page output: the trial's build has `dist/leistungen.html`, `dist/impressum.html`, `dist/index.html` (`build.format: 'file'` in the starter) |
| C14 | RISK | codex | fixed | The test's own copy of the link pattern lacked the `#fragment` the script now allows |
| G10 | RISK | melious | fixed | A config `grep` keeping part of `placeholders.spec.ts` could hide warnings while the spec still shows a line; the mapping now requires `placeholders — no leftover on <page>` per page, a missing one a 🔴 blocker |
| G11 | RISK | melious | fixed | The coupling test hard-coded two titles; it now reads every per-page title and warning prefix from the mapping (mutation: renaming the placeholder title fails it) |
| G12 | NIT | melious, outside scope | refuted | "A link inside an inline code span becomes a link": `inline()` splits code spans first and escapes them, so links inside stay literal (`test_code_keeps_markdown_and_links_literal`) |

Substantive BUGs: C8, C9, C10. Round 3 owed. Fixes in `f691d9ff`.

## Round 3 — verification of `61b36e2c` against `56f1c789`
`reviewers: codex OK, melious OK` · `timings: codex 191s (70402 tokens), melious 140s (18182 tokens)` · no BUG.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C15 | RISK | codex | fixed by a cut | G10 again: the per-file test `placeholders — no leftover in /manifest.webmanifest` was not required, so a filter could still hide warnings. The test-filter kind came back (round 1 C4, round 2 G10), so it is cut, not patched: the starter's `playwright.config.ts` filters nothing, and a site whose config sets `grep`, `grepInvert`, `testIgnore` or `testMatch`, or moves `testDir`, gets a 🔴 blocker and nothing left to the tests. With `npx playwright test` and that rule, every test runs. Earning |
| C16 | RISK | codex | refuted | C11 re-raised with no new evidence (same source, `make_redirects.py`'s header) |
| C17 | RISK | codex | refuted | C13 re-raised; the build listing is the evidence: the trial's `dist/` holds `404.html`, `datenschutz.html`, `impressum.html`, `index.html`, `intern.html`, `leistungen.html` (and `ueber-uns.html`) |
| G13 | NIT | melious | fixed | The coupling test matched a title in any spec; it now pairs each mapping row's title with that row's spec (mutation: moving the image title's spec to `seo.spec.ts` fails it) |
| G14 | NIT | melious | fixed | The title and warning patterns were narrower than what they guard; every `<page>` row must parse, and every `⚠…:` span is checked |
| G15 | NIT | melious | fixed | "the warning below" in a table cell; now points at "Warnings in the output" |

Round 4 earned by C15 (test-filter, cut). Fixes in `571ace8e`.

## Round 4 — verification of `5e92ed22`, earned by C15 (`--earned-by test-filter`, cut as above)
`reviewers: codex OK, melious OK` · `timings: codex 102s (35600 tokens), melious 88s (10597 tokens)` · no BUG.

| id | sev | seat | status | why |
|---|---|---|---|---|
| C18 | RISK | codex | fixed | A `test.only` left in a spec narrows the run outside CI (`forbidOnly` is on only when `CI` is set). The run is now `npx playwright test --forbid-only` (the flag is in Playwright 1.64.1's `--help`: "Fail if test.only is called"), so focus fails the run, a 🔴 blocker. A refusal of the input, not another required title |
| G16 | RISK | melious | fixed | "The starter's config filters nothing" had no guard; the coupling test now asserts `testDir: './tests'` and no `grep`, `grepInvert`, `testIgnore` or `testMatch` in the starter's config (mutation: adding `grep` fails it) |
| G17 | NIT | melious | fixed | The row count matched `<page>` anywhere in a row; now only in the title column |

Round 5 earned by C18 (test-filter: the fix refuses the input). Fixes in `c66f7e3c`.
