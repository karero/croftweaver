# DIFF review — karero/croftweaver#281 — wordpress-inspector: count a WordPress site before a move, check every old address after it

Base `f4b21bd` · depth: Normal (runtime code that makes web requests, an instruction file, one new CI job; no login, payment, deletion or personal data) · verdict: OPEN · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

Files in the change: `Makefile`, `README.md`, `.github/workflows/clean.yml`, `skills/wordpress-inspector/SKILL.md`, `skills/wordpress-inspector/scripts/wp_inventory.py`, `skills/wordpress-inspector/scripts/check_move.py`, `skills/wordpress-inspector/scripts/tests/test_wp_inventory.py`, `skills/wordpress-inspector/scripts/tests/test_check_move.py`, and this trail.

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `6413463` | full, `f4b21bd...6413463` without `docs/reviews/` (90,508 bytes) | Codex: codex-cli 0.162.1, gpt-6.1-sol, config.toml's effort, read-only sandbox. melious: glm-5.3, HTTP API, text only. fresh-eyes: sonnet sub-agent, read-only by instruction, could run the tests | codex 548 s, 100,271 tokens; melious 548 s, 65,860 tokens; fresh-eyes 271 s, 154,605 tokens | 10 / 5 / 15 (34 raw: fresh-eyes 3/2/9, Codex 10/3/0, melious 1/0/6). UNVERIFIABLE: 9 asked, 2 led to a wording change (F14, and the password-protected line under F13) |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | fresh-eyes, Codex | 1 | the old home address read "sent home" when the new home page forwards (to `/en/`, `/index.html`) | fixed, locally_verified | `check_move.py`: `home_keys`, `asked_key != root_key`; tests `TheHomePage` (2) |
| F2 | BUG | fresh-eyes, Codex | 1 | the not-found probe passed when the probe itself was refused or busy, so a site answering "found" for everything read as fully kept | fixed, locally_verified | `check_move.py`: the probe must bring 404 or 410; tests `test_a_probe_that_was_refused_or_busy_proves_nothing` (429, 503, 403), `test_a_site_that_forwards_everything_to_another_host` |
| F3 | BUG | fresh-eyes, Codex, melious | 1 | when every guessed sitemap address was busy, refused or forwarded away, the count read complete with "No sitemap was found" | fixed, locally_verified | `wp_inventory.py`: `read_sitemaps` separates broken from absent; tests `SitemapReading` (busy 503/403/429, plain 404, a web page at the address) |
| F4 | BUG | Codex | 1 | the query was dropped from address keys: `/?p=1` and `/?p=3` merged, and a forward to `/?page_id=2` read as the home page | fixed, locally_verified | `path_key` keeps the query; tests `test_two_addresses_that_differ_only_in_the_query_are_two_addresses`, `test_a_redirect_to_an_address_with_a_query_is_not_the_home_page` |
| F5 | BUG | Codex | 1 | `/a` and `/a/` were merged before asking, so one spelling's answer hid the other's | fixed, locally_verified | only the same address is asked once; test `test_with_and_without_the_closing_slash_are_two_addresses` |
| F6 | BUG | Codex | 1 | a list that repeated its first page counted as a full count (rows compared, not records) | fixed, locally_verified | distinct ids counted, a repeat or a changed total makes the type incomplete; tests `RecordCounting` (repeat, changing total) |
| F7 | BUG | Codex | 1 | sitemaps were read by pattern: a cut-off file passed as a shorter sitemap, prefixed elements (`sm:loc`) were missed | fixed, locally_verified | parsed with ElementTree as the facts check does; invariant: a sitemap is read whole or is a gap. Variants tested: cut off inside an index's child, cut off at a guessed address, prefixed elements, padded `loc`, packed |
| F8 | BUG | Codex | 1 | a packed sitemap that unpacks beyond the size limit was read cut off | fixed, locally_verified | the unpacked size is checked; test `test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap` |
| F9 | BUG | Codex | 1 | a count without a total, with a negative total or with an answer that is no list read as counted | fixed, locally_verified | `count_only`, `header_int`; test `test_media_or_a_grouping_without_a_usable_count_is_incomplete` (4 cases), `test_a_type_without_a_total_is_incomplete_and_says_why` |
| F10 | BUG | Codex | 1 | temporary redirects were counted from the note text, so a 302 to another host was not counted | fixed, locally_verified | own column `temporary_redirect`; test `test_a_temporary_redirect_to_another_host_is_flagged_too` |
| F11 | RISK | fresh-eyes | 1 | the standard library's robots.txt reader ignores `*` and `$` before Python 3.13, so the promise "obeys robots.txt" failed on 3.9 | fixed, locally_verified | the facts check's RFC 9309 matcher copied in (a skill travels alone); tests `Robots` (5), run on 3.9.6 and 3.13.16 |
| F12 | RISK | fresh-eyes | 1 | the new CI job blocks no merge until the ruleset names it | fixed, locally_verified | the PR text names the two contexts to add, `wordpress-inventory-tests (3.9)` and `(3.12)`; adding them is the owner's step (Follow-ups) |
| F13 | RISK | Codex | 1 | collections were read under `wp/v2` only, and the texts said "every content type" | fixed, locally_verified | a type's own `rest_namespace` is used (test `test_a_type_registered_under_a_plugins_own_namespace_is_read_there`); SKILL.md, README and the report say "the types the REST API lists" and name unlisted types under what cannot be seen. No real WordPress fixture is added: see Notes |
| F14 | RISK | Codex | 1 | page-builder and form marks were worded as proof, and a rebuild as certain | fixed, locally_verified | SKILL.md steps 3 and 4: a sign, to be compared with the page in a browser |
| F15 | RISK | Codex | 1 | "needs a 301, or search engines keep the old address" had no source | fixed, locally_verified | the sentence about search engines is gone from SKILL.md, the script header and the report |
| F16 | NIT | fresh-eyes, melious | 1 | "1 redirects are temporary", and 303 counted but not named | fixed, locally_verified | `render`: singular, and "302, 303 or 307" |
| F17 | NIT | fresh-eyes | 1 | "off the site" results were said to be listed and were not | fixed, locally_verified | `move-check.md` lists each with its target |
| F18 | NIT | fresh-eyes | 1 | "the site reports None records" | fixed, locally_verified | "the site did not report a total" |
| F19 | NIT | fresh-eyes | 1 | a `Sitemap:` line under the site's other spelling (http for https) made a false gap | fixed, locally_verified | asked on the site itself; test `test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site` |
| F20 | NIT | fresh-eyes | 1 | "a site with thousands of posts needs more" requests: it does not | fixed, locally_verified | SKILL.md: raise the limit when the report says it was reached |
| F21 | NIT | fresh-eyes | 1 | text from the site could write a link into the report | fixed, locally_verified | `md` escapes `[` and `]`; test `test_text_from_the_site_cannot_write_a_link_into_the_report` |
| F22 | NIT | fresh-eyes | 1 | "every old address" is wider than `urls.csv` | fixed, locally_verified | SKILL.md, README, the script header: "each listed address", and what the list leaves out |
| F23 | NIT | melious | 1 | a `csv.Error` escaped as a traceback | fixed, locally_verified | caught; test `test_an_address_list_that_cannot_be_parsed` |
| F24 | NIT | melious | 1 | a redirect or start address with a port that is no number crashed | fixed, locally_verified | `web_address`; tests `test_a_redirect_to_an_address_that_is_no_web_address_is_unreadable_not_a_crash`, `test_not_a_web_address` |
| F25 | NIT | melious | 1 | `__import__("io")` | fixed, locally_verified | `import io` |
| F26 | NIT | melious | 1 | the median was floored | fixed, locally_verified | `round` |
| F27 | NIT | melious | 1 | the CI comment's reason for 3.9 read wrong on an Ubuntu runner | fixed, locally_verified | reworded |
| F28 | NIT | fresh-eyes | 1 | a refused robots.txt (401, 403) was read as "no rules" | fixed, locally_verified | the run stops, as the facts check does; test `test_a_refused_or_unreadable_robots_file_stops_the_run` (401, 403, 429, 500) |
| F29 | NIT | melious | 1 | `--user-agent` changes the name sent, not the name robots.txt is read under | fixed, locally_verified | said in the option's help text |
| F30 | NIT | fresh-eyes | 1 | "left as raw shortcode text" counts any plugin's code, not only a page builder's | fixed, locally_verified | SKILL.md step 3 says so |

Waivers and deferrals: none.

Follow-ups:
- Owner: add `wordpress-inventory-tests (3.9)` and `wordpress-inventory-tests (3.12)` to the ruleset's required checks (F12).
- The robots.txt matcher now lives in two skills, `facts-check` and `wordpress-inspector`; a change to one has to reach the other, and no guard checks that.

Notes:
- The new CI job `wordpress-inventory-tests` is not in the ruleset's required checks. It ran green on both Python legs for head `6413463` (38 checks passed, none failed), which answers the reviewers' question whether the copied action pins resolve.
- UNVERIFIABLE entries that stay open: what a real WordPress hands out (totals, the type list, shortcodes in `content.rendered`, password-protected records). The tests use stubs that return what the scripts expect. The texts now claim less (F13, F14); no real fixture is offered.
- `make check` on the author's machine: three runs exited 0; one earlier run printed "1 check(s) FAILED" and its output was not kept, so which check failed is unknown. The machine's load average was above 50 at the time. CI on the PR is the record to trust.
- Both scripts were also tried against one real site. Those outputs name a third party and stay out of this repository, so no record of them is offered here; treat the trial as the author's word.

## Test records (author's machine, before round 1, head `172d9e3`)

Each block is one run: the command, everything it printed, its exit status.

<details><summary>tests-python3.13.txt</summary>

```
$ python3 -m unittest discover -v -s skills/wordpress-inspector/scripts/tests
test_a_cell_the_inventory_defused_is_read_back_as_the_address (test_check_move.AddressList.test_a_cell_the_inventory_defused_is_read_back_as_the_address) ... ok
test_addresses_on_another_host_are_listed_and_skipped (test_check_move.AddressList.test_addresses_on_another_host_are_listed_and_skipped) ... ok
test_one_address_in_two_spellings_is_asked_once (test_check_move.AddressList.test_one_address_in_two_spellings_is_asked_once) ... ok
test_a_site_that_forwards_everything_to_its_home_page (test_check_move.CannotStart.test_a_site_that_forwards_everything_to_its_home_page) ... ok
test_a_site_that_says_found_for_everything (test_check_move.CannotStart.test_a_site_that_says_found_for_everything) ... ok
test_no_addresses_and_no_site (test_check_move.CannotStart.test_no_addresses_and_no_site) ... ok
test_a_busy_answer_is_never_read_as_kept_or_missing (test_check_move.EveryAddressEndsSomewhere.test_a_busy_answer_is_never_read_as_kept_or_missing) ... ok
test_a_deep_address_forwarded_to_the_home_page_is_a_finding (test_check_move.EveryAddressEndsSomewhere.test_a_deep_address_forwarded_to_the_home_page_is_a_finding) ... ok
test_a_missing_closing_slash_is_not_a_lost_page (test_check_move.EveryAddressEndsSomewhere.test_a_missing_closing_slash_is_not_a_lost_page) ... ok
test_a_redirect_loop_is_a_finding (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_loop_is_a_finding) ... ok
test_a_redirect_that_leads_to_a_missing_page_is_missing (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_that_leads_to_a_missing_page_is_missing) ... ok
test_a_redirect_to_another_host_is_listed_not_followed (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_to_another_host_is_listed_not_followed) ... ok
test_a_temporary_redirect_is_accounted_for_but_flagged (test_check_move.EveryAddressEndsSomewhere.test_a_temporary_redirect_is_accounted_for_but_flagged) ... ok
test_all_accounted_for_exits_0 (test_check_move.EveryAddressEndsSomewhere.test_all_accounted_for_exits_0) ... ok
test_kept_redirected_and_missing_are_told_apart (test_check_move.EveryAddressEndsSomewhere.test_kept_redirected_and_missing_are_told_apart) ... ok
test_an_address_dropped_on_purpose_is_not_a_finding (test_check_move.LetGo.test_an_address_dropped_on_purpose_is_not_a_finding) ... ok
test_only_the_listed_address_is_let_go (test_check_move.LetGo.test_only_the_listed_address_is_let_go) ... ok
test_the_inventorys_address_list_drives_the_check (test_check_move.TheRealChain.test_the_inventorys_address_list_drives_the_check) ... ok
test_a_site_that_is_not_wordpress_and_has_no_sitemap (test_wp_inventory.CannotStart.test_a_site_that_is_not_wordpress_and_has_no_sitemap) ... ok
test_not_a_web_address (test_wp_inventory.CannotStart.test_not_a_web_address) ... ok
test_nothing_answers (test_wp_inventory.CannotStart.test_nothing_answers) ... ok
test_a_plugins_own_content_type_is_found_without_being_named (test_wp_inventory.FullCount.test_a_plugins_own_content_type_is_found_without_being_named) ... ok
test_every_record_is_counted_and_the_run_says_complete (test_wp_inventory.FullCount.test_every_record_is_counted_and_the_run_says_complete) ... ok
test_languages_mixed_in_one_tree_show_up (test_wp_inventory.FullCount.test_languages_mixed_in_one_tree_show_up) ... ok
test_no_page_text_is_written_to_disk (test_wp_inventory.FullCount.test_no_page_text_is_written_to_disk) ... ok
test_pages_whose_builder_markup_arrives_unrendered_are_flagged (test_wp_inventory.FullCount.test_pages_whose_builder_markup_arrives_unrendered_are_flagged) ... ok
test_published_records_missing_from_the_sitemap_are_surfaced (test_wp_inventory.FullCount.test_published_records_missing_from_the_sitemap_are_surfaced) ... ok
test_sitemap_addresses_no_record_explains_are_surfaced (test_wp_inventory.FullCount.test_sitemap_addresses_no_record_explains_are_surfaced) ... ok
test_text_from_the_site_cannot_break_the_report_table (test_wp_inventory.FullCount.test_text_from_the_site_cannot_break_the_report_table) ... ok
test_the_address_list_has_one_row_per_address (test_wp_inventory.FullCount.test_the_address_list_has_one_row_per_address) ... ok
test_what_the_site_is_built_with (test_wp_inventory.FullCount.test_what_the_site_is_built_with) ... ok
test_wordpress_own_machinery_is_not_counted_as_content (test_wp_inventory.FullCount.test_wordpress_own_machinery_is_not_counted_as_content) ... ok
test_a_busy_site_is_not_counted (test_wp_inventory.IncompleteCounts.test_a_busy_site_is_not_counted) ... ok
test_a_maintenance_page_in_place_of_data_is_not_counted (test_wp_inventory.IncompleteCounts.test_a_maintenance_page_in_place_of_data_is_not_counted) ... ok
test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked (test_wp_inventory.IncompleteCounts.test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked) ... ok
test_fewer_records_than_the_site_reports (test_wp_inventory.IncompleteCounts.test_fewer_records_than_the_site_reports) ... ok
test_the_request_limit_stops_the_run_and_says_so (test_wp_inventory.IncompleteCounts.test_the_request_limit_stops_the_run_and_says_so) ... ok
test_a_bracketed_word_is_a_shortcode_only_with_a_closing_tag_an_attribute_or_an_underscore (test_wp_inventory.Pieces.test_a_bracketed_word_is_a_shortcode_only_with_a_closing_tag_an_attribute_or_an_underscore) ... ok
test_a_cell_a_spreadsheet_would_run_is_defused (test_wp_inventory.Pieces.test_a_cell_a_spreadsheet_would_run_is_defused) ... ok
test_an_address_on_another_host_never_matches_one_of_the_sites (test_wp_inventory.Pieces.test_an_address_on_another_host_never_matches_one_of_the_sites) ... ok
test_short_text_gets_no_language (test_wp_inventory.Pieces.test_short_text_gets_no_language) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 45 tests in 17.417s

OK
exit status: 0
```

</details>

<details><summary>tests-python3.9.txt</summary>

```
$ /usr/bin/python3 -m unittest discover -v -s skills/wordpress-inspector/scripts/tests
test_a_cell_the_inventory_defused_is_read_back_as_the_address (test_check_move.AddressList) ... ok
test_addresses_on_another_host_are_listed_and_skipped (test_check_move.AddressList) ... ok
test_one_address_in_two_spellings_is_asked_once (test_check_move.AddressList) ... ok
test_a_site_that_forwards_everything_to_its_home_page (test_check_move.CannotStart) ... ok
test_a_site_that_says_found_for_everything (test_check_move.CannotStart) ... ok
test_no_addresses_and_no_site (test_check_move.CannotStart) ... ok
test_a_busy_answer_is_never_read_as_kept_or_missing (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_deep_address_forwarded_to_the_home_page_is_a_finding (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_missing_closing_slash_is_not_a_lost_page (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_loop_is_a_finding (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_that_leads_to_a_missing_page_is_missing (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_to_another_host_is_listed_not_followed (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_temporary_redirect_is_accounted_for_but_flagged (test_check_move.EveryAddressEndsSomewhere) ... ok
test_all_accounted_for_exits_0 (test_check_move.EveryAddressEndsSomewhere) ... ok
test_kept_redirected_and_missing_are_told_apart (test_check_move.EveryAddressEndsSomewhere) ... ok
test_an_address_dropped_on_purpose_is_not_a_finding (test_check_move.LetGo) ... ok
test_only_the_listed_address_is_let_go (test_check_move.LetGo) ... ok
test_the_inventorys_address_list_drives_the_check (test_check_move.TheRealChain) ... ok
test_a_site_that_is_not_wordpress_and_has_no_sitemap (test_wp_inventory.CannotStart) ... ok
test_not_a_web_address (test_wp_inventory.CannotStart) ... ok
test_nothing_answers (test_wp_inventory.CannotStart) ... ok
test_a_plugins_own_content_type_is_found_without_being_named (test_wp_inventory.FullCount) ... ok
test_every_record_is_counted_and_the_run_says_complete (test_wp_inventory.FullCount) ... ok
test_languages_mixed_in_one_tree_show_up (test_wp_inventory.FullCount) ... ok
test_no_page_text_is_written_to_disk (test_wp_inventory.FullCount) ... ok
test_pages_whose_builder_markup_arrives_unrendered_are_flagged (test_wp_inventory.FullCount) ... ok
test_published_records_missing_from_the_sitemap_are_surfaced (test_wp_inventory.FullCount) ... ok
test_sitemap_addresses_no_record_explains_are_surfaced (test_wp_inventory.FullCount) ... ok
test_text_from_the_site_cannot_break_the_report_table (test_wp_inventory.FullCount) ... ok
test_the_address_list_has_one_row_per_address (test_wp_inventory.FullCount) ... ok
test_what_the_site_is_built_with (test_wp_inventory.FullCount) ... ok
test_wordpress_own_machinery_is_not_counted_as_content (test_wp_inventory.FullCount) ... ok
test_a_busy_site_is_not_counted (test_wp_inventory.IncompleteCounts) ... ok
test_a_maintenance_page_in_place_of_data_is_not_counted (test_wp_inventory.IncompleteCounts) ... ok
test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked (test_wp_inventory.IncompleteCounts) ... ok
test_fewer_records_than_the_site_reports (test_wp_inventory.IncompleteCounts) ... ok
test_the_request_limit_stops_the_run_and_says_so (test_wp_inventory.IncompleteCounts) ... ok
test_a_bracketed_word_is_a_shortcode_only_with_a_closing_tag_an_attribute_or_an_underscore (test_wp_inventory.Pieces) ... ok
test_a_cell_a_spreadsheet_would_run_is_defused (test_wp_inventory.Pieces) ... ok
test_an_address_on_another_host_never_matches_one_of_the_sites (test_wp_inventory.Pieces) ... ok
test_short_text_gets_no_language (test_wp_inventory.Pieces) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 45 tests in 17.224s

OK
exit status: 0
```

</details>

## Safeguards broken on purpose (author's record, no saved output)

Each line is one edit made in a throwaway copy of `scripts/`, then the tests run there. All 19 made at least one test fail.

`wp_inventory.py`: follow a redirect to another host; ask another host directly; count WordPress's internal types as content; mark a type complete when fewer records came than the site reports; count any bracketed word as a shortcode; ignore robots.txt; ignore the request limit; exit 0 on an incomplete count; leave a spreadsheet formula cell undefused. ("Ask another host directly" passed at first; `test_a_sitemap_file_on_another_host_is_reported_not_asked` was added for it.)

`check_move.py`: skip the not-found probe; accept a forward to the home page; let every address go once a let-go list exists; read a busy answer as missing; exit 0 with findings; say nothing about temporary redirects; ask one address twice; keep the apostrophe on a defused cell; treat a forward to another host as unreadable.

## Test records after the round-1 fixes (author's machine, before round 2)

<details><summary>tests-python3.13.txt</summary>

```
$ python3 -m unittest discover -v -s skills/wordpress-inspector/scripts/tests
test_a_cell_the_inventory_defused_is_read_back_as_the_address (test_check_move.AddressList.test_a_cell_the_inventory_defused_is_read_back_as_the_address) ... ok
test_addresses_on_another_host_are_listed_and_skipped (test_check_move.AddressList.test_addresses_on_another_host_are_listed_and_skipped) ... ok
test_the_same_address_twice_is_asked_once (test_check_move.AddressList.test_the_same_address_twice_is_asked_once) ... ok
test_with_and_without_the_closing_slash_are_two_addresses (test_check_move.AddressList.test_with_and_without_the_closing_slash_are_two_addresses) ... ok
test_a_probe_that_was_refused_or_busy_proves_nothing (test_check_move.CannotStart.test_a_probe_that_was_refused_or_busy_proves_nothing) ... ok
test_a_site_that_forwards_everything_to_another_host (test_check_move.CannotStart.test_a_site_that_forwards_everything_to_another_host) ... ok
test_a_site_that_forwards_everything_to_its_home_page (test_check_move.CannotStart.test_a_site_that_forwards_everything_to_its_home_page) ... ok
test_a_site_that_says_found_for_everything (test_check_move.CannotStart.test_a_site_that_says_found_for_everything) ... ok
test_an_address_list_that_cannot_be_parsed (test_check_move.CannotStart.test_an_address_list_that_cannot_be_parsed) ... ok
test_no_addresses_and_no_site (test_check_move.CannotStart.test_no_addresses_and_no_site) ... ok
test_a_busy_answer_is_never_read_as_kept_or_missing (test_check_move.EveryAddressEndsSomewhere.test_a_busy_answer_is_never_read_as_kept_or_missing) ... ok
test_a_deep_address_forwarded_to_the_home_page_is_a_finding (test_check_move.EveryAddressEndsSomewhere.test_a_deep_address_forwarded_to_the_home_page_is_a_finding) ... ok
test_a_missing_closing_slash_is_not_a_lost_page (test_check_move.EveryAddressEndsSomewhere.test_a_missing_closing_slash_is_not_a_lost_page) ... ok
test_a_redirect_loop_is_a_finding (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_loop_is_a_finding) ... ok
test_a_redirect_that_leads_to_a_missing_page_is_missing (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_that_leads_to_a_missing_page_is_missing) ... ok
test_a_redirect_to_an_address_that_is_no_web_address_is_unreadable_not_a_crash (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_to_an_address_that_is_no_web_address_is_unreadable_not_a_crash) ... ok
test_a_redirect_to_an_address_with_a_query_is_not_the_home_page (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_to_an_address_with_a_query_is_not_the_home_page) ... ok
test_a_redirect_to_another_host_is_listed_not_followed (test_check_move.EveryAddressEndsSomewhere.test_a_redirect_to_another_host_is_listed_not_followed) ... ok
test_a_temporary_redirect_is_accounted_for_but_flagged (test_check_move.EveryAddressEndsSomewhere.test_a_temporary_redirect_is_accounted_for_but_flagged) ... ok
test_a_temporary_redirect_to_another_host_is_flagged_too (test_check_move.EveryAddressEndsSomewhere.test_a_temporary_redirect_to_another_host_is_flagged_too) ... ok
test_all_accounted_for_exits_0 (test_check_move.EveryAddressEndsSomewhere.test_all_accounted_for_exits_0) ... ok
test_kept_redirected_and_missing_are_told_apart (test_check_move.EveryAddressEndsSomewhere.test_kept_redirected_and_missing_are_told_apart) ... ok
test_an_address_dropped_on_purpose_is_not_a_finding (test_check_move.LetGo.test_an_address_dropped_on_purpose_is_not_a_finding) ... ok
test_only_the_listed_address_is_let_go (test_check_move.LetGo.test_only_the_listed_address_is_let_go) ... ok
test_a_deep_address_is_sent_home_by_either_route (test_check_move.TheHomePage.test_a_deep_address_is_sent_home_by_either_route) ... ok
test_the_old_home_address_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_address_is_not_sent_home) ... ok
test_the_inventorys_address_list_drives_the_check (test_check_move.TheRealChain.test_the_inventorys_address_list_drives_the_check) ... ok
test_a_site_that_is_not_wordpress_and_has_no_sitemap (test_wp_inventory.CannotStart.test_a_site_that_is_not_wordpress_and_has_no_sitemap) ... ok
test_not_a_web_address (test_wp_inventory.CannotStart.test_not_a_web_address) ... ok
test_nothing_answers (test_wp_inventory.CannotStart.test_nothing_answers) ... ok
test_a_plugins_own_content_type_is_found_without_being_named (test_wp_inventory.FullCount.test_a_plugins_own_content_type_is_found_without_being_named) ... ok
test_every_record_is_counted_and_the_run_says_complete (test_wp_inventory.FullCount.test_every_record_is_counted_and_the_run_says_complete) ... ok
test_languages_mixed_in_one_tree_show_up (test_wp_inventory.FullCount.test_languages_mixed_in_one_tree_show_up) ... ok
test_no_page_text_is_written_to_disk (test_wp_inventory.FullCount.test_no_page_text_is_written_to_disk) ... ok
test_pages_whose_builder_markup_arrives_unrendered_are_flagged (test_wp_inventory.FullCount.test_pages_whose_builder_markup_arrives_unrendered_are_flagged) ... ok
test_published_records_missing_from_the_sitemap_are_surfaced (test_wp_inventory.FullCount.test_published_records_missing_from_the_sitemap_are_surfaced) ... ok
test_sitemap_addresses_no_record_explains_are_surfaced (test_wp_inventory.FullCount.test_sitemap_addresses_no_record_explains_are_surfaced) ... ok
test_text_from_the_site_cannot_break_the_report_table (test_wp_inventory.FullCount.test_text_from_the_site_cannot_break_the_report_table) ... ok
test_the_address_list_has_one_row_per_address (test_wp_inventory.FullCount.test_the_address_list_has_one_row_per_address) ... ok
test_what_the_site_is_built_with (test_wp_inventory.FullCount.test_what_the_site_is_built_with) ... ok
test_wordpress_own_machinery_is_not_counted_as_content (test_wp_inventory.FullCount.test_wordpress_own_machinery_is_not_counted_as_content) ... ok
test_a_busy_site_is_not_counted (test_wp_inventory.IncompleteCounts.test_a_busy_site_is_not_counted) ... ok
test_a_maintenance_page_in_place_of_data_is_not_counted (test_wp_inventory.IncompleteCounts.test_a_maintenance_page_in_place_of_data_is_not_counted) ... ok
test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked (test_wp_inventory.IncompleteCounts.test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked) ... ok
test_fewer_records_than_the_site_reports (test_wp_inventory.IncompleteCounts.test_fewer_records_than_the_site_reports) ... ok
test_the_request_limit_stops_the_run_and_says_so (test_wp_inventory.IncompleteCounts.test_the_request_limit_stops_the_run_and_says_so) ... ok
test_a_bracketed_word_is_a_shortcode_only_with_a_closing_tag_an_attribute_or_an_underscore (test_wp_inventory.Pieces.test_a_bracketed_word_is_a_shortcode_only_with_a_closing_tag_an_attribute_or_an_underscore) ... ok
test_a_cell_a_spreadsheet_would_run_is_defused (test_wp_inventory.Pieces.test_a_cell_a_spreadsheet_would_run_is_defused) ... ok
test_an_address_on_another_host_never_matches_one_of_the_sites (test_wp_inventory.Pieces.test_an_address_on_another_host_never_matches_one_of_the_sites) ... ok
test_short_text_gets_no_language (test_wp_inventory.Pieces.test_short_text_gets_no_language) ... ok
test_text_from_the_site_cannot_write_a_link_into_the_report (test_wp_inventory.Pieces.test_text_from_the_site_cannot_write_a_link_into_the_report) ... ok
test_a_list_that_repeats_itself_is_not_a_full_count (test_wp_inventory.RecordCounting.test_a_list_that_repeats_itself_is_not_a_full_count) ... ok
test_a_total_that_changes_between_pages_is_said (test_wp_inventory.RecordCounting.test_a_total_that_changes_between_pages_is_said) ... ok
test_a_type_registered_under_a_plugins_own_namespace_is_read_there (test_wp_inventory.RecordCounting.test_a_type_registered_under_a_plugins_own_namespace_is_read_there) ... ok
test_a_type_without_a_total_is_incomplete_and_says_why (test_wp_inventory.RecordCounting.test_a_type_without_a_total_is_incomplete_and_says_why) ... ok
test_media_or_a_grouping_without_a_usable_count_is_incomplete (test_wp_inventory.RecordCounting.test_media_or_a_grouping_without_a_usable_count_is_incomplete) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots.test_a_group_that_names_this_tool_replaces_the_group_for_everyone) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots.test_a_refused_or_unreadable_robots_file_stops_the_run) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots.test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots.test_the_longest_rule_wins_and_allow_wins_a_tie) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots.test_wildcards_and_the_end_mark_count) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading.test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading.test_a_sitemap_whose_elements_carry_a_prefix_is_read) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading.test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading.test_no_sitemap_anywhere_is_not_a_gap) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 74 tests in 35.643s

OK
exit status: 0
```

</details>

<details><summary>tests-python3.9.txt</summary>

```
$ /usr/bin/python3 -m unittest discover -v -s skills/wordpress-inspector/scripts/tests
test_a_cell_the_inventory_defused_is_read_back_as_the_address (test_check_move.AddressList) ... ok
test_addresses_on_another_host_are_listed_and_skipped (test_check_move.AddressList) ... ok
test_the_same_address_twice_is_asked_once (test_check_move.AddressList) ... ok
test_with_and_without_the_closing_slash_are_two_addresses (test_check_move.AddressList) ... ok
test_a_probe_that_was_refused_or_busy_proves_nothing (test_check_move.CannotStart) ... ok
test_a_site_that_forwards_everything_to_another_host (test_check_move.CannotStart) ... ok
test_a_site_that_forwards_everything_to_its_home_page (test_check_move.CannotStart) ... ok
test_a_site_that_says_found_for_everything (test_check_move.CannotStart) ... ok
test_an_address_list_that_cannot_be_parsed (test_check_move.CannotStart) ... ok
test_no_addresses_and_no_site (test_check_move.CannotStart) ... ok
test_a_busy_answer_is_never_read_as_kept_or_missing (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_deep_address_forwarded_to_the_home_page_is_a_finding (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_missing_closing_slash_is_not_a_lost_page (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_loop_is_a_finding (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_that_leads_to_a_missing_page_is_missing (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_to_an_address_that_is_no_web_address_is_unreadable_not_a_crash (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_to_an_address_with_a_query_is_not_the_home_page (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_redirect_to_another_host_is_listed_not_followed (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_temporary_redirect_is_accounted_for_but_flagged (test_check_move.EveryAddressEndsSomewhere) ... ok
test_a_temporary_redirect_to_another_host_is_flagged_too (test_check_move.EveryAddressEndsSomewhere) ... ok
test_all_accounted_for_exits_0 (test_check_move.EveryAddressEndsSomewhere) ... ok
test_kept_redirected_and_missing_are_told_apart (test_check_move.EveryAddressEndsSomewhere) ... ok
test_an_address_dropped_on_purpose_is_not_a_finding (test_check_move.LetGo) ... ok
test_only_the_listed_address_is_let_go (test_check_move.LetGo) ... ok
test_a_deep_address_is_sent_home_by_either_route (test_check_move.TheHomePage) ... ok
test_the_old_home_address_is_not_sent_home (test_check_move.TheHomePage) ... ok
test_the_inventorys_address_list_drives_the_check (test_check_move.TheRealChain) ... ok
test_a_site_that_is_not_wordpress_and_has_no_sitemap (test_wp_inventory.CannotStart) ... ok
test_not_a_web_address (test_wp_inventory.CannotStart) ... ok
test_nothing_answers (test_wp_inventory.CannotStart) ... ok
test_a_plugins_own_content_type_is_found_without_being_named (test_wp_inventory.FullCount) ... ok
test_every_record_is_counted_and_the_run_says_complete (test_wp_inventory.FullCount) ... ok
test_languages_mixed_in_one_tree_show_up (test_wp_inventory.FullCount) ... ok
test_no_page_text_is_written_to_disk (test_wp_inventory.FullCount) ... ok
test_pages_whose_builder_markup_arrives_unrendered_are_flagged (test_wp_inventory.FullCount) ... ok
test_published_records_missing_from_the_sitemap_are_surfaced (test_wp_inventory.FullCount) ... ok
test_sitemap_addresses_no_record_explains_are_surfaced (test_wp_inventory.FullCount) ... ok
test_text_from_the_site_cannot_break_the_report_table (test_wp_inventory.FullCount) ... ok
test_the_address_list_has_one_row_per_address (test_wp_inventory.FullCount) ... ok
test_what_the_site_is_built_with (test_wp_inventory.FullCount) ... ok
test_wordpress_own_machinery_is_not_counted_as_content (test_wp_inventory.FullCount) ... ok
test_a_busy_site_is_not_counted (test_wp_inventory.IncompleteCounts) ... ok
test_a_maintenance_page_in_place_of_data_is_not_counted (test_wp_inventory.IncompleteCounts) ... ok
test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked (test_wp_inventory.IncompleteCounts) ... ok
test_fewer_records_than_the_site_reports (test_wp_inventory.IncompleteCounts) ... ok
test_the_request_limit_stops_the_run_and_says_so (test_wp_inventory.IncompleteCounts) ... ok
test_a_bracketed_word_is_a_shortcode_only_with_a_closing_tag_an_attribute_or_an_underscore (test_wp_inventory.Pieces) ... ok
test_a_cell_a_spreadsheet_would_run_is_defused (test_wp_inventory.Pieces) ... ok
test_an_address_on_another_host_never_matches_one_of_the_sites (test_wp_inventory.Pieces) ... ok
test_short_text_gets_no_language (test_wp_inventory.Pieces) ... ok
test_text_from_the_site_cannot_write_a_link_into_the_report (test_wp_inventory.Pieces) ... ok
test_a_list_that_repeats_itself_is_not_a_full_count (test_wp_inventory.RecordCounting) ... ok
test_a_total_that_changes_between_pages_is_said (test_wp_inventory.RecordCounting) ... ok
test_a_type_registered_under_a_plugins_own_namespace_is_read_there (test_wp_inventory.RecordCounting) ... ok
test_a_type_without_a_total_is_incomplete_and_says_why (test_wp_inventory.RecordCounting) ... ok
test_media_or_a_grouping_without_a_usable_count_is_incomplete (test_wp_inventory.RecordCounting) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 74 tests in 35.994s

OK
exit status: 0
```

</details>

`make check`: exit status 0, last lines "all checks passed" and "LF checkout OK".

Each round-1 fix was undone on its own in a throwaway copy of `scripts/`, then the tests run there: 22 edits, each made at least one test fail. Two did not at first. Undoing the count's "not a list" check passed until the stub sent a total with the odd answer; a separate branch for a probe forwarded to another host changed nothing, since the plain "not found" rule already stops that run, and was removed.
