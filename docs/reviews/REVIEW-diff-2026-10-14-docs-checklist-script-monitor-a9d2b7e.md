# DIFF review — branch `docs/checklist-script-monitor` — the checklist's step for Cloudflare's script monitor

Base `de64ec8` · depth: High (a runbook that tells owners to change an infrastructure setting and states what their privacy page relies on) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session created the worktree and the branch), POST AUTHORITY (this session created the pull request)

The commit ids are as reviewed; the branch keeps them. Seats: Codex (`gpt-6.1-sol`, read-only, config effort), GLM 5.3 over HTTP API, a fresh-eyes sub-agent on the host's own model (rounds 1 to 3, read-only), and Kimi K3 on ollama for the final full read (text only).

| Round | Head | Artifact | Seats | Seconds, tokens per seat |
|---|---|---|---|---|
| 1 | `a9d2b7e` | full: one step, three cross references | Codex, GLM, fresh-eyes | Codex 237 s / 90,326; GLM 135 s / 14,346; fresh-eyes 752 s / 241,984 |
| 2 | `4b5f0b1` | delta (the step rewritten, a loop) | Codex, GLM, fresh-eyes | Codex 236 s / 79,519; GLM 249 s / 25,983; fresh-eyes 846 s / 288,678 |
| 3 | `eff3841` | delta | Codex, GLM, fresh-eyes | Codex 270 s / 76,261; GLM 175 s / 19,166; fresh-eyes 847 s / 284,635 |
| 4 | `5f79d66` | delta, earned by the kind `loop-status` | Codex, GLM | Codex 558 s / 80,365; GLM 297 s / 24,547 |
| 5 | `08f70f6` | delta, earned by `loop-status`, with a cut | Codex, GLM | Codex 410 s / 71,045; GLM 320 s / 24,945 |
| 6 | `0ec4d9a` | delta, earned by `loop-status` and `other-remedy`, with a cut | Codex, GLM | Codex 364 s / 72,879; GLM 234 s / 21,924 |
| 7 | `38efc1e` | delta, earned by `other-remedy`, with a cut (the loop test runs under Git Bash) | Codex, GLM | Codex 319 s / 66,144; GLM 207 s / 19,887 |
| 8 | `80bf0ad` | delta, earned by `other-remedy`, with a cut | Codex, GLM | Codex 275 s / 68,333; GLM 131 s / 9,849 |
| final full read | `807171e` | the whole change, four files | Kimi K3 (ollama) | 276 s |
| wording pass | `4c71817` | delta since `80bf0ad` | Codex, config effort | 224 s / 72,935 |
| confirmation | `2c1944a` | delta since `4c71817` (one sentence) | Codex, config effort | 101 s / 33,613 |

Findings recorded across the gate: 70 rows (10 BUG, 22 RISK, 34 NIT, 4 UNVERIFIABLE questions answered), each with its disposition in the per-round records below. No waiver was granted and none is pending. Two BUGs were in sentences the change did not write (section 5's line about a 3xx status); both were fixed in prose. Rounds past 3 each name the BUG kind that earned them (`loop-status`, `other-remedy`) and carry a cut: the loop's status handling replaced by one strict rule (round 5), the remedy's promise of a status and the one-line remedy removed (round 6), the status-by-status remedy list removed (round 7), the redirect guidance removed so no status is named (round 8).

Verdict: CLEAN at `2c1944a`. The confirmation returned "No BUG/RISK/NIT findings".

Open and named in the text, not findings of this gate:
- Whether the `curl -sI` (HEAD) command in section 5 shows the monitor on a zone that has it on (the one zone is switched off). Step 5 does not depend on it.
- The zone's response-header rule state when the 40 requests were made (the text says it was not read).
- The meaning of the "Global" badge on the switch (the text says so and tells the owner to look at their other sites first).
- Follow-ups: the `pages.dev` reading guide does not say whether a `report-to:` line there could be the monitor's (unknown); a Windows run of the loop by an owner, as opposed to CI's.

Notes:
- The Windows CI leg ran the loop test in Git Bash on head `807171e` and passed: `tests 95, pass 95, fail 0, skipped 0`, with the test's own line `✔ the counting loop in the reference reads clean, header or other, and counts only a 200 that curl finished`. The loop test skipped silently on Windows in the first design; at the owner's choice it was made to run there, and on CI it fails if no usable bash is found.
- Closing edits after round 8 (the remedy order, one sentence about a 3xx, a closed-port tolerance, a comment, a message string, a default removed from the awk) were fixed without a further round (the review rules ask the owner for a grant past round 8, and round 8 had no BUG in scope). Codex's wording pass read all of them, including the three small code hunks; they were not read by a full-scope round, and the record says so.
- GLM 5.3 saw rounds 1 to 8 in full; it did not see the wording pass or the confirmation. Codex holds the unbroken chain to the last head. Fresh-eyes ran in rounds 1 to 3, as High depth says.
- Codex's sandbox cannot open sockets (`listen EPERM`), so its runs of the suite are UNVERIFIABLE; the fresh-eyes agent ran the suite in rounds 1 to 3, and the author's runs and CI's are in the pull request.

## Records, one per round (the author's record of each round's findings and what was done; the reviewers' raw output is in the pull request's review comment)

<details><summary>Round 1 (head a9d2b7e)</summary>


The author's record of what was done about each. It is a claim to check, not evidence.

- B1 BUG (Codex; GLM as RISK; fresh-eyes). Step 3 said a `report-to:` line naming `cf-csp-endpoint` "is
  not NEL: go to step 5, not step 4", which skips NEL's rule on a site where a `nel:` line (or one
  `Report-To` value carrying both groups) is still there beside the monitor's line. FIXED: step 3 now
  says a `nel:` line, or a `report-to:` line that names `cf-nel`, is still NEL (step 4) whatever else
  the command shows, and that a line that names `cf-csp-endpoint` and sends to an address on
  `csp-reporting.cloudflare.com` is the monitor (step 5). A line that names both needs both.
- B2 BUG (Codex), RISK (fresh-eyes). The text identified the monitor by group NAME alone; the checker
  identifies it by the HOST of the address and its tests treat a group of the owner's own named
  `cf-csp-endpoint` as the owner's. FIXED: step 3, step 5 and section 5 identify it by the address on
  `csp-reporting.cloudflare.com`; the name is given as what was seen. "A `report-to:` line of your
  own is yours to judge" is kept.
- B3 RISK (Codex; fresh-eyes). "The rule in step 4 doesn't remove it" was a universal on 2 answers of one
  site; "the switch does [show it is off]" did not follow and conflicted with the document's own
  lesson that a setting can read off while the header is still served. FIXED: step 5 scopes the
  observation (the one site, 2 of 40 answers, the rule in place since 12 October, "we don't know why
  the rule left it") and checks by counting after the switch is off ("none of 100 is what you want; we
  saw none of 200"), with "tell your assistant" if the switch is missing or lines still show. The
  sentence "The dashboard toggle is the proof" in CLOUDFLARE_CHECK.md is replaced.
- B4 RISK (GLM; Codex; fresh-eyes). The section 5 command greps for `report-to:` but not for the header
  Cloudflare documents, `content-security-policy-report-only:`; the capture and the loop use GET over
  HTTP/1.1 while the command is `curl -sI` (HEAD); the loop counted `report-to` only. PARTLY FIXED:
  step 5 is unconditional ("whatever the command showed") and its check is the loop, which is GET; the
  loop now counts the monitor's three headers; step 5 names the documented header and the observed
  `report-to:` line separately. NOT CHANGED: the first command itself. The author has not established
  whether `curl -sI` shows the monitor on a zone that has it on (the one zone is now switched off), so
  neither section 3 nor section 5 claims that the command shows it. Open, named in the trail.
- B5 RISK (fresh-eyes). The only road to step 5 was seeing the line in a sampled answer (about 1 run in
  20 by the step's own numbers), so an owner with the monitor on would tick the box and never read it.
  FIXED: step 5 is unconditional and its bold lead is the action; the item's lead names the second
  switch.
- B6 RISK (fresh-eyes; GLM as NIT). Step 4 said the rule "removes `Report-To` from every response";
  step 5 said it "doesn't remove it". The unchanged tail paragraph said "the header" and "the old
  note". FIXED: step 4 says the rule "is set to remove" it; step 5 states the observation and that
  the cause is unknown; the tail paragraph says "the old NEL note ... (the `max_age` from step 1)" and
  "If a `nel:` line is still there".
- B7 RISK (fresh-eyes). "The rule was in place" rests on nobody reporting its removal, not on reading
  the zone's ruleset at the time of the 40 requests. NOT FIXED, scoped: the text says "in place since
  12 October" for the one site. The ruleset was not read then (no token exists; the owner can read it
  in the dashboard). Stays the author's record; open, named in the trail.
- B8 NIT (fresh-eyes). The item's lead named four of five steps. FIXED.
- B9 NIT (fresh-eyes). "Cloudflare's page describes turning it on; switch it Off" reads as a
  contradiction. FIXED: "Cloudflare's page shows turning it on; this is the same switch."
- B10 NIT (fresh-eyes). The step was long, led with evidence, used "HTML responses", and gave
  Cloudflare's statement about browsers as fact. FIXED: action first, then *What it is*, *Check*,
  *The trade-off* (the labels the NEL item uses); "pages" not "HTML responses"; "Cloudflare says ...
  and that the visitor's browser then sends reports".
- B11 NIT (fresh-eyes). The tail paragraph's "that many seconds" no longer sat after step 1's
  `max_age`. FIXED with B6.
- B12 NIT (fresh-eyes). Section 6 gave the kit's table as the reason there is no API route. FIXED:
  "we did not look for an API call for it".
- B13 NIT (fresh-eyes). The switch's path is in three files and no test tied them. FIXED: one
  `MONITOR_PATH` in the test file is asserted against the checker's fix text and the checklist.
- B14 NIT (fresh-eyes). "its alerts when they change" came from the product overview. FIXED: cut.
- B15 NIT (GLM). The caution was stated twice (step 3, section 5). FIXED: section 5 now identifies the
  line and points to step 5.
- B16 (fresh-eyes, optional). CLOUDFLARE_FIRST_DEPLOY.md lists settings the checklist covers. NOT
  CHANGED: the sentence is a "such as" list, not an enumeration.
- B17 (Codex, injection note). Two reviewer-directed sentences in the round 1 brief were read as an
  attempt to steer. Noted: this round's brief says what changed and nothing more.
- B18 (Codex, claim C3). The evidence named one privacy template; the kit has two
  (`privacy.astro` and `_datenschutz.astro`). The claim holds for both. Record corrected below.

</details>

<details><summary>Round 2 (head 4b5f0b1)</summary>


The author's record of what was done about each. It is a claim to check, not evidence. Round 1
(a9d2b7e) found 2 BUG, 5 RISK, 8 NIT; its record was passed with --verify to round 2 and every row
was confirmed landed or its stated reason held, except the rows below that round 2 re-opened.

Round 2 (Codex, GLM 5.3, fresh-eyes): no BUG. Open findings and what was done:

- C2-1 RISK (fresh-eyes). Step 5 made the loop in CLOUDFLARE_CHECK.md the check, but the loop fetched
  `https://example.com/`, nowhere said to replace it, and counted every answer without the three
  headers whatever its status, so an unedited paste, a redirect or an error page printed `100 none`.
  FIXED: the loop uses `yourdomain.com` (as section 5 does) and the reference says to replace it; each
  count carries the answer's status line (`none HTTP/1.1 200 OK`); step 5 says only answers that are
  200 count and what the count should read.
- C2-2 RISK (fresh-eyes; Codex). "With step 4's rule in place since 12 October" was shipped as fact
  while the ruleset was not read when the 40 requests were made, and "we don't know why the rule left
  it" and the checker's "does not remove it" rested on it. FIXED: step 5 says the rule "had been set
  there on 12 October. We did not read it when we counted, so we can't say why the line was there."
  The checker's fix text now reads "did not remove it on the one site where this was seen" and its
  test pins that.
- C2-3 NIT (Codex; fresh-eyes). The switch's path has three copies (checklist, checker, reference);
  the test tied two. FIXED: the checklist-parity test also reads `references/CLOUDFLARE_CHECK.md`
  and asserts the same `MONITOR_PATH`.
- C2-4 NIT (GLM; fresh-eyes). Step 3 asked for the name `cf-csp-endpoint` AND the address, while
  section 5 and the checker use the address alone. FIXED: step 3 uses the address; step 5 gives the
  name as what was seen.
- C2-5 NIT (fresh-eyes). The tail paragraph's "If a `nel:` line is still there" no longer covered a
  `report-to:` line that names `cf-nel`. FIXED.
- C2-6 NIT (GLM; fresh-eyes). The reference said no number of requests shows it is off, then "count
  requests to see that the headers stopped". FIXED: "100 answers without the headers make it
  unlikely that they are still being sent, and do not exclude it".
- C2-7 NIT (fresh-eyes). Section 5's reading guide said "nothing else", with nothing saying a clean
  answer does not show the monitor is off (the command is a HEAD request). FIXED: one clause.
- C2-8 NIT (fresh-eyes). "none of 100" beside a loop that prints a label `none`; "lines still show";
  "the rule left it". FIXED: "the count should read `100 none HTTP/1.1 200 OK`"; "a `header` count
  shows"; the sentence is reworded (C2-2).
- C2-9 NIT (fresh-eyes). The reference reports the monitor as a `look` while step 5 is an
  instruction. FIXED: one sentence in the reference's table row.
- C2-10 NIT (fresh-eyes). Step 5 gave the cost but no "Why off", and did not weigh the other remedy
  the document uses (a line on the privacy page). FIXED: a *Why off:* line, with "If you keep it on, say
  so on your privacy page."
- C2-11 NIT (fresh-eyes). One added line was 111 characters and the reflow left a 24-character stub.
  FIXED: the tail paragraph is re-wrapped; step 5's first lines are re-wrapped.
- C2-12 UNVERIFIABLE (fresh-eyes). The switch carries a "Global" badge; its scope was not read, and
  step 5 said nothing about it. HANDLED in the text: "The switch may be marked Global; we did not check
  whether it then covers every domain in your account." Open for the owner.
- C2-13 UNVERIFIABLE (fresh-eyes). "None of 200" was counted with a `report-to`-only loop. HANDLED:
  the text and the reference now say "no `report-to:` line in 200 answers".
- NOT CHANGED, open in the trail: whether `curl -sI` (HEAD) shows the monitor on a zone that has it on;
  the zone's ruleset state at the time of the count; the Global badge's meaning.

</details>

<details><summary>Round 3 (head eff3841)</summary>


The author's record of what was done about each. It is a claim to check, not evidence. Rounds 1 and
2 were confirmed landed in round 3 except where a row below re-opens one.

Round 3 (Codex, GLM 5.3, fresh-eyes): one BUG, four RISK, ten NIT.

- D3-1 BUG (Codex). The loop took the status from the first line of the dump (`head -n 1`), which
  behind a proxy is the proxy's "200 Connection established"; a site's 503 read as `none HTTP/1.1
  200 ...`. FIXED by replacing the loop, not patching it: curl's own final status
  (`-w 'status=%{http_code}\n'`) and one `awk` that labels each answer `header` or `none` and prints
  it with the status. No `head`, no `tr`, no separate branch for failures (a failed connection
  prints `status=000`). Run three ways against a live site: a 200 prints `none status=200`, a
  redirecting name prints `none status=301`, the unedited placeholder prints `none status=000`.
- D3-2 RISK (fresh-eyes). `yourdomain.com` and `example.com` are real names that answer 200 without
  the headers, so an unedited paste printed the line step 5 says it should read. FIXED: the
  placeholder is `yourdomain.invalid`, which cannot answer; the reference names it.
- D3-3 RISK (Codex). "100 answers without the headers make it unlikely that they are still being
  sent" had no stated basis. FIXED: "would be unlikely if they still came as often as we saw (2 in
  40), and do not exclude a lower rate".
- D3-4 RISK (Codex; fresh-eyes). The checker's fix text said the rule "did not remove it on the one
  site where this was seen", which rests on a rule state that was not read. FIXED: it says what
  step 4 itself supports: "removes only the NEL and Report-To headers; it does not switch the monitor
  off". The comment above it matches; the test pins the new text.
- D3-5 NIT (fresh-eyes). "(we saw no `report-to:` line in 200 answers)" followed "Only answers that
  are 200 count" and read as a status. FIXED: "(after we switched it off we made 200 requests and
  saw no `report-to:` line)".
- D3-6 NIT (fresh-eyes). "so we can't say why the line was there" collided with *What it is*.
  FIXED: "so we can't say whether it was working then".
- D3-7 NIT (fresh-eyes). "how many failed, each with the status line": a failure has none. FIXED
  with D3-1: one count line per label and final status; a failure is `status=000`.
- D3-8 NIT (fresh-eyes). Nothing said what to do when the bare name redirects. FIXED: "with `www.` if
  the bare name redirects".
- D3-9 NIT (fresh-eyes). The Global sentence gave a worry and no action. FIXED: "look at your other
  sites before you switch it off".
- D3-10 NIT (fresh-eyes). The test's comment said "both places"; the reference's "Keeping it true"
  did not mention the pinned path. FIXED.
- D3-11 NIT (fresh-eyes, optional). Nothing tied the count step 5 quotes to the loop. FIXED: the
  parity test asserts the loop's pieces (`seq 1 100`, `status=%{http_code}`, `print h, $0`) and that
  the checklist quotes `100 none status=200`.
- D3-12 NIT (GLM). The rewrite dropped "It is not NEL". FIXED.
- D3-13 NIT (GLM). Step 3 names only the `report-to:` address, while the checker judges three
  forms. NOT CHANGED: step 3 reads the output of the section 5 command, which prints only
  `report-to:` of the three; step 5 is unconditional.
- D3-14 NIT (GLM). The test's failure message kept the general claim. FIXED with D3-4.
- Follow-ups, outside this change: the `monitorWhat` string in the checker says "a report-to group,
  cf-csp-endpoint" flatly while the reference says the two other headers rest on one capture (the
  comment above it is fixed, the string is left); the pages.dev reading guide does not say whether a
  `report-to:` line there could be the monitor's (unknown).
- NOT CHANGED, open: whether `curl -sI` (HEAD) shows the monitor on a zone that has it on; the
  zone's ruleset state at the time of the count; the meaning of the Global badge.

</details>

<details><summary>Round 4 (head 5f79d66)</summary>


The author's record of what was done about each. It is a claim to check, not evidence. Round 4
(Codex, GLM 5.3) confirmed the round 3 rows landed; its own findings and what was done:

- E4-1 BUG (Codex). curl can fail after it has received a 200 status line (exit 8 or 18);
  `%{http_code}` still printed 200, so the loop counted such answers as `none status=200`. The kind
  `loop-status` came back, so this is FIXED BY A CUT, not another patch: the loop's several status
  paths (the first status line, a label, a branch for failures) are replaced by one strict rule. An
  answer is `clean` only if curl exited 0, the final status is 200 and none of the three headers is
  there; it is `header` if one is there on such an answer; anything else prints `other` with its
  status and curl's exit code and does not count.
- E4-2 RISK (Codex). "would be unlikely if they still came as often as we saw" assumes an independent,
  constant-rate sample. FIXED: the probability claim is removed. The text says 100 answers without the
  headers "are a count, not a proof" and gives what was seen (2 of 40 before the switch).
- E4-3 RISK (Codex). The parity test passed if `none` became `absent` or `seq 1 100` became
  `seq 1 1000`. FIXED: a test runs the loop as written (three requests, a local address for the
  placeholder) and asserts its complete output for six answers and a closed port; seven breakages of
  the loop in a scratch copy each fail it.
- E4-4 RISK (GLM). The `header` branch had no traced support. FIXED: the same test asserts
  `3 header` for a `report-to` answer and for a report-only answer.
- E4-5 RISK (GLM). "The placeholder cannot answer, so an unedited run prints `status=000`" rested on
  curl's behaviour and was untested. FIXED: the sentence now says the placeholder cannot answer
  because `.invalid` is reserved (RFC 6761) and that an unedited run prints `other` lines; a closed
  port is tested (`other status=000 exit=7`). The unedited placeholder itself is not run by the test
  (a resolver that rewrites unknown names would make that test flaky).
- E4-6 NIT (GLM). The awk labels were not pinned. FIXED by the same test.
- D3-7 (Codex, re-judged WRONG). "A failure is `status=000`" is false when curl fails after a
  status line. SUPERSEDED by E4-1: the loop reports curl's exit code.
- UNVERIFIABLE (GLM). "removes only the NEL and Report-To headers" claims what step 4's rule does.
  Step 4 (docs/CLOUDFLARE-CHECKLIST.md) has the owner enter the header names `NEL` and `Report-To`
  and no others.
- OUTSIDE SCOPE (Codex RISK, GLM NIT). The `monitorWhat` string presented the monitor's two other
  headers as universal. FIXED: "On the one site where this was seen it came with a report-to group,
  cf-csp-endpoint, at csp-reporting.cloudflare.com". The pages.dev reading guide does not say
  whether a `report-to:` line there could be the monitor's: a follow-up, unknown.
- NOT CHANGED, open: whether `curl -sI` (HEAD) shows the monitor on a zone that has it on; the
  zone's ruleset state when the 40 requests were made; the meaning of the Global badge.

</details>

<details><summary>Round 5</summary>


The author's record of what was done about each. It is a claim to check, not evidence. Round 5
(Codex, GLM 5.3) confirmed rounds 1 to 4 landed except where a row below re-opens one.

- E5-1 BUG (Codex). The reference said every `other` line carries its status, but a curl that fails
  before it writes anything (a real malformed-address probe produced `3 other exit=3` on one libcurl)
  leaves the status empty. FIXED: the awk starts from `status=none` and `exit=none`; the reference
  says "`none` where curl never got far enough to report one". A stand-in `curl` that exits 3
  without writing anything pins it (`3 other status=none exit=3`); a real rejected address is
  asserted as `status=000` or `status=none`, because curl versions differ on it.
- E5-2 BUG (Codex), NIT (GLM). Step 5 said an `other` line means "fix the address", which is the
  wrong remedy for a 503 or a body cut short. FIXED: step 5 reads the status and the exit code: a
  301 or 302 means use the address the site answers on (try `www.`); `status=000` or `status=none`
  means curl could not reach the address; any other status means the site itself answered badly;
  the owner tells the assistant if `other` lines stay that they cannot explain.
- E5-3 RISK (Codex). No fixture covered `reporting-endpoints`. FIXED: a case asserts `3 header`;
  removing that alternative from the awk fails the loop test.
- E5-4 RISK (GLM). The loop test is skipped on Windows unconditionally, although Git Bash can
  supply the tools. NOT CHANGED, for the owner to waive or reverse: the CI matrix runs this file on
  four Linux legs (Node 18, 20, 22, 24; `.github/workflows/clean.yml` job `cloudflare-check-tests`),
  where the loop test runs; the Windows leg is the only one that skips. Running it there would be an
  untested change on a platform not available here (quoting of a multi-line `-c` argument from Node
  to Git Bash, MSYS path handling for a stand-in `curl`). The loop's behaviour under Git Bash is
  therefore not verified; the checklist tells Windows owners to use Git Bash or WSL.
- UNVERIFIABLE (Codex, E4-5). The RFC 6761 reservation for `.invalid`. The sentence now cites
  section 6.4 ("Domain Name Reservation Considerations for 'invalid.'").
- OUTSIDE SCOPE, still open: the pages.dev reading guide does not say whether a `report-to:` line
  there could be the monitor's (unknown).
- NOT CHANGED, open: whether `curl -sI` (HEAD) shows the monitor on a zone that has it on; the
  zone's ruleset state when the 40 requests were made; the meaning of the Global badge.

</details>

<details><summary>Round 6</summary>


The author's record of what was done about each. It is a claim to check, not evidence. Round 6
(Codex, GLM 5.3) confirmed rounds 1 to 5 landed except where a row below re-opens one.

- E6-1 BUG (Codex). Step 5 listed 301 and 302 as redirects and called every other status "the site
  itself answered badly", so a 303, 307 or 308 (a successful redirect) sent owners toward the wrong
  diagnosis. FIXED BY A CUT, not by adding codes: the status-by-status list is removed. Step 5 says a
  status in the 300s is a redirect (use the address your site answers on, try `www.`) and sends every
  other `other` line to the assistant ("tell your assistant what it says").
- E6-2 RISK (GLM). The round 6 brief said four files and "the checker's fix text"; the diff had
  three files. NOT A CODE FINDING: the checker file had not changed since round 5. The brief was
  wrong; this round's brief names the files.
- E6-3 RISK (GLM). The test pinned `exit=3` for a rejected address on every curl the CI legs use.
  FIXED: the real-curl assertion is any non-zero exit; the exact `status=none exit=3` path is carried
  by the stand-in curl.
- E6-4 NIT (GLM). Step 5 named the exit code but every branch keyed on status, so a 200 with a
  non-zero exit (a body cut short) had no reading. FIXED with E6-1: such a line goes to the assistant.
- E6-5 UNVERIFIABLE (both seats). The citation "RFC 6761, section 6.4". CHECKED against the RFC: 6.4
  is "Domain Name Reservation Considerations for \"invalid.\"" (6.2 test, 6.3 localhost, 6.5 example).
- E5-4 (the Windows skip, a RISK from round 5), reversed at the owner's choice: the loop test now
  runs on the Windows leg. `findBash` accepts on Windows only a bash whose `uname -s` is MSYS or MINGW
  (not WSL's), tried from PATH and the two Git for Windows paths; the script is written to a file and
  run as `bash file` (no multi-line argument between Node and bash); the stand-in curls are shell
  functions (no PATH or file mode); the awk ignores a trailing carriage return, the one
  Windows-specific suspect; a body cut short is accepted as curl exit 18 or 56. Not run on Windows
  from here: the Windows CI leg is its test.
- NOT CHANGED, open: whether `curl -sI` (HEAD) shows the monitor on a zone that has it on; the
  zone's ruleset state when the 40 requests were made; the meaning of the Global badge; the pages.dev
  reading guide (does a `report-to:` line there belong to the monitor?).

</details>

<details><summary>Round 7</summary>


The author's record of what was done about each. It is a claim to check, not evidence. Round 7
(Codex, GLM 5.3) confirmed rounds 1 to 6 landed except where a row below re-opens one.

- E7-1 BUG (Codex), NIT (GLM). Step 5 said "a status in the 300s is a redirect", which includes 300
  (Multiple Choices) and 304 (Not Modified): neither is a redirect to another address, and the
  remedy "use the address your site answers on" does not fit them. FIXED BY A CUT, the third time
  this kind came back: the redirect guidance is removed from step 5. An `other` line now says "use
  the address your site answers on, as the reference says, or tell your assistant what the line
  says". No status is named, so none can be wrong. The reference's own sentence ("with `www.` if the
  bare name redirects") carries the hint.
- E7-2 RISK (Codex). A missing shell or tool made the loop test skip silently on CI, so a runner
  image change could remove the coverage while CI stayed green. FIXED: when CI is set (`CI` in the
  environment, as GitHub Actions sets it) and no usable bash is found, the test fails with a message;
  elsewhere it skips and says so. Checked three ways: bash present (runs and passes), CI set without
  bash (fails), CI unset without bash (skipped, message printed).
- E7-3 OUTSIDE SCOPE, BUG per Codex (unchanged line 282 of the checklist, "A 3xx status line means
  something else is redirecting your live domain"). REFUTED: that sentence is about the first
  command of section 5, a plain request that carries no conditional header, and a 304 is the answer to
  a conditional request only (RFC 9110, section 15.4.5: "The 304 (Not Modified) status code indicates
  that a conditional GET or HEAD request has been received and would have resulted in a 200 (OK)
  response if it were not for the fact that the condition evaluated to false." Read on 2026-10-14.)
  The same holds for the counting loop, which sends none. The line is not part of this change.
- UNVERIFIABLE (GLM). Whether another call of `loopOutput` still passes an env object as its second
  argument. CHECKED: all seven call sites pass the address, and the stand-in cases pass shell text.
- NOT ESTABLISHED, open: the loop test's first run on the Windows leg (the draft PR #313 runs it);
  whether `curl -sI` (HEAD) shows the monitor on a zone that has it on; the zone's ruleset state when
  the 40 requests were made; the meaning of the Global badge; the pages.dev reading guide.

</details>

<details><summary>Round 8, the final full read and the wording pass</summary>


The author's record of what was done about each. It is a claim to check, not evidence. Round 8
(Codex, GLM 5.3) found no BUG in scope; the final full read (Kimi) found no BUG.

Round 8:
- E8-1 RISK (Codex). That GitHub sets `CI` was not established, so a missing tool could still skip
  green. REFUTED with the documentation: GitHub's default environment variables table says
  "CI: Always set to `true`" (read 2026-10-14).
- E8-2 BUG outside this change (Codex), an unchanged sentence. "A 3xx status line means something
  else is redirecting your live domain" is wrong for a 300 (Multiple Choices). FIXED in prose: "means
  something else is answering for your live domain, usually a redirect".
- E8-3 RISK (GLM). The CI guard covers only a missing bash, not a missing tool. REFUTED by reading:
  `BASH` is set only when bash exists and the probe `command -v curl && command -v awk && command -v
  seq && command -v sort && command -v uniq` succeeds; a missing tool leaves `BASH` null and the test
  fails on CI.
- E8-4 NIT (GLM). The failure message could misreport the cause. REFUTED by the same reading: the
  condition and the message both say "a shell with those tools".
- E8-5 NIT (GLM). Step 5 offered the address remedy first for every `other` line. FIXED: it leads
  with "tell your assistant what the line says"; "The reference says which address to use."

Final full read (Kimi, the whole change):
- F-1 RISK. The closed-port case asserted `status=000` exactly, while the rejected-address case
  tolerates `status=000|none`; a Git Bash curl that writes no status for exit 7 would fail CI though
  the loop is right. FIXED: the closed-port case accepts `(000|none)` with exit 7. Evidence on the
  platform: the Windows CI leg ran the loop test in Git Bash on head 807171e (before this fix) and
  passed, 95 of 95, 0 skipped (the exact `status=000 exit=7` was accepted there).
- F-2 NIT. The comment above `MONITOR_PATH` said "the test at the end of this file". FIXED: it
  names the test.
- F-3 NIT. The reference's table row says the script "does not decide what a browser would do with
  a header" while the monitor's description said flatly that browsers send reports. FIXED: "Cloudflare
  says it adds ... and that visitors' browsers then send reports to Cloudflare".
- F-4 NIT. The awk default `e = "exit=none"` could never be used (`echo "exit=$?"` always runs).
  FIXED: removed; the status default stays and is pinned by a stand-in curl.
- F-5 UNVERIFIABLE. That the docs send a Windows owner to Git Bash. CHECKED: the checklist's section 5
  (unchanged) says "on Windows use Git Bash or WSL".
- NOT ESTABLISHED, open: whether `curl -sI` (HEAD) shows the monitor on a zone that has it on; the
  zone's ruleset state when the 40 requests were made; the meaning of the Global badge; whether a
  `report-to:` line on the pages.dev address could be the monitor's.

</details>

<details><summary>Confirmation</summary>


The author's record of what was done. It is a claim to check, not evidence.

- W-1 BUG (Codex, wording pass), on the unchanged sentence of section 5 about a 3xx status line. "A 3xx
  status line means something else is answering for your live domain, usually a redirect" still
  misdirects: the intended origin can answer with a 3xx too. FIXED: the sentence now makes no claim
  about who answers: "A 3xx status line is not the 200 you want: find out what answers with it, and
  why, before you trust the rest."

</details>
