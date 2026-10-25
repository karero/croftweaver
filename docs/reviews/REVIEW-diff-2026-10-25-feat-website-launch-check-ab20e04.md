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
