# Plan: after a publish, read the live page and fail loudly when analytics is not what `src/config.ts` says

Base `origin/main` e66d445e (`ship.sh` and `check_ship_push.sh` at template-version 0.26) · branch
`plan/live-analytics-check` · review depth: High (the starter's publish script; the skill's High
row names deploy code) · red team: none (the change reads one public page and a local file; it
deletes, logs in to and moves nothing, and a failure only changes the exit status of a publish
that has already gone out).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | This plan | written 2026-11-09 | this file |
| 2 | PLAN gate, High | rounds 1-2: Codex alone (melious out of balance), 4 BUG, 6 RISK, all addressed | `docs/reviews/REVIEW-plan-2026-11-09-live-analytics-check.md` |
| 3 | `scripts/check-live-analytics.mjs` and its test, on real captures; the live leg (test 6) | — | — |
| 4 | `ship.sh` calls it; `check_ship_push.sh` cases; markers 0.27 | — | — |
| 5 | `website-launch-check` §8 runs it; `whats-new` lists the new file; `PUBLISHING.md` line; BUGLOG release-notes row | — | — |
| 6 | `make check`, mutation check, DIFF gate at High, then PR | — | — |

## What and why

On 2026-11-08 guide.croftweaver.com switched analytics on (guide commit `7c3a130`, now on its
`production`) and counted nothing for a day. Its `src/config.ts:155` has the pre-0.35 line
`enabled: USE_ANALYTICS && process.env.CF_PAGES_BRANCH === PROD_BRANCH`; Workers Builds does not set
`CF_PAGES_BRANCH`, and the build variable its `PUBLISHING.md:36` asks for had not been added. The
publish went through, `build.txt` matched, and nothing said the live page had no Plausible tag.

The kit has two checks of this, and neither reads the live site. `tests/check_analytics_gate.sh`
builds the site the ways Cloudflare does and would have refused the old line (its 0.35 Workers
check, lines 117 to 139), but a site's own CI does not run it, and it cannot see a dashboard
setting. The launch check's `analytics` setting (`SKILL.md:52`) is read from `USE_ANALYTICS` and the
README; no step fetches a live page for the tag. So a missing dashboard variable, a config line an
update did not reach, or a production-branch setting that differs from `PROD_BRANCH` all pass
silently. This is not one site's problem: any owner who turns analytics on after launch, or moves
to Workers, can hit it.

Checked first, 2026-11-09: no open PR (#504, #505, #506 are other work), no branch, and no BUGLOG
row covers a live read. Nearest: the 2026-11-08 `stageOneGaps` row (the move script does not
check the `enabled:` line; build-side, stays open) and the 2026-11-07 CLOUDFLARE_MOVE stage 1 row
(fixed in #494, docs). Workers-for-new-sites S4 checks the built HTML of both builds, not the live
page.

## Where it belongs: both, with one piece of code

- **`npm run ship`**, because it runs on every publish. The guide's case came after launch, from a
  commit that turned analytics on; only a check that runs at each publish sees that. Ship already
  waits until the live `build.txt` shows the pushed commit, so the build is Active and the
  first-request-caches-a-404 trap (`PUBLISHING.md`) cannot apply. That the home page comes from the
  same build is not implied by the marker alone (another publish can follow, `ship.sh:995-1001`), so
  B reads `build.txt` again after the page.
- **The launch check's live run (§8)**, because it is where an owner who deploys by command, or
  whose site predates the new ship, gets the same read once, and where a 🔴 stops a launch.
- The logic lives in one new starter file both call, so the two cannot disagree.

## How

**A. `scripts/check-live-analytics.mjs <page.html>`** (Node; ship's pre-push gate already needs
Node). It reads `src/config.ts` in its own site folder (found from its own path, as `verify.mjs`
does): `USE_ANALYTICS` from its top-level line, with the gate's pattern
(`check_analytics_gate.sh:79`; no line counts as on, as in the gate); `scriptHost`, `scriptId` and
`mode` with the gate's patterns (lines 93, 94, 103), but only inside the `export const ANALYTICS =
{ … }` block, so a `mode:` in another object cannot make a healthy publish fail. It counts, in the
HTML with comments removed: `<script>` tags whose `src` attribute is exactly
`<scriptHost>/js/<scriptId>.js`; inline scripts whose text contains `plausible.init(` (a mention,
counted as the gate's counter counts it; whether the stub runs is the gate's `stub_runs` at build
time, and this check claims only that the markup is there); and other analytics tags: a `src`
matching the gate's own expression `/js/(?:script(?:\.[\w.-]+)?|pa-[\w-]+)\.js(?:[?#]|$)`
(`check_analytics_gate.sh:214`: `script.js`, `script.<parts>.js`, `pa-<id>.js`; not, say,
`scriptfoo.js`), or a `data-domain` attribute. It does not fetch anything: the caller passes the
file.

"1 script and 1 stub" is the starter's markup contract: what `Base.astro:174-177` writes, which
the gate also requires. The check compares the live page with that contract. It does not test
Plausible's loader. The loader agrees with the contract as far as was read: the live
`analytics.m-squad.com` loader (`pa-3TCz….js`, fetched 2026-11-09, 6,188 bytes) ends
`plausible.o&&S(plausible.o),plausible.init=S`, so it calls its start function only when the
stub's `init()` has set `plausible.o` (it also installs `plausible.init` for a later call). Read,
not run.

| `src/config.ts` | Expected on the page | Result |
|---|---|---|
| on, script mode | 1 script, 1 stub, 0 other | ✓, exit 0 |
| on, script mode | anything else | ✗, exit 1: what was found, then the causes below |
| off | 0 of each, and neither `/js/<id>.js` nor the id anywhere | ✓ or ✗ (exit 1: "the live site loads analytics that `src/config.ts` has off") |
| on, server mode | 0 script, 0 stub | ✓ with "server mode counts from the Function; this check cannot see that counting"; a tag is ✗ (counted twice) |
| unreadable config lines, or an empty page | — | ✗, exit 2, naming what it could not read |

The causes printed for "on, tag missing": the build that made the live site had analytics off; on
Workers Builds, the `enabled:` line must read `WORKERS_CI_BRANCH` (the 0.35 release notes) or the
build needs the variable `CF_PAGES_BRANCH=<PROD_BRANCH>`; on Pages, the project's production
branch must be `<PROD_BRANCH>`; until then the live site counts no visits.

It reads one page, the home page: the tag comes from `Base.astro`, and every cause above is
build-wide. A page on another layout is the gate's job at build time, not this one's.

**B. `ship.sh`**, in the branch where the live `build.txt` equals `$id` (line 993), before
`finish` and `exit 0`, while the worktree still exists: fetch `$site/?cb=<random>` with the same
`curl -sfL -m 8` as the `build.txt` loop, into a file in the run's temporary folder; then read
`$site/build.txt?cb=<random>` once more. Only when it still shows `$id` is the page judged, by
`node "${wt:-.}/scripts/check-live-analytics.mjs" <file>`. In worktree mode that is the published
commit's copy and its `src/config.ts`.
- The second `build.txt` read shows another commit: `⚠ Analytics on the live site not checked:
  the live site changed to build <sha> while it was read`, and the run ends as it does today.
- The fromGitHub branch has just found a newer push to GitHub's `production` (`ship.sh:999`): no
  read; `⚠ Analytics on the live site not checked: a newer publish was pushed to production`.
- The second `build.txt` read fails (timeout, HTTP error, empty answer): ✗, exit 1, as for a
  failed page fetch: `✗ Analytics on the live site not checked: build.txt could not be read again`.
- ✓: its one line is printed, then today's success line.
- ✗ (exit 1 or 2), or the fetch fails: the publish is live, so the success line still says the
  build is live; the check's lines follow with `✗ Analytics on the live site: …`, and ship exits 1.
- The file is missing (a site that took the new `ship.sh` but not the script):
  `⚠ Analytics on the live site not checked: scripts/check-live-analytics.mjs is missing (whats-new
  offers it)`, exit 0. Loud, but no failure, since the publish itself was verified.
- No `site:` address, a stop, or the old-build timeout: unchanged; no analytics read.
- Markers: `ship.sh` and `check_ship_push.sh` to 0.27.

**C. `website-launch-check` §8**, one bullet: on the live domain, fetch the home page as ship does
and run the script. ✗ is a 🔴 (visits uncounted, or counted with analytics off), quoting its
lines. The site has no script: 🟡 "not checked: `scripts/check-live-analytics.mjs` missing",
with the offer to update. Baseline and pre-launch runs: "not checked yet: not deployed".

**D. Wiring.** Add the file to `whats-new.sh`'s `TEMPLATE_TRACKED` list and its site-copy names
(lines 80 and 454), and whatever `check_template_coverage.sh` asks of a new starter file (read it
when building; not checked here). One sentence in `PUBLISHING.md` where it describes ship's live
check. One "Next release notes" BUGLOG row: the new file, and that the guide-style failure now
stops `npm run ship`.

## Not covered (named so nothing passes for checked)

- A Preview build that carries the tag (every look counted as a visit): ship publishes
  `production` only and does not know a Preview address. The gate covers it at build time.
- A wrong `scriptId` or host typed into `src/config.ts`: the tag matches the file, so this passes,
  as in the gate. Only Plausible's Verify step catches it.
- Whether Plausible records anything. That needs Plausible's API and a key; out of scope.
- Sites on older kits (the guide's `ship.sh` is 0.23) get this only when they take the update.
- Freshness of the page. Measured 2026-11-09 with `curl -I`: croftweaver.com (Pages) answers
  `cf-cache-status: DYNAMIC` for `/` and for `/?cb=<random>`; guide.croftweaver.com (Workers static
  assets) answers `HIT` for both, so on Workers the query does not make a fresh cache key. There
  the read rests on one assumption, not checked: a Workers deployment serves `build.txt` and the
  HTML from the same version, so a `build.txt` showing `$id` means the page is from `$id` too.
  Test 6 checks it on a throwaway before the DIFF gate; if it fails, B's design changes first.
- Two `build.txt` reads around the page narrow the window in which another build could go live;
  they do not close it.

## How it is tested

1. **Real captures, before round 1 of the DIFF gate** (the rule of 2026-10-26). Committed under
   `tests/fixtures/`, trimmed by cutting, not editing, with host, date and build in the name:
   - `live-home-guide.croftweaver.com-2026-11-09-87ad12e.html`: today's live page, with the tag
     (curl on 2026-11-09: 200, `build.txt` 87ad12e0, one `src=".../js/pa-3TCz….js"` tag, one
     `plausible.init`).
   - `live-home-webcroft.dev-2026-11-09-30fd7ea.html`: a live kit page with no tag (checked the
     same day), paired in the test with a config that has analytics on: the guide's failure.
   - `live-home-m-squad.com-2026-11-09.html`: a real older tag (`data-domain` with `/js/script.js`),
     the "other" category.
   Expected values written by hand from these notes, never copied from the script's output.
2. **`tests/check_live_analytics.sh`**: each row of the table in A against the captures and small
   configs, including both off cases, server mode, and a config with an unrelated object that has
   its own `mode:` (must still pass), exit codes checked; plus one consistency
   case that runs the gate's counter (the Perl heredoc inside `tags_program()` in
   `check_analytics_gate.sh`, read out of that file, since the gate runs builds when sourced) on
   the same captures, plus one page with a stub mention in a comment-only inline script, and
   requires the same script, stub and other counts. That shows the two agree on these inputs
   only; it does not prove they agree on every page.
3. **Through production's call**: new `check_ship_push.sh` cases drive the real `ship.sh`, its
   stubbed `curl` serving the captures for `/` after `build.txt` matches: on + tag → exit 0 and the
   ✓ line; on + no tag → the success line, the ✗ lines, exit 1; script missing → ⚠, exit 0; home
   page fetch fails → ✗, exit 1; the second `build.txt` read shows another commit → ⚠, no
   judgment; the second read fails → ✗, exit 1; fromGitHub with a newer push → ⚠, no read.
   Run on the default bash and on the Mac's bash 3.2, as CI does.
4. **Mutation check** on the script's comparisons and ship's new branch (remove the call, flip an
   expected count, drop the off-case id search), each to be KILLED.
5. Wired into `template-tests.yml` beside the gate.
6. **Live leg, before the DIFF gate**, on a throwaway Workers site under webcroft.dev, deployed by
   Workers Builds and removed afterwards: publish with analytics off, then on, with `npm run ship`
   each time, and read `/`, `/?cb=<random>` and `/build.txt` right after each. Passes when the new
   `build.txt` and the new page arrive together on every read (the assumption above), ship's
   verdict follows the switch, and a build made without the branch variable (the guide's failure,
   reproduced) ends ship with the ✗ lines and exit 1. Connecting Workers Builds to a repo may need
   Daniel in the Cloudflare dashboard; if the throwaway token cannot do it, he is asked then.

## Verified, judged, and the strongest case against

Verified on 2026-11-09: the guide's config line and `PUBLISHING.md:36` (read in
`~/Devel/croftweaver-guide` at 87ad12e); the live page now has the tag; `ship.sh` lines 954 to
1030 (the live loop, `curl` stubbed in its test); the gate's readers and counter; the
`whats-new.sh` list. Judgment: that the home page alone is enough; that a missing script warns
rather than fails; that a failed check exits 1 after a publish that went out (ship's old-build
warning already does that, so owners have seen it).

Against: a check placed in ship reaches only sites that update `ship.sh`, and the guide, which had
the problem, runs 0.23. A plain line in the launch check, done by hand with `curl | grep`, would
cost no new starter file, no `whats-new` entry and no review of ship. The plan keeps ship because
the failure it targets happens after launch, when no launch check runs.
