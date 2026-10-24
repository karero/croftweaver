# Acting on the data — keyword strategy

How to turn the two reports into ranking moves. The worked example is
example.com targeting **"AI Events in Munich"**, **"AI Meetups in Munich"**,
and the German **"AI Treffen in München"**, but the playbook is general.

## The loop

1. **Phase 1 (`gsc_query.py`)** — what Google *already* shows us for, and how well.
2. **Phase 2 (`serp_check.py`)** — what the Top 10 looks like for the same terms.
3. Pick the **cheapest move that closes the biggest gap**, ship it, re-measure in
   1–2 weeks (GSC lags ~2–3 days and updates continuously).

## Reading Phase 1

| Signal in the report | What it means | Move |
|---|---|---|
| Target keyword "no impressions yet" | Google isn't surfacing us at all — content/relevance gap, or property too new | Make/strengthen a dedicated page for the term; confirm it's indexed in GSC |
| Target keyword avg pos 11–20 | On page 2 — striking distance | Strengthen the existing page: title match, internal links, depth, freshness |
| Striking-distance table has rows | Fastest wins available | Prioritise these over chasing brand-new terms |
| Page ranks ≤10 but CTR <2% | Seen, not clicked — a snippet **or SERP-context** problem, not a ranking problem | Live-SERP check first (mandatory — SKILL.md "Reading the numbers"); rewrite title + meta description only if it shows a snippet problem you control (`copywriting` + `website-seo-geo`) |

Striking distance first: moving pos 12 → 8 is far cheaper than 50 → 8, and the
impression data proves there's real demand.

## Reading Phase 2 (intent & format)

The Top 10's *shape* tells you the format Google rewards for a query:

- **Event aggregators dominate** (Meetup, Eventbrite, Luma, meetup-style hubs)
  → Google reads the query as "show me upcoming events". Win with a **current,
  structured listing**: real upcoming events, dates, `Event` JSON-LD, kept fresh.
  If the site already emits `Event` schema on event pages, make sure the
  hub page links them and stays up to date.
- **Listicle guides dominate** ("Top AI meetups in Munich", city guides)
  → Win with a **better guide page**: comprehensive, genuinely useful, updated,
  linking out to the real communities (including ours).
- **We're absent entirely** → it's a content gap, not a tuning problem. Build the page
  that matches the dominant format above.

In the worked example the natural home is the existing **`/ai-events-munich`** guide plus
the event detail pages — strengthen those rather than spinning up new thin pages.

## German vs. English

"AI Treffen in München" is a distinct query with its own (smaller, less contested)
SERP. The site is currently English-only. Options, cheapest first:

1. A German-language section/page targeting the German term (the site has
   `astro-i18n-setup` available in the kit if you go multi-language).
2. At minimum, ensure the German term appears naturally in on-page copy and headings
   of the Munich page so it can surface for it.

Don't keyword-stuff — match the term where it reads naturally.

## When free isn't enough (paid scale-up)

This skill stops at the free tier on purpose. If you later need **keyword volumes,
difficulty scores, or SERP history at scale**:

- **DataForSEO** — no free tier, **$50 minimum deposit**, but very cheap per call
  (~$0.0006/SERP) and a full backbone (keyword data, SERP, backlinks, audits). The
  right choice only once Serper/SerpApi's free volume is the bottleneck.
- Serper paid is also cheap ($0.30/1K) if you just need more SERP volume, not the
  wider keyword dataset.

Wiring DataForSEO would be a follow-up: add a `--provider dataforseo` branch to
`serp_check.py` (Basic-auth login/password, `/v3/serp/google/organic/live/advanced`),
plus a keyword-data call for volumes. Out of scope until the free tier is outgrown.

## See also (in SKILL.md)

- **Low-volume playbook** — the 5 tactics for a thin/niche site (track position not
  clicks, convert striking-distance one at a time, fix titles before chasing rankings,
  mine unexpected queries, use SERP+Bing for weak-competition terms).
- **Bing Webmaster Tools** — a second free source and a Copilot/ChatGPT-visibility
  proxy; often you rank far better on Bing than Google (verified on the worked example:
  pos ~2–3 on Bing vs ~6+/absent on Google).
- **Track positions over time** — `track.sh`, or any ordinary query-script run (history
  now records by default), make "is my position improving?" a single command instead of
  comparing reports by eye.
