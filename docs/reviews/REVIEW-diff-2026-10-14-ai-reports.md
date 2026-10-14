# DIFF gate — Google's and Bing's own AI reports (search-console-insights 1.8.0)

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
| 2 (verification) | 1c20966 | Codex (medium), GLM 5.3 | running | delta fef0408..1c20966 with the plan; `make test` 238 OK, `make check` exit 0 before the round |

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
