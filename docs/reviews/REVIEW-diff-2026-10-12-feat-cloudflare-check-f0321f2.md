# DIFF review — feat/cloudflare-check — `skills/new-website/scripts/cloudflare-check.mjs`: a script that runs the Cloudflare checklist from outside

Base `52a46e1` (the head of `docs/cloudflare-checklist`, which this branch is stacked on; that branch's own review trail is `docs/reviews/REVIEW-diff-2026-10-12-docs-cloudflare-checklist-d87f640.md`) · depth: **Normal** (code that runs and tells an owner their privacy page is true, but only reads: GET requests, no token, no account, no change) · verdict: **CLEAN** at `6d4e8d3`, the head round 8 reviewed; `9583a43` fixes round 8's two NITs, locally verified and not externally re-verified (8 rounds and 2 confirmations, 91 findings: 29 BUG, 26 RISK, 36 NIT) · authority used: WORKTREE-WRITE (atom A: this session created the worktree), BRANCH-COMMIT (atom A: this session created the branch), GATED-THIS-DIFF (atom A: reviewer input captured for every pair, a round 1 full capture and a verification chain bridged by no merge); POST AUTHORITY is claimed in the PR comment once the PR exists (atom A: this session creates it).

Abbreviations: `CC` = `skills/new-website/scripts/cloudflare-check.mjs`, `TT` = `skills/new-website/scripts/tests/cloudflare-check.test.mjs`, `REF` = `skills/new-website/references/CLOUDFLARE_CHECK.md`, `CL` = `docs/CLOUDFLARE-CHECKLIST.md`.

Files this change touches: `CC` (new), `TT` (new), `REF` (new), `Makefile` (a `test-cloudflare-check` target), `.github/workflows/clean.yml` (a job `cloudflare-check-tests`: Node 18, 20, 22, 24 on Ubuntu and Node 24 on Windows), `CL` (two sentences in section 5), `skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md` (one sentence). `skills/new-website/SKILL.md` is untouched, on purpose: the explanation lives in `REF`, which a session reads when it needs it. The commit that adds this trail takes only this file.

| Round | Head | Artifact (full / delta since) | Reviewers | seconds, tokens per seat | BUG/RISK/NIT (after dedup) |
|---|---|---|---|---|---|
| 1 | `f0321f2` | full `52a46e1..f0321f2` | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only (first run FAILED: model at capacity after 497 s / 89,772 tokens; rerun counted); melious glm-5.3; fresh-eyes (claude-sonnet-5-5 sub-agent, no shared context) | codex 613 s / 93,432; melious 331 s / 51,069; fresh-eyes about 1,250 s / 328,308 | 12 / 8 / 13 |
| 2 | `390dd65` | full `52a46e1..390dd65` (Codex had a gap in round 1) with R1 to R34 | codex medium; melious FAILED (curl exit 28 at its 600 s limit, reply cut off); ollama-cloud glm-5.3:cloud stood in | codex 423 s / 106,536; ollama-cloud 599 s | 6 / 2 / 5 |
| 3 | `cfd596b` | delta `390dd65..cfd596b` | codex medium; melious glm-5.3 | codex 279 s / 68,312; melious 381 s / 35,797 | 4 / 2 / 3 |
| 4 | `d114024` | delta `cfd596b..d114024` | codex medium; melious glm-5.3 | codex 308 s / 73,575; melious 432 s / 41,953 | 3 / 3 / 6 |
| 5 | `6da7f8d` | delta `d114024..6da7f8d` | codex medium; melious glm-5.3 | codex 320 s / 84,184; melious 352 s / 33,587 | 1 / 2 / 3 |
| 6 | `80518db` | delta `6da7f8d..80518db` | codex medium; melious glm-5.3 | codex 302 s / 59,212; melious 256 s / 19,143 | 0 / 2 / 2 |
| confirmation 1 (re-gate, not a round) | `0ba9e04` | delta `80518db..0ba9e04` | codex medium (`--seat codex`) | codex 107 s / 57,913 | 0 / 2 / 0 |
| confirmation 2 (re-gate) | `f6673ec` | delta `0ba9e04..f6673ec` | codex medium (`--seat codex`) | codex 239 s / 48,236 | 1 / 2 / 0 |
| 7 | `6cc9824` | delta `f6673ec..6cc9824` (owed by confirmation 2's A1) | codex medium; melious glm-5.3 | codex 311 s / 55,132; melious 366 s / 23,490 | 2 / 1 / 2 |
| 8 | `6d4e8d3` | delta `6cc9824..6d4e8d3` | codex medium; melious glm-5.3 | codex 309 s / 56,436; melious 377 s / 18,613 | 0 / 0 / 2 |


Rounds past 3, and the BUGs that earned each: round 4 by round 3's T1 to T4 (round 2's fixes of the reader were partly wrong, and headers were joined); round 5 by round 4's V1 to V3 (HSTS from a redirect, a path with a backtick, a robots.txt that threw); round 6 by round 5's X1 (a Unicode offset); round 6 had no BUG and the rounds ended. The two confirmations of round 6's fixes then reopened them: confirmation 2's A1 (a quadratic reader, introduced by confirmation 1's fix) was a substantive BUG and earned round 7; round 7's B1 and B2 (a CDATA payload dropped, a counter that could not tell which svg owned a script) earned round 8. Round 8 found no BUG: the rounds ended at 8, inside the budget, so nothing went to the owner as a decision.

| id | Sev | Source | Stage | Finding | Status (all fixed ones locally_verified; the rest in the notes) | Evidence |
|---|---|---|---|---|---|---|
| R1 | BUG | Codex, fresh-eyes, GLM 5.3 | round 1 | an answer cut off mid-body, or longer than the read limit, was judged as whole: bot/analytics/email read ok | fixed | CC `get()`: `res.complete` false is an error (EINCOMPLETE); the cap is 5 MB and sets `truncated`, and the source items are then `look`; TT "cut off", "stalls", "larger than what is read" |
| R2 | BUG | Codex, fresh-eyes | round 1 | `pages` was ok for any answer: 404, 500, a challenge, any host | fixed | CC pages: ok only below 400, no challenge, and a `.pages.dev` host; `--project` accepts a Pages name or host (or an http loopback origin, for tests); TT unit test of `evaluate`, `parseProject` |
| R3 | BUG | Codex, fresh-eyes | round 1 | REF said a scaffolded site carries a copy of the script; the scaffold recipe does not copy new-website | fixed | REF "Where it is": the toolkit folder or `$SKILLS_ROOT/new-website`, and says a site has no copy |
| R4 | BUG | Codex, fresh-eyes | round 1 | the exit status did not say "did not answer": build.txt unanswered, all crawlers unanswered, a 3xx/204/non-HTML home page exited 0 | fixed | CC `main`: exit 1 when a FAIL, a request got no answer, or an item could not be judged; JSON has `unanswered` and `couldNotJudge`; TT exit-status assertions |
| R5 | BUG | Codex, fresh-eyes | round 1 | markers inside an HTML comment, or words on the page, failed three items | fixed | CC `scanPage`: tags and script bodies only, comments and visible text left out; TT "words about these scripts" |
| R6 | BUG | Codex, fresh-eyes | round 1 | HSTS read `max-age` from a substring of another directive (`not-max-age=...; max-age=0` was ok) | fixed | CC hsts: directives anchored at start or `;`; quoted max-age; under one month is a look; TT HSTS table |
| R7 | BUG | Codex, GLM 5.3, fresh-eyes | round 1 | a sitemap host containing `example.com` (`myexample.com`, a query string) failed as the placeholder | fixed | CC robots: the host is compared to `example.(com/org/net)` exactly; TT |
| R8 | BUG | Codex | round 1 | a 7-character served marker "confirmed" a full expected commit id | fixed | CC build: the served marker must be 40 hex characters; `--build` is a prefix of it; TT |
| R9 | BUG | Codex | round 1 | a 204 empty home page was "ok" for the domain | fixed | CC domain: only 200 is ok; other 2xx is a look and the page items are "not run", exit 1; TT |
| R10 | BUG | Codex | round 1 | `--timeout 1.0001` crashed with ERR_OUT_OF_RANGE and no report | fixed | CC parseArgs: `Math.round(n * 1000)`; TT sharp fractional test, mutation killed |
| R11 | BUG | GLM 5.3, fresh-eyes | round 1 | other `/cdn-cgi/` paths (Rocket Loader, Zaraz, `/cdn-cgi/rum`) left bot/analytics/email ok: "no script you didn't add" on a page with one | fixed | CC new item `scripts` (section 5, the checklist's "No scripts you didn't add" bullet): any other `/cdn-cgi/` path is a look that names it; TT; real pages (below) |
| R12 | BUG | Codex, fresh-eyes | round 1 | REF promised that a checklist change cannot leave the script behind unnoticed; the test compares titles and paths only | fixed | REF "Keeping it true" says what is compared and what is not; TT also checks the section 5 bullet |
| R13 | RISK | Codex, fresh-eyes | round 1 | `ai` was ok when 5 of 6 crawler requests got no answer, and said "robots.txt names no crawler" when it could not be read | fixed | CC ai: any silent request is a look and exit 1; the robots wording depends on it having been read |
| R14 | RISK | fresh-eyes (C probes) | round 1 | `User-agent: *` with `Disallow: /` gave robots ok and ai ok | fixed | CC `readRobots` groups; `blocksAll` is a robots FAIL and an ai look |
| R15 | RISK | Codex, fresh-eyes, GLM 5.3 | round 1 | the `ai` ok rested on a claim about Cloudflare nobody could check | fixed | CC ai: state `hand` (policy path shown) with the outside evidence as a hint; a refusal is a look |
| R16 | RISK | fresh-eyes | round 1 | `build` was ok without `--build`: nothing was compared | fixed | CC build: look until `--build` compares |
| R17 | RISK | fresh-eyes | round 1 | any 200 from any host read ok on the domain and the privacy items | fixed | CC domain: no `cf-ray` is a look |
| R18 | RISK | fresh-eyes | round 1 | the https branch of `get()` and `--project` were never run by a test (mutation survived) | fixed | TT closed-port https; real TLS with a certificate made for the run (openssl, skipped loudly if absent); `parseProject` unit tests |
| R19 | RISK | Codex | round 1 | categorical statements about Cloudflare (error attribution, "not treated as the real crawler") | fixed | CC and REF: "probably", "may", "a hint, not a proof"; REF "What it cannot see" |
| R20 | RISK | fresh-eyes | round 1 | many behaviours had no test (mutations survived: robots 404/5xx, 308, alias 302, max-age 0, prefix compare) | fixed | TT 51 tests; a mutation battery of 19 was run, each killed |
| R21 | NIT | fresh-eyes | round 1 | `isMain` is silent under `--preserve-symlinks-main` | fixed | CC also accepts the file's own name; TT runs it through a symlink with those flags |
| R22 | NIT | fresh-eyes | round 1 | `http://<real domain>` was accepted | fixed | CC parseTarget: http only for localhost, 127.x, [::1], *.localhost, *.test |
| R23 | NIT | fresh-eyes | round 1 | `Location: https://host` (no slash) and `:443` failed | fixed | CC `leadsTo` compares parsed origin and path; TT |
| R24 | NIT | fresh-eyes | round 1 | NEL `max_age 0` failed; no `max_age` printed "undefined" | fixed | CC nel; TT |
| R25 | NIT | fresh-eyes | round 1 | `__cflb`, `_cfuvid` called "bot cookie"; a site's own cookie failed Bot Fight Mode | fixed | CC bot: Cloudflare cookies fail, others are a look that does not blame the setting; TT |
| R26 | NIT | fresh-eyes | round 1 | items judged from a redirect read ok | fixed | CC: a would-be ok from a non-200 answer is a look, "judged from the 301 answer, not the page" |
| R27 | NIT | fresh-eyes | round 1 | docs: build FAIL had no pointer; JSON state names and keys unlisted; section 5 heading differed | fixed | CC build fix; REF "For an assistant"; CC SECTIONS[5] = "Check your work" |
| R28 | NIT | fresh-eyes | round 1 | test left a temp dir; symlink needs privilege on Windows | fixed | TT `t.after` cleanup; EPERM skips loudly |
| R29 | NIT | fresh-eyes | round 1 | ENOTFOUND said "the name does not exist"; Node ignores proxy settings | fixed | CC wording; REF "What it cannot see" |
| R30 | NIT | GLM 5.3 | round 1 | a bare `report-to` was a look while the checklist said NEL is on | fixed | CC: Cloudflare's group (`cf-nel`) is a FAIL, another group a look; the checklist's sentence says so |
| R31 | NIT | GLM 5.3 | round 1 | `fix` text attached to "not run" in JSON | fixed | CC `put` keeps `fix` only on fail and look; TT asserts |
| R32 | NIT | GLM 5.3 | round 1 | the body was cut at 1 MB with no marker | fixed | see R1 |
| R33 | NIT | GLM 5.3 | round 1 | a 5xx alias printed "ok ... this is a Pages project" | fixed | see R2 |
| R34 | (unverifiable) | Codex, fresh-eyes | round 1 | Node 18 and Windows were never run | CI | `.github/workflows/clean.yml` job `cloudflare-check-tests`: Node 18, 20, 22, 24 on Ubuntu and 24 on Windows; not yet run by anyone |
| S1 | BUG | Codex | round 2 | `getHome` dropped the headers of earlier answers: NEL and `__cf_bm` on the first hop of a followed redirect read ok | fixed | CC `getHome` returns `chain`; `hdr()` joins every answer's header; cookies from the whole chain; TT "a header on the way counts" |
| S2 | BUG | Codex | round 2 | R5 partly: `title="...cloudflareinsights..."` still failed the three items | fixed | CC `scanPage` reads only src/href/data-src/srcset/action/poster values, `data-cf-beacon` and `data-cfemail` attribute names, and script bodies; TT "what a tag says about itself" |
| S3 | BUG | Codex | round 2 | R11 partly: the `scripts` exclusion matched words anywhere in a path (`/cdn-cgi/image/.../challenge-platform.png` was ok) | fixed | CC `KNOWN_CDN_CGI`: three anchored patterns; TT |
| S4 | BUG | Codex | round 2 | a group named `my-cf-nel-backup` with the owner's own endpoint failed as Cloudflare's | fixed | CC `cloudflareGroup` parses the header as JSON, group exactly `cf-nel` or an endpoint host `nel.cloudflare.com`; unparsable is a look; TT |
| S5 | BUG | Codex | round 2 | `robots.truncated` and `build.truncated` ignored: partial files judged whole | fixed | CC robots and build: truncated is a look, not judged; TT "larger than what is read" |
| S6 | BUG | Codex (outside scope) | round 2 | a zero-byte 200 HTML page was ok for the domain and the privacy items, exit 0 | fixed | CC `empty`: domain FAIL, page items not run; TT |
| S7 | RISK | Codex | round 2 | `cf-ray` absence said "not through Cloudflare", a claim nobody checked | fixed | CC domain: "no cf-ray header came with the answer, so there is no sign it came through Cloudflare" |
| S8 | RISK | GLM 5.3 | round 2 | `Disallow: /*` and `Disallow: *` read as ok (a site invisible to crawlers) | fixed | CC `readRobots`: "/", "/*", "*" are everything; Allow of the same cancels it (RFC 9309, least restrictive wins); TT table |
| S9 | NIT | GLM 5.3 | round 2 | the visible-text `[email protected]` fallback failed a page that explains the feature | fixed | CC: dropped; the link, the script and `data-cfemail` carry the evidence; TT |
| S10 | NIT | GLM 5.3 | round 2 | mutations survive: MAX_HOPS 3 to 1, single email markers, cookie names, content-signal | fixed | TT: a 3-hop and a 4-hop chain, each marker alone, each cookie name, a content-signal test; each mutant killed |
| S11 | NIT | GLM 5.3 | round 2 | a 3xx with no Location was asked three times; an exhausted chain said "run the check on it" about the same address | fixed | CC `getHome` stops without Location or at the same URL; the domain line says "redirected N times on this address"; TT counts the requests |
| S12 | NIT | GLM 5.3 | round 2 | crawler entries in `unanswered` were indistinguishable | fixed | CC `unanswered`: `GPTBot https://host/`; TT |
| S13 | NIT | GLM 5.3 | round 2 | `blockedNames` computed and never read | fixed | CC: removed |
| T1 | BUG | Codex | round 3 | the tag matcher stopped at a quoted ">": `<p title="a > b" data-cfemail="abc">` read email ok, and a URL after it was not read | fixed | CC `readHtml`: a tokenizer, quotes respected; TT "a > inside an attribute value" |
| T2 | BUG | Codex | round 3 | S2 partly: `title="Explains data-cfemail here"` still failed email, `alt="... data-cf-beacon ..."` failed analytics (names were looked for in the tag's raw text) | fixed | CC: attribute NAMES come from the parsed attributes only; TT; mutation "words of values as names" killed |
| T3 | BUG | Codex | round 3 | joined headers across answers corrupted syntax: two `max_age: 0` policies read as FAIL, two HSTS values as "0, or none" | fixed | CC `values()` returns one entry per answer; NEL judged per answer, HSTS from the page's own (last) answer; TT |
| T4 | BUG | Codex | round 3 | S3 partly: `/cdn-cgi/l/email-protection-custom.png` and `.../email-decode.min.js.backup` were still excluded from "other scripts" | fixed | CC `KNOWN_CDN_CGI` anchored at the end, matched on the pathname; TT |
| T5 | RISK | Codex, GLM 5.3 | round 3 | `Allow: /` cancelled `Disallow: /*`: no specificity | fixed | CC `readRobots`: the longer pattern wins, a tie goes to allow (RFC 9309); TT table of three cases |
| T6 | RISK | GLM 5.3 | round 3 | bare words `email-decode` and `cloudflareinsights` matched inside any attribute value or script body (`src="/img/email-decode.png"`, a comment in a script) | fixed | CC `found`: the beacon is the host `static.cloudflareinsights.com` or a `data-cf-beacon` name; address hiding is the exact path, a link, or `data-cfemail`; `/cdn-cgi/` paths come from URL attributes and script text; TT |
| T7 | NIT | Codex | round 3 | the self-redirect guard compared before the cache-buster, so `Location: /` was asked four times | fixed | CC `getHome` compares after `cb`; TT counts requests |
| T8 | NIT | GLM 5.3 | round 3 | "redirected 1 times" | fixed | CC: "once" |
| T9 | NIT | GLM 5.3 | round 3 | a Location that cannot be parsed was reported as another address to run the check on | fixed | CC `addressOf`: said as "a Location that is not an address"; TT |
| V1 | BUG | Codex, GLM 5.3 | round 4 | T3 partly: filtering empty headers before taking the last let HSTS on a redirect stand for the page (ok with --hsts-on) | fixed | CC hsts: the page's own answer; an earlier one is said ("only the redirect before it carried one"); TT |
| V2 | BUG | Codex | round 4 | an address in a script between backticks kept its closing backtick and the semicolon, so email-decode read ok | fixed | CC path pattern excludes backtick, ";" and ","; TT |
| V3 | BUG | Codex | round 4 | a permitted 2.4 MB robots.txt of 200,000 blanket rules threw RangeError (spread into Math.max) and lost the whole report | fixed | CC `longest` is a reduce; TT with 200,000 rules, mutation killed |
| V4 | RISK | Codex | round 4 | the HTML reader's fidelity: textarea text read as markup, an entity-written beacon host missed, "</scripture>" ended a script | fixed | CC `readHtml`: raw-text elements (script, style, textarea, title) with an end-tag boundary; `decodeReferences`; TT |
| V5 | RISK | Codex, GLM 5.3 | round 4 | the RFC 9309 precedence claim was not read | fixed | RFC 9309 2.2.2 read (text in the trail): "The most specific match is the match that has the most octets... If an allow rule and a disallow rule are equivalent, then the allow rule SHOULD be used"; CC comment quotes it; TT |
| V6 | RISK | GLM 5.3 | round 4 | the guard for a 3xx with no Location was deleted and relied on a catch | fixed | CC `getHome`: an explicit `if (!location) break` before the parse |
| V7 | NIT | GLM 5.3 | round 4 | "<![CDATA[...]]>" and "<?...?>" were read as tags | fixed | CC `readHtml` skips them to the next ">"; TT |
| V8 | NIT | GLM 5.3 | round 4 | abrupt comment closers "<!-->", "<!--->" and "--!>" were not ends of comments | fixed | CC `readHtml`; TT |
| V9 | NIT | GLM 5.3 | round 4 | addresses were resolved against a fixed root, not the page's own address | fixed | CC `scanPage(body, base)` with the final page URL; TT (a page at /blog/) |
| V10 | NIT | GLM 5.3 | round 4 | HSTS comment said "the page's own" but took the last answer that carried the header | fixed | see V1 |
| V11 | NIT | GLM 5.3 | round 4 | an empty Location header was reported as "no Location header" | fixed | CC; TT |
| V12 | NIT | GLM 5.3 (outside scope) | round 4 | any href to static.cloudflareinsights.com (a prose link) counted as the beacon | fixed | CC: only a <script src> host or a data-cf-beacon name; TT |
| X1 | BUG | Codex | round 5 | raw-text offsets came from `html.toLowerCase()`, whose length can change ("İ"): after such text, a textarea followed by the beacon read analytics ok | fixed | CC `readHtml`: only A to Z are lower-cased, so every offset is the original's; TT; mutation killed |
| X2 | RISK | Codex | round 5 | the RFC 9309 pattern-length claim had no primary source in the review | fixed | the text of 2.2.2 and 2.2.3 is recorded in the trail from rfc-editor.org (read 2026-10-12); CC's comment quotes the two sentences it follows |
| X3 | RISK | GLM 5.3 | round 5 | every comment copied the rest of the page and regex-scanned it (quadratic) | fixed | CC: the first closer from here by a global regex with `lastIndex`; a first version with two `indexOf` calls was itself quadratic when one closer is absent, which a new test (100,000 comments) caught; ten pathological pages near the cap each take under 0.4 s |
| X4 | NIT | GLM 5.3 | round 5 | an SVG's `<title>` was treated as text, hiding markup a browser loads | fixed | CC `readHtml`: `<svg>` depth, `title` is raw text only outside it; TT |
| X5 | NIT | GLM 5.3 | round 5 | a named reference without ";" before "=" was decoded, which browsers do not do in an attribute | fixed | CC `decodeReferences`: a named reference needs ";", numeric ones may go without; TT |
| X6 | NIT | GLM 5.3 | round 5 | `urls` in `scanPage` was filled and never read | fixed | CC: removed |
| Y1/Y2 | RISK | Codex | round 6 | `<svg/>` (self-closing) left the SVG depth raised, so a later HTML `<title>` was read as markup | fixed | CC `readHtml`: a self-closed svg start tag pushes nothing; TT |
| Y3 | RISK | Codex | round 6 | the RFC 9309 specificity claim had no primary text in the review | fixed | RFC 9309 2.2.2 and 2.2.3, verbatim from rfc-editor.org (read 2026-10-12), are in this brief; CC's comment quotes the two sentences it follows and says which reading of "most octets" it takes |
| Y4 | NIT | GLM 5.3 | round 6 | in foreign content none of script, style, textarea, title is raw text, not only title | fixed | CC: `RAW_TEXT.has(name) && ctx.at(-1) !== 'svg'`; TT (a textarea in an svg) |
| Y5 | NIT | GLM 5.3 | round 6 | the counter was not decremented for a self-closing svg: same as Y1 | fixed | see Y1 |
| Z1 | RISK | Codex | confirmation 1 | an inline <script> inside an <svg> lost its text (every raw-text element had become markup there): `bot` read ok | fixed | CC `readHtml`: in an svg the text of a `script` is collected as script text while its content is still read as markup; TT |
| Z2 | RISK | Codex | confirmation 1 | `<svg id=x/>` counted as self-closing | fixed | CC: a slash closes a tag only when it stands between attributes (the last separator before ">"); TT |
| Z3 | RISK | Codex | confirmation 1 | a foreignObject nested in another ended the outer one on its end tag | fixed | CC: every foreignObject start (not self-closed) is pushed and paired with its end; TT |
| Z4 | RISK | Codex | confirmation 1 | "as in Google's published parser" had no checked source | fixed | github.com/google/robotstxt, robots.cc, read 2026-10-12 (lines quoted in this brief): MatchAllow and MatchDisallow return `pattern.length()`; `disallow()` is `disallow_.specific.priority() > allow_.specific.priority()`, so a tie is allowed; CC's comment cites the file and the two functions |
| A1 | BUG | Codex | confirmation 2 | the svg-script branch took a suffix of the page for every start tag while the reader went on parsing it: 32,000 `<script>` starts in 256 KB gave 4.1 billion script characters to scan (quadratic) | fixed | CC `readHtml`: while an svg `<script>` is open, the text between tags is pushed once, as the reader passes it (`svgScripts`); an end tag closes it; a `</svg>` ends any left open; TT: 40,000 starts inside 20 s, and the three text cases |
| A2 | RISK | Codex | confirmation 2 | the self-closing slash was taken to suppress raw text in HTML too: `<script/>...</script>` lost the script, `<title/>...</title>` gained one | fixed | CC: in HTML a slash on a raw-text element is ignored (`RAW_TEXT.has(name) && !foreign`), it matters only for svg, foreignObject and the like; TT |
| A3 | RISK | Codex | confirmation 2 | the Google parser precedence rested on an attributed excerpt, not a pinned revision | fixed | the brief below quotes robots.cc from github.com/google/robotstxt at commit 50a0dace76c54a0f25c0d1fa6ac53ec7c657c57c (robots.cc last changed 2026-02-27); CC's comment names the repository and the short revision |
| B1 | BUG | Codex | round 7 | a CDATA section inside an svg script was dropped (the "<!" skip took it): `<svg><script><![CDATA[var a="/cdn-cgi/...jsd/main.js";]]></script></svg>` went from fail to ok | fixed | CC `readHtml`: a script in an svg is read as text to its end tag, as in HTML, so the CDATA payload is script text; TT |
| B2 | BUG | Codex | round 7 | one global counter could not tell which svg a script belonged to: a nested svg's end erased the outer script, a stray one kept an inner script alive | fixed | CC: the counter is removed with the machinery it served; TT cases for the nested shapes C reproduced |
| B3 | RISK | Codex | round 7 | the 20-second assertion did not establish linear work (the quadratic evaluator took 0.9 s on the fixture) | fixed | TT asserts the script text taken is no more than the page (`readHtml` exported); mutation "suffix per start" fails it by count |
| B4 | NIT | GLM 5.3 | round 7 | an HTML island's raw text inside an open svg script was dropped from the svg-script stream, against the code's own rule | fixed | moot: the stream is gone; a script is text to its end tag |
| B5 | NIT | GLM 5.3 | round 7 | the timing guard wrapped a whole check, not the parse | fixed | see B3 |
| N1 | NIT | GLM 5.3 | round 8 | the boundedness test asserted an upper bound, so a reader that took some text twice and dropped an equal amount could pass it | fixed, locally_verified | TT: exactly one piece, of exactly the rest of the page; not externally re-verified |
| N2 | NIT | GLM 5.3 | round 8 | the reference file did not say that a self-closed svg script has no text | fixed, locally_verified | REF: "and a self-closed one has no text"; not externally re-verified |

Waivers: none. Deferrals: none. Refuted: none outright; R34 and the UNVERIFIABLE groups were answered by the CI job and by the notes below.

Follow-ups: the pull request's CI has not run this branch; the CI job `cloudflare-check-tests` has not run (no one has run Node 18, 20, 22 or Windows; the first pull request run will). The address-hiding shapes (`data-cfemail`, `/cdn-cgi/l/email-protection`, `email-decode.min.js`) were not seen on a real page; the beacon, the JS-detection script, `/cdn-cgi/image/` and `/cdn-cgi/styles/` were. The HTML reader is not a browser (`REF` says so). The commit message of `390dd65` says "20 NITs": the deduplicated count of round 1 is 13.

Notes:
- Seats: melious ran GLM 5.3 only and kimi was not used (the owner's rule of 2026-10-12). Round 1's Codex failed for model capacity once and its rerun counted; round 2's melious seat hit its 600 s limit with 3 MB of reply and ollama-cloud GLM stood in. Fresh-eyes was a claude-sonnet-5-5 sub-agent in round 1 only (Normal depth).
- Why so many rounds: every round's findings were in the code the last round's fixes had touched. Round 3 replaced the page scanner (regular expressions over tag text) with a small HTML reader, and from then on the findings were its corners. Each fix got a test that fails when the fix is removed (a mutation battery of about 75 mutations, listed by round in the records below, all killed; the ones that survived led to a sharper test). Two of the reviewers' RISKs were about performance, and one of those fixes (round 5) was itself quadratic until a test caught it, as was confirmation 1's (found by confirmation 2).
- What no one could check: browser equivalence of the reader (UNVERIFIABLE in every round; `REF` says "not a browser"), Node 18 and Windows (the CI job), and Cloudflare's output for the address-hiding feature. The first two are in the pull request's CI.
- Data check: no credentials, zone or account identifiers or private names in the diff or the reviewers' output (`scripts/check_clean.sh` OK on every commit). The eight public home pages used as fixtures were fetched once each and are described, not named, in the records, and the saved copies stay in the author's scratch folder. Destinations: Codex, melious.ai and ollama-cloud, the repository's review convention.
- Prompt injection: none in any round. The briefs stated scope as facts and gave no orders about the report's shape.

## Test records

Each run below is complete: command, whole output or its end, exit status.

### The suite on the final tree

Command: `node --test skills/new-website/scripts/tests/cloudflare-check.test.mjs` (what `make test-cloudflare-check` runs). Exit status 0.

```
✔ a clean site: everything an outside request can judge is ok, the rest says what is left (169.145458ms)
✔ without --build the live build is only a look: nothing was compared (130.775458ms)
✔ the plain-text report names every item and ends with a result line (141.017708ms)
✔ NEL still on: the item fails and shows how long browsers keep the note (142.630416ms)
✔ Cloudflare's reporting group alone still fails; a group of your own is a "look" (282.949625ms)
✔ a nel header with max_age 0 is the way a policy is withdrawn: a "look", not "on" (139.865625ms)
✔ no answer at all: the domain fails, nothing that needs the page reads "ok", exit 1 (140.667583ms)
✔ an answer that is cut off is no answer, whatever its first bytes said (200.376625ms)
✔ an answer that starts and then stalls times out as no answer (1110.982459ms)
✔ a page larger than what is read is never "ok" on what was read (167.413125ms)
✔ an error page is not judged as the site: a 522 fails the domain and the privacy items are not run (104.981292ms)
✔ a challenge page is named as such, and the site is not judged from it (100.706708ms)
✔ an answer that is not a 200 page cannot be judged: 204 is a look and the items are not run, exit 1 (96.154ms)
✔ an answer that did not come through Cloudflare is a "look": any 200 is not the site (89.552958ms)
✔ a redirect to the same address is followed and the page is judged where it ends (85.833041ms)
✔ a redirect to another address is not followed: the items are not run, exit 1 (79.536583ms)
✔ the https redirect must lead to the whole address: a longer host is not it (77.664417ms)
✔ the https redirect is judged as an address: another host that quotes ours in a query does not pass (81.18325ms)
✔ the same address written another way is still the https redirect (80.252208ms)
✔ http:// answering 200 is a failure: Always Use HTTPS is not reaching it (71.821875ms)
✔ a 302 to the right place is a "look": visitors arrive, but it is not Always Use HTTPS (78.960125ms)
✔ what Cloudflare injects is found: the bot script (inline), the beacon, the address hiding (82.665791ms)
✔ the bot script alone is found when no cookie was set (95.305792ms)
✔ words about these scripts are not the scripts: a comment, a paragraph and a code sample pass (102.974167ms)
✔ another /cdn-cgi/ feature is a "look" that names it, not a pass (113.292ms)
✔ a cookie that is not Cloudflare's is a "look" that does not blame Bot Fight Mode (105.731083ms)
✔ HSTS: missing is a "look" until --hsts-on says it should be there (196.813625ms)
✔ HSTS: read as directives: months, subdomains, preload; a lookalike or a short age is not "on" (626.251417ms)
✔ robots.txt that still names the starter's example.com is a failure (98.172209ms)
✔ a sitemap on another host is not the placeholder because its name contains "example.com" (197.783708ms)
✔ robots.txt that tells every crawler to stay out fails; a private folder does not (207.269792ms)
✔ rules for named crawlers in robots.txt make the AI item a "look" (99.30375ms)
✔ robots.txt that is a web page fails; a comment that mentions html does not (204.660208ms)
✔ robots.txt that cannot be had: 404 is a look, 500 a failure, no answer a failure and exit 1 (302.754542ms)
✔ an AI crawler name that is refused is a "look" that names it and its status (100.367291ms)
✔ crawler requests that got no answer are not "none refused": a look, and exit 1 (101.602291ms)
✔ --build: the same commit passes, another one fails (211.339958ms)
✔ a build marker that is not a full commit id proves nothing: "dev", a page, a short id (297.3625ms)
✔ build.txt that got no answer, with the domain fine, is a look and a non-zero exit (99.162041ms)
✔ --project: the alias that forwards to the domain passes the forward, and its NEL note stays beside the domain's result (102.505458ms)
✔ --project: an alias that answers 200 means the forward is not set, and the causes are listed (106.261917ms)
✔ --project: a forward to another address fails, and a name that does not answer is named (196.939625ms)
✔ an alias that answers 404, 500 or a challenge is not "a Pages project, ok" (2.001042ms)
✔ --project takes a Pages project, not any address (0.578417ms)
✔ https: a closed port is "connection refused" through the https path (110.375791ms)
✔ https: a site behind a certificate is read over TLS, and an untrusted one is named (286.207ms)
✔ a header on the way counts: NEL and a Cloudflare cookie on the first answer of a followed redirect (122.989166ms)
✔ what a tag says about itself is not what it loads: titles, alt text and data attributes pass (109.503375ms)
✔ only Cloudflare's own paths are excluded from "other scripts": a longer path that quotes one is not (107.736042ms)
✔ a reporting group is judged by what it is: one of your own named like Cloudflare's is yours (300.516625ms)
✔ a robots.txt or build.txt larger than what is read is not judged whole (109.46ms)
✔ a 200 page with nothing in it is not the site: the domain fails and the page items are not run (112.223542ms)
✔ every spelling of "all of it" in a robots group is a stay-out; allowing it too leaves it open (402.519166ms)
✔ each of the address-hiding markers is found alone, and the words are not one (406.97175ms)
✔ each of Cloudflare's cookie names fails; a cookie of your own is a look (633.412083ms)
✔ up to three redirects on the same address are followed; a fourth, or none to go to, is said so (438.120125ms)
✔ Content-Signal lines in robots.txt are Cloudflare's managed file at work: a look for the AI item (135.163584ms)
✔ a silent crawler is named in the list of requests that got no answer (116.538458ms)
✔ a ">" inside an attribute value does not end the tag: what follows it is still read (123.248667ms)
✔ an attribute's value is not an attribute: a title that names data-cfemail or data-cf-beacon is not one (137.291292ms)
✔ headers are read one answer at a time: two withdrawn policies, and two HSTS values, are not corrupted by joining (226.817042ms)
✔ a path that only starts like one of Cloudflare's three is another path (106.773458ms)
✔ the longer pattern wins in a robots group: "Disallow: /*" beats "Allow: /", and "Allow: /*" beats "Disallow: /" (321.973833ms)
✔ a first-party file or a note in a script that happens to contain the word is not Cloudflare's (138.170458ms)
✔ Cloudflare's beacon is found by its address, written with or without a scheme (242.093959ms)
✔ a redirect to the page itself is asked once and said so; a Location that is not an address is said so (258.442625ms)
✔ HSTS on a redirect before the page does not stand for the page: with --hsts-on it fails, and says so (262.644459ms)
✔ an address written in a script between backticks, with a semicolon after it, is read whole (134.187125ms)
✔ a robots.txt with two hundred thousand blanket rules is read, not a crash (248.380959ms)
✔ what the HTML says it is: the text of a textarea or a title is text, a reference is decoded, "</scripture>" does not end a script (428.151459ms)
✔ what is not a tag is skipped, and a comment that ends abruptly does not swallow the page (536.882917ms)
✔ an address is read against the page it is on, and a link to the beacon is not the beacon (141.541583ms)
✔ an empty Location header is said to be empty (150.762959ms)
✔ text that changes length when lower-cased does not move what is found after it (184.335875ms)
✔ a page of a hundred thousand comments is read in linear time and what follows them is found (180.757375ms)
✔ an SVG's title holds markup, as in a browser; an HTML title holds text (272.679334ms)
✔ a named character reference needs its semicolon, as in a browser: "&semi=" in an address is left alone (128.671625ms)
✔ foreign content is read as a browser reads it: a self-closed svg changes nothing, a foreignObject is HTML again, an svg's textarea holds markup (539.737833ms)
✔ foreign content, edges: an svg's inline script is read, a slash inside a value is not a self-closing one, a nested foreignObject end does not end the outer (412.82675ms)
✔ thousands of unclosed script starts inside an svg: the text taken is bounded by the page, and it is script text (158.058584ms)
✔ an svg script is script text to its end tag: a CDATA section, a nested svg and a foreignObject inside it are part of it (691.8015ms)
✔ a self-closing slash on script or title does not stop raw text in HTML, as in a browser (260.304625ms)
✔ a wrong command is exit 2 with the usage text, and --help is exit 0 (1104.371833ms)
✔ a fractional timeout is accepted, and a server that never answers fails within it (1128.1215ms)
✔ it runs when started through a symlink, as an installed skill is, also with symlinks kept (236.991959ms)
✔ parseTarget takes a domain or a local page and refuses a path or a live http:// address (0.436041ms)
✔ the items are the checklist's items, and the paths are its paths (1.817834ms)
ℹ tests 87
ℹ suites 0
ℹ pass 87
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 19552.603625
```

### `make check` on the final tree

Command: `make check`. Exit status 0; 1084 lines of output, ending:

```
ok   skills/independent-review/scripts/test_sweep_claims.sh: stops with an error and leaves its folder alone
all checks passed
LF checkout OK — every text file checks out LF even with core.autocrlf=true
make check  101.96s user 95.42s system 74% cpu 4:24.93 total
```

### The script against live sites (2026-10-12)

```
$ node skills/new-website/scripts/cloudflare-check.mjs croftweaver.com --hsts-on --build 85ca07f1bb53
(the build the site served at 13:44Z; it had been redeployed since: the check says so and exits 1)
5 · Check your work
  ok       Your own robots.txt
           a robots file with a Sitemap line that names croftweaver.com.
  FAIL     The build that is live
           serves build 1e818a173b91, but you expected 85ca07f1bb53: the live domain is on another build. Wait for the deploy, or look at Deployments.
           → See section 5 of the Cloudflare checklist.
  ok       No scripts you didn't add
           no other /cdn-cgi/ path in the page we received.

Result: 9 ok, 1 FAIL, 0 look, 5 by hand, 2 not run.
FAIL means the checklist is not met and it is worth fixing first. The checklist says how.
"by hand" items have no outside check, or only a hint: open the dashboard path shown.
[exit status 1]

$ node skills/new-website/scripts/cloudflare-check.mjs croftweaver.com --hsts-on --build <the build now served>
Cloudflare check for croftweaver.com
Looked from outside with plain GET requests, 2026-10-12T16:09:37Z. Nothing was changed.

1 · Set up the site
  not run  Create a Pages project, not a Worker
           not checked: give --project <name> to check that <name>.pages.dev answers (a Worker answers on workers.dev).
  by hand  Build settings
           Workers & Pages → your project → Settings → Builds & deployments: framework preset Astro, build command npm run build, output directory dist; on a two-stage site the Production branch is production.
  ok       Attach your domain to the project
           https://croftweaver.com/ answered 200.
  by hand  Set Fail open
           Workers & Pages → your project → Settings → Runtime → Fail open / closed: it should say Fail open.
  not run  Send the <project>.pages.dev address to your live domain (301)
           not checked: give --project <name> to check that <name>.pages.dev forwards to your domain.

2 · Safe connections
  ok       Always Use HTTPS: On
           http:// answers 301 and sends visitors to https://croftweaver.com/.
  by hand  Minimum TLS Version: TLS 1.2
           Your domain → SSL/TLS → Edge Certificates → Minimum TLS Version: then run the domain through ssllabs.com/ssltest: TLS 1.0 and 1.1 should say No.
  ok       HSTS: On, and last
           on: max-age 15552000 (about 6 months), subdomains on, preload off.

3 · Keep the privacy page true
  ok       Network Error Logging (NEL): Off
           no nel and no report-to header on the home page.
  ok       Bot Fight Mode: Off
           no cookie and no bot-detection script in the page we received. A browser can see more: view the source once.
  ok       Cloudflare Web Analytics: Off
           no Cloudflare measurement script in the page we received.
  ok       Email Address Obfuscation: Off
           no Cloudflare address hiding (email-decode script, protected link or data-cfemail) in the page we received.

4 · Be found, by search engines and AI assistants
  by hand  Crawler Hints: On
           Your domain → Caching → Configuration → Crawler Hints: there is no outside check for this one.
  by hand  AI crawlers: allow
           outside evidence: none of 6 AI crawler names was refused, and robots.txt names no crawler. A name alone may not be treated as the real crawler, so this is a hint. The policy itself is in the dashboard (Your domain → Security → Settings → filter by Bot traffic → Configure AI bot policies) and cannot be read from outside.

5 · Check your work
  ok       Your own robots.txt
           a robots file with a Sitemap line that names croftweaver.com.
  ok       The build that is live
           serves build 1e818a173b91, the one you expected.
  ok       No scripts you didn't add
           no other /cdn-cgi/ path in the page we received.

Result: 10 ok, 0 FAIL, 0 look, 5 by hand, 2 not run.
"by hand" items have no outside check, or only a hint: open the dashboard path shown.
[exit status 0]

$ node skills/new-website/scripts/cloudflare-check.mjs this-name-does-not-exist-cfcheck.invalid --timeout 10
Cloudflare check for this-name-does-not-exist-cfcheck.invalid
Looked from outside with plain GET requests, 2026-10-12T16:09:37Z. Nothing was changed.

1 · Set up the site
  not run  Create a Pages project, not a Worker
           not checked: give --project <name> to check that <name>.pages.dev answers (a Worker answers on workers.dev).
  by hand  Build settings
           Workers & Pages → your project → Settings → Builds & deployments: framework preset Astro, build command npm run build, output directory dist; on a two-stage site the Production branch is production.
  FAIL     Attach your domain to the project
           no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)
           → Is the domain attached to the project, and are its DNS records on Cloudflare? See section 1 of the Cloudflare checklist.
  by hand  Set Fail open
           Workers & Pages → your project → Settings → Runtime → Fail open / closed: it should say Fail open.
  not run  Send the <project>.pages.dev address to your live domain (301)
           not checked: give --project <name> to check that <name>.pages.dev forwards to your domain.

2 · Safe connections
  FAIL     Always Use HTTPS: On
           no answer from http://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)
           → See section 2 of the Cloudflare checklist.
  by hand  Minimum TLS Version: TLS 1.2
           Your domain → SSL/TLS → Edge Certificates → Minimum TLS Version: then run the domain through ssllabs.com/ssltest: TLS 1.0 and 1.1 should say No.
  not run  HSTS: On, and last
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)

3 · Keep the privacy page true
  not run  Network Error Logging (NEL): Off
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)
  not run  Bot Fight Mode: Off
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)
  not run  Cloudflare Web Analytics: Off
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)
  not run  Email Address Obfuscation: Off
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)

4 · Be found, by search engines and AI assistants
  by hand  Crawler Hints: On
           Your domain → Caching → Configuration → Crawler Hints: there is no outside check for this one.
  not run  AI crawlers: allow
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)

5 · Check your work
  not run  Your own robots.txt
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)
  not run  The build that is live
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)
  not run  No scripts you didn't add
           not checked: no answer from https://this-name-does-not-exist-cfcheck.invalid/: the name could not be looked up (it may not exist, or this network blocks it)

Result: 0 ok, 2 FAIL, 0 look, 4 by hand, 11 not run.
10 requests got no answer, which counts as a failure: https://this-name-does-not-exist-cfcheck.invalid/, https://this-name-does-not-exist-cfcheck.invalid/robots.txt, http://this-name-does-not-exist-cfcheck.invalid/, https://this-name-does-not-exist-cfcheck.invalid/build.txt, GPTBot https://this-name-does-not-exist-cfcheck.invalid/, OAI-SearchBot https://this-name-does-not-exist-cfcheck.invalid/, ClaudeBot https://this-name-does-not-exist-cfcheck.invalid/, PerplexityBot https://this-name-does-not-exist-cfcheck.invalid/, CCBot https://this-name-does-not-exist-cfcheck.invalid/, Amazonbot https://this-name-does-not-exist-cfcheck.invalid/
9 items could not be judged, which counts as a failure: they are the "not run" lines that say "not checked".
FAIL means the checklist is not met and it is worth fixing first. The checklist says how.
"by hand" items have no outside check, or only a hint: open the dashboard path shown.
[exit status 1]

$ node skills/new-website/scripts/cloudflare-check.mjs croftweaver.com --project not-a-real-project-cfcheck --timeout 20 --json   (summary, unanswered, couldNotJudge, and the pages and canonical items)
{'ok': 9, 'fail': 1, 'look': 1, 'hand': 5, 'skip': 1}
unanswered: ['https://not-a-real-project-cfcheck.pages.dev/']
couldNotJudge: ['canonical']
pages fail - no answer from https://not-a-real-project-cfcheck.pages.dev/: the name could not be looked up (it may not exist, or this network blocks it). Check the project name: a Worker would answer on a workers.dev address, not pages.dev.
canonical skip - not checked: the pages.dev address did not answer.
[exit status 1]
```

### Eight saved public home pages, served from a local stub, through the final script

The pages are the home pages of Cloudflare-fronted public sites, fetched once each with a browser User-Agent and a text/html Accept header. Columns: bot, analytics, email, scripts.

```
a vendor's own marketing home page, 1.3 MB   bot:ok    analytics:fail  email:ok    scripts:ok    
the vendor's developer docs home page        bot:ok    analytics:fail  email:ok    scripts:look  the page uses /cdn-cgi/image/... (and other paths)
the vendor's blog home page                  bot:ok    analytics:fail  email:ok    scripts:ok    
a chat service's home page                   bot:fail  analytics:ok    email:ok    scripts:ok    
a publishing site's challenge page           bot:fail  analytics:fail  email:ok    scripts:look  the page uses /cdn-cgi/styles/... (and other paths)
a support software vendor's home page        bot:ok    analytics:ok    email:ok    scripts:look  the page uses /cdn-cgi/image/... (and other paths)
a commerce platform's home page              bot:ok    analytics:ok    email:ok    scripts:ok    
a cloud host's home page                     bot:ok    analytics:ok    email:ok    scripts:ok    
```

### Pathological pages near the 5 MB cap, through the final script (each a whole run of the program, in milliseconds)

```
unclosed anchors            725 ms   ok/ok/ok/ok
lt only                     406 ms   ok/ok/ok/ok
many unclosed scripts       174 ms   ok/ok/ok/ok
cdata openers               304 ms   ok/ok/ok/ok
comment openers             170 ms   ok/ok/ok/ok
attribute soup              361 ms   ok/ok/ok/ok
quote never closed          167 ms   ok/ok/ok/ok
references                  391 ms   ok/ok/ok/ok
close tag lookalikes        180 ms   ok/ok/ok/ok
textarea many               150 ms   ok/ok/ok/ok
```

### The primary sources the robots precedence follows

RFC 9309, "Robots Exclusion Protocol", sections 2.2.2 and 2.2.3, verbatim from https://www.rfc-editor.org/rfc/rfc9309.txt (read 2026-10-12):

```
2.2.2.  The "Allow" and "Disallow" Lines
       2.2.3.  Special Characters
```

google/robotstxt, `robots.cc`, at commit `50a0dace76c54a0f25c0d1fa6ac53ec7c657c57c` (last changed 2026-02-27; fetched from raw.githubusercontent.com on 2026-10-12, byte-identical to its master copy that day):

```
469: 
470: // Implements the default robots.txt matching strategy. The maximum number of
471: // characters matched by a pattern is returned as its match priority.
472: class LongestMatchRobotsMatchStrategy : public RobotsMatchStrategy {
...
553:   return AllowedByRobots(robots_txt, &v, url);
554: }
555: 
556: bool RobotsMatcher::disallow() const {
557:   if (allow_.specific.priority() > 0 || disallow_.specific.priority() > 0) {
558:     return (disallow_.specific.priority() > allow_.specific.priority());
559:   }
...
689: 
690: int LongestMatchRobotsMatchStrategy::MatchAllow(absl::string_view path,
691:                                                 absl::string_view pattern) {
692:   return Matches(path, pattern) ? pattern.length() : -1;
693: }
694: 
695: int LongestMatchRobotsMatchStrategy::MatchDisallow(absl::string_view path,
696:                                                    absl::string_view pattern) {
697:   return Matches(path, pattern) ? pattern.length() : -1;
698: }
```

### Mutation batteries (each: the mutation, and the number of failing tests; "caught" means the suite went red)

Round 1 (19): cut-off body read as a page; cap not reported; placeholder by substring; HSTS unanchored; wildcard block ignored; comments read as code; unanswered requests not in the exit status; could-not-judge not in the exit status; location by `includes`; no `cf-ray` rule; `pages` ok for any status; redirects not followed; Cloudflare report-to group a look; short marker accepted; silent crawlers ok; other `/cdn-cgi/` passes; non-Cloudflare cookie a pass; `http://` for a real domain; timeout not rounded. All caught, and the timeout one only after the test used 1.0001 s.
Round 2 (6): chain headers dropped; any attribute counts; known paths unanchored; group by substring; robots truncation ignored; empty page a page. All caught.
Round 3 (7): MAX_HOPS 3 to 1; only "/" is everything; no `data-cfemail`; no `_cfuvid`; content-signal ignored; unanswered unnamed; no-Location re-asked (an equivalent mutant: the same-URL guard catches it). Six caught.
Round 4 (9): quotes not respected; words of values as names; headers joined; email-protection and decode unanchored; allow beats on a tie; length ignored; scheme-relative lost; self-redirect compared early. All caught.
Round 5 (11): HSTS from any answer; backtick in paths; spread max; textarea markup; no reference decoding; no end-tag boundary; bogus comments as tags; abrupt closers lost; fixed base; any href is the beacon; empty as absent. Ten caught at once, and the spread one after the test used 200,000 blanket rules.
Round 6 (4+3): Unicode lower-casing; comment by slice and regex (the test found the first rewrite quadratic); svg title as text; named reference without a semicolon; self-closing svg counted; foreignObject ignored; only title exempt. All caught.
Confirmation 1 and 2 (3+3): svg script text dropped; slash in a value closes; foreignObject only in svg; svg script text not collected; slash stops raw text in HTML; open svg script outlives its svg. All caught.
