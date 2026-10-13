# DIFF review — karero/croftweaver#281 — wordpress-inspector: count a WordPress site before a move, check every old address after it

Base `f4b21bd` · depth: Normal (runtime code that makes web requests, an instruction file, one new CI job; no login, payment, deletion or personal data) · verdict: OPEN · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

Files in the change: `Makefile`, `README.md`, `.github/workflows/clean.yml`, `skills/wordpress-inspector/SKILL.md`, `skills/wordpress-inspector/scripts/wp_inventory.py`, `skills/wordpress-inspector/scripts/check_move.py`, `skills/wordpress-inspector/scripts/tests/test_wp_inventory.py`, `skills/wordpress-inspector/scripts/tests/test_check_move.py`, and this trail.

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|

Waivers and deferrals: none.

Follow-ups: none yet.

Notes:
- The new CI job `wordpress-inventory-tests` is not in the ruleset's required checks.
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
