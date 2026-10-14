# DIFF review — karero/croftweaver#293 — facts-check reads sitemaps with the XML parser stopped at a document type

Base `034472d` · depth: Normal (runtime code that reads files from other sites) · verdict: OPEN · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

Files in the change: `skills/facts-check/scripts/facts_check.py`, `skills/facts-check/scripts/tests/test_facts_check.py`, and this trail.

Severity bar, set before round 1: a BUG is an entity reaching the parser's expansion, a crash, or a sound sitemap read wrongly. A hand-made file the owner's own site would not serve, refused with a note, is at most a NIT.

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|

Waivers and deferrals: none.

Follow-ups: none yet.

## Test records (author's machine, before round 1, head `7d6aabe`)

<details><summary>tests-python3.13.txt</summary>

```
$ python3 -m unittest discover -v -s skills/facts-check/scripts/tests
test_a_charset_that_cannot_decode_text_falls_back_to_utf8 (test_facts_check.CheckPage.test_a_charset_that_cannot_decode_text_falls_back_to_utf8) ... ok
test_a_repeated_description_is_one_finding (test_facts_check.CheckPage.test_a_repeated_description_is_one_finding) ... ok
test_a_separator_or_a_sign_in_a_span_of_its_own_still_belongs_to_the_number (test_facts_check.CheckPage.test_a_separator_or_a_sign_in_a_span_of_its_own_still_belongs_to_the_number) ... ok
test_a_span_does_not_split_a_number_but_still_separates_a_number_from_its_label (test_facts_check.CheckPage.test_a_span_does_not_split_a_number_but_still_separates_a_number_from_its_label) ... ok
test_each_fact_yields_to_the_others_terms (test_facts_check.CheckPage.test_each_fact_yields_to_the_others_terms) ... ok
test_inline_formatting_does_not_split_numbers_or_words (test_facts_check.CheckPage.test_inline_formatting_does_not_split_numbers_or_words) ... ok
test_meta_charset_is_used_when_the_header_names_none (test_facts_check.CheckPage.test_meta_charset_is_used_when_the_header_names_none) ... ok
test_numbers_in_structured_data_carry_their_property_name (test_facts_check.CheckPage.test_numbers_in_structured_data_carry_their_property_name) ... ok
test_resolving_soft_spaces_takes_linear_time (test_facts_check.CheckPage.test_resolving_soft_spaces_takes_linear_time) ... ok
test_structured_data_inside_a_template_or_noscript_is_not_read (test_facts_check.CheckPage.test_structured_data_inside_a_template_or_noscript_is_not_read) ... ok
test_bad_facts_file_exits_two (test_facts_check.Cli.test_bad_facts_file_exits_two) ... ok
test_init_writes_once (test_facts_check.Cli.test_init_writes_once) ... ok
test_a_byte_order_mark_does_not_lose_the_first_group_of_robots_txt (test_facts_check.FetcherRules.test_a_byte_order_mark_does_not_lose_the_first_group_of_robots_txt) ... ok
test_a_llms_txt_that_redirects_into_a_disallowed_path_is_noted (test_facts_check.FetcherRules.test_a_llms_txt_that_redirects_into_a_disallowed_path_is_noted) ... ok
test_a_malformed_address_is_no_page_and_no_crash (test_facts_check.FetcherRules.test_a_malformed_address_is_no_page_and_no_crash) ... ok
test_a_page_over_5_mb_is_reported_as_cut (test_facts_check.FetcherRules.test_a_page_over_5_mb_is_reported_as_cut) ... ok
test_a_robots_txt_that_cannot_be_read_keeps_the_site_out (test_facts_check.FetcherRules.test_a_robots_txt_that_cannot_be_read_keeps_the_site_out) ... ok
test_a_robots_txt_that_redirects_without_end_keeps_the_site_out (test_facts_check.FetcherRules.test_a_robots_txt_that_redirects_without_end_keeps_the_site_out) ... ok
test_a_sitemap_with_a_malformed_entry_still_checks_the_other_pages (test_facts_check.FetcherRules.test_a_sitemap_with_a_malformed_entry_still_checks_the_other_pages) ... ok
test_an_address_that_cannot_be_read_is_not_matched_against_robots_txt (test_facts_check.FetcherRules.test_an_address_that_cannot_be_read_is_not_matched_against_robots_txt) ... ok
test_bad_address_ignores_the_fragment_and_the_ends (test_facts_check.FetcherRules.test_bad_address_ignores_the_fragment_and_the_ends) ... ok
test_clean_address_is_the_address_as_a_request_sends_it (test_facts_check.FetcherRules.test_clean_address_is_the_address_as_a_request_sends_it) ... ok
test_robots_txt_judges_the_address_that_is_requested (test_facts_check.FetcherRules.test_robots_txt_judges_the_address_that_is_requested) ... ok
test_robots_txt_judges_the_path_that_is_requested_for_an_empty_path (test_facts_check.FetcherRules.test_robots_txt_judges_the_path_that_is_requested_for_an_empty_path) ... ok
test_sitemap_entries_differing_only_in_the_fragment_are_one_page (test_facts_check.FetcherRules.test_sitemap_entries_differing_only_in_the_fragment_are_one_page) ... ok
test_the_fetcher_reads_only_web_addresses (test_facts_check.FetcherRules.test_the_fetcher_reads_only_web_addresses) ... ok
test_a_comma_ends_the_search (test_facts_check.FindMentions.test_a_comma_ends_the_search) ... ok
test_a_day_range_is_two_numbers_with_no_token_for_the_hyphen (test_facts_check.FindMentions.test_a_day_range_is_two_numbers_with_no_token_for_the_hyphen) ... ok
test_a_minus_sign_is_part_of_the_number (test_facts_check.FindMentions.test_a_minus_sign_is_part_of_the_number) ... ok
test_a_plain_four_digit_count_is_not_taken_for_a_year (test_facts_check.FindMentions.test_a_plain_four_digit_count_is_not_taken_for_a_year) ... ok
test_a_year_after_month_and_day_is_a_year (test_facts_check.FindMentions.test_a_year_after_month_and_day_is_a_year) ... ok
test_before_phrase_and_percent_unit (test_facts_check.FindMentions.test_before_phrase_and_percent_unit) ... ok
test_multiword_term (test_facts_check.FindMentions.test_multiword_term) ... ok
test_other_numbers_near_the_term_are_not_tied (test_facts_check.FindMentions.test_other_numbers_near_the_term_are_not_tied) ... ok
test_snippet_marks_the_number (test_facts_check.FindMentions.test_snippet_marks_the_number) ... ok
test_term_after_the_number (test_facts_check.FindMentions.test_term_after_the_number) ... ok
test_the_nearest_term_after_the_number_wins (test_facts_check.FindMentions.test_the_nearest_term_after_the_number_wins) ... ok
test_whole_words_terms_match_only_whole_words (test_facts_check.FindMentions.test_whole_words_terms_match_only_whole_words) ... ok
test_window_and_sentence_end_limit_the_search (test_facts_check.FindMentions.test_window_and_sentence_end_limit_the_search) ... ok
test_years_and_zero_are_ignored_unless_the_fact_is_one (test_facts_check.FindMentions.test_years_and_zero_are_ignored_unless_the_fact_is_one) ... ok
test_a_body_shorter_than_its_content_length_is_not_a_page (test_facts_check.FullRun.test_a_body_shorter_than_its_content_length_is_not_a_page) ... ok
test_a_malformed_address_in_the_page_list_does_not_stop_the_run (test_facts_check.FullRun.test_a_malformed_address_in_the_page_list_does_not_stop_the_run) ... ok
test_a_padded_site_address_is_cleaned_once_for_every_address_built_from_it (test_facts_check.FullRun.test_a_padded_site_address_is_cleaned_once_for_every_address_built_from_it) ... ok
test_a_positioning_rule_path_is_a_path_even_with_a_scheme_in_it (test_facts_check.FullRun.test_a_positioning_rule_path_is_a_path_even_with_a_scheme_in_it) ... ok
test_a_quoted_charset_in_the_header_is_honoured (test_facts_check.FullRun.test_a_quoted_charset_in_the_header_is_honoured) ... ok
test_a_redirect_into_a_page_robots_txt_disallows_is_not_followed (test_facts_check.FullRun.test_a_redirect_into_a_page_robots_txt_disallows_is_not_followed) ... ok
test_a_redirect_to_a_non_web_address_is_not_followed (test_facts_check.FullRun.test_a_redirect_to_a_non_web_address_is_not_followed) ... ok
test_a_response_that_ends_in_the_middle_does_not_stop_the_run (test_facts_check.FullRun.test_a_response_that_ends_in_the_middle_does_not_stop_the_run) ... ok
test_a_run_that_reads_no_page_is_never_clean (test_facts_check.FullRun.test_a_run_that_reads_no_page_is_never_clean) ... ok
test_a_sign_a_split_number_and_a_template_through_a_full_run (test_facts_check.FullRun.test_a_sign_a_split_number_and_a_template_through_a_full_run) ... ok
test_an_address_longer_than_8000_bytes_is_not_requested (test_facts_check.FullRun.test_an_address_longer_than_8000_bytes_is_not_requested) ... ok
test_an_address_with_a_space_before_its_fragment_is_the_page_it_names (test_facts_check.FullRun.test_an_address_with_a_space_before_its_fragment_is_the_page_it_names) ... ok
test_an_address_with_letters_beyond_ascii_is_sent_as_a_browser_sends_it (test_facts_check.FullRun.test_an_address_with_letters_beyond_ascii_is_sent_as_a_browser_sends_it) ... ok
test_clean_site_exits_zero (test_facts_check.FullRun.test_clean_site_exits_zero) ... ok
test_exempt_wins_over_a_wildcard_rule_and_redirects_are_listed (test_facts_check.FullRun.test_exempt_wins_over_a_wildcard_rule_and_redirects_are_listed) ... ok
test_finds_every_kind_of_finding (test_facts_check.FullRun.test_finds_every_kind_of_finding) ... ok
test_ignore_robots_reads_disallowed_pages (test_facts_check.FullRun.test_ignore_robots_reads_disallowed_pages) ... ok
test_image_entries_in_the_sitemap_are_not_pages (test_facts_check.FullRun.test_image_entries_in_the_sitemap_are_not_pages) ... ok
test_no_pages_is_an_error_not_a_pass (test_facts_check.FullRun.test_no_pages_is_an_error_not_a_pass) ... ok
test_only_and_extra_urls (test_facts_check.FullRun.test_only_and_extra_urls) ... ok
test_only_is_applied_while_the_sitemap_is_read (test_facts_check.FullRun.test_only_is_applied_while_the_sitemap_is_read) ... ok
test_positioning_on_the_stub_site (test_facts_check.FullRun.test_positioning_on_the_stub_site) ... ok
test_the_limit_holds_for_the_address_as_the_robots_matcher_reads_it (test_facts_check.FullRun.test_the_limit_holds_for_the_address_as_the_robots_matcher_reads_it) ... ok
test_the_path_robots_txt_is_judged_on_is_the_path_the_request_sends (test_facts_check.FullRun.test_the_path_robots_txt_is_judged_on_is_the_path_the_request_sends) ... ok
test_what_is_requested_is_the_cleaned_address (test_facts_check.FullRun.test_what_is_requested_is_the_cleaned_address) ... ok
test_a_sitemap_over_5_mb_is_read_in_full (test_facts_check.LargeSitemap.test_a_sitemap_over_5_mb_is_read_in_full) ... ok
test_a_malformed_positioning_block_is_a_message_not_a_crash (test_facts_check.LoadFacts.test_a_malformed_positioning_block_is_a_message_not_a_crash) ... ok
test_a_pasted_address_is_read_without_the_space_or_line_break_at_its_ends (test_facts_check.LoadFacts.test_a_pasted_address_is_read_without_the_space_or_line_break_at_its_ends) ... ok
test_a_wrong_type_is_a_message_not_a_crash (test_facts_check.LoadFacts.test_a_wrong_type_is_a_message_not_a_crash) ... ok
test_bad_json (test_facts_check.LoadFacts.test_bad_json) ... ok
test_positioning_alone_is_enough (test_facts_check.LoadFacts.test_positioning_alone_is_enough) ... ok
test_positioning_rules_are_validated (test_facts_check.LoadFacts.test_positioning_rules_are_validated) ... ok
test_problems_are_listed_together (test_facts_check.LoadFacts.test_problems_are_listed_together) ... ok
test_starter_file_is_valid (test_facts_check.LoadFacts.test_starter_file_is_valid) ... ok
test_whole_words_is_true_or_false (test_facts_check.LoadFacts.test_whole_words_is_true_or_false) ... ok
test_wrong_types_in_the_positioning_block_are_messages_too (test_facts_check.LoadFacts.test_wrong_types_in_the_positioning_block_are_messages_too) ... ok
test_facts_in_alt_text_and_share_title_but_not_in_addresses (test_facts_check.MorePlaces.test_facts_in_alt_text_and_share_title_but_not_in_addresses) ... ok
test_retired_phrases_in_alt_text_share_tags_and_addresses (test_facts_check.MorePlaces.test_retired_phrases_in_alt_text_share_tags_and_addresses) ... ok
test_template_and_noscript_content_is_not_page_structure (test_facts_check.MorePlaces.test_template_and_noscript_content_is_not_page_structure) ... ok
test_a_plain_space_does_not_group_thousands (test_facts_check.ParseNumber.test_a_plain_space_does_not_group_thousands) ... ok
test_formats (test_facts_check.ParseNumber.test_formats) ... ok
test_no_match_inside_words_or_codes (test_facts_check.ParseNumber.test_no_match_inside_words_or_codes) ... ok
test_only_a_plain_number_can_be_a_year (test_facts_check.ParseNumber.test_only_a_plain_number_can_be_a_year) ... ok
test_unit_letters_are_not_multipliers (test_facts_check.ParseNumber.test_unit_letters_are_not_multipliers) ... ok
test_a_paragraph_ends_where_the_browser_ends_it (test_facts_check.Positioning.test_a_paragraph_ends_where_the_browser_ends_it) ... ok
test_intro_falls_back_to_article_then_page (test_facts_check.Positioning.test_intro_falls_back_to_article_then_page) ... ok
test_only_the_first_main_counts (test_facts_check.Positioning.test_only_the_first_main_counts) ... ok
test_paths_and_first_matching_rule (test_facts_check.Positioning.test_paths_and_first_matching_rule) ... ok
test_surface_rules_alternatives_and_body (test_facts_check.Positioning.test_surface_rules_alternatives_and_body) ... ok
test_surfaces_as_the_starter_test_reads_them (test_facts_check.Positioning.test_surfaces_as_the_starter_test_reads_them) ... ok
test_term_rule_needs_title_description_and_h1_or_intro (test_facts_check.Positioning.test_term_rule_needs_title_description_and_h1_or_intro) ... ok
test_title_is_the_first_title_and_keeps_no_break_spaces (test_facts_check.Positioning.test_title_is_the_first_title_and_keeps_no_break_spaces) ... ok
test_a_hostile_pattern_costs_little_time (test_facts_check.RobotsMatcher.test_a_hostile_pattern_costs_little_time) ... ok
test_a_path_with_leading_slashes_is_judged_as_it_is_requested (test_facts_check.RobotsMatcher.test_a_path_with_leading_slashes_is_judged_as_it_is_requested) ... ok
test_a_rule_is_measured_after_its_escapes_are_normalised (test_facts_check.RobotsMatcher.test_a_rule_is_measured_after_its_escapes_are_normalised) ... ok
test_a_rule_that_ends_in_dollar_needs_its_last_piece_after_the_others (test_facts_check.RobotsMatcher.test_a_rule_that_ends_in_dollar_needs_its_last_piece_after_the_others) ... ok
test_an_empty_query_is_part_of_the_path_that_is_requested (test_facts_check.RobotsMatcher.test_an_empty_query_is_part_of_the_path_that_is_requested) ... ok
test_every_spelling_of_the_robots_txt_address_is_allowed (test_facts_check.RobotsMatcher.test_every_spelling_of_the_robots_txt_address_is_allowed) ... ok
test_groups (test_facts_check.RobotsMatcher.test_groups) ... ok
test_percent_escapes_as_the_rfc_has_them (test_facts_check.RobotsMatcher.test_percent_escapes_as_the_rfc_has_them) ... ok
test_the_file_as_the_lines_it_has (test_facts_check.RobotsMatcher.test_the_file_as_the_lines_it_has) ... ok
test_the_flags_of_a_robots_txt_that_cannot_be_read (test_facts_check.RobotsMatcher.test_the_flags_of_a_robots_txt_that_cannot_be_read) ... ok
test_the_longest_matching_rule_wins_and_allow_wins_a_tie (test_facts_check.RobotsMatcher.test_the_longest_matching_rule_wins_and_allow_wins_a_tie) ... ok
test_the_path_matching_table_of_googles_documentation (test_facts_check.RobotsMatcher.test_the_path_matching_table_of_googles_documentation) ... ok
test_the_path_that_is_requested (test_facts_check.RobotsMatcher.test_the_path_that_is_requested) ... ok
test_the_robots_txt_file_itself_is_always_allowed (test_facts_check.RobotsMatcher.test_the_robots_txt_file_itself_is_always_allowed) ... ok
test_an_index_cut_by_the_file_limit_says_so (test_facts_check.SitemapFileLimit.test_an_index_cut_by_the_file_limit_says_so) ... ok
test_an_index_within_the_limit_says_nothing (test_facts_check.SitemapFileLimit.test_an_index_within_the_limit_says_nothing) ... ok
test_a_cut_off_or_foreign_file_lists_no_page (test_facts_check.SitemapReader.test_a_cut_off_or_foreign_file_lists_no_page) ... ok
test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader.test_a_document_type_stops_the_reader_however_it_is_written) ... ok
test_a_run_whose_sitemap_declares_entities_reads_no_page_and_says_why (test_facts_check.SitemapReader.test_a_run_whose_sitemap_declares_entities_reads_no_page_and_says_why) ... ok
test_an_encoding_the_parser_does_not_know_is_a_note_not_a_crash (test_facts_check.SitemapReader.test_an_encoding_the_parser_does_not_know_is_a_note_not_a_crash) ... ok
test_what_the_reader_takes_for_a_page (test_facts_check.SitemapReader.test_what_the_reader_takes_for_a_page) ... ok

----------------------------------------------------------------------
Ran 113 tests in 5.305s

OK
exit status: 0
```

</details>

<details><summary>tests-python3.9.txt</summary>

```
$ /usr/bin/python3 -m unittest discover -v -s skills/facts-check/scripts/tests
test_a_charset_that_cannot_decode_text_falls_back_to_utf8 (test_facts_check.CheckPage) ... ok
test_a_repeated_description_is_one_finding (test_facts_check.CheckPage) ... ok
test_a_separator_or_a_sign_in_a_span_of_its_own_still_belongs_to_the_number (test_facts_check.CheckPage) ... ok
test_a_span_does_not_split_a_number_but_still_separates_a_number_from_its_label (test_facts_check.CheckPage) ... ok
test_each_fact_yields_to_the_others_terms (test_facts_check.CheckPage) ... ok
test_inline_formatting_does_not_split_numbers_or_words (test_facts_check.CheckPage) ... ok
test_meta_charset_is_used_when_the_header_names_none (test_facts_check.CheckPage) ... ok
test_numbers_in_structured_data_carry_their_property_name (test_facts_check.CheckPage) ... ok
test_resolving_soft_spaces_takes_linear_time (test_facts_check.CheckPage) ... ok
test_structured_data_inside_a_template_or_noscript_is_not_read (test_facts_check.CheckPage) ... ok
test_bad_facts_file_exits_two (test_facts_check.Cli) ... ok
test_init_writes_once (test_facts_check.Cli) ... ok
test_a_byte_order_mark_does_not_lose_the_first_group_of_robots_txt (test_facts_check.FetcherRules) ... ok
test_a_llms_txt_that_redirects_into_a_disallowed_path_is_noted (test_facts_check.FetcherRules) ... ok
test_a_malformed_address_is_no_page_and_no_crash (test_facts_check.FetcherRules) ... ok
test_a_page_over_5_mb_is_reported_as_cut (test_facts_check.FetcherRules) ... ok
test_a_robots_txt_that_cannot_be_read_keeps_the_site_out (test_facts_check.FetcherRules) ... ok
test_a_robots_txt_that_redirects_without_end_keeps_the_site_out (test_facts_check.FetcherRules) ... ok
test_a_sitemap_with_a_malformed_entry_still_checks_the_other_pages (test_facts_check.FetcherRules) ... ok
test_an_address_that_cannot_be_read_is_not_matched_against_robots_txt (test_facts_check.FetcherRules) ... ok
test_bad_address_ignores_the_fragment_and_the_ends (test_facts_check.FetcherRules) ... ok
test_clean_address_is_the_address_as_a_request_sends_it (test_facts_check.FetcherRules) ... ok
test_robots_txt_judges_the_address_that_is_requested (test_facts_check.FetcherRules) ... ok
test_robots_txt_judges_the_path_that_is_requested_for_an_empty_path (test_facts_check.FetcherRules) ... ok
test_sitemap_entries_differing_only_in_the_fragment_are_one_page (test_facts_check.FetcherRules) ... ok
test_the_fetcher_reads_only_web_addresses (test_facts_check.FetcherRules) ... ok
test_a_comma_ends_the_search (test_facts_check.FindMentions) ... ok
test_a_day_range_is_two_numbers_with_no_token_for_the_hyphen (test_facts_check.FindMentions) ... ok
test_a_minus_sign_is_part_of_the_number (test_facts_check.FindMentions) ... ok
test_a_plain_four_digit_count_is_not_taken_for_a_year (test_facts_check.FindMentions) ... ok
test_a_year_after_month_and_day_is_a_year (test_facts_check.FindMentions) ... ok
test_before_phrase_and_percent_unit (test_facts_check.FindMentions) ... ok
test_multiword_term (test_facts_check.FindMentions) ... ok
test_other_numbers_near_the_term_are_not_tied (test_facts_check.FindMentions) ... ok
test_snippet_marks_the_number (test_facts_check.FindMentions) ... ok
test_term_after_the_number (test_facts_check.FindMentions) ... ok
test_the_nearest_term_after_the_number_wins (test_facts_check.FindMentions) ... ok
test_whole_words_terms_match_only_whole_words (test_facts_check.FindMentions) ... ok
test_window_and_sentence_end_limit_the_search (test_facts_check.FindMentions) ... ok
test_years_and_zero_are_ignored_unless_the_fact_is_one (test_facts_check.FindMentions) ... ok
test_a_body_shorter_than_its_content_length_is_not_a_page (test_facts_check.FullRun) ... ok
test_a_malformed_address_in_the_page_list_does_not_stop_the_run (test_facts_check.FullRun) ... ok
test_a_padded_site_address_is_cleaned_once_for_every_address_built_from_it (test_facts_check.FullRun) ... ok
test_a_positioning_rule_path_is_a_path_even_with_a_scheme_in_it (test_facts_check.FullRun) ... ok
test_a_quoted_charset_in_the_header_is_honoured (test_facts_check.FullRun) ... ok
test_a_redirect_into_a_page_robots_txt_disallows_is_not_followed (test_facts_check.FullRun) ... ok
test_a_redirect_to_a_non_web_address_is_not_followed (test_facts_check.FullRun) ... ok
test_a_response_that_ends_in_the_middle_does_not_stop_the_run (test_facts_check.FullRun) ... ok
test_a_run_that_reads_no_page_is_never_clean (test_facts_check.FullRun) ... ok
test_a_sign_a_split_number_and_a_template_through_a_full_run (test_facts_check.FullRun) ... ok
test_an_address_longer_than_8000_bytes_is_not_requested (test_facts_check.FullRun) ... ok
test_an_address_with_a_space_before_its_fragment_is_the_page_it_names (test_facts_check.FullRun) ... ok
test_an_address_with_letters_beyond_ascii_is_sent_as_a_browser_sends_it (test_facts_check.FullRun) ... ok
test_clean_site_exits_zero (test_facts_check.FullRun) ... ok
test_exempt_wins_over_a_wildcard_rule_and_redirects_are_listed (test_facts_check.FullRun) ... ok
test_finds_every_kind_of_finding (test_facts_check.FullRun) ... ok
test_ignore_robots_reads_disallowed_pages (test_facts_check.FullRun) ... ok
test_image_entries_in_the_sitemap_are_not_pages (test_facts_check.FullRun) ... ok
test_no_pages_is_an_error_not_a_pass (test_facts_check.FullRun) ... ok
test_only_and_extra_urls (test_facts_check.FullRun) ... ok
test_only_is_applied_while_the_sitemap_is_read (test_facts_check.FullRun) ... ok
test_positioning_on_the_stub_site (test_facts_check.FullRun) ... ok
test_the_limit_holds_for_the_address_as_the_robots_matcher_reads_it (test_facts_check.FullRun) ... ok
test_the_path_robots_txt_is_judged_on_is_the_path_the_request_sends (test_facts_check.FullRun) ... ok
test_what_is_requested_is_the_cleaned_address (test_facts_check.FullRun) ... ok
test_a_sitemap_over_5_mb_is_read_in_full (test_facts_check.LargeSitemap) ... ok
test_a_malformed_positioning_block_is_a_message_not_a_crash (test_facts_check.LoadFacts) ... ok
test_a_pasted_address_is_read_without_the_space_or_line_break_at_its_ends (test_facts_check.LoadFacts) ... ok
test_a_wrong_type_is_a_message_not_a_crash (test_facts_check.LoadFacts) ... ok
test_bad_json (test_facts_check.LoadFacts) ... ok
test_positioning_alone_is_enough (test_facts_check.LoadFacts) ... ok
test_positioning_rules_are_validated (test_facts_check.LoadFacts) ... ok
test_problems_are_listed_together (test_facts_check.LoadFacts) ... ok
test_starter_file_is_valid (test_facts_check.LoadFacts) ... ok
test_whole_words_is_true_or_false (test_facts_check.LoadFacts) ... ok
test_wrong_types_in_the_positioning_block_are_messages_too (test_facts_check.LoadFacts) ... ok
test_facts_in_alt_text_and_share_title_but_not_in_addresses (test_facts_check.MorePlaces) ... ok
test_retired_phrases_in_alt_text_share_tags_and_addresses (test_facts_check.MorePlaces) ... ok
test_template_and_noscript_content_is_not_page_structure (test_facts_check.MorePlaces) ... ok
test_a_plain_space_does_not_group_thousands (test_facts_check.ParseNumber) ... ok
test_formats (test_facts_check.ParseNumber) ... ok
test_no_match_inside_words_or_codes (test_facts_check.ParseNumber) ... ok
test_only_a_plain_number_can_be_a_year (test_facts_check.ParseNumber) ... ok
test_unit_letters_are_not_multipliers (test_facts_check.ParseNumber) ... ok
test_a_paragraph_ends_where_the_browser_ends_it (test_facts_check.Positioning) ... ok
test_intro_falls_back_to_article_then_page (test_facts_check.Positioning) ... ok
test_only_the_first_main_counts (test_facts_check.Positioning) ... ok
test_paths_and_first_matching_rule (test_facts_check.Positioning) ... ok
test_surface_rules_alternatives_and_body (test_facts_check.Positioning) ... ok
test_surfaces_as_the_starter_test_reads_them (test_facts_check.Positioning) ... ok
test_term_rule_needs_title_description_and_h1_or_intro (test_facts_check.Positioning) ... ok
test_title_is_the_first_title_and_keeps_no_break_spaces (test_facts_check.Positioning) ... ok
test_a_hostile_pattern_costs_little_time (test_facts_check.RobotsMatcher) ... ok
test_a_path_with_leading_slashes_is_judged_as_it_is_requested (test_facts_check.RobotsMatcher) ... ok
test_a_rule_is_measured_after_its_escapes_are_normalised (test_facts_check.RobotsMatcher) ... ok
test_a_rule_that_ends_in_dollar_needs_its_last_piece_after_the_others (test_facts_check.RobotsMatcher) ... ok
test_an_empty_query_is_part_of_the_path_that_is_requested (test_facts_check.RobotsMatcher) ... ok
test_every_spelling_of_the_robots_txt_address_is_allowed (test_facts_check.RobotsMatcher) ... ok
test_groups (test_facts_check.RobotsMatcher) ... ok
test_percent_escapes_as_the_rfc_has_them (test_facts_check.RobotsMatcher) ... ok
test_the_file_as_the_lines_it_has (test_facts_check.RobotsMatcher) ... ok
test_the_flags_of_a_robots_txt_that_cannot_be_read (test_facts_check.RobotsMatcher) ... ok
test_the_longest_matching_rule_wins_and_allow_wins_a_tie (test_facts_check.RobotsMatcher) ... ok
test_the_path_matching_table_of_googles_documentation (test_facts_check.RobotsMatcher) ... ok
test_the_path_that_is_requested (test_facts_check.RobotsMatcher) ... ok
test_the_robots_txt_file_itself_is_always_allowed (test_facts_check.RobotsMatcher) ... ok
test_an_index_cut_by_the_file_limit_says_so (test_facts_check.SitemapFileLimit) ... ok
test_an_index_within_the_limit_says_nothing (test_facts_check.SitemapFileLimit) ... ok
test_a_cut_off_or_foreign_file_lists_no_page (test_facts_check.SitemapReader) ... ok
test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) ... ok
test_a_run_whose_sitemap_declares_entities_reads_no_page_and_says_why (test_facts_check.SitemapReader) ... ok
test_an_encoding_the_parser_does_not_know_is_a_note_not_a_crash (test_facts_check.SitemapReader) ... ok
test_what_the_reader_takes_for_a_page (test_facts_check.SitemapReader) ... ok

----------------------------------------------------------------------
Ran 113 tests in 6.066s

OK
exit status: 0
```

</details>

<details><summary>undo-each-fix.txt</summary>

```
== read on past a document type
   in facts_check.py, replaced:     def doctype(name, system_id, public_id, has_internal_subset):
        raise _StopReading
   by:     def doctype(name, system_id, public_id, has_internal_subset):
        pass
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='plain')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='after 5,000 spaces, no declaration')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='after a comment and a processing instruction')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='behind a UTF-8 byte-order mark')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='utf-16 with a byte-order mark')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='utf-16 little-endian, no mark')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='latin-1, declared')
FAIL: test_a_run_whose_sitemap_declares_entities_reads_no_page_and_says_why (test_facts_check.SitemapReader)
Ran 113 tests in 10.272s
FAILED (failures=8)

== let an unknown encoding crash the run
   in facts_check.py, replaced: except (expat.ExpatError, LookupError, ValueError):
   by: except expat.ExpatError:
ERROR: test_an_encoding_the_parser_does_not_know_is_a_note_not_a_crash (test_facts_check.SitemapReader) (enc='bogus-enc')
ERROR: test_an_encoding_the_parser_does_not_know_is_a_note_not_a_crash (test_facts_check.SitemapReader) (enc='utf-7')
Ran 113 tests in 12.027s
FAILED (errors=2)

== take any loc at any depth for a page
   in facts_check.py, replaced:         if len(path) == 3 and path[-1] == "loc" and path[1] in ("url", "sitemap"):
   by:         if path[-1] == "loc":
FAIL: test_a_padded_site_address_is_cleaned_once_for_every_address_built_from_it (test_facts_check.FullRun)
FAIL: test_finds_every_kind_of_finding (test_facts_check.FullRun)
FAIL: test_image_entries_in_the_sitemap_are_not_pages (test_facts_check.FullRun)
FAIL: test_a_cut_off_or_foreign_file_lists_no_page (test_facts_check.SitemapReader)
FAIL: test_what_the_reader_takes_for_a_page (test_facts_check.SitemapReader)
Ran 113 tests in 9.450s
FAILED (failures=5)

== ignore what the reader says is wrong
   in facts_check.py, replaced:         kind, locs, problem = read_sitemap_xml(body)
        if problem:
   by:         kind, locs, problem = read_sitemap_xml(body)
        if False:
FAIL: test_a_cut_off_or_foreign_file_lists_no_page (test_facts_check.SitemapReader)
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='plain')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='after 5,000 spaces, no declaration')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='after a comment and a processing instruction')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='behind a UTF-8 byte-order mark')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='utf-16 with a byte-order mark')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='utf-16 little-endian, no mark')
FAIL: test_a_document_type_stops_the_reader_however_it_is_written (test_facts_check.SitemapReader) (name='latin-1, declared')
FAIL: test_a_run_whose_sitemap_declares_entities_reads_no_page_and_says_why (test_facts_check.SitemapReader)
FAIL: test_an_encoding_the_parser_does_not_know_is_a_note_not_a_crash (test_facts_check.SitemapReader) (enc='bogus-enc')
FAIL: test_an_encoding_the_parser_does_not_know_is_a_note_not_a_crash (test_facts_check.SitemapReader) (enc='utf-7')
Ran 113 tests in 4.965s
FAILED (failures=11)

```

</details>

`undo-each-fix.txt`: each part of the fix undone on its own in a throwaway copy of `scripts/`, the tests run there on Python 3.9.6; a control run of the unchanged copy passed first. An earlier attempt is not counted: it named the test module so that it never loaded, and every undo showed the same import error.

`make check`: exit status 0.

Reproduced on main (`034472d`) with Python 3.9.6, through `sitemap_urls`: a sitemap declaring `encoding='bogus-enc'` raised LookupError; a sitemap with a small entity tree listed the page with the entity expanded.
