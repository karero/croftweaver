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

## Rounds

(filled in as they run)
