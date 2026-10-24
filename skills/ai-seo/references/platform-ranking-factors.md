# What the Companies' Pages and the Studies Say About Getting Cited

This guide collects what each company's own page and the studies say about getting cited, and what to do about it. Where nothing is cited, the line is advice.

Sources cited throughout: [Princeton GEO study](https://arxiv.org/abs/2311.09735) (KDD 2024), [SE Ranking study of 129,000 domains](https://seranking.com/blog/chatgpt-citation-factors/) (2025), [Sellm analysis of 400,000 pages](https://sellm.io/post/chatgpt-ranking-factors) (2025), [BrightEdge AI Overviews tracking](https://www.brightedge.com/resources/weekly-ai-search-insights/ai-overviews-one-year-presence-size-citing) (2026), [Profound citation study](https://www.tryprofound.com/blog/ai-platform-citation-patterns) (2025).

---

## The Fundamentals

Three things to do for every platform:

1. **Get your content indexed** — for Google, being indexed and eligible to be shown in Google Search with a snippet is the technical requirement for AI Overviews and AI Mode ([Google](https://developers.google.com/search/docs/appearance/ai-features)). For the other platforms, see their sections below.
2. **Let the search bots in** — allow each company's search bot in robots.txt (see "Allowing AI Bots in robots.txt" below for which bot does what; Microsoft's is unchecked).
3. **Your content should read well in pieces** — use clear structure and self-contained paragraphs, so a passage makes sense without the page around it.

Where a company's page or a study backs a statement, the source is beside it; the rest is advice.

---

## Google AI Overviews

Google says a page must be indexed and eligible to be shown in Google Search with a snippet to appear as a supporting link in AI Overviews or AI Mode, and lists no other technical requirement ([Google](https://developers.google.com/search/docs/appearance/ai-features)); indexing and serving are not guaranteed. Google adds that specific optimization isn't required, and that you don't need new machine-readable files, AI text files or markup, or any special schema.org structured data, to appear in these features. BrightEdge found AI Overviews on about 45% of the queries it tracks by late 2025.

**What the studies add:** Ordinary SEO is the base. We found no Google-specific test of what the AI layer adds on top. In the Princeton GEO study, citing sources and writing in an authoritative (not salesy) tone both raised a page's visibility in AI-generated answers (tested on the authors' own simulated engine and on Perplexity, not on Google).

**Write clear, extractable answers on every page you want cited.**

**What to focus on:**
- Schema markup — Article, FAQPage, HowTo, and Product schemas describe your page to machines. We found no study that measures how much it lifts AI visibility, and Google says no special schema.org structured data is needed for AI Overviews or AI Mode, so treat it as good hygiene, not a guaranteed boost. Google no longer shows HowTo rich results at all, and FAQ rich results only for government and health sites ([Google](https://developers.google.com/search/blog/2023/08/howto-faq-changes))
- Build topical authority through content clusters with strong internal linking
- Include named, sourced citations in your content (not just claims)
- Add author bios with real credentials
- Get into Google's Knowledge Graph where possible
- Target "how to" and "what is" query patterns, with a direct answer first

---

## ChatGPT

OpenAI says a site opted out of OAI-SearchBot is not shown in ChatGPT's search answers, though it can still appear as a link ([OpenAI](https://developers.openai.com/api/docs/bots)). The studies below look at which pages ChatGPT cited.

An SE Ranking analysis of 129,000 domains found backlinks were the strongest signal it measured: domains with over 350,000 referring domains averaged 8.4 citations, against 1.6-1.8 for those with up to 2,500.

**Freshness showed up too.** In the same SE Ranking study, pages updated within the past three months averaged 6.0 citations, against 3.6 for older ones. The study shows a correlation, not a tested cause.

**Content-answer fit weighed most in one model.** A Sellm analysis of 400,000 pages found that how well your content's style and structure matches ChatGPT's own response format carried about 55% of the weight in its model predicting which pages get cited, against 12% for domain authority and 14% for on-page structure. The study shows a correlation, not a tested cause, so treat writing the way ChatGPT answers as a cheap thing to try.

**Where ChatGPT looks beyond your site:** In Profound's study of 680 million citations across ChatGPT, Google AI Overviews and Perplexity (August 2024 to June 2025), Wikipedia was 7.8% of the ChatGPT citations Profound counted, Reddit 1.8% and Forbes 1.1%.

**What to focus on:**
- Allow OAI-SearchBot in robots.txt (OpenAI says a site opted out of it is not shown in ChatGPT's search answers; GPTBot is the training bot)
- Earn backlinks and build domain authority (the strongest signal in the SE Ranking study)
- Update competitive content at least every three months
- Structure your content the way ChatGPT structures its answers (conversational, direct, well-organized)
- Include verifiable statistics with named sources
- Clean heading hierarchy (H1 > H2 > H3) with descriptive headings

---

## Perplexity

Perplexity says PerplexityBot is designed to surface and link websites in its search results and is not used to crawl content for AI foundation models ([Perplexity](https://docs.perplexity.ai/guides/bots)).

**Habits worth adopting:**
- **FAQ Schema (JSON-LD)** — Often recommended for Perplexity, though we found no study showing it raises citations (SE Ranking found ChatGPT cited pages with FAQ schema slightly less often). It still describes your Q&A to machines
- **PDF documents** — Publish authoritative PDFs (whitepapers, research reports) publicly. If yours sit behind a form, consider making a version public.
- **Publishing rhythm** — Publish on a steady schedule you can keep
- **Self-contained paragraphs** — Write atomic, semantically complete paragraphs a reader can quote cleanly

**What to focus on:**
- Allow PerplexityBot in robots.txt
- Implement FAQPage schema on any page with Q&A content (since August 2023 Google shows FAQ rich results only for well-known government and health sites — [Google](https://developers.google.com/search/blog/2023/08/howto-faq-changes))
- Host PDF resources publicly (whitepapers, guides, reports)
- Add Article schema with publication and modification timestamps
- Write in clear, self-contained paragraphs that work as standalone answers
- Build deep topical authority in your specific niche

---

## Microsoft Copilot

Microsoft's own pages were not checked for this guide, so this section lists Bing basics, not Copilot-specific findings. The `Bingbot` line in the robots.txt section is unchecked for the same reason.

**What to focus on:**
- Submit your site to Bing Webmaster Tools
- Use the IndexNow protocol to tell search engines about new and updated content
- Write clear entity definitions — when your content defines a term or concept, make the definition explicit and extractable
- Build presence on LinkedIn (publish articles, maintain company page) and GitHub if relevant
- Ensure Bingbot has full crawl access

---

## Claude

Anthropic says Claude-SearchBot indexes pages for Claude's search results, and that blocking it may reduce your visibility there ([Anthropic](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)).

**What to focus on:**
- Allow Claude-SearchBot and Claude-User in robots.txt (ClaudeBot is the training bot; see "Allowing AI Bots in robots.txt" below)
- Maximize factual density — specific numbers, named sources, dated statistics
- Use clear, extractable structure with descriptive headings
- Cite authoritative sources within your content
- Aim to be the most accurate source on your topic

---

## Allowing AI Bots in robots.txt

The companies' own pages (read on 2026-10-11, except the Bingbot line, which was not checked against Microsoft's pages; links in the Step 4 list of `SKILL.md`) split their bots by job, so allow the search and user bots by name:

```
User-agent: OAI-SearchBot     # OpenAI: shows your pages in ChatGPT search
User-agent: ChatGPT-User      # OpenAI: fetches a page when a ChatGPT user asks (robots.txt may not apply)
User-agent: Claude-SearchBot  # Anthropic: indexes pages for Claude's search
User-agent: Claude-User       # Anthropic: fetches a page when a Claude user asks
User-agent: PerplexityBot     # Perplexity: shows your pages in its search results
User-agent: Perplexity-User   # Perplexity: fetches a page when a user asks (generally ignores robots.txt)
User-agent: Bingbot           # Microsoft Copilot (via Bing)
Allow: /
```

Google Search, including AI Overviews and AI Mode, follows your rules for Googlebot, so keep Googlebot allowed.

A bot that has a group of its own obeys only that group: under RFC 9309, crawlers use the `*` group only when no group matches them ([RFC 9309](https://www.rfc-editor.org/rfc/rfc9309)). If your `User-agent: *` group has `Disallow` lines for private paths (`/admin/`, a cart), copy them into the group above. Several `User-agent` lines in a row share the rules under them, as the block above does.

**Training vs. search:** each company's training bot is a separate choice. OpenAI says GPTBot and OAI-SearchBot are independent settings, and Anthropic lists ClaudeBot apart from its two other bots. To stay in search answers but opt out of training, leave the lines above as they are and add:

```
User-agent: GPTBot
User-agent: ClaudeBot
Disallow: /
```

Google-Extended is its own choice. Google says it does not affect inclusion in Google Search, and it also covers grounding in Gemini Apps (providing content from the Google Search index to the model at prompt time), so blocking it opts you out of that too:

```
User-agent: Google-Extended
Disallow: /
```

CCBot is Common Crawl's crawler, and Common Crawl publishes an open archive of what it crawls ([Common Crawl](https://commoncrawl.org/ccbot)). Add `CCBot` to the training group if you don't want future crawls of your pages in it.

---

## Where to Start

Order the platforms by where your own audience searches: ask your customers, or check the referral traffic from each. If you don't know yet, this is a reasonable order:

**Start with Google AI Overviews** — BrightEdge found them on about 45% of the queries it tracks, and Google's eligibility is ordinary Search eligibility. Google says specific optimization isn't required and that its SEO fundamentals stay worthwhile; on top of them, include cited sources in your content and show who wrote the page.

**Then ChatGPT** — Allow OAI-SearchBot, then work on freshness, backlinks and matching your content structure to how ChatGPT formats its responses (the studies above).

**Then Perplexity** — Allow PerplexityBot. Add FAQ schema if you have Q&A to describe, publish PDFs where you have authoritative ones, and write in clear, self-contained paragraphs.

**Then Copilot and Claude** — The same fundamentals (structured content, cited sources, schema markup), plus each one's search bot (Claude-SearchBot; Bingbot for Copilot, not checked against Microsoft's pages).

**Actions to start with:**
1. Allow the search and user bots in robots.txt (the training bots are your call)
2. Add schema markup where it describes your content (Google says none is required for AI Overviews and AI Mode)
3. Include statistics with named sources in your content
4. Update content regularly, for example every three months for competitive topics
5. Use clear heading structure (H1 > H2 > H3)
6. Keep pages fast: Google's guidance for a good Largest Contentful Paint is 2.5 seconds or less, measured at the 75th percentile of page loads ([web.dev](https://web.dev/articles/lcp))
7. Add author bios with credentials
