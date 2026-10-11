# How Each AI Platform Picks Sources

Each AI search platform has its own search index, ranking logic, and content preferences. This guide covers what matters for getting cited on each one.

Sources cited throughout: [Princeton GEO study](https://arxiv.org/abs/2311.09735) (KDD 2024), [SE Ranking study of 129,000 domains](https://seranking.com/blog/chatgpt-citation-factors/) (2025), [Sellm analysis of 400,000 pages](https://sellm.io/post/chatgpt-ranking-factors) (2025), [BrightEdge AI Overviews tracking](https://www.brightedge.com/resources/weekly-ai-search-insights/ai-overviews-one-year-presence-size-citing) (2026), [Profound citation study](https://www.tryprofound.com/blog/ai-platform-citation-patterns) (2025).

---

## The Fundamentals

Every AI platform shares three baseline requirements:

1. **Your content must be in their index** — Each platform uses a different search backend (Google, Bing, Brave, or their own). If you're not indexed, you can't be cited.
2. **Your content must be crawlable** — each platform's search bot needs access via robots.txt (see "Allowing AI Bots in robots.txt" below for which bot does what).
3. **Your content must be extractable** — AI systems pull passages, not pages. Clear structure and self-contained paragraphs win.

Beyond these basics, each platform weights different signals. Here's what matters and where.

---

## Google AI Overviews

Google AI Overviews pull from Google's own index and lean heavily on E-E-A-T signals (Experience, Expertise, Authoritativeness, Trustworthiness). BrightEdge found them on about 45% of the queries it tracks by late 2025.

**What makes Google AI Overviews different:** They already have your traditional SEO signals — backlinks, page authority, topical relevance. We found no Google-specific test of what the AI layer adds on top. In the Princeton GEO study, citing sources and writing in an authoritative (not salesy) tone both raised a page's visibility in AI-generated answers (tested on the authors' own simulated engine and on Perplexity, not on Google).

**Importantly, AI Overviews don't just recycle the traditional Top 10.** Studies disagree on how far AI Overview sources overlap with the organic top 10, but many cited pages don't rank on page 1. Pages that wouldn't crack page 1 in traditional search can still get cited if they have clear, extractable answers.

**What to focus on:**
- Schema markup — Article, FAQPage, HowTo, and Product schemas describe your page to machines. We found no study that measures how much it lifts AI visibility, so treat it as good hygiene, not a guaranteed boost. Google no longer shows HowTo rich results at all, and FAQ rich results only for government and health sites ([Google](https://developers.google.com/search/blog/2023/08/howto-faq-changes))
- Build topical authority through content clusters with strong internal linking
- Include named, sourced citations in your content (not just claims)
- Author bios with real credentials matter — E-E-A-T is weighted heavily
- Get into Google's Knowledge Graph where possible
- Target "how to" and "what is" query patterns — these trigger AI Overviews most often

---

## ChatGPT

ChatGPT's web search draws from a Bing-based index. It combines this with its training knowledge to generate answers, then cites the web sources it relied on.

**What makes ChatGPT different:** Domain authority matters more here than on other AI platforms. An SE Ranking analysis of 129,000 domains found backlinks were the strongest signal: domains with over 350,000 referring domains averaged 8.4 citations, against 1.6-1.8 for those with up to 2,500.

**Freshness is a major differentiator.** In the same SE Ranking study, pages updated within the past three months averaged 6.0 citations, against 3.6 for older ones. ChatGPT clearly favors recent information.

**The most important signal is content-answer fit** — a Sellm analysis of 400,000 pages found that how well your content's style and structure matches ChatGPT's own response format carried about 55% of the weight in its model predicting which pages get cited. That is far more than domain authority (12%) or on-page structure (14%). The study shows a link, not a tested cause, but writing the way ChatGPT answers is a cheap bet.

**Where ChatGPT looks beyond your site:** In Profound's study of 680 million citations across ChatGPT, Google AI Overviews and Perplexity (August 2024 to June 2025), Wikipedia was 7.8% of the ChatGPT citations Profound counted, Reddit 1.8% and Forbes 1.1%.

**What to focus on:**
- Allow OAI-SearchBot in robots.txt (it decides whether you appear in ChatGPT's search answers; GPTBot is the training bot)
- Invest in backlinks and domain authority — it's the strongest baseline signal
- Update competitive content at least every three months
- Structure your content the way ChatGPT structures its answers (conversational, direct, well-organized)
- Include verifiable statistics with named sources
- Clean heading hierarchy (H1 > H2 > H3) with descriptive headings

---

## Perplexity

Perplexity always cites its sources with clickable links, making it the most transparent AI search platform. It combines its own index with Google's and runs results through multiple reranking passes — initial relevance retrieval, then traditional ranking factor scoring, then ML-based quality evaluation that can discard entire result sets if they don't meet quality thresholds.

**What makes Perplexity different:** It's the most "research-oriented" AI search engine, and its citation behavior reflects that. Perplexity maintains curated lists of authoritative domains (Amazon, GitHub, major academic sites) that get inherent ranking boosts. It uses a time-decay algorithm that evaluates new content quickly, giving fresh publishers a real shot at citation.

**Perplexity has unique content preferences:**
- **FAQ Schema (JSON-LD)** — Often recommended for Perplexity, though we found no study showing it raises citations (SE Ranking found ChatGPT cited pages with FAQ schema slightly less often). It still describes your Q&A to machines
- **PDF documents** — Publicly accessible PDFs (whitepapers, research reports) are prioritized. If you have authoritative PDF content gated behind a form, consider making a version public.
- **Publishing velocity** — How frequently you publish matters more than keyword targeting
- **Self-contained paragraphs** — Perplexity prefers atomic, semantically complete paragraphs it can extract cleanly

**What to focus on:**
- Allow PerplexityBot in robots.txt
- Implement FAQPage schema on any page with Q&A content (since August 2023 Google shows FAQ rich results only for well-known government and health sites — [Google](https://developers.google.com/search/blog/2023/08/howto-faq-changes))
- Host PDF resources publicly (whitepapers, guides, reports)
- Add Article schema with publication and modification timestamps
- Write in clear, self-contained paragraphs that work as standalone answers
- Build deep topical authority in your specific niche

---

## Microsoft Copilot

Copilot is embedded across Microsoft's ecosystem — Edge, Windows, Microsoft 365, and Bing Search. It relies entirely on Bing's index, so if Bing hasn't indexed your content, Copilot can't cite it.

**What makes Copilot different:** The Microsoft ecosystem connection creates unique optimization opportunities. Mentions and content on LinkedIn and GitHub provide ranking boosts that other platforms don't offer. Copilot also puts more weight on page speed — sub-2-second load times are a clear threshold.

**What to focus on:**
- Submit your site to Bing Webmaster Tools (many sites only submit to Google Search Console)
- Use IndexNow protocol for faster indexing of new and updated content
- Optimize page speed to under 2 seconds
- Write clear entity definitions — when your content defines a term or concept, make the definition explicit and extractable
- Build presence on LinkedIn (publish articles, maintain company page) and GitHub if relevant
- Ensure Bingbot has full crawl access

---

## Claude

Claude uses Brave Search as its search backend when web search is enabled — not Google, not Bing. This is a completely different index, which means your Brave Search visibility directly determines whether Claude can find and cite you.

**What makes Claude different:** Claude is extremely selective about what it cites. While it processes enormous amounts of content, its citation rate is very low — it's looking for the most factually accurate, well-sourced content on a given topic. Data-rich content with specific numbers and clear attribution performs significantly better than general-purpose content.

**What to focus on:**
- Verify your content appears in Brave Search results (search for your brand and key terms at search.brave.com)
- Allow Claude-SearchBot and Claude-User in robots.txt (ClaudeBot is the training bot; see "Allowing AI Bots in robots.txt" below)
- Maximize factual density — specific numbers, named sources, dated statistics
- Use clear, extractable structure with descriptive headings
- Cite authoritative sources within your content
- Aim to be the most factually accurate source on your topic — Claude rewards precision

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

If you're optimizing for AI search for the first time, focus your effort where your audience actually is:

**Start with Google AI Overviews** — They reach the most users (about 45% of the queries BrightEdge tracks) and you likely already have Google SEO foundations in place. Add schema markup, include cited sources in your content, and strengthen E-E-A-T signals.

**Then address ChatGPT** — It's the most-used standalone AI search tool for tech and business audiences. Focus on freshness (update content at least every three months), domain authority, and matching your content structure to how ChatGPT formats its responses.

**Then expand to Perplexity** — Especially valuable if your audience includes researchers, early adopters, or tech professionals. Add FAQ schema, publish PDF resources, and write in clear, self-contained paragraphs.

**Copilot and Claude are lower priority** unless your audience skews enterprise/Microsoft (Copilot) or developer/analyst (Claude). But the fundamentals — structured content, cited sources, schema markup — help across all platforms.

**Actions that help everywhere:**
1. Allow the search and user bots in robots.txt (the training bots are your call)
2. Implement schema markup (FAQPage, Article, Organization at minimum)
3. Include statistics with named sources in your content
4. Update content regularly — at least every three months for competitive topics
5. Use clear heading structure (H1 > H2 > H3)
6. Keep page load time under 2 seconds
7. Add author bios with credentials
