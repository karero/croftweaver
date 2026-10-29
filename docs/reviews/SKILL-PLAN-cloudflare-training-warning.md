# Plan: warn before a Cloudflare Training setting shuts out Google and Bing

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-29 | this file |
| 2 | PLAN gate (High: the setup script configures the owner's zone, the review skill's "deploy or infra" row) | ⬜ | — |
| 3 | Capture: the bot settings a real zone returns for each Training choice (C1–C6 below), by the maintainer on a spare zone | ⬜ | — |
| 4 | Build, one PR: the captures as fixtures, the script's warnings and their tests, the prose in four places, a release-note row | ⬜ | — |

No red team: the change adds lines the script prints and words in the skills. It writes no new
setting and touches no login, data, money or deletion.

## Why

Cloudflare's blog of 15 September 2026, "Have it both ways: stay discoverable in search while
disallowing AI training" (https://blog.cloudflare.com/accountable-mixed-use-ai-crawlers/, read
2026-10-29):

- "Block and 'Block on pages with ads' now apply to mixed-use crawlers, including Applebot,
  Bingbot, and Googlebot, so either setting impacts search as well as training."
- "To stop training and keep search, use Disallow AI Training". With it, "Bot Preference Sync
  publishes the applicable no-training preference in robots.txt. Accountable mixed-use
  crawlers remain allowed for search. Every other training crawler is blocked".
- Bing does not read that preference yet: "Until that support launches, selecting Disallow AI
  Training will not automatically convey a no-training preference to Bing through robots.txt";
  Microsoft's support is "targeted for early 2027", and Bing's `NOARCHIVE` tag works today.

So an owner who picks **Block** on Training to refuse AI training also stops Google, Bing and
Apple from crawling the site. The failure is silent: the site just drops out of search. The kit
never says this. `docs/CLOUDFLARE-CHECKLIST.md` section 4 and `search-console-setup` say a
Training block also blocks crawlers that combine search and training, without naming Google
or Bing; `cloudflare-check.mjs` says only "Bot Preference Sync Off unless you block Training";
none names **Disallow AI Training**. `ai-seo`
Step 4 calls training "a separate choice". `cloudflare-setup.mjs` reads the bot settings
(its `ai` line) but says nothing about what a Training block does.

## What is known, and what the capture must show

Known from the second trial's captures (14 October 2026, `tests/fixtures/cloudflare-api/`):
the field is `ai_training`; the kit's Allow is `"disabled"`; the API accepts `"disallow"`
(T2-061), and after that PUT the answer showed `bot_preference_sync_enabled: true`, though the
PUT had not sent it (T2-061, T2-062). One zone read `ai_bots_protection: "block"` with
`ai_training: "disallow"` (T2-016).

Not known, and the build waits for it (global rule 5): which `ai_training` value each dashboard
choice gives, so the warning compares against real values. On a **spare zone that serves no
live site**, the maintainer sets each choice in the dashboard (Security → Settings → Bot
traffic → Configure AI bot policies → Training) and reads `GET /zones/<id>/bot_management`
after each:

| Capture | Training set to | Also noted |
|---|---|---|
| C1 | as the zone is now | the dashboard's exact labels for the Training choices |
| C2 | Block | |
| C3 | Block on pages with ads | |
| C4 | Disallow AI Training | whether `bot_preference_sync_enabled` turned on by itself |
| C5 | Disallow AI Training, then Bot Preference Sync switched off | |
| C6 | Allow (the kit's setting), as cleanup | |

The captures stay outside every repository. `clean-captures.mjs` makes the fixtures from them,
as it does for the two trials, under a third trial name (T3); the fixture test then checks them
for real names.

## Scenarios

Lena's bakery (`lenas-backstube`) is the made-up site the fixtures already use.

| # | Given | When | Then |
|---|---|---|---|
| S1 | Training is Block (C2) | `setup` runs with the `ai` line in | the list shows the `ai` change as today, plus a warning: Block also stops Googlebot, Bingbot and Applebot crawling, so the site leaves Google, Bing and Apple search; to refuse training and stay in search, choose Disallow AI Training in the dashboard and run with `--skip ai` |
| S2 | Training is Block on pages with ads (C3) | `setup` runs with the `ai` line in | the same warning, saying it applies to pages that show ads |
| S3 | Training is Block or Block on pages with ads | `setup` runs with `--skip ai` | the same warning is printed, and the run still ends as today (exit code unchanged) |
| S4 | Training is Disallow AI Training (C4) | `setup` runs with the `ai` line in | the list says this change lets training crawlers in, and that `--skip ai` keeps the owner's choice |
| S5 | Training is Disallow AI Training with Sync off (C5) | `setup` runs with `--skip ai` | a note: with Bot Preference Sync off, the no-training preference is not written into robots.txt |
| S6 | Training is Allow (C6) | `setup` runs either way | no warning and no note: the output is as today |
| S7 | Training holds a value none of C1–C6 showed | `setup` runs | one line names the value and says the kit does not know it; never a guess, never silence |

The warning never calls Googlebot or Bingbot a training crawler: Cloudflare's word is
"mixed-use". Bing's case is said once: Disallow AI Training does not reach Bing yet
(Cloudflare's words: targeted for early 2027).

## Design

- **Script:** after the bot read in `cloudflare-setup.mjs` (the `BOT_LINES` loop), one check on
  `ai_training` against the captured values, compared literally. It adds lines to the printed
  list. It changes no setting, no question code, and no exit code. The warning and the note
  print in the run that asks and again in the run with `--confirm`, so an owner who said yes
  without reading sees them once more.
- **Prose, same facts in four places:** `docs/CLOUDFLARE-CHECKLIST.md` section 4,
  `skills/search-console-setup/SKILL.md` ("Also in the Cloudflare dashboard"),
  `skills/ai-seo/SKILL.md` Step 4, and the `lookFor` and hand-check text of
  `cloudflare-check.mjs`. Each names Googlebot and Bingbot, names Disallow AI Training as the
  setting that refuses training and keeps search, says it needs Bot Preference Sync on, and
  says Bing does not read it yet. Allow stays the kit's default; training stays the owner's
  call.
- **Release note:** one BUGLOG "Next release notes" row.

## Tests

In `tests/cloudflare-setup.test.mjs`, through the stub built from the T3 fixtures and the same
entry the tests already use for a run: one test per scenario S1–S7, each asserting the printed
lines and that the setting, code and exit code are as before. S6 also asserts the output
equals today's for the same zone, so the check cannot add noise. One test replaces the Block
value with C6's and sees the warning go: a guard that cannot fail is the thing to avoid. The
existing fixture test checks the new files for real names.

## Not covered

- `ai_bots_protection` (the older Block AI bots switch, which Cloudflare is retiring and
  migrating): the `ai` line already sets it to `"disabled"`. Whether a leftover `"block"` there
  also stops Googlebot is not stated; a BUGLOG row records it.
- Cloudflare's note that Managed robots.txt is being retired in favour of Bot Preference Sync
  touches the script's `is_robots_txt_managed` handling: a BUGLOG row, not this change.
- Bing's interim tool (`noarchive`): the prose names it as the owner's option; the starter is
  not changed.

## Review trail

| Round | Findings | Disposition |
|---|---|---|
