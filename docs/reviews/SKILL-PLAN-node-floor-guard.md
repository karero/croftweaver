# Plan: the starter's Node floor, held by a check and enforced as a warning

A second pull request, after the one for the Astro 7.4.2 bump (#377, planned stacked on it, merged before this was built, so the branch starts from `main`). It
closes the three items that review waived for that PR. Written 2026-10-22, before any of it is built;
this is the seventh version, after five rounds of its own review and a closing full read: round 1 (33 findings from three reviewers, merged into 19 rows and answered in the second version), round 2 (2 BUG, 6 RISK, 5 NIT; answered in the third), round 3 (3 BUG, 4 RISK, 3 NIT; answered in the fourth), round 4 (2 BUG, 1 RISK, 4 NIT; answered in the fifth), round 5 (2 BUG-labelled wording errors, rated not substantive, 1 RISK, 4 NIT; answered in the sixth) and the closing full read by another model (0 BUG, 3 RISK, 2 NIT; answered here).

## Why

Astro raised its Node minimum twice in three releases (7.3.8: 22.12.0, 7.4.0: 22.22.0, 7.4.2: 22.23.4),
the last time because of Node's October 2026 security releases. The starter states the floor in several
places, a Dependabot bump changes none of them, and CI cannot see the gap. Astro also skips its own Node
check above Node 23 (`astro/bin/astro.mjs`: `skipSemverCheckIfAbove = 23`), so the starter's `engines`
(`>=22.23.4`) lets Node 24.0 and 26.0 through, though the fixed versions are 24.22.1 and 26.12.1. And
the installer's source says its floor is "the same as the site template's", which has stopped being true.

Sources: Node's advisory page, https://nodejs.org/en/blog/vulnerability/october-2026-security-releases
(read raw 2026-10-22: 10 CVEs, 4 High, 3 Medium, 3 Low; fixed 22.23.4, 24.22.1, 26.12.1); Astro's 7.4.2
release notes (the `withastro/astro` releases: "Bumps the minimum supported Node.js version to 22.23.4,
which includes the fixes from the October 2026 Node.js security releases"); Node's release index,
https://nodejs.org/dist/index.json, which carries a `security` flag per release.

## Where the floor is stated, and what the check does with each place

| Place | Ships in the zip? | What it states | The check |
|---|---|---|---|
| starter `package.json` `engines.node` | yes | the range: the source of truth | G1 (inside Astro's), G4 (`.nvmrc` and CI major) |
| starter `package-lock.json`, root `engines.node` | yes | a copy | G2 (equal to `package.json`) |
| starter `package-lock.json`, `node_modules/astro` `engines.node` | yes | Astro's own range | read by G1 |
| starter README: the tree comment, step 2 | yes | the lowest version only (the per-line fixed versions are removed: "keep Node current; SETUP.md lists the fixed version of each line") | G3, one phrase each |
| `templates/SETUP.md` | yes | the lowest version, and the fixed version of each line | G3, one phrase for each |
| `new-website/SKILL.md` | yes | the same | G3 |
| `docs/UPGRADING.md` | yes | the fixed version of each line, odd lines named unsupported (build review, round 2: "22.23.4 or newer" alone reads as fine on Node 23 and 25, which `engines` refuses) | G3 |
| root `README.md` | yes | no number for the site (a pointer to the setup guide); the installer's own 22.12 stays, as the installer's floor | — |
| the starter's `ci.yml` comment | yes | no number: "the floor in `package.json`'s engines" | — |
| `.github/dependabot.yml` comment | **no** (root `.github/` is not in the zip) | no number: "engines never goes below Astro's floor; see `package.json`" | not read |
| the installer: `index.mjs` comment, its README | **no** (`packages/` is not in the zip) | no number for the site: "building a site needs more: see SETUP.md" | not read |
| `docs/BUGLOG.md` | **no** | history | not read |

The check may read only files that ship, because CI runs `make check` inside the unzipped zip and a zip
recipient runs it with no git (`.github/workflows/clean.yml`, the `macos-stock-tools` job, and
`Makefile:18`). The number is removed from every place that does not need it, so there is less to go stale.

## What changes

**A. `scripts/check_node_floor.sh`** (run by `make check` and CI; the parser is `node`). It fails, naming
the file, when any of these is false:
- **G1.** The starter's `engines.node` admits no version that Astro's own range (the lockfile's
  `packages["node_modules/astro"].engines.node`, offline) refuses, and the starter's lowest version is
  not below Astro's. A line may be stricter than Astro's, never looser. This catches Astro raising any
  line's minimum, not just the lowest.
- **G2.** The lockfile's root `engines.node` (`packages[""]`) equals `package.json`'s.
- **G3.** The anchored phrases, matched one line at a time (the check never joins lines; a blockquote's leading `>` and leading
  spaces are ignored), each exactly once, and written in the docs so that each sits on one line (a rewrap
  that splits one gives red, "phrase not on one line", which is the intended loud failure; the test wraps a
  blockquote to show it, and the phrases are run against the real files once B's sentences exist); the versions they capture equal the starter's own `engines`, not Astro's (the docs follow
  `package.json`):

  | File | Phrase (a regular expression; the captures are checked) | Expected |
  |---|---|---|
  | starter README | `the starter needs >=([0-9.]+) \(Cloudflare Pages reads it\)` | the lowest |
  | starter README | `Requires \*\*Node ≥([0-9.]+)\*\*` | the lowest |
  | `templates/SETUP.md` | `\*\*Node ≥([0-9.]+) required\*\*` | the lowest |
  | `templates/SETUP.md` | `current security fixes are in \*\*([0-9.]+), ([0-9.]+) and ([0-9.]+)\*\*` | the minimum of the 22, 24 and 26 alternatives |
  | `new-website/SKILL.md` | `This starter needs Node ≥([0-9.]+)\*\*, and Node's current security fixes are in ([0-9.]+), ([0-9.]+) and ([0-9.]+)` | the lowest, then the three minima |
  | `docs/UPGRADING.md` | `must be ([0-9.]+) or newer on Node 22, ([0-9.]+) or newer on Node 24, or ([0-9.]+) or newer` | the minimum of the 22, 24 and 26 alternatives (changed from the lowest only, build review round 2) |

  The version-bearing phrases say what is required now ("current security fixes"), not history
  ("October 2026"), so a later floor change moves them together with `engines` and the check can demand
  it without forcing a false statement about the past. B changes the two sentences accordingly.
- **G4.** The major in `.nvmrc` and in the starter's `ci.yml` `node-version` is admitted by some alternative, meaning that alternative's interval intersects that major's (`[M.0.0, M+1.0.0)`): `^24.22.1` intersects 24, nothing intersects 25. A value it cannot read (`.nvmrc` saying `v24` or `lts/*`, a `node-version` that is not a plain major) fails with "cannot read", like the range reader.
- **G5.** The set of lines is pinned: `engines` has exactly one alternative per major, and the number of
  alternatives equals the number of versions the `SETUP.md` and `SKILL.md` phrases list (three: 22, 24, 26),
  whose captures are the alternatives' minima in ascending order. Adding `|| ^25.9.0` (which would admit a
  line that gets no fixes, and still pass G1 as a subset of Astro's open range) or dropping the 24
  alternative is red, with "engines names N lines, the docs list 3: change the phrase table on purpose".
- **No scan for unlisted places.** The second and third versions had one. Two rounds of review found it
  flagging the check's own script and then the root README, and left its match rules (a year such as 2026,
  bare majors, letter case, which majors) open: the same kind of defect twice, so it is cut, not patched
  again. The table is the list; the numbers are kept to the files in it; and D's release step greps for each
  distinct version in `engines`, before and after a floor moves, so a person sees every place that states one.

It reads `||`-joined alternatives, each `>=X[.Y[.Z]]` or `^X[.Y[.Z]]`, with optional spaces after the
operator and around `||`. Anything else, a bare `22`, `22.x`, `~22.23`, `20 || >=22`, fails with "cannot
read this range": a person extends the reader on purpose, and the check never passes on a range it did
not understand. It reads JSON by key, so a
missing `engines` on the astro entry cannot be mistaken for the next entry's. It reads only Astro's range:
a transitive package's own floor is not checked (said in the header). A documented `--admits '<range>'
<version>` mode exists for the test only. Without `node` the script prints one `SKIP` line and exits 0,
and with `REQUIRE_NODE_FLOOR=1`, which both CI jobs set, it prints the same line and exits 1: a skip turned into a failure. The variable is implemented in each of the two new scripts.

**B. The Node security fixes in `engines`.** Astro 7.4.2's own range, as the lockfile records it, is
`{ node: '>=22.23.4', npm: '>=9.6.5', pnpm: '>=7.1.0' }`, open above, so the starter's `engines.node`
becomes `^22.23.4 || ^24.22.1 || >=26.12.1` (inside it, and stricter on 24 and 26) in `package.json`, regenerated into the lockfile root with `npm install --package-lock-only` (not edited
by hand). npm then warns, at install time, on a Node older than the fixed version of its line, and on
Node 23 and 25, which get no fixes. `new-website/SKILL.md` gets one sentence: when `npm install` prints
`EBADENGINE` for the site's own package (the `name@version` in the site's `package.json`, whatever the owner
named it) and `node`, stop and have the owner update Node (SETUP.md); a warning for another package is
not this. The parentheticals "the floor of the Astro this starter ships" (SETUP.md, the starter README) become "this starter's
floor, never below Astro's own", and `new-website/SKILL.md`'s "**Astro needs Node ≥22.23.4**" becomes "**This starter needs Node ≥22.23.4**"; all stay true when the starter is stricter than Astro.
`SETUP.md` and `new-website/SKILL.md` say "current security fixes" (not "October 2026") beside the three
versions; the starter README keeps only the lowest version and points to SETUP.md. `docs/UPGRADING.md` says
"`node --version` must be 22.23.4 or newer on Node 22, 24.22.1 or newer on Node 24, or 26.12.1 or newer (Node 23 and 25 are not supported)"
(it was to keep only the lowest; the build review's round 2 found that reads as fine on Node 23 and 25).
`SETUP.md` and the starter README say a new site
gets the warning ("a new site's `package.json`"), because `package.json` is the site's own file for
`whats-new` and an existing site keeps the one it has. The starter README's step 3 says the overlay's
`package.json` is the one to use, so `engines` reaches the site.

**C. The installer** (`packages/create-croftweaver`): the comment at `index.mjs:257` and the README's
line 16 say the installer's own floor (22.12) and "building a site needs more: see SETUP.md", with no
number for the site; version 0.2.0 to 0.2.1. The installer's floor stays 22.12 (raising it is a separate
decision). The owner publishes 0.2.1 after 0.33 is live: the pre-publish check would pass against v0.32
too, but the README's sentence is true only for a starter from 0.33.

**D. Around it.** The public README's release section gets a paragraph and the commands for comparing
`engines` with Node's newest security release per line (the release index's `security` flag), run at
each release, so the compensation for the check's deliberate blindness to Node releases is written
where a maintainer reads it, with `git grep -n -F` for each distinct version in `engines`' alternatives, run before the floor moves (to find the places to update) and after (for each old version, to find a place left behind); a hit outside the files in the table (the starter's `package.json` and lockfile, its README, `SETUP.md`, `new-website/SKILL.md`, `docs/UPGRADING.md`) is a place the check does not cover. Expected hits that are not findings: the history rows of `docs/BUGLOG.md`, and the installer's own 22.12 (the root README and `packages/create-croftweaver`). `docs/BUGLOG.md`: the guard and installer-comment rows close, and the
release-notes row says that a new site's `engines` makes npm warn on any Node outside `^22.23.4 || ^24.22.1 || >=26.12.1`: a Node older than the fixed version of its line, Node 23 and 25, and any line older than 22.
After the merge the owner is asked to add the `node-floor` job to the "main checks" ruleset's required
checks (the list is by job name, so a new job blocks nothing until it is added); that is a repo setting,
and it is his to approve.

## Scenarios

| # | Given | When | Then |
|---|---|---|---|
| 1 | Dependabot bumps Astro to 7.5.0, whose range is `>=22.30.1`; the starter still says 22.23.4 | CI | `node-floor` red: "Astro needs 22.30.1, `engines` admits 22.23.4", with the files |
| 2 | Astro's range becomes `^22.23.4 \|\| ^24.30.0` (it raises a different line) | CI | red: `engines` admits `24.22.1`, which Astro refuses |
| 3 | `engines` updated, `SETUP.md` still names the old version | CI | red, naming `SETUP.md` and its phrase |
| 4 | Everything updated | CI | green |
| 5 | `engines` is `>=22.12.0`, Astro's `>=22.23.4` | `make check` | red: looser than Astro's |
| 6 | `engines` is `^22.24.1 \|\| ^24.22.1 \|\| >=26.12.1` (a Node security release, Astro unchanged) and the docs say 22.24.1 | `make check` | green: lines may be stricter than Astro's |
| 7 | `engines` is `22.x`, `~22.23` or `20 \|\| >=22` | `make check` | red: "cannot read this range" |
| 8 | Astro's range is spelled `>= 22.30.1`, `>=22` or `>=22.30` | `make check` | read correctly, no red over spacing |
| 9 | The lockfile's root `engines` differs from `package.json`'s (round 1's own BUG) | `make check` | red |
| 10 | The astro entry has no `engines` but the next entry has one | `make check` | red: "Astro's entry has no `engines`"; not "Astro needs 4" |
| 11 | `package.json` has no `engines` | `make check` | red |
| 12 | A listed file is missing, or its phrase is missing or twice | `make check` | red, naming it |
| 13 | `.nvmrc` says 25 | `make check` | red: no alternative admits Node 25 |
| 14 | A new doc states the floor and is not in the table | `make check` | green: the check does not look for unlisted places (a known limit); the release step's grep lists it |
| 15 | An owner's Node is below the range (measured: Node 26.12.0, below 26.12.1) | `npm install` in a new site | npm prints `EBADENGINE` for `site@1.0.0` and `node`, exit 0; the assistant stops and has the owner update Node |
| 16 | An owner's Node is 24.22.1 | `npm install` | no `EBADENGINE` for `node` (another package's warning is not this) |
| 17 | An owner on Node 22.12 runs the installer, then builds a site | the installer starts; later `npm install` | the installer runs; `npm install` warns; the installer's README says "building a site needs more: see SETUP.md" |
| 18 | An existing site | `whats-new` | its `package.json` is untouched; `SETUP.md` arrives, worded for a new site |
| 19 | `engines` gains `\|\| ^25.9.0` | `make check` | red: "engines names 4 lines, the docs list 3" (G5) |
| 20 | `engines` drops `^24.22.1` | `make check` | red (G5), not a docs list that claims a line npm no longer allows |
| 21 | `.nvmrc` says `v24` or `lts/*` | `make check` | red: "cannot read" (G4) |

Measured on 2026-10-22 with npm 11.20.0 on Node 26.12.0 (commands: `npm install --package-lock-only
--ignore-scripts --no-audit --no-fund --offline` in a copy of the starter): with `engines.node` set to
`^22.23.4 || ^24.22.1 || >=26.12.1`, npm printed `EBADENGINE Unsupported engine { package: 'site@1.0.0',
required: { node: '^22.23.4 || ^24.22.1 || >=26.12.1' }, current: { node: 'v26.12.0', npm: '11.20.0' } }`,
exit 0. With `>=99.0.0`: exit 0 and `EBADENGINE`; with `--engine-strict`: exit 1, `npm error code EBADENGINE`.
The starter has no `.npmrc`. `npm config get node-version` is undefined and `--node-version` is "Unknown cli
config", so npm cannot be told to pretend to be another Node; scenarios 15 and 16 are tested on the range. Measured later the same day on a dependency-free fixture (name,
version, `engines`), plain `npm install --ignore-scripts --no-audit --no-fund` and `npm ci`, which is what
an owner runs: with the range and Node 26.12.1 (admitted), silent, exit 0; with `>=99.0.0`, exit 0 and 5
`EBADENGINE` lines naming `site@1.0.0`, from both commands. On the same Mac, with the same range, Node 26.12.0
had printed the warning that morning: both halves, on one machine, before and after its Node was updated.

## Tests

- `scripts/test_node_floor.sh` enters through the command `make check` runs
  (`bash scripts/check_node_floor.sh`), on throwaway copies, for scenarios 1 to 14, and once on the real
  tree, where it also asserts the real range string. A loop mutates each listed file in turn (its phrase
  removed, then doubled) and expects red naming that file. The throwaway copy mirrors the zip's layout
  (no `.github/`, no `packages/`, no git).
- The range table: for 22.12.0, 22.23.3, 22.23.4, 23.11.0, 24.10.0, 24.22.0, 24.22.1, 25.9.0, 26.12.0,
  26.12.1, 27.0.0, the script's `--admits` answer must equal `semver.satisfies` from npm's own bundled
  `semver` (at `$(npm root -g)/npm/node_modules/semver`, the nested path of a stock install, checked on this Mac: semver 7.8.5 refuses 24.22.0 and admits 24.22.1 for the range); expected admitted: 22.23.4, 24.22.1, 26.12.1, 27.0.0. Without
  that module the test prints a loud `SKIP` for the table (and CI's require-variable fails it).
- One real npm run on a minimal fixture (name, version and `engines` only, no dependencies): `engines`
  `>=99.0.0` gives `EBADENGINE` and exit 0, with `--package-lock-only --offline --ignore-scripts`, so no
  network. It follows the skip convention of `test_pre_push_hook.sh` when `npm` is missing, and that skip, like every skip in both new scripts, honors `REQUIRE_NODE_FLOOR=1`.
- The skip-to-failure conversion itself, for both scripts: run with a `PATH` that has `bash` and no `node`:
  with `REQUIRE_NODE_FLOOR=1` the exit is 1, without it one `SKIP` line and exit 0. Without these a renamed
  variable or a dropped `setup-node` step would ship with every scenario green.
- Constraints it must meet: bash 3.2 and BSD tools (the `macos-stock-tools` job); no early-exit consumer
  after a pipe (`check_pipefail_pipes.sh`); a `mktemp` failure prints "could not create a temp dir" last
  and exits non-zero (`test_mktemp_guard.sh`).

## Tasks and status

| # | Step | State | Evidence |
|---|---|---|---|
| 1 | This plan, reviewed until no BUG is open | ✅ closed; the seventh version is the one built | PLAN gate round 1: 1 BUG, 10 RISK, 5 NIT from the pair and 2 BUG, 8 RISK, 7 NIT from fresh-eyes; round 2: 2 BUG, 6 RISK, 5 NIT; round 3: 3 BUG, 4 RISK, 3 NIT; round 4: 2 BUG, 1 RISK, 4 NIT; round 5: 2 BUG-labelled wording errors (rated not substantive), 1 RISK, 4 NIT; the closing full read (Kimi): 0 BUG, 3 RISK, 2 NIT. This version answers them |
| 2 | A: `check_node_floor.sh` and `test_node_floor.sh`; wiring in `Makefile` (target and the long `##` description), `clean.yml` (the job and its header), `package.sh` (the zip list and `REQUIRED`, both scripts), `check_cdpath_safe.sh` (subjects or not-run), `test_mktemp_guard.sh` (scripts or exempt), `README.md` (script list and the `make check` line); `check_pipefail_pipes.sh` finds the scripts by their shebang and needs nothing. The `node-floor` job runs on `ubuntu-latest`; both it and `macos-stock-tools` get an explicit `actions/setup-node` step (`node-version: 24`, the starter's), because the existing tests skip without Node and prove nothing about the image (`test_verify.sh` prints "SKIP" and exits 0 without it); both set `REQUIRE_NODE_FLOOR=1`, the variable that turns a skip into a failure | ✅ done | `e73cce58`; review fixes `35a5943a`, `37d19698`, `ae960e71` |
| 3 | B: `engines`, the lockfile root (regenerated), the texts, the one skill sentence, the README step 3 line | ✅ done | `e73cce58`; UPGRADING changed in `37d19698` (all three lines named) |
| 4 | C: the installer comment, README line, version | ✅ done, publish is task 8 | `e73cce58`, `35a5943a` |
| 5 | D: the README release paragraph; BUGLOG rows | ✅ done | `e73cce58`, `35a5943a` |
| 6 | `make check` green; the diff reviewed (Normal depth); the PR opened and stamped | ▶ this pull request | trail: `docs/reviews/REVIEW-diff-2026-10-22-deps-node-floor-guard-e73cce5.md` |
| 7 | The owner adds `node-floor` to the ruleset's required checks | ⏸ not started | — |
| 8 | The owner publishes `create-croftweaver` 0.2.1 after 0.33 is live; then `docs/WHAT-THE-SKILLS-RUN.md` stops saying 0.2.0 is the newest | ⏸ not started | — |

## Decided before this plan

The owner, 2026-10-22: waived the guard, the installer comment and the stricter `engines` for the Astro
PR ("Waive, plan it for 0.34", "Waive, fix at the next installer change", "Not in this PR: advice only"),
then asked for "another PR to fix the remaining issues", chose to include the installer fix ("Yes,
include it": 0.2.1, he publishes) and to "Hold 0.33 until it is merged".

## Not in this plan

Raising the installer's own Node floor (the same Node flaws touch its downloads); a check that reads
Node's release index in CI (it needs the network and changes with the day; D writes the comparison into
the release routine instead); a `node --version` check at the start of the new-website skill;
`.npmrc` with `engine-strict` (it would stop an owner's install: a bigger decision); transitive packages'
own floors; a scan for unlisted places that state the floor (cut in round 4, above).

## Risks

- Each Node security release raises a per-line floor, and `engines` then lags until someone moves it. The
  check cannot know (no network); D's release step compares at every release.
- A text that states the floor and is not in the table is not found by the check (the scan for unlisted
  places was cut); D's release grep is the backstop.
- Node 23 and 25 users get a warning they cannot fix except by changing line; that is the point.
- Cloudflare Pages builds read `.nvmrc` (Node 24); if the Pages image carries a Node older than 24.22.1
  the build log shows the warning and the build still succeeds (not checked against a build).
- `setup-node` with `node-version: 24` may resolve below 24.22.1; G4 checks the declared major only.
- The new job blocks nothing until the ruleset lists it (task 7).

## Cost

PLAN gate at Normal depth: three rounds of Codex and GLM 5.3 at 150 to 250k tokens each, plus fresh-eyes in
round 1 (done). No red team: this touches no server, user data, login, money or deletion. The diff gate
after the build costs about as much again.
