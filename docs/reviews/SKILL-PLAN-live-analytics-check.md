# Plan: the launch check reads the live page and fails loudly when analytics is not what `src/config.ts` says

Base `origin/main` e66d445e · branch `plan/live-analytics-check` · review depth: High (an
instruction file agents load, a check script; the first five rounds reviewed a version that also
changed `ship.sh`) · red team: none (the change reads one public page and a local file; it
deletes, logs in to and moves nothing).

**Scope, narrowed by the maintainer, 2026-11-09** ("Yes, narrow it", relayed by the manager session): the
plain live check only. Not in scope: proving which build served the page, and any change to
`npm run ship`. Rounds 1 to 5 reviewed the wider plan; their trail stays in
`docs/reviews/REVIEW-plan-2026-11-09-live-analytics-check.md`.

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | This plan | narrowed 2026-11-09 | this file |
| 2 | PLAN gate, High | rounds 1-5 on the wider plan: Codex alone (melious out of balance), 10 BUG, 9 RISK; rounds 6-7 on this narrow plan, 4 BUG, 1 RISK; total 14 BUG, 10 RISK, all fixed; round 7's one BUG fixed by wording, not yet re-reviewed | `docs/reviews/REVIEW-plan-2026-11-09-live-analytics-check.md` |
| 3 | `skills/website-launch-check/scripts/check_live_analytics.py` and its tests, on real captures | built 2026-11-09 | 03b3dbee, a488e5a1; `make test-launch-check`: 43 tests OK |
| 4 | `website-launch-check` §8 runs it; BUGLOG release-notes row | built 2026-11-09 | 03b3dbee |
| 5 | `make check` and `make test-launch-check`, mutation check, live run, DIFF gate, then PR | checks done; DIFF gate and PR open | `make check` exit 0 at a488e5a1; mutation-check a488e5a: 3 killed, 0 survived; live run 2026-11-09 21:02Z on the guide: ✓, exit 0 |

## What and why

On 2026-11-08 guide.croftweaver.com switched analytics on (guide commit `7c3a130`, now on its
`production`) and counted nothing for a day. Its `src/config.ts:155` has the pre-0.35 line
`enabled: USE_ANALYTICS && process.env.CF_PAGES_BRANCH === PROD_BRANCH`; Workers Builds does not set
`CF_PAGES_BRANCH`, and the build variable its `PUBLISHING.md:36` asks for had not been added.
Nothing read the live page, so nothing said it had no Plausible tag.

The kit's analytics checks all work on builds. `tests/check_analytics_gate.sh` builds the site
the ways Cloudflare does and refuses the old line (lines 117 to 139), but a site's own CI does not
run it, and it cannot see a dashboard setting. The launch check's `analytics` setting
(`SKILL.md:52`) comes from `USE_ANALYTICS` and the README; no step fetches a live page for the
tag. A missing dashboard variable, a config line an update did not reach, or a production branch
that differs from `PROD_BRANCH` all pass silently.

Checked first, 2026-11-09: no open PR (#504, #505, #506 are other work), no branch, and no BUGLOG
row covers a live read. Nearest: the 2026-11-08 `stageOneGaps` row (build-side, stays open) and
the 2026-11-07 CLOUDFLARE_MOVE stage 1 row (fixed in #494). Workers-for-new-sites S4 checks the
built HTML, not the live page.

## Where it belongs

In `website-launch-check`, as a script beside `report_html.py`, run by the live run (§8) and
whenever the owner asks ("is analytics on the live site?", after turning it on or moving to
Workers). Not in `npm run ship`: the maintainer's decision. The launch check is copied into every site
with the other skills, so the script needs no new starter file.

## How

**A. `scripts/check_live_analytics.py <live address>`**, run in the site's folder (where
`src/config.ts` is), as `report_html.py` is run. It fetches `<address>/?cb=<random>` (Python's
`urllib`, redirects followed, 10 s timeout, User-Agent `croftweaver-launch-check`; a refusal such
as a 403 from a bot rule is exit 2, never a verdict), and reads `src/config.ts`: `USE_ANALYTICS` as
the gate reads it (`check_analytics_gate.sh:78-90`): one line `export const USE_ANALYTICS = true;`
or `= false;` (a `//` comment after it allowed); a file that never names `USE_ANALYTICS` counts
as on (a site made before the switch); a file that names it in any other form, or on more than one
such line, is exit 2. Then `scriptHost`, `scriptId` and `mode` with the gate's patterns (lines 93, 94, 103),
but only inside the `export const ANALYTICS = { … }` block, so a `mode:` in another object cannot
fail a healthy site. In the page, with HTML comments removed, it counts what the gate's counter
counts (`check_analytics_gate.sh:194-237`): `<script>` tags whose `src` is exactly
`<scriptHost>/js/<scriptId>.js`; inline scripts (no `type`, or `text/javascript`,
`application/javascript` or `module`) whose text matches `\bplausible\.init\s*\(`, as at
`check_analytics_gate.sh:220-221` (a mention: a JSON-LD script does not count, a commented call
does; whether the stub runs is the gate's `stub_runs`, at build time); and other analytics tags, a `src`
matching the gate's expression `/js/(?:script(?:\.[\w.-]+)?|pa-[\w-]+)\.js(?:[?#]|$)` (line 214:
`script.js`, `script.<parts>.js`, `pa-<id>.js`) or a `data-domain` attribute.

| `src/config.ts` | Expected on the page | Result |
|---|---|---|
| on, script mode | 1 script, 1 stub, 0 other | ✓, exit 0 |
| on, script mode | anything else | ✗, exit 1: what was found, then the causes below |
| off | 0 of each, and neither `/js/<id>.js` nor the id anywhere | ✓, or ✗ exit 1, saying which it found: an analytics tag ("the live page carries an analytics tag that `src/config.ts` has off"), or only the script's path or id in the text ("the live page names the analytics script or id; check whether it loads analytics") |
| on, server mode | 0 of each | ✓, or ✗ exit 1: "browser analytics on the page in server mode" |
| config lines it cannot read, or the page cannot be fetched (an error, a non-2xx answer, an empty body) | — | ✗, exit 2, naming what failed |

"1 script and 1 stub" is the starter's markup contract: what `Base.astro:174-177` writes, which
the gate also requires. The check compares the live page with it; it does not test Plausible's
loader.

The causes printed for "on, tag missing": the build that made the live site had analytics off; on
Workers Builds, the `enabled:` line must read `WORKERS_CI_BRANCH` (the 0.35 release notes) or the
build needs the variable `CF_PAGES_BRANCH=<PROD_BRANCH>`; on Pages, the project's production
branch must be `<PROD_BRANCH>`. Until then the page sends no visits from the browser; whether
anything counts them is not checked (a Pages site with `PLAUSIBLE_HOST` and `PLAUSIBLE_DOMAIN` set
still counts on the server, `functions/_middleware.ts:85-86,170-178`, whatever `src/config.ts` says).

It reads one page, the home page: the tag comes from `Base.astro`, and each cause above is
build-wide. A page on another layout is the gate's job at build time.

**B. `website-launch-check` §8**, one bullet beside HTTPS and the 404 status: run the script with
the live address. ✗ is a 🔴, quoting its lines (a tag missing: the browser sends no visits; a tag present with
analytics off: visits may be counted without the privacy page saying so; only the path or id seen:
🔴 until someone looks);
exit 2 is 🟡 "not checked: <its reason>". It reads the site folder's `src/config.ts`, so that
file must be the live one: after `git fetch`, `git diff --quiet origin/<PROD_BRANCH> --
src/config.ts`, run in the site folder, must succeed; otherwise the row is 🟡 "not checked:
`src/config.ts` here differs from the live branch". Baseline and pre-launch runs: "not checked
yet: not deployed".

The bullet also says, in plain words: **right after a publish, the live page may still come from a
cache, so its answer can be about the build before; run it again a minute later before acting on
a ✗.** Measured 2026-11-09 with `curl -I`: croftweaver.com (Pages) answers
`cf-cache-status: DYNAMIC` for `/` and `/?cb=<random>`; guide.croftweaver.com (Workers static
assets) answers `HIT` for both, so on Workers a fresh query is no proof of a fresh page.

**C. One "Next release notes" BUGLOG row**: the launch check now reads the live page for the
analytics tag.

## Not covered (named so nothing passes for checked)

- Which build served the page (out of scope, the maintainer 2026-11-09): a cached page can mislead, as B
  says.
- `npm run ship` does not run it (out of scope): a publish that turns analytics on is checked only
  when someone runs the launch check or the script.
- A Preview build that carries the tag: the gate covers it at build time.
- A wrong `scriptId` or host typed into `src/config.ts`: the tag matches the file, so this passes,
  as in the gate. Only Plausible's Verify step catches it.
- Whether Plausible records anything (needs Plausible's API and a key).
- A site whose `/` redirects to another page reads that page; the rule is the same.

## How it is tested

1. **Real captures** (the rule of 2026-10-26), committed under the skill's `scripts/tests/fixtures/`,
   trimmed by cutting, not editing, with host and date in the name:
   - `live-home-guide.croftweaver.com-2026-11-09.html`: the live page with the tag (curl on
     2026-11-09: 200, `build.txt` 87ad12e0, one `src=".../js/pa-ExampleId….js"` tag, one `plausible.init`).
   - `live-home-webcroft.dev-2026-11-09.html`: a live kit page with no tag, paired with a config that
     has analytics on: the guide's failure.
   - `live-home-older-tag-2026-11-09.html`: a real older tag (`data-domain`, `/js/script.js`).
   Expected values are written by hand from these notes, never copied from the script's output.
   The pages are whole: nothing needed cutting. `scripts/check_clean.sh` refuses a client's or a
   person's name in this public repo, so names, hosts and script ids in them are replaced with made-up
   ones (the one edit allowed), and the third capture is named for what it holds, not its host.
2. **`scripts/tests/test_check_live_analytics.py`** (`unittest`, run by `make test-launch-check`,
   `Makefile:66-67`, and by CI, `.github/workflows/clean.yml:449`; not part of `make check`). Each test runs the script as §8 does, `python3 <script> <address>` in a site
   folder, against a local `http.server` that serves the captures, so it enters through the real
   call: every row of the table, both off cases, server mode with an older tag, a config with an
   unrelated object that has its own `mode:` (still ✓), a 404, a 403, an empty 200 and a refused
   connection (each exit 2),
   and that the request carries a `cb` query; `USE_ANALYTICS` written `export const USE_ANALYTICS:
   boolean = false;` (exit 2, not "on"), a JSON-LD script naming `plausible.init()` (not a stub),
   `plausible.init ()` (a stub), and a page that only names the id in a paragraph (the second off
   message). One more case runs the gate's counter (the Perl
   heredoc inside `tags_program()` in `check_analytics_gate.sh`, read out of that file) on the same
   captures and a comment-only stub page, and requires the same three counts: agreement on these
   inputs only, not on every page.
3. **Mutation check** on the comparisons (flip an expected count, drop the off-case id search,
   read `mode` from the whole file), each to be KILLED.
4. **One live run** before the DIFF gate: the script on https://guide.croftweaver.com in the
   guide's folder (✓ expected), quoted in the PR.

## Verified, judged, and the strongest case against

Verified on 2026-11-09: the guide's config line and `PUBLISHING.md:36` (in
`~/Devel/croftweaver-guide` at 87ad12e); the live page now has the tag; the gate's readers and
counter (Codex ran the counter on the edge cases in rounds 1 to 4); the cache headers above; the
launch check's §8 and `Makefile:66-67`. Judgment: that the home page alone is enough; that the launch
check, not ship, is the right home (the maintainer's call).

Against: the guide's failure came after launch, and nothing runs the launch check then, so this
check catches it only when someone thinks to run it. A check in `npm run ship` would run at every
publish, but needs build proof to be trustworthy on Workers, which is what was cut.
