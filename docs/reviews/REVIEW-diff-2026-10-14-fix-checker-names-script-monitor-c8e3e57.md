# Review trail: the checker names Cloudflare's script monitor

Branch `fix/checker-names-script-monitor`, change `c8e3e57` (3 files, +90 -1), base `origin/main` `3519d2d`.
Gate: DIFF, Normal depth. The change is the logic of a check script, so it is never Light.
Seats: Codex, GLM 5.3 on melious, and a fresh-eyes agent in round 1.

## What was asked and what was built

Asked: the checker shows Cloudflare's script monitor header as a bare "look" instead of naming it.
Built: in the NEL item, any one of the monitor's three headers (a `report-to` group `cf-csp-endpoint`
or an endpoint at `csp-reporting.cloudflare.com`, a `reporting-endpoints` entry, a
`content-security-policy-report-only` policy) is named, with where the switch is and that it comes on a
sample of pages. NEL on, or Cloudflare's NEL group, still fails first. A group of your own stays the
plain look. Files: `cloudflare-check.mjs`, its test file (4 new tests), `CLOUDFLARE_CHECK.md` (one table
row and one "what it cannot see" bullet).

## Records (saved before round 1)

### The checker's whole suite

Command: `node --test skills/new-website/scripts/tests/cloudflare-check.test.mjs` in the worktree,
Node v26.11.1, macOS. Whole output:

```
✔ a clean site: everything an outside request can judge is ok, the rest says what is left (152.016542ms)
✔ without --build the live build is only a look: nothing was compared (132.768167ms)
✔ the plain-text report names every item and ends with a result line (129.493417ms)
✔ NEL still on: the item fails and shows how long browsers keep the note (153.405209ms)
✔ Cloudflare's reporting group alone still fails; a group of your own is a "look" (362.218958ms)
✔ a nel header with max_age 0 is the way a policy is withdrawn: a "look", not "on" (237.99875ms)
✔ no answer at all: the domain fails, nothing that needs the page reads "ok", exit 1 (173.308ms)
✔ an answer that is cut off is no answer, whatever its first bytes said (207.817708ms)
✔ an answer that starts and then stalls times out as no answer (1133.921208ms)
✔ a page larger than what is read is never "ok" on what was read (194.681042ms)
✔ an error page is not judged as the site: a 522 fails the domain and the privacy items are not run (141.949459ms)
✔ a challenge page is named as such, and the site is not judged from it (273.9425ms)
✔ an answer that is not a 200 page cannot be judged: 204 is a look and the items are not run, exit 1 (137.25375ms)
✔ an answer that did not come through Cloudflare is a "look": any 200 is not the site (130.6565ms)
✔ a redirect to the same address is followed and the page is judged where it ends (127.104125ms)
✔ a redirect to another address is not followed: the items are not run, exit 1 (132.784667ms)
✔ the https redirect must lead to the whole address: a longer host is not it (133.952916ms)
✔ the https redirect is judged as an address: another host that quotes ours in a query does not pass (120.52575ms)
✔ the same address written another way is still the https redirect (131.430875ms)
✔ http:// answering 200 is a failure: Always Use HTTPS is not reaching it (135.203125ms)
✔ a 302 to the right place is a "look": visitors arrive, but it is not Always Use HTTPS (130.671875ms)
✔ what Cloudflare injects is found: the bot script (inline), the beacon, the address hiding (118.620542ms)
✔ the bot script alone is found when no cookie was set (108.222209ms)
✔ words about these scripts are not the scripts: a comment, a paragraph and a code sample pass (102.156583ms)
✔ another /cdn-cgi/ feature is a "look" that names it, not a pass (103.980042ms)
✔ a cookie that is not Cloudflare's is a "look" that does not blame Bot Fight Mode (105.415709ms)
✔ HSTS: missing is a "look" until --hsts-on says it should be there (206.731416ms)
✔ HSTS: read as directives: months, subdomains, preload; a lookalike or a short age is not "on" (618.463292ms)
✔ robots.txt that still names the starter's example.com is a failure (103.184667ms)
✔ a sitemap on another host is not the placeholder because its name contains "example.com" (214.543583ms)
✔ robots.txt that tells every crawler to stay out fails; a private folder does not (219.855333ms)
✔ rules for named crawlers in robots.txt make the AI item a "look" (109.564375ms)
✔ robots.txt that is a web page fails; a comment that mentions html does not (256.755042ms)
✔ robots.txt that cannot be had: 404 is a look, 500 a failure, no answer a failure and exit 1 (339.028334ms)
✔ an AI crawler name that is refused is a "look" that names it and its status (123.716625ms)
✔ crawler requests that got no answer are not "none refused": a look, and exit 1 (139.362875ms)
✔ --build: the same commit passes, another one fails (213.808834ms)
✔ a build marker that is not a full commit id proves nothing: "dev", a page, a short id (380.640833ms)
✔ build.txt that got no answer, with the domain fine, is a look and a non-zero exit (100.25075ms)
✔ --project: the alias that forwards to the domain passes the forward, and its NEL note stays beside the domain's result (100.421167ms)
✔ --project: an alias that answers 200 means the forward is not set, and the causes are listed (95.101458ms)
✔ --project: a forward to another address fails, and a name that does not answer is named (197.656875ms)
✔ an alias that answers 404, 500 or a challenge is not "a Pages project, ok" (2.049875ms)
✔ --project takes a Pages project, not any address (0.912959ms)
✔ https: a closed port is "connection refused" through the https path (126.032417ms)
✔ https: a site behind a certificate is read over TLS, and an untrusted one is named (403.154542ms)
✔ a header on the way counts: NEL and a Cloudflare cookie on the first answer of a followed redirect (96.75675ms)
✔ what a tag says about itself is not what it loads: titles, alt text and data attributes pass (99.40775ms)
✔ only Cloudflare's own paths are excluded from "other scripts": a longer path that quotes one is not (101.214625ms)
✔ a reporting group is judged by what it is: one of your own named like Cloudflare's is yours (281.857458ms)
✔ the script monitor is named, not shown as a bare report-to header (97.33125ms)
✔ any one of the script monitor's three headers names it (402.708084ms)
✔ a group of your own is not the script monitor, and NEL on still fails beside it (264.535125ms)
✔ an address that only looks like Cloudflare's reporting host is not the script monitor (179.696583ms)
✔ a robots.txt or build.txt larger than what is read is not judged whole (98.43ms)
✔ a 200 page with nothing in it is not the site: the domain fails and the page items are not run (87.317083ms)
✔ every spelling of "all of it" in a robots group is a stay-out; allowing it too leaves it open (379.437125ms)
✔ each of the address-hiding markers is found alone, and the words are not one (383.471334ms)
✔ each of Cloudflare's cookie names fails; a cookie of your own is a look (470.157667ms)
✔ up to three redirects on the same address are followed; a fourth, or none to go to, is said so (311.724084ms)
✔ Content-Signal lines in robots.txt are Cloudflare's managed file at work: a look for the AI item (117.73ms)
✔ a silent crawler is named in the list of requests that got no answer (108.999667ms)
✔ a ">" inside an attribute value does not end the tag: what follows it is still read (107.77975ms)
✔ an attribute's value is not an attribute: a title that names data-cfemail or data-cf-beacon is not one (107.883708ms)
✔ headers are read one answer at a time: two withdrawn policies, and two HSTS values, are not corrupted by joining (203.511458ms)
✔ a path that only starts like one of Cloudflare's three is another path (97.073417ms)
✔ the longer pattern wins in a robots group: "Disallow: /*" beats "Allow: /", and "Allow: /*" beats "Disallow: /" (349.793541ms)
✔ a first-party file or a note in a script that happens to contain the word is not Cloudflare's (118.145958ms)
✔ Cloudflare's beacon is found by its address, written with or without a scheme (264.116417ms)
✔ a redirect to the page itself is asked once and said so; a Location that is not an address is said so (218.925875ms)
✔ HSTS on a redirect before the page does not stand for the page: with --hsts-on it fails, and says so (229.094208ms)
✔ an address written in a script between backticks, with a semicolon after it, is read whole (123.903792ms)
✔ a robots.txt with two hundred thousand blanket rules is read, not a crash (208.85625ms)
✔ what the HTML says it is: the text of a textarea or a title is text, a reference is decoded, "</scripture>" does not end a script (329.115167ms)
✔ what is not a tag is skipped, and a comment that ends abruptly does not swallow the page (434.210042ms)
✔ an address is read against the page it is on, and a link to the beacon is not the beacon (107.587375ms)
✔ an empty Location header is said to be empty (111.45825ms)
✔ text that changes length when lower-cased does not move what is found after it (107.63525ms)
✔ a page of a hundred thousand comments is read in linear time and what follows them is found (126.139125ms)
✔ an SVG's title holds markup, as in a browser; an HTML title holds text (204.227958ms)
✔ a named character reference needs its semicolon, as in a browser: "&semi=" in an address is left alone (97.634875ms)
✔ foreign content is read as a browser reads it: a self-closed svg changes nothing, a foreignObject is HTML again, an svg's textarea holds markup (405.353166ms)
✔ foreign content, edges: an svg's inline script is read, a slash inside a value is not a self-closing one, a nested foreignObject end does not end the outer (336.375292ms)
✔ thousands of unclosed script starts inside an svg: the text taken is bounded by the page, and it is script text (110.612958ms)
✔ an svg script is script text to its end tag: a CDATA section, a nested svg and a foreignObject inside it are part of it (611.290709ms)
✔ a self-closing slash on script or title does not stop raw text in HTML, as in a browser (241.979083ms)
✔ a wrong command is exit 2 with the usage text, and --help is exit 0 (1112.2825ms)
✔ a fractional timeout is accepted, and a server that never answers fails within it (1109.950542ms)
✔ it runs when started through a symlink, as an installed skill is, also with symlinks kept (298.710667ms)
✔ parseTarget takes a domain or a local page and refuses a path or a live http:// address (0.392584ms)
✔ the items are the checklist's items, and the paths are its paths (1.28175ms)
ℹ tests 91
ℹ suites 0
ℹ pass 91
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 20391.715458
exit status: 0
```

### Five breakages of the change, each tried in a scratch copy of the three files

Command: `python3 -I monitor-mutations.py <worktree>` (a copy of `skills/new-website/scripts`,
`skills/new-website/references` and the checklist; one line changed per run; the four new tests
selected with `--test-name-pattern="script monitor"`). Whole output:

```
unmutated: exit 0, new tests failing: none

M1 the monitor branch is removed (falls back to the bare look)
    KILLED; new tests that failed: ['the script monitor is named', 'any one of the script monitor']
M2 any report-to group counts as the monitor
    KILLED; new tests that failed: ['a group of your own is not the script monitor']
M3 the monitor is judged before NEL on and Cloudflare's NEL group
    KILLED; new tests that failed: ['the script monitor is named', 'any one of the script monitor', 'a group of your own is not the script monitor']
M4 the address is matched as a plain substring
    KILLED; new tests that failed: ["looks like Cloudflare's reporting host"]
M5 a value that does not parse is not judged by its text
    KILLED; new tests that failed: ['any one of the script monitor']
```

### `make check` in the worktree

Command: `make check`, exit status 0. 1,156 lines of output, 1,131 of them `ok` lines, 4 `warn` lines
(description lengths and one SKILL.md length, none in files this change touches), no failure marker.
Everything that is not an `ok` line, whole:

```
OK — no private names in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs scripts packages; no contact info or credentials in: skills README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs LICENSE packages
OK — all 11 subjects behave identically with and without an exported CDPATH.
OK — whats-new.sh resolves a relative <project_dir> to the real one, not a CDPATH decoy.
OK — no early-exit pipe under pipefail in 20 scripts (2 exempt, each with a reason in scripts/check_pipefail_pipes.sh).
OK — independent-review stays model-agnostic (no concrete model names/tags in its 23 pipeline files)
OK — all 53 files under skills/new-website/templates/astro are accounted for (TEMPLATE_TRACKED, SITE_OWNED, or SITE_SOURCE).
warn — independent-review: description 995 chars — nearing the 1024-char hard limit (warning starts at 900).
warn — new-website: SKILL.md is 729 lines — over the 500-line soft budget; move detail to references/.
warn — search-console-insights: description 998 chars — nearing the 1024-char hard limit (warning starts at 900).
warn — website-review: description 1005 chars — nearing the 1024-char hard limit (warning starts at 900).
OK (with warnings) — no skill over a hard budget; see the warn lines above (36 skills checked).
real-curl cases: curl /usr/bin/curl, python3 /opt/homebrew/bin/python3 (3.15.0)
all checks passed
SKIP — perl/*.pl: every program is run and declares its Perl, but Perl::MinimumVersion is not installed (apt libperl-minimumversion-perl, or CPAN), so their minimum Perl was NOT checked. CI checks it.
all checks passed
all checks passed
test_whats_new_removed_skill: all cases passed
all checks passed
skip bash, block off: without /proc (no unprivileged unshare here)
skip bash, block on: without /proc (no unprivileged unshare here)
skip sh, block off: without /proc (no unprivileged unshare here)
skip sh, block on: without /proc (no unprivileged unshare here)
skip dash, block off: without /proc (no unprivileged unshare here)
skip dash, block on: without /proc (no unprivileged unshare here)
all checks passed
all checks passed
test_clean_denylist: all passed
test_git_stand_hook: all passed
all whats-new missing-file tests passed
all checks passed
LF checkout OK — every text file checks out LF even with core.autocrlf=true
make check exit status: 0
```

Skipped locally, not checked here: the Perl minimum-version check (CI runs it) and six cases without
`/proc` (no unprivileged unshare on this machine). Neither concerns this change.

## Round 1 (DIFF, Normal depth), change `c8e3e57` (rebased as `cce7a87`)

Seats: Codex (gpt-6.1-sol, read-only, 243 s, 61,614 tokens), GLM 5.3 on melious (287 s, 22,003 tokens),
fresh-eyes (a Sonnet sub-agent with no shared context, 1,044 s, 292,506 tokens). Brief: the diff, the
facts the change rests on (one live capture, Cloudflare's own pages) and the author's records above.
The script ended `reviewers: codex OK, melious OK`.

Findings, consolidated and answered (this is the author's record, also the `--verify` input):

- F1 BUG (Codex, fresh-eyes BUG 1; GLM NIT 2): the text path judged a boundary-delimited substring of the
  raw header, so a user name that was the monitor's host (the host, an at sign, another host), a query or a
  path that quoted the host were named as the monitor. FIXED: each address in the value is parsed and its host judged
  (`monitorHost`), on the report-to, reporting-endpoints and report-only paths alike.
- F2 BUG (Codex; GLM NIT 1): a group of your own named `cf-csp-endpoint` on another address was named as
  Cloudflare's monitor. FIXED: the name no longer counts, only the address does. Test: the exact-name
  collision.
- F3 RISK (fresh-eyes RISK 2): six breakages survived the four new tests (parsed host guard, the name
  clause, the parse path, `.flat()`, the `i` flag). FIXED: lookalikes through all three headers, the
  collision, a JSON array value, an upper-case scheme, a trailing dot, a sub-host, a port. Then a weak
  assertion was found by the new breakages (the clean line also says "script monitor", so a
  `/script monitor/` match passed on the wrong state): the tests now assert the state and the phrase
  "script monitor is switched on". 15 breakages tried, 14 caught, 1 equivalent (below).
- F4 RISK (fresh-eyes RISK 3): the clean NEL line carried no caveat, so a site with the monitor on read
  `ok` in about 19 of 20 runs. FIXED: the ok line and the off-page look say one answer cannot show it is
  off. JUDGMENT: that is noise on sites that never had it; kept, because this file's other ok lines carry
  scope notes ("A browser can see more: view the source once").
- F5 RISK (fresh-eyes RISK 4): the look's fix was "See section 3 of the checklist", which has no entry for
  the monitor, and whose NEL rule removes only NEL and Report-To. FIXED: the fix line carries the path to
  the switch and says the NEL rule does not remove it. NOT DONE, by design: a paragraph in the checklist
  itself (a runbook, High depth): a follow-up.
- F6 RISK (fresh-eyes RISK 5): the reference turned 2 observations into a rate and a procedure. FIXED:
  it states the observation (2 of 40; none of 200 after the switch-off), says a hundred clean requests
  make it unlikely and not excluded, names the toggle as the proof, and gives a loop (run as written).
- F7 NIT (GLM NIT 3, fresh-eyes NIT 6): a withdrawn `nel` header hid the monitor. FIXED: the monitor is
  named beside NEL on, Cloudflare's NEL group and a withdrawn header ("switched on as well").
- F8 NIT (GLM NIT 4, fresh-eyes NIT 7): "still sends them" had no antecedent. FIXED: "still sends nel and
  report-to headers"; the pinned test follows.
- F9 NIT (fresh-eyes NIT 8): wording: "this zone's", "sample" twice, "is on"/"comes on". FIXED, in this
  file's own style ("Your domain → Security → Settings → filter by Client-side abuse").
- F10 NIT (fresh-eyes NIT 9): a sub-host and a trailing dot were judged differently by the two paths.
  FIXED: one address rule; the trailing dot is removed before the test.
- F11 NIT (fresh-eyes NIT 10): the reference's "positives" paragraph. FIXED: one clause says the monitor's
  headers come from one capture of a live site.
- F12 NIT (GLM NIT 5): "Client-side security, formerly Page Shield" is not cited in the brief. NO CHANGE:
  Cloudflare's own page https://developers.cloudflare.com/page-shield/ (read 2026-10-14) says
  "Page Shield is now called Client-side security".
- F13 UNVERIFIABLE (GLM): that Node hands header names over in lower case. SETTLED by test: the fixtures
  now spell the names as Cloudflare does on the wire (`Report-To`, `Reporting-Endpoints`,
  `Content-Security-Policy-Report-Only`) and the checker reads them.
- F14 UNVERIFIABLE (fresh-eyes): that the toggle is per zone. NO CHANGE: the text says "Your domain →
  Security → Settings", the zone's page; the "Global" badge is not explained by Cloudflare's get-started
  page and is not relied on.
- F15 (Codex): the first record of breakage M3 differed from a clean reorder because that mutant replaced
  the message. FIXED in the record: M3 now moves the branch and keeps the message; only the test for NEL on
  fails.

## Records after round 1

Rebased onto `origin/main` `f380fcb` before this work (no overlap with the three files; commits became
`cce7a87` and `e67b69d`).

### The checker's whole suite, `node --test skills/new-website/scripts/tests/cloudflare-check.test.mjs`

```
ℹ tests 92
ℹ suites 0
ℹ pass 92
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 19628.511834
exit status: 0
```
(92 tests: the 87 that were there and 5 for this change; whole output kept in the session's scratchpad.)

### Fifteen breakages of the revised change, each in a scratch copy of the three files

```
unmutated: exit 0, new tests failing: none

M1  the monitor branch is removed (falls back to the bare look)
    KILLED; new tests that failed: ['T1', 'T2']
M2  a group named cf-csp-endpoint counts without an address on Cloudflare's host
    KILLED; new tests that failed: ['T3']
M3  the monitor is judged before NEL on and Cloudflare's NEL group (same message)
    KILLED; new tests that failed: ['T4']
M4  the text path matches the host as a substring, anywhere in the value
    KILLED; new tests that failed: ['T3']
M5  a report-to value that does not parse is not judged by its text
    KILLED; new tests that failed: ['T2']
M6  .flat() dropped (a JSON array value is not read)
    KILLED; new tests that failed: ['T2']
M7  the i flag dropped from the address finder (upper-case scheme)
    KILLED; new tests that failed: ['T2']
M8  the host is not anchored at its end (a longer host that starts like it)
    KILLED; new tests that failed: ['T3']
M9  the host is not anchored at its start (not-csp-reporting...)
    KILLED; new tests that failed: ['T3']
M10 a trailing dot on the host is not removed
    KILLED; new tests that failed: ['T2']
M11 the monitor is not named beside NEL on
    KILLED; new tests that failed: ['T4']
M12 the monitor is not named beside a withdrawn nel header
    KILLED; new tests that failed: ['T4']
M13 the clean line loses its caveat
    KILLED; new tests that failed: ['T5']
M14 the look carries the checklist pointer instead of the path to the switch
    KILLED; new tests that failed: ['T1']
M15 the host test is case-sensitive (equivalent: new URL lower-cases the host)
    SURVIVED (equivalent: the URL parser lower-cases a host); new tests that failed: none
```

M15 is an equivalent mutant: `new URL(...).hostname` is lower-cased by the parser, so the `i` flag on the
host test changes nothing.

## Round 2 (DIFF verification, Normal depth), delta `cce7a87..873941c`

Seats: Codex (medium, read-only, 276 s, 59,399 tokens) and GLM 5.3 on melious (485 s, 32,455 tokens); no
fresh-eyes (round 1 only at Normal depth). The script ended `reviewers: codex OK, melious OK`.
Result: 2 BUGs, 3 RISKs and one out-of-scope RISK from Codex; 3 NITs from GLM 5.3, no BUG or RISK.

- R2-1 BUG (Codex): the address finder split values before judging hosts, so a `;` before a user name and a
  comma inside a query still named the monitor. FIXED by reading each header by its own syntax, not by
  hunting for addresses: `report-to` as JSON groups (a value that does not parse is not read),
  `reporting-endpoints` as quoted strings, a report-only policy by the addresses of its `report-uri`
  directive (policies split at commas, directives at semicolons: the browser's own CSP parser splits
  there too). The comma-in-a-query shape is no longer named (its second half is not a `report-uri`
  address); the `;` shape is named, which is what a browser would do: it reports to the part before the
  `;`. Test: the comma shape; the `;` shape is not pinned.
- R2-2 BUG (Codex): the pages.dev note said "nel and report-to headers" when either alone triggered it.
  FIXED: it names the header or headers the alias sends ("a nel header", "a report-to header", both);
  two new tests, and the old pin follows.
- R2-3 RISK (Codex): the reference's loop counted a failed request as one without the header, so a dead
  network printed `100 0`. FIXED: it prints `failed`, `none` and `header` apart; run as written against a
  site that sends none (`100 none`) and against an address that always fails (`3 failed`).
- R2-4 RISK (Codex): "a hundred requests make it unlikely" assumed a sampling model. FIXED: removed. The
  reference says no number of requests shows it, that Cloudflare does not document how often it sends
  them, and that the toggle is the proof.
- R2-5 RISK (Codex): the clean-line test pinned "sample of pages only", not the conclusion. FIXED: it is
  pinned on "so this one answer cannot show that it is off", on the 200 line and on the off-page look.
- R2-6 RISK (Codex, out of scope): an array endpoint address was coerced to a monitor address, and a
  `connect-src` address alone triggered detection. FIXED: only a string address counts, and only the
  addresses of `report-uri`.
- R2-7 NIT (GLM): a report-to value that parses to a bare string hid the addresses in its text. MOOT: the
  text path is gone.
- R2-8 NIT (GLM): the code comment said "reports to" while the policy path judged every address. FIXED:
  the code now does what the comment says.
- R2-9 NIT (GLM): the finder's stop set left out some closing characters. MOOT: there is no finder.
- Found by `make check`, not by a reviewer: `scripts/check_clean.sh` reads a lookalike address of the form
  host, at sign, other host as an email address, in the test file and in this trail (CI's `no-pii-secrets`
  job runs it). FIXED: the test spells the at sign as `\x40`, and this trail says it in words.

Records after round 2: the suite is 93 tests, 93 pass (the 87 that were there, 5 for the monitor, 1 for
the alias note); the nineteen breakages below, each in a scratch copy of the three files, are all caught
(the first `make check` of this round failed on the clean check above and was re-run after the fix).

```
unmutated: exit 0, new tests failing: none

M1  the monitor branch is removed (falls back to the bare look)
    KILLED; new tests that failed: ['T1', 'T2']
M2  a group named cf-csp-endpoint counts without an address on Cloudflare's host
    KILLED; new tests that failed: ['T3']
M3  the monitor is judged before NEL on and Cloudflare's NEL group (same message)
    KILLED; new tests that failed: ['T4']
M4  a report-to value that does not parse is searched as text for the host
    KILLED; new tests that failed: ['T3']
M5  .flat() dropped (a JSON array value is not read)
    KILLED; new tests that failed: ['T2']
M6  an address that is not a string is accepted
    KILLED; new tests that failed: ['T3']
M7  the host is not anchored at its end (a longer host that starts like it)
    KILLED; new tests that failed: ['T3']
M8  the host is not anchored at its start (not-csp-reporting...)
    KILLED; new tests that failed: ['T3']
M9  a trailing dot on the host is not removed
    KILLED; new tests that failed: ['T2']
M10 reporting-endpoints is searched for any address in its text, not its quoted values
    KILLED; new tests that failed: ['T3']
M11 a report-only policy is read for any address, not only its report-uri
    KILLED; new tests that failed: ['T3']
M12 a report-only policy is split at semicolons only (not at commas between policies)
    KILLED; new tests that failed: ['T2']
M13 the directive name is matched case-sensitively
    KILLED; new tests that failed: ['T2']
M14 the monitor is not named beside NEL on
    KILLED; new tests that failed: ['T4']
M15 the monitor is not named beside a withdrawn nel header
    KILLED; new tests that failed: ['T4']
M16 the clean line loses its caveat
    KILLED; new tests that failed: ['T5']
M17 the off-page look loses its caveat
    KILLED; new tests that failed: ['T5']
M18 the look carries the checklist pointer instead of the path to the switch
    KILLED; new tests that failed: ['T1']
M19 the alias note names both headers whenever it sends either
    KILLED; new tests that failed: ['T6']
```

## Round 3 (DIFF verification, Normal depth), delta `873941c..7986e32`

Seats: Codex (medium, read-only, 242 s, 56,932 tokens) counted. GLM 5.3 on melious (448 s, 27,161 tokens)
answered, and the script did not recognise the answer as a review ("output is not a review"); it is a
real review and is counted here by hand from its raw file, as the script's own text says. The ollama-cloud
stand-in failed at once (its session usage limit, 429). The script said: one reviewer counted, degraded.

- R3-1 RISK (Codex): `reporting-endpoints` was read with a plain quoted-string pattern, so a parameter that
  quoted the host, or an escaped quote inside an address, could still name the monitor. FIXED: it is read
  as the dictionary it is: members split at commas outside quotes, only a member's own string is an
  address, backslash escapes are undone, parameters are not read.
- R3-2 RISK (Codex): a policy with two `report-uri` directives named the monitor from the second, which a
  browser ignores. FIXED: the first `report-uri` of each policy is the one read.
- R3-3 NIT (GLM, by hand): the same escaped-quote shape as R3-1. FIXED with it.
- GLM confirmed every R2 answer as landed and found no BUG or RISK. Both seats' UNVERIFIABLE entries
  (the Reporting API and CSP grammars as a browser applies them; Cloudflare's observed shapes, one site)
  stand as unverified: the reference says the headers come from one capture of one site.
- Codex's sandbox could not start local servers (`listen EPERM`), so it ran direct `evaluate()` calls and
  not the suite: the suite's result is the author's record above.

Records after round 3: the suite is 93 tests, 93 pass, exit 0; `check_clean.sh` OK; `make check` on the
tree before this round's code change: exit 0 (1,150 lines of output, no failure marker; the Perl
minimum-version check and six cases without /proc skipped on this machine, none concerns this change).
Twenty-one breakages of the revised readers, each in a scratch copy, all caught:

```
unmutated: exit 0, new tests failing: none

M1  the monitor branch is removed (falls back to the bare look)
    KILLED; new tests that failed: ['T1', 'T2']
M2  a group named cf-csp-endpoint counts without an address on Cloudflare's host
    KILLED; new tests that failed: ['T3']
M3  the monitor is judged before NEL on and Cloudflare's NEL group (same message)
    KILLED; new tests that failed: ['T4']
M4  a report-to value that does not parse is searched as text for the host
    KILLED; new tests that failed: ['T3']
M5  .flat() dropped (a JSON array value is not read)
    KILLED; new tests that failed: ['T2']
M6  an address that is not a string is accepted
    KILLED; new tests that failed: ['T3']
M7  the host is not anchored at its end (a longer host that starts like it)
    KILLED; new tests that failed: ['T3']
M8  the host is not anchored at its start (not-csp-reporting...)
    KILLED; new tests that failed: ['T3']
M9  a trailing dot on the host is not removed
    KILLED; new tests that failed: ['T2']
M10 a parameter's string is read as an address too
    KILLED; new tests that failed: ['T3']
M11 a report-only policy is read for any address, not only its report-uri
    KILLED; new tests that failed: ['T3']
M12 a report-only value is not split into policies at commas
    KILLED; new tests that failed: ['T2']
M13 the directive name is matched case-sensitively
    KILLED; new tests that failed: ['T2']
M20 a duplicate report-uri counts, not only the first
    KILLED; new tests that failed: ['T3']
M21 escapes inside a quoted address are ignored
    KILLED; new tests that failed: ['T2']
M14 the monitor is not named beside NEL on
    KILLED; new tests that failed: ['T4']
M15 the monitor is not named beside a withdrawn nel header
    KILLED; new tests that failed: ['T4']
M16 the clean line loses its caveat
    KILLED; new tests that failed: ['T5']
M17 the off-page look loses its caveat
    KILLED; new tests that failed: ['T5']
M18 the look carries the checklist pointer instead of the path to the switch
    KILLED; new tests that failed: ['T1']
M19 the alias note names both headers whenever it sends either
    KILLED; new tests that failed: ['T6']
```

## Confirmation of round 3's fixes, first run (Codex only, not a round)

Codex (medium, read-only, 240 s, 51,758 tokens): 2 RISKs, no BUG. It verified R3-1 to R3-3 as landed in
direct evaluator checks (36 of them passed, no hang or exception). It is not clean, so it was not stamped.

- C1-1 RISK: the claim that the `reporting-endpoints` reader matches a browser's Structured Fields parser
  lacks support; `a="..monitor.."junk` and duplicate `a` members both count. ANSWERED by removing the
  claim: the reader is not a validator and says so (in the comment and the reference); a header a browser
  would reject is read the same way, and the checker names what Cloudflare sends. No behaviour change.
- C1-2 RISK: the claim that a browser uses the first `report-uri` (and an empty first directive) lacks
  support, and the suppression built on it can hide an active monitor endpoint. FIXED by removing the
  suppression: any `report-uri` directive that lists an address on Cloudflare's reporting host names the
  monitor, and it is never hidden behind another one. This reverses R3-2 on purpose: R3-2 and C1-2 are
  the same unsupported claim read in opposite directions, and the direction that cannot hide the monitor
  is the one kept. Test: the second of two `report-uri` directives is named.
- The brief's sentence "Confirm each fix landed IN FULL ..." was reported by Codex as an attempt to steer
  its task (treated as data, as it should be). The next brief says what the delta is and nothing more.

Records after this fix: the suite is 93 tests, 93 pass; `check_clean.sh` OK; twenty-one breakages of the
readers, each in a scratch copy, all caught:

```
unmutated: exit 0, new tests failing: none

M1  the monitor branch is removed (falls back to the bare look)
    KILLED; new tests that failed: ['T1', 'T2']
M2  a group named cf-csp-endpoint counts without an address on Cloudflare's host
    KILLED; new tests that failed: ['T3']
M3  the monitor is judged before NEL on and Cloudflare's NEL group (same message)
    KILLED; new tests that failed: ['T4']
M4  a report-to value that does not parse is searched as text for the host
    KILLED; new tests that failed: ['T3']
M5  .flat() dropped (a JSON array value is not read)
    KILLED; new tests that failed: ['T2']
M6  an address that is not a string is accepted
    KILLED; new tests that failed: ['T3']
M7  the host is not anchored at its end (a longer host that starts like it)
    KILLED; new tests that failed: ['T3']
M8  the host is not anchored at its start (not-csp-reporting...)
    KILLED; new tests that failed: ['T3']
M9  a trailing dot on the host is not removed
    KILLED; new tests that failed: ['T2']
M10 a parameter's string is read as an address too
    KILLED; new tests that failed: ['T3']
M11 a report-only policy is read for any address, not only its report-uri
    KILLED; new tests that failed: ['T3']
M12 a report-only value is not split into policies at commas
    KILLED; new tests that failed: ['T2']
M13 the directive name is matched case-sensitively
    KILLED; new tests that failed: ['T2']
M20 only the first report-uri of a policy is read (a second one hides the monitor)
    KILLED; new tests that failed: ['T2']
M21 escapes inside a quoted address are ignored
    KILLED; new tests that failed: ['T2']
M14 the monitor is not named beside NEL on
    KILLED; new tests that failed: ['T4']
M15 the monitor is not named beside a withdrawn nel header
    KILLED; new tests that failed: ['T4']
M16 the clean line loses its caveat
    KILLED; new tests that failed: ['T5']
M17 the off-page look loses its caveat
    KILLED; new tests that failed: ['T5']
M18 the look carries the checklist pointer instead of the path to the switch
    KILLED; new tests that failed: ['T1']
M19 the alias note names both headers whenever it sends either
    KILLED; new tests that failed: ['T6']
```

## Confirmation, second run: clean

First attempt: Codex failed at once ("selected model is at capacity", 61 s, 6,835 tokens); no reviewer
counted and nothing was reviewed. Re-run with the standard pair: Codex (177 s, 47,186 tokens) and GLM 5.3
on melious (147 s, 12,391 tokens), both OK. **Both: No BUG/RISK/NIT findings.** Both verified C1-1 and C1-2
as landed in full (Codex: 53 direct assertions against the reader and five direct `evaluate()` checks;
GLM: traced the new branch and every retained case).

Outside the scope of a confirmation, recorded as follow-ups; none blocks:

- Codex RISK, outside scope: Cloudflare's endpoint identity, its sampling and the switch path lack
  independently checked vendor support. ANSWER: the reference says the three headers come from one
  capture of one live site; the dashboard path comes from Cloudflare's get-started page (it names the
  toggle but not the way to turn it off) and the owner's own screenshot, after which the headers stopped
  (none of 200). No vendor page documents the headers. Follow-up: more captures from other zones; cite a
  vendor page if one appears.
- GLM NIT, outside scope: a value ending in a lone backslash leaves its string unterminated; the member
  then fails the address pattern. Harmless. Follow-up only.
- GLM UNVERIFIABLE: which header names reach `cloudflareMonitor`. SETTLED: the call site passes exactly
  `report-to`, `reporting-endpoints` and `content-security-policy-report-only`.

## Gate summary

Normal depth. 3 rounds and 3 confirmation runs (one with 2 RISKs, one that did not run, one clean).
26 findings in all: 4 BUG, 12 RISK, 10 NIT, each fixed, moot or answered with its reason; 1 more found by
`make check` and fixed. No waivers, no deferrals of a BUG. Two rebases onto main during the work (no
overlap with the three files; own files byte-identical before and after, merge link empty).

Cost (as the seats reported it): Codex 6 runs, 283,724 tokens, 1,239 s (one failed on capacity);
GLM 5.3 on melious 4 runs, 94,010 tokens, 1,367 s (one counted by hand); fresh-eyes 1 run, 292,506
tokens, 1,044 s; the ollama stand-in failed on its quota in round 3.
