# Plan: `ai-seo` leads with being found, then the GEO table

Status: plan, not built. Idea 4 of the October 2026 research (`geo-skill-ideas/IDEAS.md` in the
private feature hub). Nothing is built before the maintainer's go.

## Status

| Step | State | Evidence |
|---|---|---|
| Plan written | done | this file |
| PLAN gate (Normal) and claims sweep | — | — |
| Maintainer's go | — | — |
| Build (steps 1–7 below) | — | — |
| DIFF gate (Normal) | — | — |
| BUGLOG "Next release notes" row | — | — |
| Merged; IDEAS.md status updated | — | — |

## What and why

`skills/ai-seo/SKILL.md` tells an owner where to spend time on AI search. Today its strategy is
"The Three Pillars" (structure, authority, presence), and its strongest numbers are the 2023 GEO
paper's (+41% for quotations, +31% for statistics; `SKILL.md:182–183`). The table's lead names
its setting (a simulated engine, one measure, a smaller Perplexity test; `SKILL.md:178`), but the
table reads as the main lever. Two 2026 studies say the main lever comes earlier: the engine's own
search has to find the page. Page features explained far less, and the GEO paper's gains were
measured on pages already handed to the engine. For a small business this changes the first job:
a page whose title and a paragraph answer each question that matters.

The change opens the strategy with that finding, says both studies are arXiv preprints with no
venue listed, and keeps the GEO table, framed as gains for a page already found. No table row or
source is deleted; two bullet headings lose their figures, which stay in the table (step 4).

## Sources, re-opened on 2026-11-10

Each was fetched again on 2026-11-10 with curl (arXiv abstract pages, PDFs through `pdftotext`,
Google's guide). The gate's evidence file carries the quoted passages as READs.

| Source | What was read | What the new text may say |
|---|---|---|
| Chen & Koudas, "What Drives AI Citations? Content, Retrieval and Model Knowledge in Generative Engine Optimization (GEO)", [arXiv 2610.15033](https://arxiv.org/abs/2610.15033), submitted 10 Oct 2026 | Abstract and full PDF (11 pages; no venue listed: the PDF's header is a blank conference template) | 158,099 answers, 468,037 citations, two 90-day collections of commercial questions (one for a US fiber internet provider, one for small B2B software vendors), both from ChatGPT, Gemini and Perplexity through "the public API of each engine" (GPT-5.4 nano, Gemini 3.1 Flash Lite, Sonar). Within a website, title match and best-paragraph match pass all five of its robustness tests; first-paragraph match fails one. FAQ blocks, structured data, summary and author boxes and page speed "appear effective only across websites". The best-matching paragraph sits at a median of 45% of the page length: "It need not be at the top". In the replay of the questions through the engines' APIs, "every page ChatGPT cites is one its own search retrieved", and retrieval explains 32% (95% CI 24–42%) of the within-website variation in ChatGPT's 90-day citation counts, all page features 2.8%. Engines match "in meaning". A little-known vendor "is named mainly when a cited third-party page names it". Limits it states: "The results are associations"; the API replay "need not behave like" the consumer apps; about a third of cited URLs could not be analysed; English questions about the US market; Perplexity could not be replayed |
| Martinez, "Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization (2023-2026)", [arXiv 2607.14035](https://arxiv.org/abs/2607.14035), submitted 15 Jul 2026 | Abstract, plus a search of the full PDF for its "foundational paper" and the Perplexity test | 45 studies. The foundational paper (its section 4 names Aggarwal et al. [2024], the 2023 GEO paper) has gains "conditional on a source already being present in a fixed context"; "topical relevance and context position are the most reproducible levers"; "no reviewed technique shows a stable, longitudinal, cross-platform causal effect on organic discoverability or downstream behavior". Its Perplexity test used "texts uploaded as files rather than web pages retrieved organically" |
| Aggarwal et al., the 2023 GEO paper, [arXiv 2311.09735](https://arxiv.org/abs/2311.09735) v3 | PDF, its engine design and appendix C.1 | Its engine used "the top 5 sources ... fetched from the Google search engine for every query"; on Perplexity "we instead provide source text as file uploads ... ensuring all answers are generated only using the file sources provided". So both of its tests handed the engine the pages |
| Google, "Optimizing your website for generative AI features on Google Search", [guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), last updated 2026-07-10 | Whole page | "AI systems can understand synonyms and general meanings of what someone is seeking"; a page for every variation of a search, made "primarily to manipulate rankings or generative AI responses", "violates Google's scaled content abuse spam policy"; chunking, AI rewrites, inauthentic mentions and overfocusing on structured data are listed under "things you can ignore for Google Search" |

Neither 2026 paper shows a venue on its abstract page or its PDF, so the skill says "preprint,
no venue listed", not "not peer reviewed". The research notes of 2026-10-28 read Chen & Koudas as
an abstract only; today's full read closes that gap. Martinez was read as its abstract plus two
searched passages, and the skill says so. Vishwakarma et al. (arXiv 2605.25517, a lab test with
two pages) supports the same point, but is left out to keep the text short.

## Two places the wording differs from the brief

1. **"Title and opening lines."** The paper found a title and *a* paragraph (its best-matching
   one) that answer the question; first-paragraph match failed one robustness test, and the
   paper says the matching paragraph "need not be at the top: the engines find it wherever it
   is". So the skill says "a title and a paragraph", and keeps answer-first writing as advice for
   readers, not as a study finding.
2. **"The exact question."** The paper says engines match "in meaning", and Google says its
   systems understand synonyms. So the skill says "in the words a customer would use", not
   exact phrasing, and says no page per phrasing is needed (Google's guide).

## How (all in `skills/ai-seo/`)

1. **New subsection under "Key Difference from Traditional SEO"**, after the Google paragraph,
   named "What the 2026 studies found". It replaces the sentence "So ordinary SEO is the base, and
   the structure, authority and presence work below is what the studies and company pages point
   to for being cited." Draft:

   > Two 2026 studies put being found ahead of what is on the page. Both are preprints on arXiv
   > with no venue listed.
   >
   > - [Chen & Koudas](https://arxiv.org/abs/2610.15033) (October 2026; we read the full text)
   >   followed 158,099 answers that ChatGPT, Gemini and Perplexity gave through their APIs (not
   >   the apps people use) over 90 days, to English commercial questions about the US market:
   >   one set for an internet provider, one for small B2B software vendors.
   >   Comparing pages of the same website, a title and a paragraph that answer the question went
   >   with more citations. FAQ blocks, structured data, summary boxes and page speed went with
   >   more citations only when different websites were compared, not between pages of one
   >   site. When the authors replayed the questions through ChatGPT's API, every page it cited
   >   was one its own search had retrieved, and which pages that search found explained 32% of
   >   the differences in citations between pages of a website, all page features together 2.8%.
   >   Little-known vendors were named mainly when a page on another site that the engine cited
   >   named them. These citation and retrieval findings are associations, not experiments, and
   >   an engine's API need not behave like its app.
   > - [Martinez](https://arxiv.org/abs/2607.14035) (July 2026; we read its summary and two
   >   passages) reviewed 45 GEO studies. The 2023 GEO paper's gains (the table in Pillar 2) were
   >   measured with the page already in front of the engine, and no technique reviewed showed a
   >   stable, long-term, cross-platform causal effect on being found or on what readers do
   >   next. Relevance to the question was among the most reproducible levers.
   >
   > So ordinary SEO is still the base, and the first job is a page the engine's search finds:
   > for each question that matters, a page whose title and a paragraph answer it in the words a
   > customer would use. Engines match by meaning, so you don't need a page for every phrasing
   > (Google's [guide](…ai-optimization-guide) says the same). For a little-known business,
   > being named on other sites (Pillar 3) is part of being found. Pillars 1 and 2 are about a
   > page once it is found.

2. **"Critical stats"**, GEO bullet: append that the gains were measured on pages already given
   to the engine (see "What the 2026 studies found").
3. **"The Three Pillars"**: one line above the code block: "Start with being found (above).
   For a little-known business, presence (Pillar 3) is part of being found; structure and
   authority (Pillars 1 and 2) are about a page once it is found." Pillar 1 is left as it is:
   the paper's results on headings, lists and length differ between its two steps (no effect
   within a website; at equal rank, more headings and shorter pages went with more citations and
   lists with fewer), and for headings between its two datasets, so the skill makes no claim
   about them.
4. **Pillar 2, the GEO table**: the lead sentence names it "the 2023 GEO lab study" and adds that
   both its tests handed the engine the pages to cite, so the gains apply to a page already
   retrieved: ways to improve a found page, not the main lever. The table and its numbers stay.
   The bullet headings "Statistics and data (+31% in the GEO study)" and "Expert attribution
   (+41% for quotations in the GEO study)" lose their figures (the table keeps them).
5. **Audit**: Step 2 gets a first bullet, "Retrieval — do you have a page whose title and a
   paragraph answer this question? Is theirs a closer answer?"; Step 3's checklist gets a first
   row, "Title and one paragraph (anywhere on the page) answer the question this page is for?".
6. **Common Mistakes**: one new bullet, "Tuning a page no engine finds": the GEO gains were
   measured on pages the engine already had, and in 2026 FAQ blocks and schema went with more
   citations only across websites, not within one; start with a page that answers the question.
7. **Consistency outside SKILL.md**: `references/platform-ranking-factors.md` ("What the studies
   add") and `references/content-patterns.md` (the GEO patterns' lead) each get one clause: the
   gains were measured on pages already given to the engine. `evals/evals.json` eval 1: the
   expected output puts being found before the pillars and the GEO findings as conditional; the
   assertion "Applies three pillars framework (Structure, Authority, Presence)" becomes "Starts
   with being found, then applies the three pillars", and "References Princeton GEO research
   findings" adds "as gains for a page already retrieved".

Left as it is: everything else in the file, including "Best combination: Fluency + Statistics"
(not re-checked here; this change adds no sentence to it), the "Princeton" name, and the
Wikipedia, Reddit and content-type figures.

## How it is tested

Prose an agent follows; nothing runs. Checks: `make check` (it includes `check_clean.sh`, no
client names), a JSON parse of `evals/evals.json` (syntax only), and a hand check of every new
or changed sentence against the READs (about twenty sentences). The claims sweep on the branch
is an aid to that check: it lists sentences that use words from its own list of absence and
universality words, and does not replace reading the rest. The hand check is the only check on
meaning before the DIFF gate. The eval change is checked by reading it; no eval run is planned
(a search for "evals" in `scripts/`, `.github/` and the `Makefile` finds nothing; a runner
outside them would not show).

## Review

PLAN gate at Normal (an instruction file an agent loads): Codex and GLM 5.3 on melious, plus
Sonnet fresh-eyes in round 1; if melious is out of balance, Codex alone, as the rules allow. DIFF
gate at Normal. Cost so far: rounds 1–3 of this gate logged 380,846 tokens with every seat
counted (fresh-eyes's 110,426 among them). A DIFF gate of the same shape would cost about as
much, so expect 700,000–800,000 tokens for both gates. A judgment, not a measurement.

Counter-argument: two preprints now come before a KDD paper in the skill's order. The answer is
scope: the GEO paper's tests handed the engine the pages, so they did not test being found, and
the 2026 work answers that question; the skill says "preprint" in the sentence. If either
preprint is withdrawn or contradicted, these places depend on it: the new subsection, the
Critical-stats clause, the line above the pillars, the Pillar 2 lead, the audit bullet and row,
the Common Mistakes bullet, the two reference clauses and eval 1.
