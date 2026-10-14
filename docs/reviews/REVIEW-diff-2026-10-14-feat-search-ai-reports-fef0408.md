# DIFF review — branch feat/search-ai-reports — Google's and Bing's own AI reports (search-console-insights 1.8.0)

Base `e038603` · depth: Normal (shipped runtime code; nothing in the High row) · verdict: CLEAN (seen pair: merge-base
01504df, head d0ae6a4; bridged to merge-base 3519d2d by an empty merge link; later commits touch this trail only) · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session
works in this worktree and created the branch by renaming the harness's branch for it); POST
AUTHORITY not yet held (no PR; one is opened only on the owner's word).

Branch `feat/search-ai-reports`, base `origin/main` e038603. Plan and scenarios:
`docs/reviews/SKILL-PLAN-ai-reports.md` (sent with the diff, since `docs/reviews/` is otherwise
left out of the artifact).

- **Depth: Normal.** Shipped runtime code (a new reader of owner-downloaded files, a new section
  on the owner's report page), but no auth, secrets, deletion, payments or deploy path: nothing
  in the High row. Pair: Codex + GLM 5.3 on melious (`SECOND_SEAT=melious`); fresh-eyes Sonnet in
  round 1.
- **Data check:** the artifact holds no keys, tokens or real site names (a real site name found in
  the plan before round 1 was removed and the unpushed commits folded into one, so it never left
  the machine). Owner's OK for this pair, given in reply to a message naming "Codex + GLM 5.3":
  "A2 and A7 are fine, run the review" (2026-10-14).
- **Severity bar, agreed before round 1:** a refusal of a hand-made input that no real export
  produces is a NIT; wrong numbers, a 0 shown as a finding, another site's file accepted, or a
  page that crashes are BUGs.
- **Claims sweep before round 1:** 17 sentences listed; 3 reworded (an "only", a "most", and "the
  language does not matter", which was tested with a German screen only), 14 checked against the
  sources and the six real files.
- **Test records before round 1** (head fef0408): `make test` 227 tests OK, exit 0;
  `make check` exit 0.

## Rounds

| Round | Head | Seats | BUG / RISK / NIT (after dedup) | Notes |
|---|---|---|---|---|
| 1 | fef0408 | Codex (318 s, 85k tokens), GLM 5.3 on melious (352 s, 36k), fresh-eyes Sonnet (232 s, 133k) | 5 / 4 / 8 | 12 UNVERIFIABLE questions asked, none confirmed as a finding (each points at evidence outside the repo, now recorded below) |
| 2 (verification) | 1c20966 | Codex medium (245 s, 59k tokens); GLM 5.3 on ollama (487 s) standing in for melious, whose reply was cut off at the 300 s limit while still arriving | 4 / 3 / 6 (F18–F28) | delta fef0408..1c20966 with the plan; `make test` 238 OK, `make check` exit 0 before the round. 2 BUGs were round-1 fixes left partial (F1, F2); round 3 owed. 6 UNVERIFIABLE questions, 1 checked and refuted (below) |
| 3 (verification) | 0118cf2 | Codex medium (321 s, 76k tokens), GLM 5.3 on melious (443 s, 34k) | 2 / 3 / 2 (F29–F35) | delta 1c20966..0118cf2; `make test` 244 OK, `make check` exit 0 before the round. F30 is a substantive BUG: round 4 earned (named here, as the budget asks past round 3) |
| 4 (verification) | 3090c40 | Codex medium (340 s, 67k tokens), GLM 5.3 on melious (328 s, 22k) | 1 / 1 / 2 (F36–F39) | delta 0118cf2..3090c40; `make test` 246 OK, `make check` exit 0 before the round. F36 is a substantive BUG: round 5 earned |
| 5 (verification) | 296d55c | Codex medium (207 s, 62k tokens), GLM 5.3 on melious (224 s, 22k) | 1 / 0 / 5 (F40–F45) | delta 3090c40..296d55c; `make test` 248 OK, `make check` exit 0 before the round. F40 refuted with the owner's agreement, so no substantive BUG: **the rounds end** (stop condition a2). The NIT fixes and F40's hardening are locally_verified, not externally re-verified until the re-gate below |
| re-gate (not a round) | 1136a76 | Codex medium only (105 s, 58k tokens): the seat with an unbroken chain (melious's broke in round 2) | 0 / 0 / 0 | delta 296d55c..1136a76: F40's hardening, F41, F43, F44 at full scope; the trail and the plan's status row for factual contradictions only. Clean; it confirmed the prose hunks hold no code. `make test` 249 OK, `make check` exit 0 before it |
| merge link (not a round) | ac928c7 | Codex medium only (216 s, 79k tokens) | 1 / 0 / 0 (F46, record only) | `origin/main` merged at 0b903d3 (49 commits; new merge-base 01504df); `merge_link.sh e038603 1136a76 01504df -- docs/WHAT-THE-SKILLS-RUN.md` lists no change in the change's own files, so the merge left them as reviewed. Its one file is that extra path, which is new on main, so the script prints the whole file as added (401 lines); this change's own edit to it is one sentence (`git diff 01504df..HEAD -- docs/WHAT-THE-SKILLS-RUN.md`), and that sentence plus the plan's status row were the artifact. Codex re-derived the path list with read-only git (the script's temp folder was denied in its sandbox), confirmed the skill's files are unchanged since 1136a76, and checked the sentence against `ai_reports.py` under a network audit: local files in, local JSON out. `make test` 249 OK, `make check` exit 0 on ac928c7. It read the scope note as "prompt injection"; it is the scope the skill prepends to a narrow pass |
| confirmation of F46 (not a round) | a71e7fd | Codex medium only | 2 / 0 / 0 (record) | F46's own contradiction gone, but the fix added two wrong record sentences ("check_clean.sh does not scan docs/reviews/"; "RISKs F16 …", F16 being a NIT); both corrected in d0ae6a4 |
| confirmation of that fix (the last allowed) | d0ae6a4 | Codex medium only | 0 / 0 / 0 | both corrections verified, no new contradiction; the private name list's count (0) is the author's measurement, which the seat could not reproduce without seeing the list |
| second merge link (not a round) | e842451 | none needed | — | the PR was behind `main` (PR 294 merged); `origin/main` merged at e842451, new merge-base 3519d2d. `merge_link.sh 01504df d0ae6a4 3519d2d -- docs/WHAT-THE-SKILLS-RUN.md` printed nothing (0 bytes): nothing of the change moved, so no seat had anything to read. `git diff d0ae6a4 HEAD` on the change's files is empty; `make test` 249 OK, `make check` exit 0 on e842451 |

## Findings

Ids are this gate's. Sources: C = Codex, G = GLM 5.3, S = fresh-eyes Sonnet.

| Id | Sev | Source | Where | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | C (G as RISK) | `search_report.py` `load_ai` | A saved record with the right state but a bad field (`pages` not a list, a one-item page row, a count as text, a numeric `checked`, `empty` with one date) crashed the whole page build | fixed, locally_verified | `_ai_record_ok` checks every field the section reads; `test_damaged_records_of_every_shape_read_as_nothing_added` (9 shapes; 7 errored on fef0408) |
| F2 | BUG | C, S (RISK + NIT) | `ai_reports.py` `parse_google`, `parse_bing` | Other reports were accepted: a Google zip with `Date,Revenue`, a zip of header-only `Name,Value`, a Bing CSV `Date,Clicks,Impressions` — saved as impressions, "empty" or citations | fixed, locally_verified | Invariant: a file is accepted only once it is known to be the right report. Google: a filter file naming a Web search type, one chart, chart and pages counting the same metric; Bing: the exact header (case and padding ignored). Tests: 4 Google variants (incl. Discover's filter), 3 Bing headers, one padded header accepted; all six real files still read |
| F3 | BUG | C, G (NIT) | `parse_google` | A pages file with an unreadable count was taken for the filter file, skipping the wrong-site check | fixed, locally_verified | URL files are recognised by their first column alone; any unreadable count refuses. Test: 3 variants (`broken`, `3.5`, empty) |
| F4 | BUG | C | `parse_google` | `2026-99-99` passed the date pattern, was saved, then crashed the page | fixed, locally_verified | Dates parsed at import, periods must not end before they start. Test: 3 variants (`2026-99-99`, `2026-02-30`, a reversed week) |
| F5 | BUG | C | `search_report.py` Google card | "the pages add up to more than the total" is false when one page holds every impression | fixed, locally_verified | now "can add up to more"; asserted in `test_one_day_reads_as_one_day` |
| F6 | RISK | C | plan, Facts and real-file section | Google's export format, zero semantics and API absence rest on claims a reviewer could not inspect | fixed (support recorded) | "Evidence" below: the probe commands and their output, the six real files' reconciled totals. The real exports hold the owner's site data and stay out of the repo; the test copies follow their shape |
| F7 | RISK | C | plan, Bing | Bing's columns, date order and API absence: same; "normalise other orderings" | fixed (support recorded) / refuted (ordering) | Evidence below. The one real export runs ascending, one row per day; any other order or a gap is refused with a message, never misread — failing loud is the chosen behaviour |
| F8 | RISK | S | `parse_google` host check | A Domain property covers subdomains, so a real export listing `blog.example.com` was refused | fixed, locally_verified | `same_site()`: the site, `www.` or any subdomain; look-alikes refused. Test: subdomain and `WWW.…:443` accepted; `evil-example.com`, `example.com.evil.de`, `notexample.com` refused |
| F9 | RISK | S | A2 wording, `ai_section` empty branch | Google writes "not available" as 0, so an all-zero download cannot prove "No impressions … yet" | fixed, locally_verified | owner chose the change (2026-10-14, "Change it"): "Your download shows no impressions in Google's AI answers (it covers …)"; A2 updated in the plan; tests assert the new text |
| F10 | NIT | G, S | `number()` | "3.5" read as 35 | fixed | whole counts only, thousands separators allowed; test: 3 accepted, 4 refused (`3.5`, `12,5`, `1,15`, `-1`) |
| F11 | NIT | G, S | `_span`, CLI | "between 14 July and 14 July", "on 1 of those 1 days", "1 citations", "1 pages" | fixed | one day reads "on 14 July 2026"; plurals; test `test_one_day_reads_as_one_day` |
| F12 | NIT | G | `read_bundle` | a folder unzipped twice was not searched; `__MACOSX` filtered in zips only | fixed | `rglob`, same filters both ways; test `test_a_folder_unzipped_twice_is_read` |
| F13 | NIT | G | `references/ai-reports.md` | "Never ask them to rename" contradicted the script's own rename advice | fixed | wording scoped to files that already carry the domain |
| F14 | NIT | S | `known_sites()` | a `.DS_Store` in the reports folder counted as a second site | fixed | folders only, dot names skipped; test `test_a_finder_file_in_the_reports_folder_is_not_a_second_site` |
| F15 | NIT | S | SKILL.md description | the new import phrases are not among the triggers; "my AI report" means two pages | refuted | the description is at 997 of 1,024 characters (`check_skill_budgets.sh` warns from 900); "show me my AI report" still opens the AI page as before; the SKILL.md pointer sends the agent to `references/ai-reports.md` before any import |
| F16 | NIT | S | `not-shown` | silently replaces a real download; a mistyped domain creates a folder that later counts as a site | fixed (the note) / waived (the typo folder: owner, 2026-10-14, "Leave it") | `test_not_shown_says_when_it_replaces_a_download` |
| F17 | NIT | S | plan status table | a stale "DIFF gate: not started" row beside "running" | fixed | row removed |
| F18 | BUG | C (round 2) | `_ai_record_ok`; `parse_google` | caused-by: F1 (partial). A saved page address that cannot be parsed (`https://[broken/`) still crashed the page; at import the same address raised a traceback, not a refusal | fixed, locally_verified | `host_of()` returns None for an unreadable address → refusal; saved records check each address with `urlsplit`. Test: 3 address variants at import, 1 saved |
| F19 | BUG | C; G (2 RISKs) | `parse_google` | caused-by: F2 (partial). Identity still too loose: any value starting "web" (G: `Webcam`) and any metric matching itself passed; a headers-only bundle beside the ordinary report's wide files was saved as empty | fixed, locally_verified, except one input refuted | Invariant restated: Google's report is known by its structure — `Web` as a whole word (`WEB` regex), every view under one metric header, and with data at least one other view adding up to the chart's total (true of all three real exports: 564, 1,155, 193); the headers-only case also needs no wide file. Test: 6 variants. **Refuted under the severity bar:** two header-only `Name,Value` files beside a Web filter are still saved as "empty" — no real export produces it and the page then says "Your download shows no impressions", no number. Named to the owner; **owner agreed with the refutation** (2026-10-14: "agree with the refutation, carry on") |
| F20 | RISK | C | plan Facts | F6/F7 re-raised: provider evidence not inspectable | stands as recorded (re-raise without new evidence) | The real exports hold the owner's site data and stay out of the repo. The settling observation GLM names — import the six real exports into a throwaway home and compare with an independent sum — is what was done, again at this round's head: unchanged totals |
| F21 | BUG | C (outside scope); G (NIT) | `parse_google` | a second pages file replaced the first before the host check | fixed, locally_verified | a second pages file is refused. In the 6-variant test |
| F22 | BUG | C (outside scope) | `references/ai-reports.md` | "The pages add up to more" kept F5's categorical claim | fixed | "can add up to more" |
| F23 | RISK | C (outside scope) | `ai_reports.py` CLI | the import line still said "no impressions … yet" after F9 | fixed | "your download shows no impressions"; test |
| F24 | NIT | G | F14's test | asserted only the exit code | refuted, and strengthened | the test failed on fef0408 (round-1 record), so it did discriminate; it now also asserts `known_sites() == {site}` |
| F25 | NIT | G | `parse_google` docstring | "in any screen language" overstated: the "Web" word is read | fixed | docstring says which word is read and that a translated one is refused, never misread |
| F26 | NIT | G | `_ai_record_ok` | a hand-edited "data" record with 0 would print "shown 0 times" | fixed | data needs total / citations ≥ 1; test |
| F27 | NIT | G | `read_bundle` | `rglob("*.csv")` skipped `Seiten.CSV` | fixed | suffix compared in lower case; test |
| F28 | NIT | G | `COUNT` | "1,155.000" read as 1155000 | fixed | one separator kind per count; test, 3 variants |

Round 2 UNVERIFIABLE checked: G asked whether a one-column header over two-column rows raises IndexError at `head[1]`. Refuted: `len(head) != 2` skips the file before `head[1]` is read.

| F29 | BUG | C (round 3) | `parse_google` | caused-by: F19 (partial). A hand-built zip copying every structural rule (a Web filter, a dated `Revenue` chart, a `Country,Revenue` view adding up to it) is still saved as AI impressions | refuted under the severity bar, **owner agreed** (2026-10-14, "Refute under the bar") | Third link of the F2 chain. Structure cannot tell a careful fake from the real file without reading the metric word; the alternative offered — allow-list "Impressionen"/"Impressions" and refuse other screen languages — was declined. No real export is known to produce this input; the realistic wrong files (the ordinary Performance export, Discover's report, another site's, Excel) are each refused by a test |
| F30 | BUG | C | `_ai_record_ok` | caused-by: F18 (partial). A saved page address or search type holding a lone surrogate (`\ud800`) passed the check, then the page's UTF-8 write failed | fixed, locally_verified | `text()` requires a string that encodes as UTF-8, used for addresses and the search type. Test: 2 variants, the page is written; both failed on 0118cf2 |
| F31 | RISK | C | `parse_google` total check | "another view adds up to the chart's total" rests on 3 of 3 real exports; if Google ships one where it doesn't, a real download is refused | waived, **owner** (2026-10-14, "Accept (waive the RISK)") | the refusal fails loud and now names every view's total, so the first such case shows what differed; test asserts the message |
| F32 | RISK | C | plan, Bing | F7/F20 re-raised without new evidence | stands as recorded | — |
| F33 | RISK | G | `_ai_record_ok` `address()` | `urlsplit(v) is not None` cannot be false; rejection relied on the caller catching `ValueError` | fixed | `address()` catches `ValueError` itself (the caller, `load_ai`, also catches `ValueError`, `TypeError`, `OSError`) |
| F34 | NIT | G | refusal text | "as it does in Google's own" read backwards | fixed | "…; in Google's own, one of them always does"; test |
| F35 | NIT | G | `_ai_record_ok` | a saved Bing record with citations but `days_cited: 0` would print "on 0 of N days" | fixed | `days_cited` ≥ 1 in state data; test (failed on 0118cf2) |

Round 3 questions checked and refuted by reading: the zip branch of `read_bundle` already compares `.csv` in lower case (G); `span_ok`'s `fromisoformat` raising is caught by `load_ai`'s `except (ValueError, TypeError, OSError)` (G, follow-up); a non-UTF-8 CSV is refused, not a traceback: `read_bundle` and the Bing branch of `do_import` both catch `UnicodeDecodeError` (G, follow-up).

| F36 | BUG | C (round 4) | `load_ai` | caused-by: F30 (partial). A saved record nested 10,000 levels deep raised `RecursionError`, which no check caught: the page was not written | fixed, locally_verified | Fourth link of the F1 chain, so closed as a class, not a shape: `ai_part()` puts the AI section behind one boundary — nothing in the saved AI files can stop the page being written; a failure past the checks is said on the page and in the log (fail loud). `load_ai` also catches `RecursionError`. Tests: the deep record and a forced failure; both fail on 3090c40 |
| F37 | RISK | G | round-3 test, "citations without a cited day" | the subtest could not fail if the guard regressed | refuted, and strengthened | the "nothing added" text appears only when no record was accepted, and the subtest failed on 0118cf2 (round-3 record); it now also asserts no "of those" line |
| F38 | NIT | G | `_ai_record_ok` | "on 5 of 3 days" from a hand-edited record | fixed | `days_cited` ≤ `days`; test |
| F39 | NIT | G | test file | three blank lines before a class | fixed | — |

Round 4 questions checked and refuted by reading: `others` is a list built by `append`, so the refusal's order is the files' order and stable (G).

| F40 | BUG | C (round 5) | `ai_part` | if writing the error to the log itself fails (stderr raising `OSError`), the page is not written | refuted, **owner agreed** (2026-10-14, "Refute, and harden it locally") — and hardened locally | a broken log stream is an environment failure outside the AI-file boundary F36 promises; the older log lines in `build()` fail the same way. Hardened anyway: the log line is best-effort (`try`/`except`). Test `test_a_broken_log_stream_does_not_cost_the_page` fails on 296d55c. locally_verified, not externally re-verified |
| F41 | NIT | C, G | test file | three blank lines before `RoundFourFindings` (F39 again) | fixed | — |
| F42 | NIT | G | `_ai_record_ok` | `days_cited` ≤ `days` compares raw values; digit strings would compare as text | refuted | `count()` accepts only `int` (not `bool`), so a string fails before the comparison: `isinstance(v, int) and not isinstance(v, bool) and v >= least` |
| F43 | NIT | G | `render` | its default path called `ai_section({})` outside the boundary | fixed | the default is `ai_part(site, today)`; one path. locally_verified |
| F44 | NIT | G | `ai_part` | the fallback repeated the section heading by hand | fixed | one constant, `AI_HEADING`. locally_verified |
| F45 | — | G | questions | `sys` imported? other callers of `render`, `load_ai`, `ai_section`? | refuted by reading | `import sys` at the top; `grep` finds no caller outside `build()` and `ai_part()` |

Fix chains: F1 → F18 → F30 → F36 (four links; closed by the boundary in F36) and F2 → F19 → F29 (three links; the owner was told and chose, see F29). Round 2's new tests (7, with 16 subtests) all fail on 1c20966 and pass now.
| F46 | BUG (record) | C (merge link) | plan status row; the merge link's scope note | "merge … and its link check: see the trail" pointed at no entry, and the note did not tell the script's whole-file output from the one-sentence edit | fixed | the merge-link row above records both, with the commands; not substantive (the review record, not what the product does), so it takes the wording pass's one confirmation, not a round |

## Evidence (for F6, F7 and the plan's own claims)

**Google API probe, 2026-10-14, read-only, owner's OK, through the skill's own sign-in**
(`search_report.make_service()` and `pick_property()`):

```
property: sc-domain:<owner's site D>            # no export downloaded; no rows at all: inconclusive
web -> []   discover -> []   news -> []          # dimensions ["searchAppearance"], last 90 days
type aiOverview rejected: <HttpError 400 … "Inv…
type aiMode rejected: <HttpError 400 … "Inv…
property: sc-domain:<owner's site B>            # site B below: 1,155 AI impressions in its export
web -> []   discover -> []
web total impressions, 90 days: [8077]
```

**Bing method list:** https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi
(updated 2023-11-14): 60-odd methods, none about AI, citations or grounding queries.

**The six real exports, reconciled** (sums computed by a separate script, then by the import):

| Site | Chart | Countries | Devices | Pages | Import total | Bing citations (import) |
|---|---|---|---|---|---|---|
| A | 564 (weekly rows) | 564 | 564 | 621 | 564 | 39 |
| B | 1,155 (daily) | 1,155 | 1,155 | 1,217 | 1,155 | 10 |
| C | 193 (daily) | 193 | 193 | 204 | 193 | 27 |

**Nine deliberate breakages (head before round 1), each caught by a failing test:** total from
pages; zeros saved as data (Google); zeros saved as data (Bing); no file-name check; no page-host
check; stale at 35 days; `www.` not the same site; out-of-order dates accepted; 0-impression
pages listed. Round 1's 11 new tests were also run against fef0408: all 11 fail there (22
failures, 7 errors across their subtests) and pass now.

**Test records after the round-1 fixes** (head 1c20966): `make test` 238 tests OK, exit 0; `make check` exit 0.

## Verdict, waivers, follow-ups

**Verdict:** CLEAN: F46's fix confirmed on d0ae6a4 (rows above). Every BUG is fixed or refuted: the
refutations F19 (part), F29 and F40 have the owner's agreement, quoted in their rows. F16's typo-folder
NIT and F31's RISK are waived by the owner, quoted in their rows; F20 and F32 stand as
recorded (re-raises without new evidence, the real exports being the owner's site data).

**Seen pair for the stamp:** base = `git merge-base origin/main HEAD`, head = d0ae6a4, the head the
last confirmation saw. Codex is the seat with an unbroken chain (rounds 1–5, the re-gate, the merge
link, the confirmation); melious's chain broke in round 2 (cut off; GLM 5.3 on ollama stood in),
and fresh-eyes' ended at round 1 by design.

**Follow-ups:** none from the rounds. Outside this change: a real site name sat in this plan
before round 1 and was caught by hand. `scripts/check_clean.sh` scans `docs/` (its `SCAN_BASE`),
but its private, gitignored name list does not hold that name; adding it is the owner's call.

**Notes:** Rounds 4 and 5 ran past round 3, earned by F30 and F36. The F1 chain (F1 → F18 → F30 →
F36) was closed by a boundary, not one more shape; the F2 chain (F2 → F19 → F29) ended on the
owner's decision. The six real exports were re-imported after rounds 1, 2 and 3; totals unchanged.
