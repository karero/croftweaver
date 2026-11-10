# Plan: Claude-SearchBot in the live check, and two launch-week paragraphs

*2026-11-10. Ideas 6, 7 and 10 of the October 2026 SEO/GEO research (kept in the maintainer's
private notes). One small PR. Idea 6 changes what a script does, so this plan goes through the
PLAN gate first.*

## What and why

1. **Idea 6: the live Cloudflare check sends Claude-SearchBot too.** `cloudflare-check.mjs`
   sends six requests that carry AI crawler names: GPTBot, OAI-SearchBot, ClaudeBot,
   PerplexityBot, CCBot, Amazonbot. ClaudeBot is Anthropic's training crawler. Anthropic's
   search crawler, Claude-SearchBot, is missing, though the starter's own robots test already
   counts it as a search crawler (`templates/astro/tests/seo.spec.ts`, `SEARCH_CRAWLERS`).
   Anthropic's page (opened 2026-11-10) says blocking it "may reduce your site's visibility and
   accuracy in user search results". The check should try the bot that matters for being found.
2. **Idea 7: where an owner sees which AI crawlers came.** Nothing in the kit tells the owner
   where to look. Cloudflare's AI Crawl Control shows it for free.
3. **Idea 10: how long AI search takes to find a new site.** The kit doesn't say. The nearest
   text, `search-console-insights/references/geo-check.md` ("Retraining is slow"), is about what
   a model remembers from training, not about AI search finding the site. An owner whose site
   ChatGPT doesn't know after a week may think it is broken.

## How

**Idea 6, `skills/new-website/scripts/cloudflare-check.mjs`.** Add one row to `CRAWLERS`, after
ClaudeBot: `['Claude-SearchBot', 'Mozilla/5.0 (compatible; Claude-SearchBot/1.0)']`. Anthropic's
page gives the token `Claude-SearchBot` and no full user-agent string, so the string copies the
form of the ClaudeBot row; the version `1.0` is ours. The judging code needs no change: it already
works on the list, and its messages count with `crawlers.length`. Not added: Googlebot and
Bingbot. A request that only carries their name is not the verified crawler, so a pass or a
refusal would prove nothing.

Follow-on text, all "six" becoming "seven": `skills/new-website/references/CLOUDFLARE_CHECK.md`
lines 86 and 150. `docs/WHAT-THE-SKILLS-RUN.md` line 214 says "GPTBot, ClaudeBot and others" and
stays true; no change.

**Ideas 7 and 10, `skills/search-console-setup/SKILL.md`, section 4 "Confirm it's working".** Two
new bullets after the IndexNow one. This is the kit's post-launch "is it working?" step, the
skill ships inside each site, and idea 10 is best read next to the places to watch. The brief
also named `docs/CLOUDFLARE-CHECKLIST.md` and `search-console-insights`; the checklist is a list
of settings to set, and `search-console-insights` is for later weeks, so neither fits a
launch-week question as well. Draft wording:

> - **AI crawlers (free, on Cloudflare):** your domain → **AI Crawl Control** → **Overview** shows
>   which AI companies' crawlers fetched your site, with filters for Hostname and Path. On a
>   free-plan domain on 30 October 2026 its 7-day view showed data; Cloudflare's own
>   page says the free plan's Metrics tab shows only the past 24 hours. On the free plan it knows a
>   crawler by the name the request gives ([Cloudflare](https://developers.cloudflare.com/ai-crawl-control/get-started/)),
>   so a crawler that doesn't name itself is not shown. The Cloudflare check's seven
>   crawler-named requests may show up here as well. A visit is not a mention: it can't tell you
>   whether any AI answer names you.
> - **How long AI assistants take:** we found no published measurement, with a stated method, of
>   how long AI assistants take to first cite a brand-new website. Google's own ranges, and what
>   companies measured for new pages on sites that already exist, are in
>   [How long until Google and AI assistants find a new website?](https://guide.croftweaver.com/how-long)
>   So a week of silence from ChatGPT is not, by itself, a sign that something is broken. Watch the crawlers
>   above, and later Google's and Bing's AI reports (`search-console-insights`).

Sources behind each claim: the Free-plan look is the maintainer's dashboard record of
2026-10-30 (Overview: Hostname, Path, Category and Content type filters; range picker up to 30
days; 7-day view with data; 30-day view not opened). The 24-hour Metrics sentence and "identifies
AI crawlers based on their user agent strings" are from Cloudflare's get-started page, last
updated 23 April 2026, re-read 2026-11-10. The "no published measurement" finding is the
guide's (searched 29 October 2026, page checked 3 November 2026, live 2026-11-10); I link it and
restate nothing else from it. **Not checked:** whether the checker's own requests appear in AI
Crawl Control (an inference from "user agent strings"; hence "may"), and whether the 30-day
range holds 30 days on Free (so the text promises 7).

**`docs/BUGLOG.md`:** a "Next release notes" row: the check sends seven names, Claude-SearchBot
added; search-console-setup says where to see AI crawler visits and how long AI search takes.

## How it is tested

- **Existing tests** that count six (`cloudflare-check.test.mjs` lines 107 and 639) change to
  seven. That is the expected value following the list, not a weakening.
- **New test, through the real entry point** (the tests run the script with `execFile`): a stub
  site refuses only requests whose user agent contains `Claude-SearchBot/`. Expect the AI item
  to be `look`, its detail to name `Claude-SearchBot (403)`, and not ClaudeBot. It fails today
  (no such request is sent) and fails if the row is removed or misnamed.
- **The existing ClaudeBot refusal test** matches `/ClaudeBot/`; `Claude-SearchBot` does not
  contain that string, so it still refuses one request. I'll confirm its detail names ClaudeBot
  alone.
- **Prose:** no test reads the two bullets' wording; `check_skill_budgets.sh` (in `make check`)
  measures the file's size, which stays far under its budget. The DIFF review and
  `check_clean.sh` cover the wording.
- `make check` and `make test-cloudflare-check` before each review round and after the last
  edit.

## Cost and risk

Code: one list row and one test. Each run sends one more GET to the owner's own domain. No new
dependency, permission or token. Risk is low: a wrong user-agent string at worst makes the hint
miss a Cloudflare block, as any of the six can today.

## Status

| Step | State | Evidence |
|---|---|---|
| Plan, PLAN gate | in review | — |
| Maintainer's go | waiting | — |
| Build: check row, tests, two bullets, BUGLOG row | not started | — |
| DIFF gate, PR, merge | not started | — |
