# Plan: warn before a Cloudflare Training setting shuts out Google and Bing

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-29 | this file |
| 2 | PLAN gate (High: the setup script configures the owner's zone, the review skill's "deploy or infra" row) | ⬜ | — |
| 3 | Capture: the bot settings a real zone returns for each choice (C1–C9 below), by the maintainer on a spare zone | ⬜ | — |
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
`skills/new-website/scripts/tests/fixtures/cloudflare-api/`): Allow is `"disabled"` in
`ai_search`, `ai_user` and `ai_training` (T1-013, T2-040); the API accepts
`ai_training: "disallow"` (T2-061, T2-062), also with Bot Preference Sync off (T2-063, T2-064).
Sync was already on before that PUT (T2-040, T2-060), so whether choosing Disallow turns it on
is not known. One zone read `ai_bots_protection: "block"` with `ai_training: "disallow"` and Sync
off (T2-016). No capture shows any Block value: the existing test 13 uses a made-up `"block"`.

Not known, and the build waits for it (global rule 5): which values each dashboard choice
gives, in which fields. On a **spare zone that serves no live site** and has one proxied host,
the maintainer makes each change in the dashboard (Security → Settings → Bot traffic →
Configure AI bot policies), and after each one the trial helper (the one recorded in
`trial-helper.txt`) reads `GET /zones/<id>/bot_management`, so the captures come out in the
format `clean-captures.mjs` reads. Each capture is compared field by field with the one before.

| Capture | Change | Also saved |
|---|---|---|
| 1 (Codex at High; melious out of balance, no rerun owed; fresh-eyes on the host's model) | Codex: 1 BUG (the fixture tooling takes two trials only), 2 RISK (the check script's refusal line; "leaves search" overstated). Fresh-eyes: 3 BUG (the confirmed run would warn about a value it had just changed; the asking list is not printed when nothing else changes; the T3 tooling, as Codex), 9 RISK (the older `ai_bots_protection`; Search and Agent not captured; values may sit in other fields; the Sync claim and C4's order; three more prose places; launch day; what Disallow writes into robots.txt; unnamed test baselines; a missing field), 6 NIT | all taken: notes keyed to the `ai` line's end state and printed in the ask and in the report (S1–S5); a Fixtures task list; C1–C9 with Sync off before Disallow, Search and Agent, robots.txt saved, whole objects compared; S8, S10; prose places added; launch day a BUGLOG row; baselines named; wording follows Cloudflare's "impacts search" |
| C1 | none: the zone as it is | the dashboard's exact labels for every choice of Search, Agent and Training, and whether the older Block AI bots switch shows |
| C2 | Training: Block | |
| C3 | Training: Block on pages with ads | |
| C4 | Training: Allow; Bot Preference Sync: off | the robots.txt the host serves |
| C5 | Training: Disallow AI Training | whether Sync turned on by itself; the robots.txt the host serves |
| C6 | Bot Preference Sync: off, Training left on Disallow | the robots.txt the host serves |
| C7 | Training: Allow; Search: Block | |
| C8 | Search: Allow; Agent: Block on pages with ads | |
| C9 | Agent: Allow (everything back to the kit's settings) | |

The captures stay outside every repository, like the two trials'.

## Scenarios

Lena's bakery (`lenas-backstube`) is the made-up site the fixtures already use. "The ask" is
the run that prints the numbered list and a code; "the report" is the run that prints what is
done, after `--confirm` or when there is nothing to change.

| # | Given | When | Then |
|---|---|---|---|
| S1 | Training is Block (C2) | the ask, `ai` line in | after the list, a note: Training is set to Block; Cloudflare says Block also keeps Googlebot, Bingbot and Applebot out, which affects search; the yes sets it to Allow. To refuse training and stay in search, choose Disallow AI Training in the dashboard and run with `--skip ai` |
| S2 | Training is Block on pages with ads (C3) | the ask, `ai` line in | the same note, for pages that show ads |
| S3 | Training was Block or Block on pages with ads | the report after the yes (`ai` line done) | one past-tense line: Training was that value and is now Allow; to refuse training and stay in search, the same advice |
| S4 | Training is Block or Block on pages with ads | `--skip ai`, with something else to change: the ask | the S1 note, with "the yes leaves it as it is" in place of "the yes sets it to Allow" |
| S5 | the same | `--skip ai`, nothing else to change: the report | the same note after the report |
| S6 | Training is Disallow AI Training (C5) | the ask, `ai` line in | a note: the yes sets Training to Allow and lets training crawlers in; `--skip ai` keeps the owner's choice |
| S7 | Training is Disallow AI Training with Sync off (C6) | `--skip ai`, ask or report | a note: with Bot Preference Sync off the no-training preference is not written into robots.txt (training-only crawlers are still blocked) |
| S8 | Search or Agent is not Allow (C7, C8), or the older `ai_bots_protection` is not `"disabled"` | `--skip ai`, ask or report | one note per field, naming its dashboard label and value and pointing to checklist section 4; with the `ai` line in, the list already shows the change |
| S9 | everything is Allow (C9) | any run | no note: the output is the same as today's |
| S10 | a field holds a value no capture showed, or `ai_training` is missing | any run | one note naming the field and value (or "missing") and saying the kit does not know it; never a guess, never silence |

When the bot read is refused, the script already prints its "by hand" line for `bot` and
`ai`; it adds no note, since it has no values. Notes use the labels C1 records. They never call
Googlebot or Bingbot training crawlers: Cloudflare's word is "mixed-use".

## Design

- **Script:** one function in `cloudflare-setup.mjs` takes the bot object read and the `ai`
  line's state, and returns the notes, comparing values literally against those the captures
  showed. The ask prints them after the numbered list; the report prints them after its last
  line (`reportQuiet(…, { done: true })`). They change no setting, no question code and no exit
  code. Launch day reads no bot settings and gets no notes (a BUGLOG row).
- **Prose, the same facts everywhere:** checklist section 4 and its section 6 sentence on
  blocking Training on purpose; `skills/search-console-setup/SKILL.md` ("Also in the Cloudflare
  dashboard"); `skills/ai-seo/SKILL.md` Step 4; `cloudflare-check.mjs`'s `lookFor`, `aiHand`
  and refusal line (a refused crawler under Disallow AI Training is expected; under Block,
  Google and Bing are out too); `skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`,
  which also tells the assistant to pass the notes on in the report, not only in the ask. Each
  names Googlebot and Bingbot, names Disallow AI Training as the setting that refuses training
  and keeps search, says Bot Preference Sync is what writes the preference into robots.txt,
  says what C5's robots.txt holds (for example whether it names `Google-Extended`, which
  `ai-seo` says is the owner's separate choice), and says Bing does not read it yet
  (`NOARCHIVE` is Bing's own tool). Allow stays the kit's default; training stays the owner's
  call.
- **Fixtures:** the tooling takes two trials today. The build adds a third: a third folder
  argument and a T3 batch in `clean-captures.mjs`'s `SELECTION` (after the two, so no existing
  made-up id moves) and a `T3` key in the private map; the file-name pattern in
  `cloudflare-setup.test.mjs` widened to T1–T3; each new value added to `allowed-values.json`
  after looking at it; a row in the fixtures README's claims table.
- **Rows:** one "Next release notes" row; BUGLOG rows for launch day and for Cloudflare retiring
  Managed robots.txt (the script's `is_robots_txt_managed` handling).

## Tests

In `tests/cloudflare-setup.test.mjs`, through the stub built from the T3 fixtures and the
run entry the suite already uses: one test per scenario S1–S10, each asserting the note's lines
and that the PUT body, the question code and the exit code are what they would be without the
note. Baselines are named, not assumed:

- S9: the output is identical to the same run against T2-040's bot object, which the suite's
  `freshState` already uses.
- S4: the code equals the code of the same zone with `ai_training: "disabled"`, since a skipped
  line's value is not in the code.
- One test swaps C2's Block value for C9's Allow and sees the note go, so the check cannot pass
  vacuously.
- Test 13's made-up `ai_training: "block"` becomes C2's captured value.

The fixture test checks every new file for real names.

## Not covered

- Launch day (see Design).
- The starter's pages get no `noarchive` tag; the prose names it as Bing's own tool.

## Review trail

| Round | Findings | Disposition |
|---|---|---|
