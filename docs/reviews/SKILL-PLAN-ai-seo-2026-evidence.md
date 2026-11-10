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
paper's (+41% for quotations, +31% for statistics). That table is honest about its setting, but
it reads as the main lever. Two 2026 studies say the main lever comes earlier: the engine's own
search has to find the page. Page features matter far less, and the GEO paper's gains hold only
for a page the engine already has. For a small business this changes the first job: one page per
important question, whose title and a paragraph answer it.

The change opens the strategy with that finding, says both studies are preprints, and keeps the
GEO table, demoted to "for a page already found". No table row, figure or source is deleted.

## Sources, re-opened on 2026-11-10

Each was fetched again on 2026-11-10 (curl of the arXiv abstract page and Google's guide; the
full PDF for Chen & Koudas). The DIFF gate's evidence file carries the quoted passages as READs.

| Source | What was read | What the new text may say |
|---|---|---|
| Chen & Koudas, "What Drives AI Citations? Content, Retrieval and Model Knowledge in Generative Engine Optimization (GEO)", [arXiv 2610.15033](https://arxiv.org/abs/2610.15033), submitted 10 Oct 2026 | Abstract and full PDF (11 pages, no venue: the PDF's header is a blank conference template) | 158,099 answers, 468,037 citations, two 90-day collections, commercial questions, ChatGPT, Gemini and Perplexity. Within a website, title match and best-paragraph match pass all five of its robustness tests; first-paragraph match fails one. FAQ blocks, structured data, summary and author boxes and page speed "appear effective only across websites". The best-matching paragraph sits at a median of 45% of the page length: "It need not be at the top". "Every page ChatGPT cites is one its own search retrieved." Retrieval explains 32% (95% CI 24–42%) of the within-website variation in ChatGPT's 90-day citation counts, all page features 2.8%. Engines match "in meaning". Limits it states: associations; English questions about the US market; Perplexity could not be replayed |
| Martinez, "Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization (2023-2026)", [arXiv 2607.14035](https://arxiv.org/abs/2607.14035), submitted 15 Jul 2026 | Abstract only | 45 studies. The foundational paper's gains are "conditional on a source already being present in a fixed context"; "topical relevance and context position are the most reproducible levers"; "no reviewed technique shows a stable, longitudinal, cross-platform causal effect on organic discoverability" |
| Google, "Optimizing your website for generative AI features on Google Search", [guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), last updated 2026-07-10 | Whole page | "AI systems can understand synonyms and general meanings of what someone is seeking"; chunking, AI rewrites, inauthentic mentions and overfocusing on structured data are listed under "things you can ignore for Google Search" |

Neither arXiv paper shows a peer-review venue on its abstract page. The research notes of
2026-10-28 read Chen & Koudas as an abstract only; today's full read closes that gap, and
Martinez stays abstract-only. Vishwakarma et al. (arXiv 2605.25517, a lab test with two pages)
supports the same point, but the two above suffice; it is left out to keep the text short.

## Two places the wording differs from the brief

1. **"Title and opening lines."** The paper found a title and *a* paragraph (its best-matching
   one) that answer the question; first-paragraph match failed one robustness test, and the
   paper says the matching paragraph "need not be at the top: the engines find it wherever it
   is". So the skill says "a title and a paragraph", and keeps answer-first writing as advice for
   readers, not as a study finding.
2. **"The exact question."** The paper says engines match "in meaning", and Google says its
   systems understand synonyms. So the skill says "the question, in the words a customer would
   use", not exact phrasing, and warns against a page per phrasing (Google's scaled-content note).

## How (all in `skills/ai-seo/`)

1. **New subsection under "Key Difference from Traditional SEO"**, after the Google paragraph,
   named "What the 2026 studies found". It replaces the sentence "So ordinary SEO is the base, and
   the structure, authority and presence work below is what the studies and company pages point
   to for being cited." Draft:

   > Two 2026 studies put being found ahead of anything on the page. Both are preprints, not yet
   > peer reviewed.
   >
   > - [Chen & Koudas](https://arxiv.org/abs/2610.15033) (October 2026; we read the full text)
   >   followed 158,099 answers from ChatGPT, Gemini and Perplexity to English buying questions
   >   about the US market. Comparing pages of the same website, a title and a paragraph that
   >   answer the question went with more citations. FAQ blocks, structured data, summary boxes
   >   and page speed did not. Every page
   >   ChatGPT cited was one its own search had retrieved: which pages that search found explained
   >   32% of the differences in ChatGPT's citations between pages of a website, all page features
   >   together 2.8%. These are associations, not tested causes.
   > - [Martinez](https://arxiv.org/abs/2607.14035) (July 2026; we read its summary) reviewed 45
   >   GEO studies. The 2023 GEO paper's gains (the table in Pillar 2) hold only for a page the
   >   engine already has in front of it, and no technique reviewed showed a lasting effect on
   >   being found across engines. Relevance to the question was among the most reproducible
   >   levers.
   >
   > So ordinary SEO is still the base, and the first job is a page the engine's search finds:
   > for each question that matters, one page whose title and a paragraph answer it in the words
   > a customer would use. Engines match by meaning, so one good page per question beats a page
   > per phrasing (Google's [guide](…ai-optimization-guide) says the same). The pillars below
   > help a page once it is found.

2. **"Critical stats"**, GEO bullet: append that the gains were measured on pages already given
   to the engine (see "What the 2026 studies found").
3. **"The Three Pillars"**: one line above the code block: "Start with being found (above). The
   pillars help a page the engine has already found." Pillar 1 is left as it is: the paper's
   results on headings, lists and length differ between its two datasets and its two steps
   (retrieval, then choosing among retrieved pages), so the skill makes no claim about them.
4. **Pillar 2, the GEO table**: the lead sentence names it "the 2023 GEO lab study" and adds that
   its engine was handed the pages to cite, so the gains apply only to a page already retrieved.
   Treat the methods as ways to improve a found page, not as the main lever. The table and its
   numbers stay. The bullet headings "Statistics and data (+31% in the GEO study)" and "Expert
   attribution (+41% for quotations in the GEO study)" lose their figures (the table keeps them).
5. **Audit**: Step 2 gets a first bullet, "Retrieval — do you have a page whose title and a
   paragraph answer this question? Is theirs a closer answer?"; Step 3's checklist gets a first
   row, "Title and one paragraph answer the question this page is for?".
6. **Common Mistakes**: one new bullet, "Tuning a page no engine finds": the GEO gains were
   measured on pages the engine already had, and FAQ blocks and schema showed no within-site
   effect in 2026; start with a page that answers the question.
7. **Consistency outside SKILL.md**: `references/platform-ranking-factors.md` ("What the studies
   add") and `references/content-patterns.md` (the GEO patterns' lead) each get one clause: the
   gains were measured on pages already given to the engine. `evals/evals.json` eval 1: expected
   output and assertions put being found before the pillars, and the GEO findings as conditional.

Left as it is: everything else in the file, including "Best combination: Fluency + Statistics"
(not re-checked here; this change adds no sentence to it), the "Princeton" name, and the
Wikipedia, Reddit and content-type figures.

## How it is tested

Prose an agent follows; nothing runs. Checks: `make check` (it includes `check_clean.sh`, no
client names), the claims sweep on the branch, a JSON parse of `evals/evals.json`, and a read of
every new sentence against the table above. The eval change is checked by reading it; no eval run
is planned (nothing in `scripts/`, `.github/` or the `Makefile` reads `evals.json`).

## Review

PLAN gate at Normal (an instruction file an agent loads): Codex and GLM 5.3 on melious, plus
Sonnet fresh-eyes in round 1; if melious is out of balance, Codex alone, as the rules allow. DIFF
gate at Normal. Expected cost: about 250,000–400,000 tokens for both gates together, from recent
Normal plan and diff rounds in the review log (30,000–80,000 tokens per Codex round, about three
rounds each). A judgment, not a measurement.

Counter-argument: two preprints, one read only in summary, now outrank a peer-reviewed KDD paper
in the skill's order. The answer is scope: the GEO paper's own setting (pages handed to the
engine; Martinez: gains "conditional on a source already being present in a fixed context") did
not test being found, so the 2026 work answers a question it did not ask, and the
wording says preprint in the sentence. If either preprint is withdrawn or contradicted, the new
subsection is the one place to change.
