# DIFF review — karero/croftweaver#281 — wordpress-inspector: count a WordPress site before a move, check every old address after it

Base `f4b21bd` · depth: Normal (runtime code that makes web requests, an instruction file, one new CI job; no login, payment, deletion or personal data) · verdict: OPEN · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

Files in the change: `Makefile`, `README.md`, `.github/workflows/clean.yml`, `skills/wordpress-inspector/SKILL.md`, `skills/wordpress-inspector/scripts/wp_inventory.py`, `skills/wordpress-inspector/scripts/check_move.py`, `skills/wordpress-inspector/scripts/tests/test_wp_inventory.py`, `skills/wordpress-inspector/scripts/tests/test_check_move.py`, and this trail.

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `6413463` | full, `f4b21bd...6413463` without `docs/reviews/` (90,508 bytes) | Codex: codex-cli 0.162.1, gpt-6.1-sol, config.toml's effort, read-only sandbox. melious: glm-5.3, HTTP API, text only. fresh-eyes: sonnet sub-agent, read-only by instruction, could run the tests | codex 548 s, 100,271 tokens; melious 548 s, 65,860 tokens; fresh-eyes 271 s, 154,605 tokens | 10 / 5 / 15 (34 raw: fresh-eyes 3/2/9, Codex 10/3/0, melious 1/0/6). UNVERIFIABLE: 9 asked, 2 led to a wording change (F14, and the password-protected line under F13) |
| 2 | `802b977` | delta since `6413463` without `docs/reviews/` (72,680 bytes), with the round-1 findings as `--verify` | Codex: codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only sandbox. melious: glm-5.3, HTTP API, text only | codex 296 s, 84,386 tokens; melious 844 s, 80,874 tokens | 4 / 2 / 2 (10 raw: Codex 4/1/0, melious 0/2/3; one RISK is F12 again). Confirmed fixed by a reviewer: 26 of 30. UNVERIFIABLE: 8 asked, none confirmed; two led to softer wording (the robots.txt and Markdown sentences) |
| 3 | `70f5649` | delta since `802b977` without `docs/reviews/` (17,781 bytes), with round 2's findings as `--verify` | Codex: codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only sandbox. melious: glm-5.3, HTTP API, text only | codex 212 s, 58,278 tokens; melious 222 s, 27,754 tokens | 2 / 0 / 4 (8 raw: Codex 2/0/0, melious 0/1/5). Confirmed fixed by a reviewer: F32, F33, F34, F36, F37. UNVERIFIABLE: 7 asked, 1 confirmed (the list of internal types lacked "styles"; reworded) |
| 4 | `b575c65` | delta since `70f5649` without `docs/reviews/` (17,605 bytes), with round 3's findings as `--verify`. Earned by F38 and F39 | Codex: codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only sandbox. melious: glm-5.3, HTTP API, text only | codex 162 s, 40,131 tokens; melious 257 s, 26,577 tokens | 2 / 0 / 2 (6 raw: Codex 2/0/0, melious 1/1/2; the RISK is F12 again). Confirmed fixed by a reviewer: F40, F41, F42, F43. UNVERIFIABLE: 6 asked, none confirmed |
| 5 | `7d026b0` | delta since `b575c65` without `docs/reviews/` (18,899 bytes), with round 4's findings as `--verify`. Earned by F44 and F45 | Codex: codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only sandbox. melious: glm-5.3, HTTP API, text only | codex 274 s, 65,005 tokens; melious 405 s, 35,321 tokens | 2 / 0 / 1 (4 raw: Codex 2/0/0, melious 0/0/2; melious also names F12 again, as outside scope). Confirmed fixed by a reviewer: F44, F45, F46, F47; Codex reproduced the parser measurement on both Pythons. UNVERIFIABLE: 7 asked, none confirmed |
| 6 | `2db66bd` | delta since `7d026b0` without `docs/reviews/` (8,422 bytes), with round 5's findings as `--verify`. Earned by F48 | Codex: codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only sandbox. melious: glm-5.3, HTTP API, text only | codex 127 s, 44,128 tokens; melious 196 s, 18,710 tokens | 1 / 0 / 2 (4 raw: Codex 1/0/0, melious 0/1/2; Codex's BUG and melious's RISK are one finding). Confirmed fixed by a reviewer: F48, F49, F50. UNVERIFIABLE: 7 asked, none confirmed |
| 7 | `5ce4007` | delta since `2db66bd` without `docs/reviews/` (11,906 bytes), with round 6's findings as `--verify`. Earned by F51 | Codex: codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only sandbox. melious: glm-5.3, HTTP API, text only | codex 169 s, 46,288 tokens; melious 451 s, 21,549 tokens | 2 / 0 / 3 (5 raw: Codex 2/0/0, melious 0/0/3). Confirmed fixed by a reviewer: F52, F53. UNVERIFIABLE: 8 asked, 1 led to a change (F56) |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | fresh-eyes, Codex | 1 | the old home address read "sent home" when the new home page forwards (to `/en/`, `/index.html`) | fixed, locally_verified, externally_reverified (round 2) | `check_move.py`: `home_keys`, `asked_key != root_key`; tests `TheHomePage` (2) |
| F2 | BUG | fresh-eyes, Codex | 1 | the not-found probe passed when the probe itself was refused or busy, so a site answering "found" for everything read as fully kept | fixed, locally_verified, externally_reverified (round 2) | `check_move.py`: the probe must bring 404 or 410; tests `test_a_probe_that_was_refused_or_busy_proves_nothing` (429, 503, 403), `test_a_site_that_forwards_everything_to_another_host` |
| F3 | BUG | fresh-eyes, Codex, melious | 1 | when every guessed sitemap address was busy, refused or forwarded away, the count read complete with "No sitemap was found" | fixed, locally_verified, externally_reverified (round 2) | `wp_inventory.py`: `read_sitemaps` separates broken from absent; tests `SitemapReading` (busy 503/403/429, plain 404, a web page at the address) |
| F4 | BUG | Codex | 1 | the query was dropped from address keys: `/?p=1` and `/?p=3` merged, and a forward to `/?page_id=2` read as the home page | fixed, locally_verified, externally_reverified (round 2) | `path_key` keeps the query; tests `test_two_addresses_that_differ_only_in_the_query_are_two_addresses`, `test_a_redirect_to_an_address_with_a_query_is_not_the_home_page` |
| F5 | BUG | Codex | 1 | `/a` and `/a/` were merged before asking, so one spelling's answer hid the other's | fixed, locally_verified, externally_reverified (round 2) | only the same address is asked once; test `test_with_and_without_the_closing_slash_are_two_addresses` |
| F6 | BUG | Codex | 1 | a list that repeated its first page counted as a full count (rows compared, not records) | fixed in part, completed in round 2's fixes (F32); locally_verified | distinct ids counted, a repeat or a changed total makes the type incomplete; tests `RecordCounting` (repeat, changing total) |
| F7 | BUG | Codex | 1 | sitemaps were read by pattern: a cut-off file passed as a shorter sitemap, prefixed elements (`sm:loc`) were missed | fixed in part, completed in round 2's fixes (F31, F33, F35); locally_verified | parsed with ElementTree as the facts check does; invariant: a sitemap is read whole or is a gap. Variants tested: cut off inside an index's child, cut off at a guessed address, prefixed elements, padded `loc`, packed |
| F8 | BUG | Codex | 1 | a packed sitemap that unpacks beyond the size limit was read cut off | fixed, locally_verified, externally_reverified (round 2) | the unpacked size is checked; test `test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap` |
| F9 | BUG | Codex | 1 | a count without a total, with a negative total or with an answer that is no list read as counted | fixed, locally_verified, externally_reverified (round 2) | `count_only`, `header_int`; test `test_media_or_a_grouping_without_a_usable_count_is_incomplete` (4 cases), `test_a_type_without_a_total_is_incomplete_and_says_why` |
| F10 | BUG | Codex | 1 | temporary redirects were counted from the note text, so a 302 to another host was not counted | fixed, locally_verified, externally_reverified (round 2) | own column `temporary_redirect`; test `test_a_temporary_redirect_to_another_host_is_flagged_too` |
| F11 | RISK | fresh-eyes | 1 | the standard library's robots.txt reader ignores `*` and `$` before Python 3.13, so the promise "obeys robots.txt" failed on 3.9 | fixed, locally_verified, externally_reverified (round 2) | the facts check's RFC 9309 matcher copied in (a skill travels alone); tests `Robots` (5), run on 3.9.6 and 3.13.16 |
| F12 | RISK | fresh-eyes | 1 | the new CI job blocks no merge until the ruleset names it | OPEN: the owner's step or the owner's waiver. Round 2 (Codex, melious) did not accept a sentence in the PR as a fix | the live ruleset `main checks` requires 27 checks; `wordpress-inventory-tests (3.9)` and `(3.12)` are not among them, and neither are the existing `facts-check-tests` and `cloudflare-check-tests` jobs (read with `gh api repos/karero/croftweaver/rulesets/24584953` on 2026-10-13) |
| F13 | RISK | Codex | 1 | collections were read under `wp/v2` only, and the texts said "every content type" | fixed in part, completed in round 2's fixes (F34); locally_verified | a type's own `rest_namespace` is used (test `test_a_type_registered_under_a_plugins_own_namespace_is_read_there`); SKILL.md, README and the report say "the types the REST API lists" and name unlisted types under what cannot be seen. No real WordPress fixture is added: see Notes |
| F14 | RISK | Codex | 1 | page-builder and form marks were worded as proof, and a rebuild as certain | fixed, locally_verified, externally_reverified (round 2) | SKILL.md steps 3 and 4: a sign, to be compared with the page in a browser |
| F15 | RISK | Codex | 1 | "needs a 301, or search engines keep the old address" had no source | fixed, locally_verified, externally_reverified (round 2) | the sentence about search engines is gone from SKILL.md, the script header and the report |
| F16 | NIT | fresh-eyes, melious | 1 | "1 redirects are temporary", and 303 counted but not named | fixed, locally_verified, externally_reverified (round 2) | `render`: singular, and "302, 303 or 307" |
| F17 | NIT | fresh-eyes | 1 | "off the site" results were said to be listed and were not | fixed, locally_verified, externally_reverified (round 2) | `move-check.md` lists each with its target |
| F18 | NIT | fresh-eyes | 1 | "the site reports None records" | fixed, locally_verified, externally_reverified (round 2) | "the site did not report a total" |
| F19 | NIT | fresh-eyes | 1 | a `Sitemap:` line under the site's other spelling (http for https) made a false gap | fixed, locally_verified, externally_reverified (round 2) | asked on the site itself; test `test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site` |
| F20 | NIT | fresh-eyes | 1 | "a site with thousands of posts needs more" requests: it does not | fixed, locally_verified, externally_reverified (round 2) | SKILL.md: raise the limit when the report says it was reached |
| F21 | NIT | fresh-eyes | 1 | text from the site could write a link into the report | fixed, locally_verified, externally_reverified (round 2) | `md` escapes `[` and `]`; test `test_text_from_the_site_cannot_write_a_link_into_the_report` |
| F22 | NIT | fresh-eyes | 1 | "every old address" is wider than `urls.csv` | fixed, locally_verified, externally_reverified (round 2) | SKILL.md, README, the script header: "each listed address", and what the list leaves out |
| F23 | NIT | melious | 1 | a `csv.Error` escaped as a traceback | fixed, locally_verified, externally_reverified (round 2) | caught; test `test_an_address_list_that_cannot_be_parsed` |
| F24 | NIT | melious | 1 | a redirect or start address with a port that is no number crashed | fixed, locally_verified, externally_reverified (round 2) | `web_address`; tests `test_a_redirect_to_an_address_that_is_no_web_address_is_unreadable_not_a_crash`, `test_not_a_web_address` |
| F25 | NIT | melious | 1 | `__import__("io")` | fixed, locally_verified, externally_reverified (round 2) | `import io` |
| F26 | NIT | melious | 1 | the median was floored | fixed, locally_verified, externally_reverified (round 2) | `round` |
| F27 | NIT | melious | 1 | the CI comment's reason for 3.9 read wrong on an Ubuntu runner | fixed, locally_verified, externally_reverified (round 2) | reworded |
| F28 | NIT | fresh-eyes | 1 | a refused robots.txt (401, 403) was read as "no rules" | fixed, locally_verified, externally_reverified (round 2) | the run stops, as the facts check does; test `test_a_refused_or_unreadable_robots_file_stops_the_run` (401, 403, 429, 500) |
| F29 | NIT | melious | 1 | `--user-agent` changes the name sent, not the name robots.txt is read under | fixed, locally_verified, externally_reverified (round 2) | said in the option's help text |
| F30 | NIT | fresh-eyes | 1 | "left as raw shortcode text" counts any plugin's code, not only a page builder's | fixed, locally_verified, externally_reverified (round 2) | SKILL.md step 3 says so |
| F31 | BUG | Codex, melious | 2 | a cut-off sitemap at a guessed address was filed "absent" when its first element sat beyond the first 4,000 bytes | fixed in part, completed in round 3's fixes (F39); locally_verified | the 4,000-byte look is gone: a start address is "absent" only for a not-found answer or a web page (served as HTML); anything else that does not parse is a gap. Invariant: a sitemap is read whole or is a gap. Variants tested: no lead, a 5,000-byte comment, 6,000 blank lines; a page with and without a document type. `caused-by: F7 (partial)` |
| F32 | BUG | Codex | 2 | records without an id skipped the repeat check, so two copies read as two records and a complete count | fixed, locally_verified, externally_reverified (round 3) | a record whose id is missing, empty or not a number or text makes the type incomplete; test `test_records_without_an_id_cannot_pass_for_a_full_count` (None, empty, a boolean). `caused-by: F6 (partial)` |
| F33 | BUG | Codex | 2 | the XML parser also raises `LookupError` (unknown encoding) and `ValueError` (some multibyte encodings); both escaped as a crash | fixed, locally_verified, externally_reverified (round 3) | reproduced on Python 3.9.6 and 3.15.0, then caught; test `test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash`. `caused-by: F7 (introduced)` |
| F34 | BUG | Codex | 2 | "each content type the API lists" was still wider than the code: WordPress's internal types are skipped and media is one number | fixed, locally_verified, externally_reverified (round 3) | SKILL.md (description and step 2), README and the report's "cannot see" list say so |
| F35 | RISK | melious | 2 | sitemap bytes from any site were handed to the XML parser with document types allowed; the Python a Mac ships with has expat 2.2.8, older than the entity-expansion guard | fixed in part, completed in round 3's fixes (F38); locally_verified | a body with a document type is never parsed (a gap, or "absent" for a web page at a start address); test `test_a_sitemap_with_a_document_type_is_refused_unparsed`. `caused-by: F7 (introduced)` |
| F36 | NIT | melious | 2 | an old home address spelled `/index.html` or `/index.php` still read "sent home" | fixed, locally_verified, externally_reverified (round 3) | `HOME_FILES`; test `test_the_old_home_page_under_its_file_name_is_not_sent_home` |
| F37 | NIT | melious | 2 | the "unpacks to more than 50 MB" message hard-coded the limit | fixed, locally_verified, externally_reverified (round 3) | the message takes it from `SITEMAP_MAX_BYTES` |
| F38 | BUG | Codex, melious (as RISK) | 3 | the document-type guard looked for ASCII letters, so a document type written in UTF-16 reached the parser and its entities were expanded | fixed in part; the code it added is replaced in round 4's fixes (F44); locally_verified; the replacement externally_reverified (round 5) | `sitemap_refusal`: bytes with a NUL (UTF-16) are refused, and the document type is looked for in the prolog only. Invariant: no document type reaches the parser, however it is written. Variants tested: UTF-16 with a mark, little-endian and big-endian without, UTF-32, Latin-1 and cp1252 declared, after a comment and a processing instruction, behind a UTF-8 mark, EBCDIC after an ASCII declaration. Measured on Python 3.9.6 and 3.13.16: the parser reads Latin-1 and unmarked UTF-16 documents with a document type and expands their entities; an EBCDIC one is a parse error. `caused-by: F35 (partial)` |
| F39 | BUG | Codex, melious (as NIT) | 3 | a cut-off sitemap sent with a `text/html` header at a guessed address was filed "absent" | fixed in part; the code it added is replaced in round 4's fixes (F45); locally_verified; the replacement externally_reverified (round 5) | a web page is known by its own markup (`<html`, `<!DOCTYPE html`), not by the header; test `test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap`. `caused-by: F31 (partial)` |
| F40 | NIT | melious | 3 | the words `<!DOCTYPE` inside a comment made a sound sitemap a gap | fixed, locally_verified, externally_reverified (round 4) | only the prolog is read for a document type; test `test_the_words_of_a_comment_are_not_a_document_type` |
| F41 | NIT | melious | 3 | "came without an id" also covered an id that is a fraction or a list | fixed, locally_verified, externally_reverified (round 4) | "without a usable id (a number or a text)"; the test covers a fraction, a list and an object |
| F42 | NIT | melious | 3 | re-flowed paragraphs in SKILL.md ran past the file's line width | fixed, locally_verified, externally_reverified (round 4) | re-wrapped; one command line in a code block stays long |
| F43 | NIT | melious | 3 | SKILL.md named `/` and `/index.php` as the old home, the code also takes `/index.html` and `/index.htm` | fixed, locally_verified, externally_reverified (round 4) | SKILL.md names all four |
| F44 | BUG | Codex, melious | 4 | the look for a document type read only 4,096 bytes of the prolog, so one behind that much white space reached the parser and its entities were expanded | fixed, locally_verified, externally_reverified (round 5) | the look is gone. `parse_sitemap` reads the file with expat alone and stops it at the document-type event, before it reads on. Invariant: nothing after a document type is read. Variants tested: plain, behind 5,000 spaces, behind a comment and 9,000 line ends, behind a processing instruction, behind a UTF-8 mark, UTF-16 with a mark and both ways without, Latin-1 and cp1252 declared. Measured on expat 2.2.8 (Python 3.9.6) and 2.7.4 (3.13.16), record below: a 10-level entity bomb stops with no entity declaration read. `caused-by: F38 (partial)` |
| F45 | BUG | Codex | 4 | `<html>` or `<!DOCTYPE html>` inside a comment or processing instruction made a cut-off sitemap read "absent" | fixed, locally_verified, externally_reverified (round 5) | a web page is what the parser says it is: a document type named html, or a first element named html. A comment's words reach no handler. Tests: `test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap` (four leads), `test_what_the_reader_takes_for_an_address`. One look at the first line remains, for an old HTML document type that XML cannot read, and only where the parser had met no element. `caused-by: F39 (partial)` |
| F46 | NIT | melious | 4 | "(a number or a text)" in the note, where a fraction is refused | fixed, locally_verified, externally_reverified (round 5) | "(a whole number or a text)" |
| F47 | NIT | melious | 4 | every UTF-16 sitemap had become a gap | fixed, locally_verified, externally_reverified (round 5) | no longer: expat reads UTF-16, and a sound UTF-16 sitemap is read (case in `test_the_words_of_a_comment_are_not_a_document_type`) |
| F48 | BUG | Codex | 5 | the one look at the bytes left in `parse_sitemap` (for an old HTML page whose document type XML cannot read) took `html-foo`, `html:foo` and `html.foo` for `html`, so such a document type in front of a cut-off sitemap read as a web page and the count as complete | fixed, locally_verified, externally_reverified (round 6) | the look is removed, not sharpened: where the parser cannot name a document, the reader names none. Tests: `test_what_the_reader_takes_for_an_address` (the three names and `html` itself, each in front of a cut-off sitemap, read as damaged). `caused-by: F45 (introduced)` |
| F49 | BUG (Codex), NIT (melious) | Codex, melious | 5 | the same look read only 1,024 bytes and not past a comment, so an old-style page behind either read as a gap instead of "no sitemap here" | fixed, locally_verified, externally_reverified (round 6) | with the look gone, every old-style page of that kind at a guessed address is a gap that names the address, the loud side; SKILL.md step 1 says to open such an address in a browser. Test `test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address`. A page with an HTML5 or a complete document type is still known by the parser, also behind a comment and 3,000 spaces (tested). `caused-by: F45 (introduced)` |
| F50 | NIT | melious | 5 | two tests compared only part of the result (`why[:16]`, `[::2]`) | fixed, locally_verified, externally_reverified (round 6) | they compare the whole result |
| F51 | BUG (Codex), RISK (melious) | Codex, melious | 6 | the sentence added to SKILL.md for F49 let a reader settle any sitemap gap by seeing a web page in a browser, also for a sitemap that robots.txt or an index names, where a web page means addresses are missing; and the gap note did not say what had come back | fixed in part, completed in round 7's fixes (F54, F55, F57, F58); locally_verified | a note about a guessed address says "(a usual address, only tried)"; a note about a file that did not parse says what it was sent as and that it may be a web page the parser cannot name. SKILL.md step 1 tells the two kinds of gap apart. Tests: `test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address`, `test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there`. `caused-by: F49 (introduced)` |
| F52 | NIT | melious | 6 | no test for `<!DOCTYPE html>` in front of a cut-off sitemap | fixed, locally_verified, externally_reverified (round 7); the answer it pinned is changed by F56 | asserted, with the designed answer: "page". A file that declares itself an HTML page is one; the reader stops there and reads no further. The reviewer expected "damaged"; rounds 5 and 6 list this path as checked and intended, and no sitemap begins that way |
| F53 | NIT | melious | 6 | the test of a page behind a UTF-8 byte-order mark was dropped with the fallback | fixed, locally_verified, externally_reverified (round 7) | added to the page list |
| F54 | BUG | Codex | 7 | when a sitemap that robots.txt names could not be read, the usual addresses were tried as well, so the same address was asked twice and noted once as named and once as "only tried", with opposite advice | fixed, locally_verified | the usual addresses are tried only where robots.txt names no sitemap; test `test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there` (the address is asked once, no "only tried"). `caused-by: F51 (introduced)` |
| F55 | BUG | Codex | 7 | the report cut a gap note at 300 characters, so behind a long address the cause and "sent as" were lost | fixed, locally_verified | gap notes are kept to 4,000 characters; test `test_a_gap_note_keeps_its_end_however_long_the_address` (a 400-character address). `caused-by: F51 (partial)` |
| F56 | NIT | melious (and a Codex UNVERIFIABLE entry) | 7 | `<!DOCTYPE html>` in front of a sitemap read as a web page, on the author's word that no sitemap begins so | fixed, locally_verified | the reader no longer takes that on trust: a document type named html that declares nothing itself is read past as far as the first element. `<html>` there makes a page; a sitemap's element there is refused; a document type with an internal subset is refused at once, whatever its name. Tests in `test_what_the_reader_takes_for_an_address` (six cases). Measured with the reader itself on expat 2.2.8 and 2.7.4, record below: a 10-level entity bomb under the names urlset, html and HTML is refused in under a millisecond |
| F57 | NIT | melious | 7 | "only tried" also marks a guessed address that was busy, refused or could not be unpacked, where a browser settles nothing | fixed, locally_verified | SKILL.md step 1: the browser settles a note that says "sent as text/html"; for the others, run the count again |
| F58 | NIT | melious | 7 | the two notes about a packed file did not say what it was sent as | fixed, locally_verified | they do; test `test_a_packed_file_that_cannot_be_unpacked_says_what_it_was_sent_as` |

Waivers and deferrals: none. F12 waits for the owner: add the checks to the ruleset, or waive in words.

Follow-ups:
- `skills/facts-check/scripts/facts_check.py` hands sitemap bytes to the same XML parser with document types allowed (the exposure of F35), and its test jobs are not required checks either. Both are outside this change.
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

Each round-1 fix was undone on its own in a throwaway copy of `scripts/`, then the tests run there (no output kept): 21 edits. 19 made at least one test fail at once; two did not. Undoing the count's "not a list" check passed until the stub sent a total with the odd answer; a separate branch for a probe forwarded to another host changed nothing, since the plain "not found" rule already stops that run, and was removed, which left 20 edits, all failing a test.

## Test records after the round-2 fixes (author's machine, before round 3)

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_page_under_its_file_name_is_not_sent_home) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots.test_a_group_that_names_this_tool_replaces_the_group_for_everyone) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots.test_a_refused_or_unreadable_robots_file_stops_the_run) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots.test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots.test_the_longest_rule_wins_and_allow_wins_a_tie) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots.test_wildcards_and_the_end_mark_count) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading.test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading.test_a_sitemap_whose_elements_carry_a_prefix_is_read) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading.test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading.test_no_sitemap_anywhere_is_not_a_gap) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 79 tests in 41.244s

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 79 tests in 40.964s

OK
exit status: 0
```

</details>

<details><summary>undo-each-fix.txt</summary>

```
== G1 file a cut-off sitemap at a guessed address as absent
   in wp_inventory.py, replaced:         except (ET.ParseError, LookupError, ValueError):  # damaged, or an encoding the parser does not know
            (absent if a_page else broken).append(
   by:         except (ET.ParseError, LookupError, ValueError):
            (absent if sm in first else broken).append(
FAIL: test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too)
FAIL: test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) (lead=0)
FAIL: test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) (lead=5009)
FAIL: test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) (lead=6000)
FAIL: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='bogus-enc')
FAIL: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='utf-7')
Ran 79 tests in 41.087s
FAILED (failures=6)

== G6 parse a sitemap that declares a document type
   in wp_inventory.py, replaced:         if re.search(rb"<!DOCTYPE", body, re.I):
   by:         if False:
FAIL: test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed)
Ran 79 tests in 40.968s
FAILED (failures=1)

== G3 let an unknown encoding crash the run
   in wp_inventory.py, replaced: except (ET.ParseError, LookupError, ValueError):
   by: except ET.ParseError:
ERROR: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='bogus-enc')
ERROR: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='utf-7')
Ran 79 tests in 41.118s
FAILED (errors=2)

== G2 call records without an id a full count
   in wp_inventory.py, replaced:         elif no_id:
   by:         elif False:
FAIL: test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) (bad=None)
FAIL: test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) (bad='')
FAIL: test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) (bad=True)
Ran 79 tests in 41.228s
FAILED (failures=3)

== G7 call the old /index.php sent home
   in check_move.py, replaced: in home_keys and asked_key not in old_home:
   by: in home_keys and asked_key != root_key:
FAIL: test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_page_under_its_file_name_is_not_sent_home)
Ran 79 tests in 41.373s
FAILED (failures=1)

```

</details>

`undo-each-fix.txt`: each round-2 fix undone on its own in a throwaway copy of `scripts/`, the tests run there on Python 3.13.16; the lines kept are the failing tests' names and the summary.

`make check`: exit status 0.

Notes on the rounds: three round-2 findings (F31, F33, F35) come from one round-1 fix, the sitemap reader of F7. Round 3 is owed by F31, F32 and F33.

## Test records after the round-3 fixes (author's machine, before round 4)

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_page_under_its_file_name_is_not_sent_home) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots.test_a_group_that_names_this_tool_replaces_the_group_for_everyone) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots.test_a_refused_or_unreadable_robots_file_stops_the_run) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots.test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots.test_the_longest_rule_wins_and_allow_wins_a_tie) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots.test_wildcards_and_the_end_mark_count) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) ... ok
test_a_document_type_in_any_encoding_never_reaches_the_parser (test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading.test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading.test_a_sitemap_whose_elements_carry_a_prefix_is_read) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading.test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading.test_no_sitemap_anywhere_is_not_a_gap) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 82 tests in 51.474s

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_document_type_in_any_encoding_never_reaches_the_parser (test_wp_inventory.SitemapReading) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 82 tests in 51.118s

OK
exit status: 0
```

</details>

<details><summary>undo-each-fix.txt</summary>

```
== F38 let NUL bytes (UTF-16) through
   in wp_inventory.py, replaced:     if b" " in body:
   by:     if False:
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='utf-16 with a byte-order mark')
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='utf-16 little-endian, no mark')
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='utf-16 big-endian, no mark')
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='utf-32')
Ran 54 tests in 33.102s
FAILED (failures=4)

== F38 let a document type through
   in wp_inventory.py, replaced:     if re.match(rb"\s*<!DOCTYPE", body[pos:pos + 4096], re.I):
   by:     if False:
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='latin-1, declared')
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='an 8-bit code page, declared')
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='utf-8 after a comment and a processing instruction')
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='utf-8 with a byte-order mark')
FAIL: test_a_sitemap_with_a_document_type_is_refused_unparsed (tests.test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed)
Ran 54 tests in 32.879s
FAILED (failures=5)

== F38 look right after the declaration only
   in wp_inventory.py, replaced:     while True:
        m = _PROLOG_SKIP.match(body, pos)
        if not m:
            break
        pos = m.end()
   by:     m = re.match(rb"\s*<\?xml.*?\?>", body[pos:], re.S)
    pos += m.end() if m else 0
FAIL: test_a_document_type_in_any_encoding_never_reaches_the_parser (tests.test_wp_inventory.SitemapReading.test_a_document_type_in_any_encoding_never_reaches_the_parser) (name='utf-8 after a comment and a processing instruction')
Ran 54 tests in 33.728s
FAILED (failures=1)

== F40 take a comment's words for a document type
   in wp_inventory.py, replaced:     if re.match(rb"\s*<!DOCTYPE", body[pos:pos + 4096], re.I):
   by:     if re.search(rb"<!DOCTYPE", body, re.I):
FAIL: test_the_words_of_a_comment_are_not_a_document_type (tests.test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) (name='plain')
FAIL: test_the_words_of_a_comment_are_not_a_document_type (tests.test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) (name='with a byte-order mark')
FAIL: test_the_words_of_a_comment_are_not_a_document_type (tests.test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) (name='in Latin-1, declared')
Ran 54 tests in 33.166s
FAILED (failures=3)

== F39 trust the header to say what is a web page
   in wp_inventory.py, replaced:             if sm in first and _HTML_PAGE.search(body):
   by:             if sm in first and "html" in (resp.ctype or "").lower():
FAIL: test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) (lead=0)
FAIL: test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) (lead=5009)
Ran 54 tests in 34.466s
FAILED (failures=2)

== F33 let an unknown encoding crash the run
   in wp_inventory.py, replaced: except (ET.ParseError, LookupError, ValueError):
   by: except ET.ParseError:
ERROR: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='bogus-enc')
ERROR: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='utf-7')
Ran 54 tests in 36.710s
FAILED (errors=2)

== F41 take a fraction for an id
   in wp_inventory.py, replaced: isinstance(rec.get("id"), (int, str)) and not isinstance(rec.get("id"), bool)
   by: rec.get("id") is not None and not isinstance(rec.get("id"), (bool, list, dict))
FAIL: test_records_without_an_id_cannot_pass_for_a_full_count (tests.test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) (bad=1.5)
Ran 54 tests in 35.772s
FAILED (failures=1)

```

</details>

`make check`: exit status 0.

Two guards written for F38 were taken out again before this commit: a strict UTF-8 check and a check of the declared encoding. Undoing either made no test fail, and the measurement above says why: every encoding the parser accepts, UTF-16 apart, writes XML's own characters as ASCII does, so the look for a document type reads what the parser reads. They would also have turned a sound Latin-1 sitemap into a gap.

Notes on the rounds: round 4 is earned by F38 and F39, the substantive BUGs of round 3. Both continue chains that start at F7, the sitemap reader (F7, F35, F38 and F7, F31, F39). The reader's rules are now written out in order in `read_sitemaps` and `sitemap_refusal`; if round 4 finds a further defect there, the option to put to the owner is to stop parsing XML from other people's sites with the standard library at all.

## Test records after the round-4 fixes (author's machine, before round 5)

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_page_under_its_file_name_is_not_sent_home) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots.test_a_group_that_names_this_tool_replaces_the_group_for_everyone) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots.test_a_refused_or_unreadable_robots_file_stops_the_run) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots.test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots.test_the_longest_rule_wins_and_allow_wins_a_tie) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots.test_wildcards_and_the_end_mark_count) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading.test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading.test_a_sitemap_whose_elements_carry_a_prefix_is_read) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading.test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading.test_no_sitemap_anywhere_is_not_a_gap) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 83 tests in 61.425s

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 83 tests in 68.766s

OK
exit status: 0
```

</details>

<details><summary>undo-each-fix.txt</summary>

```
== F44 read on past a document type
   in wp_inventory.py, replaced:         seen["doctype"] = name
        raise _StopParsing
   by:         seen["doctype"] = name
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='plain')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='after 5,000 spaces, no declaration')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='after a comment and 9,000 line ends')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='after a processing instruction')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='behind a UTF-8 byte-order mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='utf-16 with a byte-order mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='utf-16 little-endian, no mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='utf-16 big-endian, no mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='latin-1, declared')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='an 8-bit code page, declared')
FAIL: test_a_sitemap_with_a_document_type_is_refused_unparsed (tests.test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed)
FAIL: test_what_the_reader_takes_for_an_address (tests.test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address)
Ran 55 tests in 32.449s
FAILED (failures=12)

== F45 read on into a document that is no sitemap
   in wp_inventory.py, replaced:             if local not in ("urlset", "sitemapindex"):
                raise _StopParsing
   by:             pass
FAIL: test_what_the_reader_takes_for_an_address (tests.test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address)
Ran 55 tests in 38.462s
FAILED (failures=1)

== take any loc at any depth for an address (end)
   in wp_inventory.py, replaced:         if path and path[-1] == "loc" and len(path) == 3 and path[1] in ("url", "sitemap"):
   by:         if path and path[-1] == "loc":
FAIL: test_sitemap_addresses_no_record_explains_are_surfaced (tests.test_wp_inventory.FullCount.test_sitemap_addresses_no_record_explains_are_surfaced)
FAIL: test_the_address_list_has_one_row_per_address (tests.test_wp_inventory.FullCount.test_the_address_list_has_one_row_per_address)
FAIL: test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked (tests.test_wp_inventory.IncompleteCounts.test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked)
FAIL: test_two_addresses_that_differ_only_in_the_query_are_two_addresses (tests.test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses)
FAIL: test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (tests.test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap)
FAIL: test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (tests.test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site)
FAIL: test_what_the_reader_takes_for_an_address (tests.test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address)
FAIL: test_a_sitemap_file_on_another_host_is_reported_not_asked (tests.test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked)
Ran 55 tests in 38.003s
FAILED (failures=8)

== F33 let an unknown encoding crash the run
   in wp_inventory.py, replaced:     except (expat.ExpatError, LookupError, ValueError):  # cut off
   by:     except expat.ExpatError:  # cut off
ERROR: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='bogus-enc')
ERROR: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='utf-7')
Ran 55 tests in 38.612s
FAILED (errors=2)

== call an old-style web page a damaged file
   in wp_inventory.py, replaced:         if seen["root"] is None and re.match(
   by:         if False and re.match(
FAIL: test_what_the_reader_takes_for_an_address (tests.test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address)
Ran 55 tests in 37.346s
FAILED (failures=1)

== F45 file an unreadable file at a start address as absent
   in wp_inventory.py, replaced:             if not why and sm in first:
   by:             if sm in first:
FAIL: test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too)
FAIL: test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) (lead=0)
FAIL: test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) (lead=5009)
FAIL: test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) (lead=6000)
FAIL: test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) (lead='')
FAIL: test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) (lead='<!-- xxxxxxxxxxxxxxxxxxx')
FAIL: test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) (lead='<!-- <html> <!DOCTYPE ht')
FAIL: test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (tests.test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) (lead="<?note <html lang='en'> ")
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='plain')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='after 5,000 spaces, no declaration')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='after a comment and 9,000 line ends')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='after a processing instruction')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='behind a UTF-8 byte-order mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='utf-16 with a byte-order mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='utf-16 little-endian, no mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='utf-16 big-endian, no mark')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='latin-1, declared')
FAIL: test_a_document_type_however_it_is_written_stops_the_reader (tests.test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) (name='an 8-bit code page, declared')
FAIL: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='bogus-enc')
FAIL: test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) (enc='utf-7')
FAIL: test_a_sitemap_with_a_document_type_is_refused_unparsed (tests.test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed)
Ran 55 tests in 39.134s
FAILED (failures=21)

== call a web page with a document type a damaged file
   in wp_inventory.py, replaced:             if seen["doctype"].lower() == "html":
                return "page", [], ""
   by:             pass
FAIL: test_a_web_page_at_a_guessed_address_is_not_a_gap (tests.test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) (page='<!DOCTYPE html>')
FAIL: test_what_the_reader_takes_for_an_address (tests.test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address)
Ran 55 tests in 37.284s
FAILED (failures=2)

One more edit, "take any loc at any depth for an address" on the element's start, made no test fail: the lines it changed did nothing (the text is emptied at every element's end), and they were removed.
```

</details>

<details><summary>expat-probe.txt</summary>

```
$ /usr/bin/python3 -I expat_probe.py
3.9.6 expat_2.2.8
  bomb (10^10 characters if expanded)        stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb after 5000 spaces                     stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb after a comment and 9000 newlines     stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb in utf-16-le, no mark                 stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb in utf-16 with a mark                 stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb in latin-1, declared                  stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  html page with a doctype, tag soup         stopped at the document type | {'doctype': 'html', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  html page, no doctype, tag soup            ExpatError: mismatched tag: line 1, column 28 | {'doctype': None, 'root': 'html', 'entity': 0, 'chars': 7} | 0.000s
  cut-off sitemap with <html> in a comment   ExpatError: unclosed token: line 1, column 117 | {'doctype': None, 'root': 'http://www.sitemaps.org/schemas/sitemap/0.9}urlset', 'entity': 0, 'chars': 0} | 0.000s
  sound sitemap with prefixes                parsed | {'doctype': None, 'root': 'http://www.sitemaps.org/schemas/sitemap/0.9}urlset', 'entity': 0, 'chars': 19} | 0.000s
  unknown encoding                           LookupError: unknown encoding: bogus-enc | {'doctype': None, 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  utf-7                                      ValueError: multi-byte encodings are not supported | {'doctype': None, 'root': None, 'entity': 0, 'chars': 0} | 0.001s
  undefined entity, no doctype               ExpatError: undefined entity: line 1, column 18 | {'doctype': None, 'root': 'urlset', 'entity': 0, 'chars': 0} | 0.000s
exit status: 0
$ python3 -I expat_probe.py
3.13.16 expat_2.7.4
  bomb (10^10 characters if expanded)        stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb after 5000 spaces                     stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb after a comment and 9000 newlines     stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb in utf-16-le, no mark                 stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb in utf-16 with a mark                 stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  bomb in latin-1, declared                  stopped at the document type | {'doctype': 'urlset', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  html page with a doctype, tag soup         stopped at the document type | {'doctype': 'html', 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  html page, no doctype, tag soup            ExpatError: mismatched tag: line 1, column 28 | {'doctype': None, 'root': 'html', 'entity': 0, 'chars': 7} | 0.000s
  cut-off sitemap with <html> in a comment   ExpatError: unclosed token: line 1, column 117 | {'doctype': None, 'root': 'http://www.sitemaps.org/schemas/sitemap/0.9}urlset', 'entity': 0, 'chars': 0} | 0.000s
  sound sitemap with prefixes                parsed | {'doctype': None, 'root': 'http://www.sitemaps.org/schemas/sitemap/0.9}urlset', 'entity': 0, 'chars': 19} | 0.000s
  unknown encoding                           LookupError: unknown encoding: bogus-enc | {'doctype': None, 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  utf-7                                      ValueError: multi-byte encodings are not supported | {'doctype': None, 'root': None, 'entity': 0, 'chars': 0} | 0.000s
  undefined entity, no doctype               ExpatError: undefined entity: line 1, column 18 | {'doctype': None, 'root': 'urlset', 'entity': 0, 'chars': 0} | 0.000s
exit status: 0
```

</details>

<details><summary>expat_probe.py, the script behind expat-probe.txt</summary>

```python
import sys, time, pyexpat
from xml.parsers import expat

class Stop(Exception):
    pass

def probe(body):
    seen = {"doctype": None, "root": None, "entity": 0, "chars": 0}
    p = expat.ParserCreate(namespace_separator="}")
    def doctype(name, sysid, pubid, internal):
        seen["doctype"] = name
        raise Stop
    def start(name, attrs):
        if seen["root"] is None:
            seen["root"] = name
    def chars(data):
        seen["chars"] += len(data)
    def entity(*a):
        seen["entity"] += 1
    p.StartDoctypeDeclHandler = doctype
    p.StartElementHandler = start
    p.CharacterDataHandler = chars
    p.EntityDeclHandler = entity
    t = time.time()
    try:
        p.Parse(body, True)
        how = "parsed"
    except Stop:
        how = "stopped at the document type"
    except Exception as e:
        how = type(e).__name__ + ": " + str(e)[:50]
    return "%s | %r | %.3fs" % (how, seen, time.time() - t)

levels = "".join("<!ENTITY l%d '%s'>" % (i, ("&l%d;" % (i - 1)) * 10) for i in range(1, 10))
bomb = "<?xml version='1.0'?>%s<!DOCTYPE urlset [<!ENTITY l0 'aaaaaaaaaa'>" + levels + "]><urlset><url><loc>&l9;</loc></url></urlset>"
cases = {
 "bomb (10^10 characters if expanded)": (bomb % "").encode(),
 "bomb after 5000 spaces": (bomb % (" " * 5000)).replace("<?xml version='1.0'?>", "").encode(),
 "bomb after a comment and 9000 newlines": (bomb % ("<!-- x -->" + "\n" * 9000)).encode(),
 "bomb in utf-16-le, no mark": (bomb % "").encode("utf-16-le"),
 "bomb in utf-16 with a mark": (bomb % "").replace("?>", " encoding='UTF-16'?>", 1).encode("utf-16"),
 "bomb in latin-1, declared": (bomb % "").replace("?>", " encoding='ISO-8859-1'?>", 1).encode("latin-1"),
 "html page with a doctype, tag soup": b"<!DOCTYPE html><html><body><p>Nothing<br></body></html>",
 "html page, no doctype, tag soup": b"<html><body><p>Nothing<br></body></html>",
 "cut-off sitemap with <html> in a comment": b"<?xml version='1.0'?><!-- <html> <!DOCTYPE html> --><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><lo",
 "sound sitemap with prefixes": b"<sm:urlset xmlns:sm='http://www.sitemaps.org/schemas/sitemap/0.9'><sm:url><sm:loc> http://x.test/a&amp;b </sm:loc></sm:url></sm:urlset>",
 "unknown encoding": b"<?xml version='1.0' encoding='bogus-enc'?><urlset/>",
 "utf-7": b"<?xml version='1.0' encoding='utf-7'?><urlset/>",
 "undefined entity, no doctype": b"<urlset><url><loc>&bomb;</loc></url></urlset>",
}
print(sys.version.split()[0], pyexpat.EXPAT_VERSION)
for k, b in cases.items():
    print("  %-42s %s" % (k, probe(b)))
```

</details>

`make check`: exit status 0.

Notes on the rounds: round 5 is earned by F44 and F45, the substantive BUGs of round 4. Both sat in the hand-written filter in front of the XML parser, which round 3's fixes had added and which had now drawn six findings in three rounds (F31, F33, F35, F38, F39, then F44, F45). Each was a case where the filter and the parser read the same bytes differently. The filter is gone: the fix for F44 and F45 replaces it by the parser's own events (`parse_sitemap`), so no second reading of the bytes exists. That is a rewrite of one function, about 60 lines, within this gate and this artifact; round 5 sees it as a delta like any other.

## Test records after the round-5 fixes (author's machine, before round 6)

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_page_under_its_file_name_is_not_sent_home) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots.test_a_group_that_names_this_tool_replaces_the_group_for_everyone) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots.test_a_refused_or_unreadable_robots_file_stops_the_run) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots.test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots.test_the_longest_rule_wins_and_allow_wins_a_tie) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots.test_wildcards_and_the_end_mark_count) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading.test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading.test_a_sitemap_whose_elements_carry_a_prefix_is_read) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) ... ok
test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (test_wp_inventory.SitemapReading.test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading.test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading.test_no_sitemap_anywhere_is_not_a_gap) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 84 tests in 56.415s

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (test_wp_inventory.SitemapReading) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 84 tests in 57.087s

OK
exit status: 0
```

</details>

`make check`: exit status 0.

No undo run this time: the fix takes code away and adds no guard. What the tests pin instead is the behaviour after the removal.

Notes on the rounds: round 6 is earned by F48, a substantive BUG of round 5 (a count that read complete when it was not). Round 5 confirmed the rewrite of the sitemap reader; its two BUGs sat in the single look at the bytes the rewrite had kept. That look is now gone as well, at a stated price (F49).

## Test records after the round-6 fixes (author's machine, before round 7)

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_page_under_its_file_name_is_not_sent_home) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots.test_a_group_that_names_this_tool_replaces_the_group_for_everyone) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots.test_a_refused_or_unreadable_robots_file_stops_the_run) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots.test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots.test_the_longest_rule_wins_and_allow_wins_a_tie) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots.test_wildcards_and_the_end_mark_count) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading.test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) ... ok
test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there (test_wp_inventory.SitemapReading.test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading.test_a_sitemap_whose_elements_carry_a_prefix_is_read) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) ... ok
test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (test_wp_inventory.SitemapReading.test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading.test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading.test_no_sitemap_anywhere_is_not_a_gap) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 85 tests in 55.432s

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (test_wp_inventory.SitemapReading) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 85 tests in 54.973s

OK
exit status: 0
```

</details>

<details><summary>undo-each-fix.txt</summary>

```
== F51 never say that an address was only tried
   in wp_inventory.py, replaced: if only_tried and sm in first else ""
   by: if False else ""
FAIL: test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (tests.test_wp_inventory.SitemapReading.test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address)
Ran 57 tests in 39.100s
FAILED (failures=1)

== F51 call a sitemap the site names only tried
   in wp_inventory.py, replaced: if only_tried and sm in first else ""
   by: if sm in first else ""
FAIL: test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there)
Ran 57 tests in 38.841s
FAILED (failures=1)

== F51 leave out what came back
   in wp_inventory.py, replaced: broken.append("%s: %s; sent as %s; not read" % (named(sm), why or "a web page or another kind of document, not a sitemap", sent_as))
   by: broken.append("%s: %s; not read" % (named(sm), why or "not a sitemap"))
FAIL: test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there)
FAIL: test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (tests.test_wp_inventory.SitemapReading.test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address)
Ran 57 tests in 37.817s
FAILED (failures=2)

```

</details>

`make check`: exit status 0.

Notes on the rounds: round 7 is earned by F51, which Codex filed as a BUG: an instruction in SKILL.md that a reader would follow to a wrong estimate. The owner asked on 2026-10-13, in the session, to "Merge 281 once clean and green"; F12 still needs the owner's waiver or the ruleset change before the gate can be clean.

## Test records after the round-7 fixes (author's machine, before round 8)

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage.test_the_old_home_page_under_its_file_name_is_not_sent_home) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting.test_records_without_an_id_cannot_pass_for_a_full_count) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting.test_two_addresses_that_differ_only_in_the_query_are_two_addresses) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots.test_a_group_that_names_this_tool_replaces_the_group_for_everyone) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots.test_a_refused_or_unreadable_robots_file_stops_the_run) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots.test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots.test_the_longest_rule_wins_and_allow_wins_a_tie) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots.test_wildcards_and_the_end_mark_count) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading.test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading.test_a_document_type_however_it_is_written_stops_the_reader) ... ok
test_a_gap_note_keeps_its_end_however_long_the_address (test_wp_inventory.SitemapReading.test_a_gap_note_keeps_its_end_however_long_the_address) ... ok
test_a_packed_file_that_cannot_be_unpacked_says_what_it_was_sent_as (test_wp_inventory.SitemapReading.test_a_packed_file_that_cannot_be_unpacked_says_what_it_was_sent_as) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading.test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading.test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading.test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading.test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash) ... ok
test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there (test_wp_inventory.SitemapReading.test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading.test_a_sitemap_whose_elements_carry_a_prefix_is_read) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading.test_a_sitemap_with_a_document_type_is_refused_unparsed) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading.test_a_web_page_at_a_guessed_address_is_not_a_gap) ... ok
test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (test_wp_inventory.SitemapReading.test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading.test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading.test_no_sitemap_anywhere_is_not_a_gap) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading.test_the_words_of_a_comment_are_not_a_document_type) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite.test_a_redirect_to_another_host_is_reported_not_followed) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite.test_a_rest_api_reached_by_query_string_is_read_too) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite.test_a_sitemap_file_on_another_host_is_reported_not_asked) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite.test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it) ... ok

----------------------------------------------------------------------
Ran 87 tests in 56.901s

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
test_the_old_home_page_under_its_file_name_is_not_sent_home (test_check_move.TheHomePage) ... ok
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
test_records_without_an_id_cannot_pass_for_a_full_count (test_wp_inventory.RecordCounting) ... ok
test_two_addresses_that_differ_only_in_the_query_are_two_addresses (test_wp_inventory.RecordCounting) ... ok
test_a_group_that_names_this_tool_replaces_the_group_for_everyone (test_wp_inventory.Robots) ... ok
test_a_refused_or_unreadable_robots_file_stops_the_run (test_wp_inventory.Robots) ... ok
test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api (test_wp_inventory.Robots) ... ok
test_the_longest_rule_wins_and_allow_wins_a_tie (test_wp_inventory.Robots) ... ok
test_wildcards_and_the_end_mark_count (test_wp_inventory.Robots) ... ok
test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits (test_wp_inventory.SitemapReading) ... ok
test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_document_type_however_it_is_written_stops_the_reader (test_wp_inventory.SitemapReading) ... ok
test_a_gap_note_keeps_its_end_however_long_the_address (test_wp_inventory.SitemapReading) ... ok
test_a_packed_file_that_cannot_be_unpacked_says_what_it_was_sent_as (test_wp_inventory.SitemapReading) ... ok
test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_whose_elements_carry_a_prefix_is_read (test_wp_inventory.SitemapReading) ... ok
test_a_sitemap_with_a_document_type_is_refused_unparsed (test_wp_inventory.SitemapReading) ... ok
test_a_web_page_at_a_guessed_address_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address (test_wp_inventory.SitemapReading) ... ok
test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete (test_wp_inventory.SitemapReading) ... ok
test_no_sitemap_anywhere_is_not_a_gap (test_wp_inventory.SitemapReading) ... ok
test_the_words_of_a_comment_are_not_a_document_type (test_wp_inventory.SitemapReading) ... ok
test_what_the_reader_takes_for_an_address (test_wp_inventory.SitemapReading) ... ok
test_a_redirect_to_another_host_is_reported_not_followed (test_wp_inventory.StaysOnTheSite) ... ok
test_a_rest_api_reached_by_query_string_is_read_too (test_wp_inventory.StaysOnTheSite) ... ok
test_a_sitemap_file_on_another_host_is_reported_not_asked (test_wp_inventory.StaysOnTheSite) ... ok
test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it (test_wp_inventory.StaysOnTheSite) ... ok

----------------------------------------------------------------------
Ran 87 tests in 57.221s

OK
exit status: 0
```

</details>

<details><summary>undo-each-fix.txt</summary>

```
== F56 read past a page's document type that declares things
   in wp_inventory.py, replaced: if has_internal_subset or name.lower() != "html":
   by: if name.lower() != "html":
FAIL: test_what_the_reader_takes_for_an_address (tests.test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address)
Ran 59 tests in 41.563s
FAILED (failures=1)

== F56 read a sitemap that sits behind a page's document type
   in wp_inventory.py, replaced:             if seen["doctype"] is not None:  # a sitemap behind a page's document type
                seen["refused"] = True
                raise _StopParsing
   by:             pass
FAIL: test_what_the_reader_takes_for_an_address (tests.test_wp_inventory.SitemapReading.test_what_the_reader_takes_for_an_address)
Ran 59 tests in 41.059s
FAILED (failures=1)

== F54 try the usual addresses after a named sitemap failed
   in wp_inventory.py, replaced:     if not named:  # the usual addresses
   by:     if not files:  # the usual addresses
FAIL: test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there (tests.test_wp_inventory.SitemapReading.test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there)
Ran 59 tests in 40.892s
FAILED (failures=1)

== F55 cut a gap note after 300 characters
   in wp_inventory.py, replaced: md(x, 4000) for x in d["incomplete_because"]
   by: md(x, 300) for x in d["incomplete_because"]
FAIL: test_a_gap_note_keeps_its_end_however_long_the_address (tests.test_wp_inventory.SitemapReading.test_a_gap_note_keeps_its_end_however_long_the_address)
Ran 59 tests in 41.131s
FAILED (failures=1)

== F58 leave out what a packed file was sent as
   in wp_inventory.py, replaced: broken.append("%s: cannot be unpacked; sent as %s; not read" % (named(sm), sent_as))
   by: broken.append("%s: cannot be unpacked" % named(sm))
FAIL: test_a_packed_file_that_cannot_be_unpacked_says_what_it_was_sent_as (tests.test_wp_inventory.SitemapReading.test_a_packed_file_that_cannot_be_unpacked_says_what_it_was_sent_as)
Ran 59 tests in 40.360s
FAILED (failures=1)

```

</details>

<details><summary>bomb-probe.txt</summary>

```
$ /usr/bin/python3 -I bomb_probe.py <scripts dir>
3.9.6 expat_2.2.8
  document type urlset, first element urlset -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0001 s
  document type html  , first element html   -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0000 s
  document type html  , first element urlset -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0000 s
  document type HTML  , first element html   -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0000 s
exit status: 0
$ python3 -I bomb_probe.py <scripts dir>
3.13.16 expat_2.7.4
  document type urlset, first element urlset -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0000 s
  document type html  , first element html   -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0000 s
  document type html  , first element urlset -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0000 s
  document type HTML  , first element html   -> ('', [], 'declares a document type, which a sitemap does not need') in 0.0000 s
exit status: 0
```

</details>

<details><summary>bomb_probe.py, the script behind bomb-probe.txt</summary>

```python
"""The production reader against a 10-level entity bomb (10^10 characters if expanded), under each name
a document type can carry. usage: python3 -I bomb_probe.py <scripts dir>"""
import sys, time, pyexpat
sys.path.insert(0, sys.argv[1])
import wp_inventory as wi
levels = "".join("<!ENTITY l%d '%s'>" % (i, ("&l%d;" % (i - 1)) * 10) for i in range(1, 10))
print(sys.version.split()[0], pyexpat.EXPAT_VERSION)
for name, root in (("urlset", "urlset"), ("html", "html"), ("html", "urlset"), ("HTML", "html")):
    doc = ("<?xml version='1.0'?><!DOCTYPE %s [<!ENTITY l0 'aaaaaaaaaa'>%s]><%s><url><loc>&l9;</loc></url></%s>" % (name, levels, root, root)).encode()
    t = time.time(); got = wi.parse_sitemap(doc)
    print("  document type %-6s, first element %-6s -> %r in %.4f s" % (name, root, got, time.time() - t))
```

</details>

`make check`: exit status 0.

Notes on the rounds: round 8 is earned by F54 and F55, the substantive BUGs of round 7; both sat in what round 6's fix for F51 had added. Round 8 is the last the skill's budget allows without the owner: whatever it leaves open goes to the owner as one decision.
