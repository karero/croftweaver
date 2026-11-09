# Plan: the launch check reads the Cloudflare zone settings

Written 2026-11-09 for the maintainer's go. One item in `website-launch-check`: the owner reads
five places in the Cloudflare dashboard, and the report records what they showed.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan, with every dashboard path read on a real zone | ✅ written 2026-11-09; the Account API tokens list read in round 2 | this file, "Seen in the dashboard" |
| 2 | PLAN gate (Normal: a SKILL.md and an owner-facing checklist) | 🔄 4 rounds, 30 findings (8 BUG), none open | "Review trail" below |
| 3 | Build: launch check description, run table, §3 and §8, the report template, the checklist's sections 4 and 5, new-website's lines 54 and 349 (one PR) | ⬜ | — |
| 4 | DIFF gate (Normal) | ⬜ | — |

## Why

The setup script (`skills/new-website/scripts/cloudflare-setup.mjs`) sets Bot Fight Mode off and
the AI crawler policies to Allow, and refuses a token whose end date is more than eight days away
(`MAX_TOKEN_MS`, line 28: the dashboard sets an end date, so "a week at most" can end late on day
7). Its `launch` stage reads the AI policy fields again (`readAiNow`) and notes them in its
report. Nothing reads Bot Fight Mode after setup, nothing reads the security rules or the
per-crawler switches, and nothing asks whether the token was deleted; an owner who sets the site
up by hand gets no read at all. The outside check says it "cannot see" the settings
themselves (`skills/new-website/references/CLOUDFLARE_CHECK.md`, "What it cannot see").
`website-launch-check` never mentions Cloudflare, and no kit file mentions security rules or IP
access rules.

The case behind it: the toolkit's own guide site launched on 2026-11-09, and its launch row closed
without anyone reading the zone. Two IP access rules that apply to every website in the account
are on it and still unread. An account-wide rule made for one site reaches every site in the
account, so a new site can launch behind a rule nobody on it chose.

## Seen in the dashboard

Read on 2026-11-09 on webcroft.dev, a free-plan zone, in the maintainer's signed-in browser.
Nothing was changed: the one panel opened was closed with Cancel. No captures are committed: the
pages show the account's own addresses and token names.

1. **Bot Fight Mode:** Your domain → Security → Settings. The page groups its settings; the
   **Bot traffic** group lists **Bot fight mode** with a switch in the Status column (off on this
   zone). Same group: **AI Labyrinth**, a switch (off).
2. **AI crawler policies:** same group → **AI Crawler and Agent access policies**. Its number
   under Configurations opens a panel: **Search**, **Training**, **Agents**, each set to "Allow
   (do not block)" here; then **Personal Agents**, one line per named agent (four, plus one
   "Coming soon"), each Allow; then **Enable Bot Preference Sync**, a switch (off). The checklist's
   section 4 item "AI crawlers: allow" covers the first three, Bot Preference Sync, AI Labyrinth
   and content bots, each with its expected state; it does not mention Personal Agents.
3. **Per-crawler blocks (new to the kit):** Your domain → **AI Crawl Control** → **Security**.
   One row per crawler, with a **Block Crawler** switch: GPTBot, ClaudeBot, Googlebot, Baidu,
   BingBot, CCBot, PerplexityBot and more. Googlebot and BingBot are on this list. A **Show
   inactive crawlers** box widens the list to crawlers that have not called lately (it was ticked
   here); a blocked crawler may be among those. No kit file names this page. What a blocked
   crawler receives was not tested; the switch's name is the evidence.
4. **Security rules:** Your domain → Security → **Security rules**. One page with sections:
   Custom rules ("No Custom rules created"), Rate limiting rules, Managed rules, **IP access
   rules** ("2 active", columns Order, Name, Applies to, Notes, Action, Status), and Response rules
   ("Cloudflare default protection applied"). Both IP access rules read "All websites in account"
   and Allow: so account-wide rules do show on each domain's page. Cloudflare's docs say the IP
   access section shows only once a rule exists ("Create an IP access rule", 2026-08-03); with
   none, not seen here.
5. **Tokens:** My Profile → **API Tokens** (`https://dash.cloudflare.com/profile/api-tokens`).
   Each token has a coloured dot; hovering reads **Active** (green), **Expires soon** (orange) or
   **Expired** (red). Expired tokens stay in the list until deleted. Tokens made under Manage
   account → **Account API tokens** (`https://dash.cloudflare.com/<account id>/api-tokens`) are a
   separate list with the same dots and columns for Created and Last used. The checklist (section 6) has the owner make the token under My
   Profile, and allows a second token for launch day.

## What the owner reads, and where the paths live

The owner reads the five places above (or shows the assistant a screenshot). The assistant never
signs in and never asks for a token.

The paths live in one place: `docs/CLOUDFLARE-CHECKLIST.md` section 5 gains a short list, "Read
in the dashboard", with the five places and what each should show; Bot Fight Mode and the AI
policies point to their items in sections 3 and 4 rather than repeat them. Section 4's AI item
gains two lines: Personal Agents each Allow, and the per-crawler page with **Show inactive
crawlers** ticked and every Block Crawler switch off. The launch check names the five and what
counts as a finding, and points to "`docs/CLOUDFLARE-CHECKLIST.md` in the Croftweaver folder,
section 5", the form `search-console-setup` already uses (its `SKILL.md` line 109). It does not copy
the paths: Cloudflare moves them, and two copies drift.

No script. A read-only API call would need a new token that can read the zone's rules and the
account's rules (the exact permission rows not checked), so the owner would make a token at the
moment the check asks them to have deleted theirs. The
dashboard read takes a few minutes and needs nothing new.

## When it runs

- **Pre-launch (10c):** only when the domain is already on Cloudflare (a relaunch, or a domain
  moved early). That is when old rules are most likely, and a block found before launch costs
  nothing. Otherwise the row goes under "Not checked yet" as "deferred to the live re-check: the
  domain is not on Cloudflare yet", as the deploy-only rows do; it does not count in the verdict.
  No token question: launch day may still need it.
- **Live (12a):** always, once launch day's work is done: the production build Active, the
  domain attached (the setup script's `launch` stage, or by hand), and the owner says nothing more
  is left for the token. Then this is what visitors and crawlers meet. If the owner says launch
  day still needs the token, the rest is read and the token line reads "deferred: launch day
  still needs it; read again when it is done", under "Not checked yet", with no finding.
- **Baseline (5a):** no.

12a is optional today. The zone read is the one part of it nothing else covers, so 12a stops
being optional: it runs once launch day's work is done, for the zone read, and the speed and
comparison parts may be skipped. Every place that calls it optional changes: launch check
`SKILL.md` lines 10–11 (description), 29 (run table) and §8; new-website `SKILL.md` lines 54 and
349 (row 12a). The pre-launch report's "Not checked yet" line names it, so an owner who stops
after launch day sees what is still open.

## What a finding is

- **A setting that differs from the checklist** (Bot Fight Mode, AI Labyrinth, the AI policies
  with Personal Agents, Bot Preference Sync, a Block Crawler switch): ask the owner whether it was
  their choice (intent decides, launch check `SKILL.md` §4). Yes: recorded as "owner's choice, <date>", with the
  checklist's trade-off in one line, quoted from the checklist and credited to it (for Training on
  Block, section 4 quotes Cloudflare that it also reaches Googlebot, Bingbot and Applebot; for a
  Block Crawler switch on Googlebot or BingBot, that it is named to block that search engine's
  crawler). No or don't know: 🔴, with the checklist item that sets it right.
- **A security rule:** every rule on the Security rules page, in whichever section (custom, rate
  limiting, managed, IP access), is listed with its name, action, what it matches, and "this
  domain" or "all websites in account". The assistant says in plain words what each does, from
  what the owner reads out.
  - A rule that blocks or challenges, whose effect or owner nobody can state, or that could stop
    visitors or crawlers the owner wants: 🔴 until the owner keeps, changes or removes it.
  - A rule whose action is Allow or Skip, whose owner nobody can state: 🟡. Its action names no
    block, and an account-wide one may be another site's. The owner finds out whose it is.
  - Any rule the owner knows and keeps: "owner's choice, <date>".
  - The Response rules section ("Cloudflare default protection applied" on this zone): the kit
    leaves it alone; the report quotes what it shows, with no finding.
- **The setup tokens (live run only):** the owner reads both lists (My Profile → API Tokens, and
  Manage account → Account API tokens) and names every token made for this site's setup and
  launch day; the checklist allows two. Each one Active or Expires soon: 🔴, delete it now
  (checklist section 6, "When it is done"). Expired: 🟡, delete it. In neither list: fine. An
  owner who cannot tell which tokens they were: 🟡, with the advice to delete any token they
  cannot place. Other tokens are the owner's own business and are not named in the report.
- **Not read** (no dashboard access, or the owner stops): "not checked: <reason>", never a pass;
  🟡 at both the pre-launch and the live run. This is not the pre-launch deferral above, which
  has its own wording and no finding.

## Scenarios

- **S1.** Given a new site whose domain moves to Cloudflare on launch day, when the pre-launch run
  ends on Tuesday, then its "Not checked yet" list has "Cloudflare zone settings: deferred to the
  live re-check: the domain is not on Cloudflare yet", and the verdict does not count it.
- **S2.** Given the same site live on Friday, with Bot Fight Mode, AI Labyrinth and Bot Preference
  Sync off, every AI policy and Personal Agent on Allow, no Block Crawler switch on, no security
  rules and the setup token deleted, when the live re-check runs, then the zone row reads ✅ with
  each place as seen, dated Friday.
- **S2a.** Given the same, but Bot Preference Sync on with Training on Allow, and the owner did
  not choose it, then the row is 🔴 with the checklist's section 4 line for the switch.
- **S2b.** Given the same as S2, but on Friday the owner says launch day still needs the token,
  then the zone row reads ✅ for the settings and rules, and "Not checked yet" lists "the setup
  tokens: deferred: launch day still needs it; read again when it is done", with no finding.
- **S3.** Given a bakery's relaunch whose domain has been on Cloudflare for years, with a custom
  rule that blocks two countries and Training on Block, when the pre-launch run reads the zone,
  then the owner is asked about both; they say the rule is theirs and Training was not, and the
  report records the rule as the owner's choice and Training as 🔴 with the checklist's fix.
- **S4.** Given an account with two IP access rules that allow two addresses on all websites in
  the account, which no one on this site can place, when the live re-check reads the zone, then
  both are listed as account-wide Allow rules and the row is 🟡 until the owner finds out whose
  they are.
- **S5.** Given the Googlebot row in AI Crawl Control → Security with its Block Crawler switch on,
  and the owner did not mean it, then the row is 🔴: "Googlebot's Block Crawler switch is on", with
  the checklist's line to turn it off.
- **S6.** Given a setup token made on Monday and a second one for launch day on Thursday, and on
  Friday's live re-check the first is red (Expired) and the second still green (Active), then the
  row is 🔴 "delete the launch-day token now" and 🟡 "delete the expired setup token", with the
  checklist's path.
- **S6a.** Given a Block Crawler switch on for a crawler that has not called this week, when the
  owner reads AI Crawl Control → Security with **Show inactive crawlers** ticked, then that row
  shows and the finding is raised as in S5.
- **S7.** Given an owner whose agency holds the Cloudflare account, at the live re-check (a
  relaunch's pre-launch run ends the same way), then the row reads "not
  checked: the owner has no access to the Cloudflare account" and is 🟡, never ✅.

## How it is tested

The change is skill text and checklist prose; there is no code to test.

1. **Paths on a real zone:** done before this gate ("Seen in the dashboard").
2. **`make check`** before round 1 of the DIFF gate and after the last edit.
3. **A dry run after the build:** walk all ten scenarios (S1 to S7, S2a, S2b and S6a) through the new
   text by hand and confirm each ends in the row the scenario names; write the result in the PR.

## Out of scope

- Changing any setting for the owner. The check reads; the checklist fixes.
- The setup script does not set or read the per-crawler switches; whether it should is a
  follow-up (a BUGLOG row), not this change.
- Content bots. The Bot traffic group on webcroft.dev listed five settings and none for content
  bots, and the checklist sends an owner who finds no switch to the API, which this check does
  not use. The check never reads it, switch or not; the setup script sets it off.
- Sections of the Security rules page beyond the ones above: rules in any section are read and
  judged as "A security rule" says; the kit sets none of them.
- The guide site's own two rules and its tokens: the 0.35 session's, not the kit's.

## Review trail

- **Round 1** (Codex and GLM 5.3, 79,035 tokens): 3 BUG, 7 RISK, 4 NIT, some raised by both.
  Fixed: two setup tokens and both token lists; Show inactive crawlers; the setup script's
  launch-stage read and its eight-day limit stated as they are; 12a no longer called optional;
  the token read waits for launch day's work; Cloudflare behaviour credited to the checklist or
  the switch's name, not asserted; the pre-launch not-read verdict; an owner who cannot tell the
  tokens apart; the checklist's exact path; every scenario in the dry run. Refuted: "no checklist
  item for AI Labyrinth" (section 4 has "AI Labyrinth: Off"; the plan now names it). Left as
  unverifiable to the reviewers: the dashboard read (no captures, private data) and the API
  permission rows (now marked not checked).
- **Round 2** (Codex and GLM 5.3, 71,907 tokens; 150,942 over both rounds): 3 BUG, 2 RISK,
  4 NIT. Fixed: every place that calls 12a optional is named; S2 sets Bot Preference Sync off
  and S2a covers it on; the Account API tokens list opened and described; S5 states only the
  switch's state; the Allow/Skip and response-rules lines claim nothing about Cloudflare's
  behaviour; the pre-launch deferral and "not checked" worded apart; the waiting token line
  named; content bots in the list; the dry run names all nine scenarios.
  (The two behaviour RISKs share one row in the round's dispositions file.)
- **Round 3** (Codex and GLM 5.3, 50,479 tokens; 201,421 over three rounds): 1 BUG, 1 RISK,
  3 NIT. Fixed: content bots, added in round 2, are not read (no dashboard switch on
  webcroft.dev), so S2's ✅ needs nothing it cannot see; §4 named with its file; S2b covers the
  waiting token line; S7 names its run.
- **Round 4** (earned by content-bots-read; Codex and GLM 5.3, 55,764 tokens; 257,185 over four
  rounds): 1 BUG (content bots again: a shown switch left S2 open), 1 NIT. Cut, not patched:
  content bots are out of the check entirely, switch or not (Out of scope says why). The NIT:
  rules in every section of the Security rules page are judged alike.
