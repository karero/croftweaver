# DIFF review — docs/cloudflare-checklist — `docs/CLOUDFLARE-CHECKLIST.md`: the Cloudflare settings a Croftweaver site relies on, with dashboard paths and a token route

Base `e58d3ae` (origin/main, merged in at `e856039`; rounds 1 to 4 ran against `896e3c5`) · depth: **High** (an owner or an assistant holding an API token changes settings that can lock visitors out of the site, change what its privacy page may say, or hide it from search engines and AI assistants) · verdict: **CLEAN** at `f48fb2a` (4 rounds, 95 findings: 11 BUG, 33 RISK, 51 NIT; every BUG and RISK fixed, refuted or waived; none after round 3 was a BUG) · authority used: WORKTREE-WRITE (atom A: this session created the worktree), BRANCH-COMMIT (atom A: this session created the branch), GATED-THIS-DIFF (atom A: reviewer input captured for the pair, a round 1 full capture and a verification chain bridged by a merge link at `e8d4942`); POST AUTHORITY is claimed in the PR comment once the PR exists (atom A: this session creates it).

Abbreviations: `CL` = `docs/CLOUDFLARE-CHECKLIST.md`, `CFD` = `skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`, `SCS` = `skills/search-console-setup/SKILL.md`, `WA` = `skills/new-website/references/WEBSITE_ARCHITECTURE.md`.

Files this change touches: `docs/CLOUDFLARE-CHECKLIST.md` (new), `README.md` (one row in the docs tree), `CFD` (one section), `WA` (two lines), `SCS` (one sentence), `docs/BUGLOG.md` (one row). The commit that adds this trail takes only this file.

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT (after dedup) |
|---|---|---|---|---|---|
| 1 | `d87f640` | full `896e3c5...d87f640`, after a claims sweep (`sweep_claims.sh`) whose list led to that head | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only; melious glm-5.3 (HTTP API); fresh-eyes (claude-sonnet-5-5 sub-agent, no shared context) | codex 348 s / 67,522; melious 250 s / 23,490 | 4 / 13 / 16 |
| 2 | `5990bd9` | delta since `d87f640` | codex; ollama-cloud glm-5.3:cloud (melious FAILED: curl exit 28 at its 300 s limit, reply cut off); fresh-eyes | codex 654 s / 96,436; ollama-cloud 870 s | 4 / 7 / 14 |
| 3 | `63b16c4` | delta since `5990bd9` | codex; melious glm-5.3; fresh-eyes | codex 485 s / 81,486; melious 149 s / 26,690 | 3 / 6 / 11 |
| 4 | `bacc3d7` | delta since `63b16c4` | codex; melious glm-5.3 (MELIOUS_API_TIMEOUT 600); fresh-eyes | codex 498 s / 82,286; melious 299 s / 33,319 | 0 / 4 / 8 |
| wording pass (not a round) | `e8d4942` | delta `bacc3d7..e8d4942`, prose only | codex 0.162.1 (`--seat codex`, medium, read-only) | codex 154 s / 43,883 | 0 / 1 / 0 |
| final full read (not a round) | `7a665a0` | the whole change `e58d3ae...7a665a0`, with the repository facts quoted in the brief | ollama-cloud kimi-k3:cloud (`--seat ollama`) | 374 s | 0 / 1 / 2 |
| confirmation (re-gate, not a round) | `f48fb2a` | delta `e8d4942..f48fb2a` by merge link (`896e3c5`, `e8d4942`, `e58d3ae`), prose only | codex 0.162.1 (`--seat codex`, medium, read-only) | codex 136 s / 47,297 | 0 / 1 / 0 |

Round 4 was earned by round 3's three BUGs (F59 to F61: what an owner runs and accepts) and found none, so the rounds ended there. Merge link: the base was merged in after the wording pass. Of this change's own files the merge moved three: `CL` (the F91 paragraph), `docs/BUGLOG.md` (the row about the privacy templates dropped, because the base branch removed the sentences it was about) and `WA` (one analytics line that came from the base branch). Files the merge changed that this change's text leans on were read on the merged tree: `public/_headers` (five security headers, no HSTS), `Base.astro` line 135 (reads `localStorage.getItem('theme')` only) and the two privacy pages (their statements about the device are quoted in the full-read brief).

| id | Sev | Source | Round | Finding — one line | Status (+ locally_verified / externally_reverified) | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex, GLM, fresh-eyes | 1 | Section 5 expected `includeSubDomains`, contradicting section 2 ("If unsure, Off") | fixed, locally_verified | CL section 5: expects `max-age=15552000`, `; includeSubDomains` only if turned on |
| F2 | BUG | Codex, fresh-eyes | 1 | "no analytics" stated for every site; the template privacy page describes a cookieless Plausible setup | fixed, locally_verified | CL section 3 heading and intro reworded; Cloudflare Web Analytics named as separate; CFD sentence reworded |
| F3 | BUG | Codex | 1 | HTTPS check printed only line 1 and hid Location and curl failure | fixed, locally_verified | CL section 5 third command prints `HTTP` and `location:`; empty output means curl failed |
| F4 | BUG | Codex, GLM, fresh-eyes | 1 | "a command that checks it / each ... with a check" untrue for Fail open and Crawler Hints (README row, CFD) | fixed, locally_verified | README row, CFD sentence reworded; CL section 5 names the two with no outside check |
| F5 | RISK | fresh-eyes | 1 | Section 5 run before the deployment is Active and without a cache-bust | fixed, locally_verified | CL section 5 intro and `?cb=1` on the first two commands |
| F6 | RISK | fresh-eyes | 1 | Section 1 written for the create form but run after deploy; no `.pages.dev` test; no production-branch location | fixed, locally_verified | CL section 1 split in two; address test; path from Pages "branch and build controls" page |
| F7 | RISK | fresh-eyes | 1 | HSTS in a list run right after first deploy removes the rollback | fixed, locally_verified | CL HSTS item: "On, and last", start with 1 month if the domain moved |
| F8 | RISK | fresh-eyes | 1 | Minimum TLS: "applies to your own domain" is the author's gloss | fixed, locally_verified | gloss deleted; the page's statement attributed; SSL Labs fallback |
| F9 | RISK | GLM, fresh-eyes | 1 | "the browser keeps a note for seven days" on no cited page | fixed, locally_verified | CL now says what Cloudflare's header said on 2026-10-12 and points to the owner's own `nel:` line; MDN added to Sources |
| F10 | RISK | fresh-eyes | 1 | NEL "note on the device" reasoning also applies to HSTS; template privacy pages say nothing else is stored | fixed in CL; template part follow-up | NEL reason rewritten around reports sent to Cloudflare; HSTS paragraph says it is also a note; BUGLOG row 2026-10-12 |
| F11 | RISK | fresh-eyes | 1 | First check cannot see `cf_clearance`; "settings keep that true" over-promises | fixed, locally_verified | CL section 5 text; section 3 intro softened |
| F12 | RISK | fresh-eyes | 1 | SCS and CL give two click paths for the AI crawler panel | fixed, locally_verified | SCS pointer sentence to CL section 4; BUGLOG row 54 (dashboard verification) stays open |
| F13 | RISK | fresh-eyes, Codex | 1 | WA lines 188 and 247 say `_headers` carries HSTS | fixed, locally_verified | both lines edited; cache-rule half of line 188 is a BUGLOG row |
| F14 | RISK | Codex, GLM, fresh-eyes | 1 | NEL "first is not enough on a Pages site" generalizes one site; `editable: false` and the missing-switch case absent; Support flag not shown to stop a served header | fixed, locally_verified | CL NEL item is switch, check, rule; "when we tried this on a Pages site"; missing or greyed out goes to step 3; Support wording describes the flag |
| F15 | RISK | fresh-eyes | 1 | "You want 301" on no cited page | fixed, locally_verified | CL: "a redirect (301 or 308)" and a `location:` line |
| F16 | RISK | GLM | 1 | "starter sends nosniff" and "kit hides addresses" unverified | refuted | Codex VERIFIED both: `public/_headers:5` declares nosniff; `EmailLink.astro` calls `src/lib/obfuscate.ts`, tests in `tests/email.spec.ts` |
| F17 | RISK | GLM | 1 | "You don't need a key file" has no source in the document | fixed, locally_verified | sentence deleted |
| F18 | NIT | GLM, fresh-eyes | 1 | Create-screen layout undated | fixed | "As of October 2026" and a fallback |
| F19 | NIT | GLM | 1 | § 25 paraphrase dropped "for a service the visitor expressly asked for" | fixed | CL NEL "Why off" |
| F20 | NIT | fresh-eyes | 1 | Training "Allow" framed as for assistants; it is an owner choice | fixed | CL section 4 |
| F21 | NIT | fresh-eyes | 1 | "leave it Off" for a setting that may be On | fixed | "make sure it is Off" |
| F22 | NIT | fresh-eyes | 1 | NEL step 1 never says switch Off, nor that any zone admin can switch it back on | fixed | CL NEL step 1 |
| F23 | NIT | fresh-eyes | 1 | HSTS confirmation dialog and Save missing | fixed | CL HSTS item |
| F24 | NIT | fresh-eyes | 1 | `CANONICAL_URL` unexplained | fixed | assistant sets it; link to CFD "After go-live" |
| F25 | NIT | fresh-eyes | 1 | "look rather than assume" gives a non-technical owner nothing to do | fixed | "tell your assistant" |
| F26 | NIT | fresh-eyes | 1 | Web Analytics: nothing said when the domain is not listed | fixed | one sentence |
| F27 | NIT | fresh-eyes | 1 | curl/grep on Windows | fixed | "on Windows use Git Bash or WSL" |
| F28 | NIT | fresh-eyes | 1 | "so you lose little" is a judgment | fixed | named as a trade-off |
| F29 | NIT | fresh-eyes | 1 | Rule removes a later `Report-To` silently | fixed | one sentence |
| F30 | NIT | fresh-eyes | 1 | "right away"; "Cloudflare's docs add rules" | fixed | "soon after"; "Cloudflare adds rules" |
| F31 | NIT | fresh-eyes | 1 | Cost of TLS 1.2 unstated | fixed | one sentence |
| F32 | NIT | fresh-eyes | 1 | "§ 25 asks for consent" placed before its hedge | fixed | merged into the F10 rewrite |
| F33 | NIT | fresh-eyes | 1 | Intro said the paths were checked; the file did not state they were not | fixed | CL intro |
| F34 | BUG | Codex, GLM | 2 | section 5's redirect check matched with an alternation that dropped the status line (it is `HTTP/1.1 301`, no colon after HTTP) and read a 200 as a failed request; F3's fix landed broken | fixed, locally_verified | pattern now starts `^(HTTP/` and has `location:` as its second alternative; run on synthetic header text: a 301 prints both lines |
| F35 | BUG | Codex, GLM, fresh-eyes | 2 | CL section 5 expected `max-age=15552000` (six months) though section 2 allows starting with 1 month | fixed, locally_verified | CL section 5: "max-age= followed by the seconds for the months you chose (for six months we saw 15552000)" |
| F36 | BUG | Codex | 2 | CFD still promised "a command that checks each" | fixed, locally_verified | CFD: "and an outside check where one exists" |
| F37 | BUG | Codex, fresh-eyes | 2 | BUGLOG row misquoted the English privacy page (no theme exception there; the general sentence is the German page's) | fixed, locally_verified | row rewritten: German page's sentence vs English page's measurement sentence and missing theme disclosure |
| F38 | RISK | Codex, fresh-eyes | 2 | Token matrix: Free-plan Bot Management, AI-policy writes and readbacks unsubstantiated | fixed | CL section 6: "If the API refuses a setting (some are limited to certain plans), do that item by hand from sections 2 to 4" |
| F39 | RISK | Codex, fresh-eyes | 2 | F10's template half: German privacy template says nothing else is stored, while the checklist recommends HSTS; "Nothing was deferred or waived" was inaccurate | partly fixed; template half open for the owner | CL HSTS item now tells the owner their privacy page needs a line (judgment, not a ruling); the template wording is a BUGLOG row (2026-10-12); owner waiver of the template half requested in the PR text |
| F40 | RISK | Codex, fresh-eyes | 2 | Seven-day expiry stated unhedged | fixed | CL: "until the `max_age` in your `nel:` line runs out (604800 seconds is seven days)" |
| F41 | RISK | Codex, GLM | 2 | `?cb=1` reused on every rerun | fixed | CL section 5 uses `?cb=$(date +%s)`; robots.txt command drops the query |
| F42 | RISK | GLM, fresh-eyes | 2 | The token route and section 5 put HSTS on day one | fixed | CL intro, section 5 (line absent until HSTS is on) and section 6 (HSTS not part of the token afternoon) |
| F43 | RISK | fresh-eyes | 2 | "read back to show they took" contradicts the NEL evidence | fixed | CL section 6: "Then check it yourself ... Before you delete the token, run section 5" |
| F44 | RISK | fresh-eyes | 2 | "Give the assistant the token as an environment variable" is not something a non-technical owner can do | fixed | CL section 6: tell the assistant; it shows where to put it; do not paste it into email, a document or a shared chat |
| F45 | NIT | GLM, fresh-eyes | 2 | Production-branch path exists only for Git-connected projects | fixed | CL section 1 |
| F46 | NIT | GLM, fresh-eyes | 2 | NEL switch missing from the section 6 table | fixed | Zone Settings row now lists it |
| F47 | NIT | GLM, fresh-eyes | 2 | "each set to Edit" above a Read row | fixed | "each set to Edit except the Zone → Read row" |
| F48 | NIT | fresh-eyes | 2 | Pages row has no Account Resources; Pages Edit is account-wide | fixed | Account Resources line |
| F49 | NIT | fresh-eyes | 2 | TTL "tomorrow" vs CFD "about 1 week" | fixed | "tomorrow, a week at most" |
| F50 | NIT | fresh-eyes | 2 | SCS pointer scope and qualifier | fixed | SCS: "For the first bullet ... in the Croftweaver folder" |
| F51 | NIT | fresh-eyes | 2 | A Worker's address form | fixed | "a `.workers.dev` address" |
| F52 | NIT | fresh-eyes | 2 | "find out what" not actionable | fixed | "tell your assistant" |
| F53 | NIT | fresh-eyes | 2 | robots.txt check fails an owner who chose to block Training | fixed | "other than ones from a policy you set to block" |
| F54 | NIT | fresh-eyes | 2 | "A change reaches your site with the next deployment" unsupported for disabling | fixed | "After you disable it, deploy again and check the page source" |
| F55 | NIT | fresh-eyes | 2 | `cdn-cgi/scripts` path not on a cited page | fixed | "`email-decode` is email obfuscation" |
| F56 | NIT | fresh-eyes | 2 | `/robots.txt?cb=1` equivalence unknown | fixed | query dropped for robots.txt |
| F57 | NIT | Codex, GLM, fresh-eyes | 2 | WA line 188 still lists cache rules the template lacks | fixed | clause removed; the BUGLOG row for it dropped |
| F58 | NIT | fresh-eyes | 2 | RFC 6797, § 25 TDDDG and the browser-compat data not among the cited sources | fixed | added to Sources |
| F59 | BUG | Codex, fresh-eyes | 3 | section 5's first command printed nothing for a clean 200, a 301 without the four headers, and a failed request, so "NEL is gone" could pass on a dead request | fixed, locally_verified | the pattern now includes the `HTTP/` status line; "an empty answer is never a pass"; a 3xx on the live domain is explained |
| F60 | BUG | Codex | 3 | "starts `https://yourdomain.com`" accepts `https://yourdomain.com.au/` | fixed, locally_verified | both redirect checks now say the `location:` line starts `https://yourdomain.com/` and explain the slash; demonstrated: prefix without slash passes `.com.au`, with slash rejects it |
| F61 | BUG | Codex, fresh-eyes | 3 | BUGLOG row said `Base.astro` "keeps" the theme in `localStorage`; it only reads it | fixed, locally_verified | row now says line 135 only reads `getItem('theme')`, nothing in the starter writes it (the only `setItem` is `tests/a11y.spec.ts`); `rg localStorage` over the starter's `src` shows one use |
| F62 | RISK | Codex, fresh-eyes | 3 | F39's template half: the German template's "nothing else is stored" wording is unchanged while the checklist recommends HSTS | **waived by the owner** | Owner, in the session, 2026-10-12: "yes, waive the template half". CL HSTS item tells the owner to add a privacy-page line (judgment, not a ruling); BUGLOG row 2026-10-12 stays open as the follow-up |
| F63 | RISK | Codex, fresh-eyes | 3 | API claims in section 6 (Free-plan Bot Management, AI policy writes, the Pages variable call) lack run evidence | fixed | CL section 6: "We have run only the Transform Rules call on live sites, so for the others the assistant should read each setting back, and you run section 5"; "a change to one variable may replace the project's others, so it must list what is there before and after" |
| F64 | RISK | fresh-eyes | 3 | "redeploy with a new commit" does not publish production on a two-stage site (preview only) or a Direct Upload project | fixed | CL section 1 item: the assistant "publishes the production site again ... has the steps for each kind of project", pointing at CFD "After go-live" step 2 |
| F65 | RISK | fresh-eyes | 3 | The 301 item dropped CFD's pre-save `build.txt` check and the warning that browsers remember a 301; entry condition weaker; placeholder matched the check | fixed | item heading: "Active, and `https://yourdomain.com/build.txt` shows the current build"; "the assistant opens `build.txt` on that address first"; "Browsers remember a 301 ..."; the value is described as `https://` and the owner's domain, not a literal placeholder |
| F66 | RISK | fresh-eyes | 3 | NEL on the alias: the 301 was presented as the remedy, but the 301 answer comes from that host and the check hid `nel:`/`report-to:` | fixed | CL section 5's last command prints them and says what they mean; section 3 no longer claims the redirect removes them; BUGLOG row added for trying to strip them in the middleware |
| F67 | NIT | GLM, fresh-eyes | 3 | A 200 on the alias: causes incomplete, "value was refused" misattributes (the middleware ignores it) | fixed | CL: five causes including misnamed, predates the redirect, and "isn't one the redirect accepts" |
| F68 | NIT | GLM | 3 | "HSTS item never says to wait a few days" | refuted | CL section 2 HSTS item opens "HSTS: On, and last. Do this one when the site has been live and working for a few days"; the reviewer saw only a hunk |
| F69 | NIT | GLM, fresh-eyes | 3 | `yourproject` placeholder not covered by "Replace" sentence | fixed | CL section 5 intro names both placeholders |
| F70 | NIT | fresh-eyes | 3 | Intro said one item waits; sources line said two project steps; Pages API pages not in Sources | fixed | intro: two items wait; sources line lists three CFD steps; the Pages edit API page added |
| F71 | NIT | fresh-eyes | 3 | Section 6 said "sections 1 to 4" then "by hand from sections 2 to 4"; Pages row omitted attaching the domain | fixed | "by hand from sections 1 to 4"; Pages row lists attaching the domain |
| F72 | NIT | fresh-eyes | 3 | prior-findings record said "Nothing was deferred" while F39's template half awaited a waiver | fixed | this file; the PR text will say waived |
| F73 | NIT | fresh-eyes | 3 | "A privacy page that says nothing ... is stored" ambiguous; `max_age` points at a line the rule removed | fixed | reworded; NEL step 2 tells the owner to note the `max_age` number |
| F74 | NIT | fresh-eyes | 3 | "a policy you set to block" omits Training "Disallow" | fixed | "block or disallow" |
| F75 | RISK | fresh-eyes | 3 | "Cloudflare adds rules only when at least one of the three is set to a block" vs a separate managed robots.txt switch (`is_robots_txt_managed`; SCS) | fixed | the sentence is replaced by "Cloudflare can also add its own managed robots.txt rules. Section 5 shows the file."; section 5 tells the owner what to do if lines show |
| F76 | NIT | fresh-eyes | 3 | "rewrites any plain email address" | fixed | "the plain email addresses it finds in your page text" |
| F77 | NIT | fresh-eyes, Codex | 3 | German page's theme sentence describes storage the starter does not do | in the BUGLOG row; template half waived (F62) | BUGLOG row 2026-10-12 |
| F78 | NIT | Codex | 3 | Codex: the F35 "observation" of 15552000 is unverified | stands as observation | CL words it as "for six months we saw 15552000" |
| F79 | RISK | Codex, fresh-eyes | 4 | F66 partly fixed: CL still presented forwarding the alias as the NEL remedy; no way to remove the headers on that host has been found | fixed, locally_verified | CL section 3 closing paragraph: "the rule can't reach it, and we have found no way to remove the headers there. Sending that address to your live domain moves visitors on; it removes nothing. The last command in section 5 shows whether that address still sends them"; section 5 adds "Tell your assistant; we have found no way to remove them there" |
| F80 | RISK | GLM | 4 | A placeholder left in a command can reach a stranger's site and print a clean 200 | fixed, locally_verified | CL section 5 intro: "make sure the domain in the command is yours ... the robots.txt below must be your own file" |
| F81 | RISK | GLM | 4 | The slash requirement in the alias check may fail a correctly configured site if the middleware redirects to the bare canonical value | refuted | `skills/new-website/templates/astro/functions/_middleware.ts:67`: `return Response.redirect(live + url.pathname + url.search, 301);` and a pathname always begins with `/`; three seats executed or traced the middleware |
| F82 | RISK | fresh-eyes | 4 | Section 5 asked only for an Active deployment; a domain whose nameservers have not moved reads as a pass | fixed, locally_verified | CL section 5 intro: "once your own domain serves this site: the production deployment shows Active, the custom domain is Active, and build.txt shows the current build" |
| F83 | NIT | Codex | 4 | `max_age` was noted only after the switch had removed the header | fixed, locally_verified | CL NEL step 1 "Look first" notes `max_age` before step 2, the switch |
| F84 | NIT | fresh-eyes | 4 | "A 200 means one of" omitted the empty host part and the Fail open day | fixed, locally_verified | CL section 5 alias paragraph |
| F85 | NIT | fresh-eyes | 4 | Section 6 said only HSTS waits; CANONICAL_URL also waits for the domain | fixed, locally_verified | CL section 6 intro: "Setting CANONICAL_URL waits too" |
| F86 | NIT | fresh-eyes | 4 | "says nothing at all is stored" parses as "says nothing" | fixed | "says that nothing at all is stored" |
| F87 | NIT | fresh-eyes | 4 | Email rewrite wording left out mail links | fixed | "in your pages, mail links included" |
| F88 | NIT | GLM | 4 | "HTTP/2 200" hardcoded | fixed | "a 200 status line (`HTTP/2 200`, or `HTTP/1.1 200 OK` on an older curl)" |
| F89 | NIT | GLM | 4 | A 3xx on the live domain was not interpreted | fixed | "A 3xx status line means something else is redirecting your live domain" |
| F90 | NIT | GLM | 4 | Section 1 says ask the assistant; section 6 said stop if anything would be overwritten | fixed | CL section 6: read what is there and send it back with the change; list variables before and after and put back any that went missing |
| F91 | RISK | Codex | wording pass | F90's fix said the assistant should "put back any that went missing"; a listed variable may not carry what restores it (a secret's value), so the restore step rested on nothing checked | fixed `7a665a0`; confirmation: see the round table | CL section 6: "stop and tell you if any is missing, because it may not be able to put them back"; and "or it can't be sure the project's other variables are kept, do that item by hand from sections 1 to 4" |
| F92 | RISK | kimi-k3 | full read | the token table mapped "AI crawler policies" to Bot Management Edit with no cited API call | fixed `f48fb2a`; the claim itself held when read from the live page | the row links Cloudflare's Bot Management update page; its request body lists `fight_mode`, `enable_js`, `ai_search`, `ai_user`, `ai_training`, `ai_bots_protection`, `is_robots_txt_managed`, and it asks for "Bot Management Write" (the permissions page names it "Bot Management Edit") |
| F93 | NIT | kimi-k3 | full read | section 5 said "the first request a new domain sees is the one Cloudflare's edge keeps" with no source, next to cache-busters | fixed `f48fb2a` | the sentence now says the live domain serves the previous deployment or an error earlier, and names the kit's own rule (`PUBLISHING.md`, "Never request a page on the live domain before its build is Active") for a 404 cached at the edge |
| F94 | NIT | kimi-k3 | full read | the robots.txt check said the file "ends with your sitemap line"; the starter ships `Sitemap: https://example.com/sitemap-index.xml` | fixed `f48fb2a` | "a `Sitemap:` line that names your own domain, not the starter's `example.com`" |
| F95 | RISK | Codex | confirmation | F92's link landed, but the fields and the Bot Management Edit permission were "unsupported by primary evidence checked here" (the seat has no network) | answered by evidence, no text change; locally_verified | the live pages were read and recorded in the test records below (command, output, exit status): the update page lists `fight_mode`, `ai_search`, `ai_user`, `ai_training`, `ai_bots_protection`, `is_robots_txt_managed` and "Bot Management Write"; the permissions page lists "Bot Management Edit" and "Bot Management Write" as the same grant |

Waivers: **F62 only** (the template half of F39: the starter's German privacy page wording against the checklist's HSTS advice). The owner's words, in the session, 2026-10-12: "yes, waive the template half". It is moot now: the base branch (#264) rewrote those privacy sentences, and the BUGLOG row that tracked them was dropped in `7a665a0`. Nothing else is waived. Deferrals: none. Refuted with evidence: F16, F68, F81.

Follow-ups: the `<project>.pages.dev` alias still carries `nel` and `report-to` and no way to remove them was found (a BUGLOG row, 2026-10-12, says what to try); `SCS` still shows the older AI-crawler dashboard names (an existing BUGLOG row, 2026-10-11); `CFD` step 2's heading "Redeploy with a new commit" is looser than its body (outside this change, not edited).

Notes:
- Seats: melious ran GLM 5.3 only and kimi ran on ollama only (the owner's rule of 2026-10-12). Round 2's melious seat hit its 300 s limit and ollama-cloud GLM stood in; later rounds used `MELIOUS_API_TIMEOUT=600` and melious counted. Fresh-eyes was a claude-sonnet-5-5 sub-agent in rounds 1 to 4.
- Wording pass and final full read: F91 (wording pass) and F92 to F94 (full read) were fixed locally; the confirmation verified F91, F93 and F94 and could not read Cloudflare's page for F92, so F95 is answered by the recorded read of that page below. Its fixes are locally_verified, and the confirmation is the only outside pass over them.
- Where the seats' UNVERIFIABLE groups stand. Dashboard paths and labels: the document says in its third paragraph that none was re-checked in a dashboard. Pages runtime and edge behaviour (variable timing, the Fail open day, the cached first request): from the kit's own notes, now named in the text. NEL: the zone setting read "off" from 08:18Z while the header was served until 08:51Z, and the Transform Rule removed it within seconds, on five zones on 2026-10-12. Token table: read from Cloudflare's API pages (record below); only the Transform Rules and NEL calls were run on live zones, and the text says so.
- Data check: no credentials, zone or account identifiers or private names in the diff or the reviewers' output (`scripts/check_clean.sh` and a grep over `git diff origin/main...HEAD` for the identifiers named in the session). Destinations: Codex, melious.ai and ollama-cloud, the repository's review convention.
- Prompt-injection flags: the diff wrapper's scope orders were filed as injection and treated as data by Codex in the wording pass, and the confirmation brief's scope sentences were too; nothing in the diff addressed the reviewer.

## Test records

Every run below is complete: command, whole output, exit status.

### Section 5's four grep patterns, on synthetic header text

Command: `bash pattern-tests.sh` (feeds each pattern the header text shown). Exit status 0.

```
bash 3.2.57(1)-release, grep: grep (BSD grep, GNU compatible) 2.6.0-FreeBSD

## The old pattern (finding F34/F59): '^(HTTP|location):' needs a colon after HTTP
### OLD pattern on a 301
  pattern: ^(HTTP|location):
  input:
    | HTTP/1.1 301 Moved Permanently
    | location: https://yourdomain.com/
    | content-length: 0
  output:
    > location: https://yourdomain.com/
  grep exit status: 0

### OLD pattern on a clean 200
  pattern: ^(HTTP|location):
  input:
    | HTTP/2 200
    | content-type: text/html
    | cache-control: public
  output:
    (nothing printed)
  grep exit status: 1

## Section 5, command 1 (home page): '^(HTTP/|nel:|report-to:|strict-transport-security:|set-cookie:)'
### cmd 1, clean 200
  pattern: ^(HTTP/|nel:|report-to:|strict-transport-security:|set-cookie:)
  input:
    | HTTP/2 200
    | content-type: text/html
    | cache-control: public
  output:
    > HTTP/2 200
  grep exit status: 0

### cmd 1, NEL still on + HSTS + cookie
  pattern: ^(HTTP/|nel:|report-to:|strict-transport-security:|set-cookie:)
  input:
    | HTTP/2 200
    | nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
    | report-to: {"group":"cf-nel"}
    | strict-transport-security: max-age=15552000; includeSubDomains
    | set-cookie: __cf_bm=abc; path=/
  output:
    > HTTP/2 200
    > nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
    > report-to: {"group":"cf-nel"}
    > strict-transport-security: max-age=15552000; includeSubDomains
    > set-cookie: __cf_bm=abc; path=/
  grep exit status: 0

### cmd 1, a dead request (curl printed nothing)
  pattern: ^(HTTP/|nel:|report-to:|strict-transport-security:|set-cookie:)
  input:
  output:
    (nothing printed)
  grep exit status: 1

## Section 5, command 3 (http to https): '^(HTTP/|location:)'
### cmd 3, 301 to the domain
  pattern: ^(HTTP/|location:)
  input:
    | HTTP/1.1 301 Moved Permanently
    | location: https://yourdomain.com/
    | content-length: 0
  output:
    > HTTP/1.1 301 Moved Permanently
    > location: https://yourdomain.com/
  grep exit status: 0

### cmd 3, a 200 (no redirect)
  pattern: ^(HTTP/|location:)
  input:
    | HTTP/2 200
    | content-type: text/html
    | cache-control: public
  output:
    > HTTP/2 200
  grep exit status: 0

## Section 5, command 4 (the alias): '^(HTTP/|location:|nel:|report-to:)'
### cmd 4, alias answers 200 with NEL headers
  pattern: ^(HTTP/|location:|nel:|report-to:)
  input:
    | HTTP/2 200
    | nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
    | report-to: {"group":"cf-nel"}
    | strict-transport-security: max-age=15552000; includeSubDomains
    | set-cookie: __cf_bm=abc; path=/
  output:
    > HTTP/2 200
    > nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
    > report-to: {"group":"cf-nel"}
  grep exit status: 0

## The slash rule: does the location line start with https://yourdomain.com/ ?
  location: https://yourdomain.com/        with the slash: accepted
  location: https://yourdomain.com/        without it:     accepted
  location: https://yourdomain.com.au/     with the slash: rejected
  location: https://yourdomain.com.au/     without it:     accepted
  location: https://yourdomain.com         with the slash: rejected
  location: https://yourdomain.com         without it:     accepted
```

### Cloudflare's pages the token table rests on (F92, F95)

Command: `bash api-evidence.sh` (the script is below; it reads three public pages and counts or prints the names the table uses). Exit status 0.

```bash
#!/bin/bash
# Reads three of Cloudflare's own pages and prints what the checklist's token table rests on.
# Every fetch prints its URL, curl's exit status, the page size, then the counts and the context lines.
d=$(mktemp -d)
fetch() { curl -sL --max-time 90 "$1" -o "$2"; printf 'GET %s\n  curl exit status: %s, size: %s bytes\n' "$1" "$?" "$(wc -c < "$2" | tr -d ' ')"; }
text() { sed 's/<[^>]*>/ /g' "$1" | tr -s ' \n' ' '; }
printf 'read at %s\n\n' "$(date -u +%Y-%m-%dT%H:%MZ)"
echo "== 1. Bot Management update (the table row's link)"
fetch 'https://developers.cloudflare.com/api/resources/bot_management/methods/update/' "$d/bm.html"
for k in fight_mode enable_js ai_search ai_user ai_training ai_bots_protection is_robots_txt_managed 'Bot Management Write'; do
  printf '  %-24s %s occurrence(s)\n' "$k" "$(grep -o -- "$k" "$d/bm.html" | wc -l | tr -d ' ')"
done
echo "  request-body context for the three AI policy fields:"
text "$d/bm.html" | grep -o -E 'ai_(search|user|training) .{0,90}' | sort -u | head -3 | sed 's/^/    /'
echo "  required permission:"
text "$d/bm.html" | grep -o -E 'Bot Management Write' | sort -u | sed 's/^/    /'
echo
echo "== 2. API token permissions page"
fetch 'https://developers.cloudflare.com/fundamentals/api/reference/permissions/' "$d/perm.html"
text "$d/perm.html" | grep -o -E '(Bot Management|Zone Settings|Transform Rules) (Edit|Write) Grants write access to [A-Za-z ]+' | sort -u | sed 's/^/    /'
echo
echo "== 3. Zone settings edit page"
fetch 'https://developers.cloudflare.com/api/resources/zones/subresources/settings/methods/edit/' "$d/zs.html"
for k in always_use_https min_tls_version email_obfuscation 'Zone Settings Write'; do
  printf '  %-24s %s occurrence(s)\n' "$k" "$(grep -o -- "$k" "$d/zs.html" | wc -l | tr -d ' ')"
done
rm -rf "$d"
```

Output:

```
read at 2026-10-12T13:24Z

== 1. Bot Management update (the table row's link)
GET https://developers.cloudflare.com/api/resources/bot_management/methods/update/
  curl exit status: 0, size: 2633859 bytes
  fight_mode               578 occurrence(s)
  enable_js                27 occurrence(s)
  ai_search                146 occurrence(s)
  ai_user                  75 occurrence(s)
  ai_training              91 occurrence(s)
  ai_bots_protection       91 occurrence(s)
  is_robots_txt_managed    26 occurrence(s)
  Bot Management Write     1 occurrence(s)
  request-body context for the three AI policy fields:
    ai_search , 12 more } ai_bots_migration_opt_out : optional boolean Temporary migration flag tracking
    ai_search , 12 more } or SuperBotFightModeDefinitelyConfiguration { ai_bots_migration_opt_out , ai_b
    ai_search , 14 more } ai_bots_migration_opt_out : optional boolean Temporary migration flag tracking
  required permission:
    Bot Management Write

== 2. API token permissions page
GET https://developers.cloudflare.com/fundamentals/api/reference/permissions/
  curl exit status: 0, size: 207387 bytes
    Bot Management Edit Grants write access to Bot Management 
    Bot Management Write Grants write access to Bot Management 
    Transform Rules Edit Grants write access to Transform Rules 
    Transform Rules Write Grants write access to Transform Rules 
    Zone Settings Edit Grants write access to zone settings
    Zone Settings Write Grants write access to zone settings

== 3. Zone settings edit page
GET https://developers.cloudflare.com/api/resources/zones/subresources/settings/methods/edit/
  curl exit status: 0, size: 3321558 bytes
  always_use_https         1 occurrence(s)
  min_tls_version          23 occurrence(s)
  email_obfuscation        1 occurrence(s)
  Zone Settings Write      1 occurrence(s)
```

### `make check` on `f48fb2a`

Command: `make check`. Exit status 0; 1084 lines of output, ending:

```
all checks passed
LF checkout OK — every text file checks out LF even with core.autocrlf=true
make check  85.16s user 76.28s system 88% cpu 3:03.18 total
```
