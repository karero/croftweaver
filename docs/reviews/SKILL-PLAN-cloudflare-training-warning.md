# Plan: warn before a Cloudflare Training setting shuts out Google and Bing

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-29 | this file |
| 2 | PLAN gate (High: the setup script configures the owner's zone, the review skill's "deploy or infra" row) | ✅ clean 2026-10-29: 9 rounds, the final full read and the wording pass | Review trail, below |
| 3 | Capture: the bot settings a real zone returns for each choice (C1–C9 below), by the maintainer on a spare zone | ✅ 2026-10-30: C1–C9 and C5b, plus C10–C12 (Search: Block on pages with ads; Agent: Block; back to Allow); the stop rule checked by hand, every capture fits its scenarios | captures outside every repository, 13 reads |
| 4 | Build, one PR: the captures as fixtures (with the tooling changes under "Fixtures"), the script's notes and their tests, the prose, a release-note row, two BUGLOG rows | ⬜ | — |

No red team: the change adds lines the script prints and words in the skills. It writes no new
setting and touches no login, data, money or deletion.

## Why

Cloudflare's blog of 15 September 2026, "Have it both ways: stay discoverable in search while
disallowing AI training" (https://blog.cloudflare.com/accountable-mixed-use-ai-crawlers/, read
2026-10-29):

- "Block and Block on pages with ads now apply to mixed-use crawlers, including Applebot,
  Bingbot, and Googlebot, so either setting impacts search as well as training."
- "To stop training and keep search, use Disallow AI Training". With it, "Bot Preference Sync
  publishes the applicable no-training preference in robots.txt. Accountable mixed-use
  crawlers remain allowed for search. Every other training crawler is blocked".
- Bing does not read that preference yet: "Until that support launches, selecting Disallow AI
  Training will not automatically convey a no-training preference to Bing through robots.txt";
  Microsoft's support is "targeted for early 2027", and Bing's `NOARCHIVE` tag works today.

So an owner who picks **Block** on Training to refuse AI training also keeps Google's, Bing's
and Apple's crawlers out, which Cloudflare says impacts search. Nothing tells them. The kit's
words don't either: `docs/CLOUDFLARE-CHECKLIST.md` section 4 and `search-console-setup` say a
Training block also blocks crawlers that combine search and training, without naming Google or
Bing; `cloudflare-check.mjs` says "Bot Preference Sync Off unless you block Training" and, when
an AI crawler is refused, "If you chose to block Training that is expected"; none names
**Disallow AI Training**. `ai-seo` Step 4 calls training "a separate choice".
`cloudflare-setup.mjs` reads the bot settings and says nothing about what they do.

## What is known, and what the capture must show

Known from the second trial (14 October 2026,
`skills/new-website/scripts/tests/fixtures/cloudflare-api/`): the kit's reads show
`"disabled"` in `ai_search`, `ai_user` and `ai_training` (T1-013, T2-040), which the kit takes
for Allow (C4, C8 and C9 settle that it is the dashboard's Allow); the API accepts
`ai_training: "disallow"` (T2-061, T2-062), also with Bot Preference Sync off (T2-063, T2-064).
Sync was already on before that PUT (T2-040, T2-060), so whether choosing Disallow turns it on
is not known. One zone read `ai_bots_protection: "block"` with `ai_training: "disallow"` and Sync
off (T2-016). No read shows a Block value for `ai_training`, `ai_search` or `ai_user`. T2-059
sent `ai_training: "block"` and was refused, but it also sent `is_robots_txt_managed: true`,
the cause the stub models (T2-065 is refused the same way with `"disallow"`), so it says
nothing about Block. The existing test 13 uses that made-up value.

Not known, and the build waits for it (code that reads another program's output is tested on a real capture first): which values each dashboard choice
gives, in which fields. On a **spare zone that serves no live site**, with one proxied host
that serves a known robots.txt of its own (a throwaway Pages project with the starter's
file), the maintainer makes each change in the dashboard (Security → Settings → Bot traffic →
Configure AI bot policies), and after each one the trial helper (the one recorded in
`trial-helper.txt`) reads `GET /zones/<id>/bot_management`, so the captures come out in the
format `clean-captures.mjs` reads. Each capture is compared field by field with the one before.
**One stop rule:** before any code is written, each capture is run, by hand, through the
scenarios that cite it: Block (C2) must call for S1's note, Block on pages with ads (C3) for
S2's, Disallow with Sync on (C5 or C5b) for none under S9b, Disallow with Sync off (C6) for
S7's, Search and Agent (C7, C8) for S8's, and Allow (C4, C9) for none. If the values a capture
holds cannot give its scenario's result without breaking another's, the build stops for the
plan to be amended and re-reviewed. The scenario tests then hold the same facts in code.

| Capture | Change | Also saved |
|---|---|---|
| C1 | none: the zone as it is | the dashboard's exact labels for every choice of Search, Agent and Training, and whether the older Block AI bots switch shows |
| C2 | Training: Block | the robots.txt the host serves |
| C3 | Training: Block on pages with ads | |
| C4 | Training: Allow; Bot Preference Sync: off | the robots.txt the host serves |
| C5 | Training: Disallow AI Training | whether Sync turned on by itself; the robots.txt the host serves |
| C5b | only if Sync is still off at C5: Bot Preference Sync on | the robots.txt the host serves |
| C6 | Bot Preference Sync: off, Training left on Disallow | the robots.txt the host serves |
| C7 | Training: Allow; Search: Block | |
| C8 | Search: Allow; Agent: Block on pages with ads | |
| C9 | Agent: Allow (everything back to the kit's settings) | |

The captures stay outside every repository, like the two trials'.

## Scenarios

Lena's bakery (`lenas-backstube`) is the made-up site the fixtures already use. "The ask" is
the run that prints the numbered list and a code; "the report" is the run that prints what is
done, after `--confirm` or when there is nothing to change.

**The fields watched** are `ai_training`, `ai_search`, `ai_user` (Agent) and
`ai_bots_protection` (the older Block AI bots). No other field of the bot object gets a note
(`cf_robots_variant`, `enable_js`, `crawler_protection`, `content_bots_protection`; Sync only as
S7 says). **Which values:** the values read at the start of the run (before any PUT), in every
state. **Known values** are per field: a value counts as known for a field only if a capture
showed it in that field; anything else is S10.

| # | Given | When | Then |
|---|---|---|---|
| S1 | Training is Block (C2) | the ask, `ai` line in (state `change`) | a note: Training is set to Block; Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search; the yes sets it to Allow. To refuse training and stay in search, choose Disallow AI Training in the dashboard (and turn Bot Preference Sync on, unless C5 shows it turns on by itself) and run with `--skip ai` |
| S2 | Training is Block on pages with ads (C3) | the same | the same note, for pages that show ads |
| S3 | Training was Block, Block on pages with ads or Disallow AI Training | the report, `ai` line `done` | one past-tense line: Training was that value and is now Allow; to refuse training and stay in search, the S1 advice |
| S4 | Training is Block or Block on pages with ads | `ai` line `skipped`, in the ask or the report | the S1 note, with "this run leaves it as it is" in place of "the yes sets it to Allow" |
| S5a | Training is Block, Block on pages with ads or Disallow AI Training | `ai` line `unread` with values: the records could not be read, so nothing was written | the S4 note (for Disallow, S6's advice to keep it with `--skip ai`): the value is still there and this run did not change it |
| S5b | any watched field was not `"disabled"` | `ai` line `hand`, however it came about (any unsuccessful answer to the PUT, a 5xx included; an accepted PUT whose read-back failed or differed) | one line per such field, and no claim about any value now: "<label> read <value> before this run; Cloudflare did not confirm the change, so look at it in the dashboard" and the path; where Training read Block or Block on pages with ads, S1's advice follows |
| S6 | Training is Disallow AI Training (C5) | the ask, `ai` line in | a note: the yes sets Training to Allow and lets training crawlers in; `--skip ai` keeps the owner's choice |
| S7 | Training is Disallow AI Training with Sync off (C6) | `ai` line `skipped`, or `unread` with values, ask or report | a note: with Bot Preference Sync off, the no-training preference is not written into robots.txt |
| S8 | Search or Agent holds a non-Allow value a capture showed for that field (C7, C8), or `ai_bots_protection` is `"block"` | `ai` line `skipped`, or `unread` with values | one note per field: its dashboard label (for `ai_bots_protection`, "the older Block AI bots setting", or "no longer shown in the dashboard" if C1 says so), its value, and checklist section 4. With the `ai` line `change` (the ask) or `done` (the report), the list or the report already shows the change, so no note |
| S9 | every watched field is `"disabled"` (C9, T2-040) | any run | no note |
| S9b | Training is Disallow AI Training with Sync on (C5, or C5b if C5 left Sync off), the state S1's advice leads to | `ai` line `skipped`, any run | no note |
| S10 | a watched field holds a value no capture showed, or is missing | any run with values | one note naming the field and value (or "missing") and saying the kit does not know it. It replaces S1–S8's note for that field: never a guess, never silence |

When the bot read is refused there are no values and no note: the `ai` line then prints "by
hand" when it is in, and "stays as it is (it could not be read)" when it is skipped, as today.
Notes use the labels C1 records. They never call Googlebot or Bingbot training crawlers:
Cloudflare's word is "mixed-use".

## Design

- **Script:** one exported function in `cloudflare-setup.mjs` takes the `ai` line's `now`
  (which holds Sync too) and its state, and returns the notes, comparing values literally against those the
  captures showed. The ask prints them after `reportQuiet` and before the build-failed line;
  the report prints them after `reportQuiet(…, { done: true })` and before the connection
  lines. They change no setting, no question code and no exit code. Launch day reads no bot
  settings and gets no notes (a BUGLOG row).
- **Prose, the same facts everywhere:** checklist section 4 and its section 6 sentence on
  blocking Training on purpose; `skills/search-console-setup/SKILL.md` ("Also in the Cloudflare
  dashboard"); `skills/ai-seo/SKILL.md` Step 4 and its Common Mistakes line on blocking the
  training bots; `skills/new-website/references/CLOUDFLARE_CHECK.md` ("blocking Training may be
  your choice"); `cloudflare-check.mjs`'s `lookFor`, `aiHand` and refusal line: one line for
  any refusal, as today, which says a Training choice is one possible cause, that under Block
  Google and Bing are out too, and that any other refusal or server error still needs a look;
  `skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`, which also tells the assistant to
  pass the notes on in the report, not only in the ask. Each names Googlebot, Bingbot and Applebot, names
  Disallow AI Training as the setting that refuses training and keeps search, says Bot
  Preference Sync is what writes the preference into robots.txt, says what C5's robots.txt
  holds (for example whether it names `Google-Extended`, which `ai-seo` says is the owner's
  separate choice), and says Bing does not read it yet (`NOARCHIVE` is Bing's own tool). The
  checklist's and `search-console-setup`'s sentence on new domains' defaults is rewritten from
  the blog and C1, which may differ from what they say today. Allow stays the kit's default;
  training stays the owner's call.
- **Fixtures:** the tooling takes two trials today. The build adds a third, T3, in
  `clean-captures.mjs`: its usage line and the folder list (`dirs`); a T3 batch in `SELECTION`,
  after the two, so no existing made-up id moves; the loop over trials, which names T1 and T2
  and must take a batch that has no T3 key (`selection[trial] ?? []`);
  the helper check, which looks for T1 and T2 names; a `T3` key in the private map. In
  `cloudflare-setup.test.mjs`, both patterns widened to T1–T3: `MADE_UP` (the `capture` value)
  and the file-name pattern. Each new value goes into `allowed-values.json` after looking at it.
  The fixtures README, the stub and `clean-captures.mjs`'s header comments say "three trials",
  and the README's claims table gets a row.
- **Rows:** one "Next release notes" row; BUGLOG rows for launch day and for Cloudflare retiring
  Managed robots.txt (the script's `is_robots_txt_managed` handling). The open row of 2026-10-11
  on `search-console-setup`'s dashboard names, which C1 settles, is closed.

## Tests

In `tests/cloudflare-setup.test.mjs`, through the stub built from the T3 fixtures and the
run entry the suite already uses: one test per scenario S1–S10 (S5 and S9 as below), each asserting the note's lines
and that the PUT body, the question code and the exit code are what they would be without the
note. Baselines are named, not assumed:

- S9: runs against C9's bot object and against T2-040's print no line holding any note's
  opening words; the existing tests on T2-040 pass unchanged; the exported function returns no
  notes for either object.
- S4: the code equals the code of the same zone with `ai_training: "disabled"`, since a skipped
  line's value is not in the code.
- One test swaps C2's Block value for C9's Allow and sees the note go, so the check cannot pass
  vacuously.
- Test 13's made-up `ai_training: "block"` becomes C2's captured value; its `enable_js` and
  `crawler_protection` values stay, as they are not watched.

In `tests/cloudflare-check.test.mjs`, in the shape of its existing refusal tests (`withSite`
and a user-agent match): a refused GPTBot and a 503 for OAI-SearchBot each print the one new
refusal line. In `tests/cloudflare-setup.test.mjs`, S5a gets a test with an unread record list; S5b gets
four, each starting from C2's Block and asserting the line names the value read before the run
and says Cloudflare did not confirm: a refused PUT, a 502 to the PUT, an accepted PUT whose
read-back fails, and test 13b's read-back that differs. S9b gets a test with the capture that reads
`ai_training: "disallow"` and Sync on (C5 or C5b), the `ai` line skipped. The fixture test checks every new file for real names.

## Not covered

- Launch day (see Design).
- The starter's pages get no `noarchive` tag; the prose names it as Bing's own tool.

## Review trail

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex at High; melious out of balance, no rerun owed; fresh-eyes on the host's model) | Codex: 1 BUG (the fixture tooling takes two trials only), 2 RISK (the check script's refusal line; "leaves search" overstated). Fresh-eyes: 3 BUG (the confirmed run would warn about a value it had just changed; the ask's list is not printed when nothing else changes; the T3 tooling, as Codex), 9 RISK (the older `ai_bots_protection`; Search and Agent not captured; values may sit in other fields; the Sync claim and C4's order; three more prose places; launch day; what Disallow writes into robots.txt; unnamed test baselines; a missing field), 6 NIT | taken: notes keyed to the `ai` line's end state and printed in the ask and in the report; a Fixtures task list; C1–C9 with Sync off before Disallow, Search and Agent, robots.txt saved, whole objects compared; S8, S10; prose places added; launch day a BUGLOG row; baselines named; wording follows Cloudflare's "impacts search" |
| 2 (as round 1) | Codex: 3 BUG (`MADE_UP` also names T1/T2; S9's baseline compared two different objects; a refused read with `--skip ai` prints another line), 1 RISK (the refusal line would excuse a server error). Fresh-eyes: 5 RISK (no rule for `hand` and `unread` with values, nor which read the report uses; the watched fields not named, S8 and S10 overlapping; S9's baseline; S7's unsupported "still blocked"; the T3 list short), 10 NIT (this table's row had landed in the capture table; two prose places; S6 in the report; where in each run the notes print; the capture host's own robots.txt; C2's robots.txt; S1's Sync advice; S8's label for the older switch; test 13's other values; "What is known" wording) | all taken: the watched fields and the values used named above the scenarios; S3 covers Disallow too; S5 for `hand` and `unread`; S10 wins over S1–S8; S7's parenthesis cut; S9's baseline rewritten; the full T3 list; the refused-read lines; the check script's tests; the two prose places; print positions fixed; capture host and C2 robots.txt |
| 3 (Codex at High; melious out of balance; fresh-eyes on the host's model) | Codex: 1 BUG (S5: a `hand` line does not mean the value is unchanged; an accepted PUT can read back with another field differing), 1 RISK (Disallow under `hand` or `unread` had no note). Fresh-eyes: 1 RISK (the same S5 case, a silent wrong result), 6 NIT (T2-059's refusal had another cause; S8's "`ai` line in"; the function's inputs; the refusal line's form and its tests; `clean-captures.mjs`'s comments; row 2's NIT count) | all taken: S5 split into S5a (nothing written, or refused), S5b (built from the read-back) and S5c (no value claim), Disallow included, each with a test; the rest as named |
| 4 (Codex at High, earned by round 3's BUG; melious out of balance) | Codex: 1 RISK (S5a's "refused PUT": the script counts any unsuccessful answer, a 502 after an applied write included, as refused, so "the value is still there" is unproven) | taken: a `hand` line with no read-back makes no claim about the value now (S5c), with tests for a refused PUT and a 502; S5a keeps only the case where nothing was written |
| 5 (Codex at High, earned by round 4's RISK; melious out of balance) | none | clean |
| final full read (a new reader on the host's model, whole plan) | 4 RISK (S5b's test could pass with no note code; S5b and S5c claimed values for Search, Agent and the older switch, and S5b had no wording; the state S1's advice leads to had no scenario; no rule for captures that do not fit), 9 NIT (the rule's name; which captures settle Allow; known values per field; S7 under `unread`; S5b against S3; Applebot in the prose; the open BUGLOG row C1 settles; new-domain defaults; the trial loop's missing T3 key) | taken. Cut, as the unconfirmed-write kind earned rounds 4 and 5 too: the read-back case is removed, and every `hand` line gets one strict line that names the values read before the run and claims nothing about now; S9b added; a stop rule for captures that do not fit; the NITs as named |
| 6 (Codex at High, earned by the full read's RISKs; cut: the read-back case; melious out of balance) | 2 RISK (the stop rule also caught the Sync changes the captures study; S9b's fixture could be Disallow with Sync off) | cut again, as both kinds earned round 6: the stop rule is one strict condition (C2 and C3 must differ in a watched field), other surprises being S10 notes; C5b captures Sync on when C5 left it off, and S9b uses the capture that reads Disallow with Sync on |
| 7 (Codex at High, earned by round 6's RISKs; cut: the stop rule and S9b's fixture; melious out of balance) | 1 RISK (the stop rule missed a Block that reads like Allow) | cut: the stop rule compares every pair of choices whose notes differ, in all the note function takes |
| 8 (Codex at High, earned by round 7's RISK; cut: the pairwise stop rule; melious out of balance) | 1 RISK (the pairwise rule still passes a Block that reads like Allow apart from Sync) | cut after the last round the owner's go covers: the separate rule is gone; each capture must give the result of the scenarios that cite it, checked before any code. Not re-reviewed: round 9 needs the owner's OK |
| 9 (Codex at High, on the owner's OK past round 8, earned by round 8's RISK; cut: the separate stop rule; melious out of balance) | none | clean: each capture is checked by hand against the scenarios that cite it before any code |
| wording pass (Codex, the delta since round 9: its trail row) | none | clean; the gate closes |
