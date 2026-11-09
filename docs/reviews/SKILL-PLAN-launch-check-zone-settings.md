# Plan: the launch check reads the Cloudflare zone settings

Written 2026-11-09 for the maintainer's go. One item in `website-launch-check`: the owner reads
five places in the Cloudflare dashboard, and the report records what they showed.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan, with every dashboard path read on a real zone | ✅ written 2026-11-09 | this file, "Seen in the dashboard" |
| 2 | PLAN gate (Normal: a SKILL.md and an owner-facing checklist) | ⬜ | — |
| 3 | Build: launch check §3 and §8, the report template, the checklist's sections 4 and 5, new-website's row 12a (one PR) | ⬜ | — |
| 4 | DIFF gate (Normal) | ⬜ | — |

## Why

The setup script (`skills/new-website/scripts/cloudflare-setup.mjs`) sets Bot Fight Mode off and
the AI crawler policies to Allow, and refuses a token that lasts more than a week, but only on the
day it runs. Nothing reads the zone again. The outside check says it "cannot see" the settings
themselves (`skills/new-website/references/CLOUDFLARE_CHECK.md`, "What it cannot see").
`website-launch-check` never mentions Cloudflare, and no kit file mentions security rules or IP
access rules.

The case behind it: the toolkit's own guide site launched on 2026-11-09, and its launch row closed
without anyone reading the zone. Two IP access rules that apply to every website in the account
are on it and still unread. An account-wide rule made for one site reaches every site in the
account, so a new site can launch behind a rule nobody on it chose.

## Seen in the dashboard

Read on 2026-11-09 on webcroft.dev, a free-plan zone, in the maintainer's signed-in browser.
Nothing was changed: the one panel opened was closed with Cancel.

1. **Bot Fight Mode:** Your domain → Security → Settings. The page groups its settings; the
   **Bot traffic** group lists **Bot fight mode** with a switch in the Status column (off on this
   zone). Same group: **AI Labyrinth**, a switch (off).
2. **AI crawler policies:** same group → **AI Crawler and Agent access policies**. Its number
   under Configurations opens a panel: **Search**, **Training**, **Agents**, each set to "Allow
   (do not block)" here; then **Personal Agents**, one line per named agent (four, plus one
   "Coming soon"), each Allow; then **Enable Bot Preference Sync**, a switch (off). The checklist
   (section 4) lists the first three and the switch, not Personal Agents.
3. **Per-crawler blocks (new to the kit):** Your domain → **AI Crawl Control** → **Security**.
   One row per crawler, with a **Block Crawler** switch: GPTBot, ClaudeBot, Googlebot, Baidu,
   BingBot, CCBot, PerplexityBot and more. Googlebot and BingBot are on this list, so one switch
   here can take a site out of Google or Bing. A **Show inactive crawlers** box widens the list
   (it was ticked here). No kit file names this page.
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
   account → Account API tokens are a separate list (not opened).

## What the owner reads, and where the paths live

The owner reads the five places above (or shows the assistant a screenshot). The assistant never
signs in and never asks for a token.

The paths live in one place: `docs/CLOUDFLARE-CHECKLIST.md` section 5 gains a short list, "Read
in the dashboard", with the five places and what each should show; Bot Fight Mode and the AI
policies point to their items in sections 3 and 4 rather than repeat them. Section 4's AI item
gains two lines: Personal Agents each Allow, and the per-crawler page with every Block Crawler
switch off. The launch check names the five and what counts as a finding, and points to that list
in the Croftweaver folder, as `search-console-setup` already does for section 4. It does not copy
the paths: Cloudflare moves them, and two copies drift.

No script. A read-only API call would need a token with firewall and account-rule read rows, so
the owner would make a new token at the moment the check asks them to have deleted theirs. The
dashboard read takes a few minutes and needs nothing new.

## When it runs

- **Pre-launch (10c):** only when the domain is already on Cloudflare (a relaunch, or a domain
  moved early). That is when old rules are most likely, and a block found before launch costs
  nothing. Otherwise the row goes under "Not checked yet: the domain is not on Cloudflare yet",
  as the deploy-only rows do. No token question: launch day may still need it.
- **Live (12a):** always. Launch day has run (the setup script's `launch` stage, any changes by
  hand), so this is what visitors and crawlers meet, and the token's work is done.
- **Baseline (5a):** no.

12a is optional today. The zone read is the one part of it nothing else covers, so new-website's
row 12a and launch check §8 say: optional, except the zone read, which runs once the production
build is Active. The pre-launch report's "Not checked yet" line names it, so an owner who stops
after launch day sees what is still open.

## What a finding is

- **A setting that differs from the checklist** (Bot Fight Mode, AI Labyrinth, the AI policies
  with Personal Agents, Bot Preference Sync, a Block Crawler switch): ask the owner whether it was
  their choice (intent decides, §4). Yes: recorded as "owner's choice, <date>", with the
  checklist's trade-off in one line where it has one (Training on Block also blocks Googlebot,
  Bingbot and Applebot; Googlebot's own switch stops Google crawling the site). No or don't know:
  🔴, with the checklist item that sets it right.
- **A security rule:** each rule is listed with its name, action, what it matches, and "this
  domain" or "all websites in account". The assistant says in plain words what each does, from
  what the owner reads out.
  - A rule that blocks or challenges, whose effect or owner nobody can state, or that could stop
    visitors or crawlers the owner wants: 🔴 until the owner keeps, changes or removes it.
  - A rule that allows or skips, whose owner nobody can state: 🟡. It cannot stop a visitor, but
    it lets some traffic past Cloudflare's checks, and an account-wide one may be another site's.
  - Any rule the owner knows and keeps: "owner's choice, <date>".
  - Response rules' "Cloudflare default protection applied" is Cloudflare's default, not a
    finding.
- **The setup token (live run only):** the owner names the token they made for setup and launch
  day. Active or Expires soon: 🔴, delete it now (checklist section 6, "When it is done"). Expired:
  🟡, delete it. Not in the list: fine. Other tokens are the owner's own business and are not
  listed in the report.
- **Not read** (no dashboard access, or the owner stops): "not checked: <reason>", never a pass;
  🟡 at the live run.

## Scenarios

- **S1.** Given a new site whose domain moves to Cloudflare on launch day, when the pre-launch run
  ends on Tuesday, then its report lists "Cloudflare zone settings: not checked yet, the domain is
  not on Cloudflare yet; read at the live re-check", and the verdict does not count it.
- **S2.** Given the same site live on Friday, with Bot Fight Mode and AI Labyrinth off, every AI
  policy Allow, no Block Crawler switch on, no security rules and the setup token deleted, when the
  live re-check runs, then the zone row reads ✅ with each place as seen, dated Friday.
- **S3.** Given a bakery's relaunch whose domain has been on Cloudflare for years, with a custom
  rule that blocks two countries and Training on Block, when the pre-launch run reads the zone,
  then the owner is asked about both; they say the rule is theirs and Training was not, and the
  report records the rule as the owner's choice and Training as 🔴 with the checklist's fix.
- **S4.** Given an account with two IP access rules that allow two addresses on all websites in
  the account, which no one on this site can place, when the live re-check reads the zone, then
  both are listed as account-wide Allow rules and the row is 🟡 until the owner finds out whose
  they are.
- **S5.** Given the Googlebot row in AI Crawl Control → Security switched to Block, and the owner
  did not mean it, then the row is 🔴: "Googlebot is blocked; Google can no longer crawl the site".
- **S6.** Given the setup token still shows a green dot on the day of the live re-check, then the
  row is 🔴 "delete the setup token now", with the checklist's path.
- **S7.** Given an owner whose agency holds the Cloudflare account, then the row reads "not
  checked: the owner has no access to the Cloudflare account" and is 🟡, never ✅.

## How it is tested

The change is skill text and checklist prose; there is no code to test.

1. **Paths on a real zone:** done before this gate ("Seen in the dashboard").
2. **`make check`** before round 1 of the DIFF gate and after the last edit.
3. **A dry run after the build:** walk S1, S4, S5 and S6 through the new text by hand and confirm
   each ends in the row the scenario names; write the result in the PR.

## Out of scope

- Changing any setting for the owner. The check reads; the checklist fixes.
- The setup script does not set or read the per-crawler switches; whether it should is a
  follow-up (a BUGLOG row), not this change.
- Rate limiting, managed rules and other paid-plan sections: they show on the same Security rules
  page, and the owner reads out whatever is listed; the kit sets none of them.
- The guide site's own two rules and its tokens: the 0.35 session's, not the kit's.
