# PLAN review — `ai-seo` leads with being found, then the GEO table

Artifact: `docs/reviews/SKILL-PLAN-ai-seo-2026-evidence.md`. Depth: Normal (an instruction file an
agent loads; no High-row item). Seats: Codex (gpt-6.1-sol) + GLM 5.3 on melious; fresh-eyes
(Sonnet 5.5 sub-agent, read-only) in round 1. Gate id 20261110T065111Z-28235. Evidence: the
sources re-opened on 2026-11-10, as READs (curl of arXiv abstract pages, PDFs through `pdftotext`,
Google's guide), sent with `--evidence` every round.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | bcf7ade7 | full plan | codex · melious · fresh-eyes | codex 141 s, 54,180 · melious 187 s, 21,203 · fresh-eyes 56 s, 110,426 | 3/6/4 (after dedup) |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex, fresh-eyes (RISK) | 1 | Martinez bullet dropped "causal" and "organic discoverability" | fixed | Draft now: "no technique reviewed showed a stable, long-term, cross-platform causal effect on being found" (READ 3) |
| F2 | BUG | codex | 1 | "The pillars help a page once it is found" is wrong for Pillar 3, which is about being found elsewhere | fixed | Draft and How 3: presence (Pillar 3) helps you be found; Pillars 1 and 2 improve a found page. Support: small vendors "depend on being found by search and on third-party pages that name them" (READ 2b) |
| F3 | BUG | codex | 1 | "The new subsection is the one place to change" is wrong: How 2–7 repeat the conclusions | fixed | Review section lists every dependent place |
| F4 | RISK | codex, fresh-eyes | 1 | "One good page per question beats a page per phrasing" has no support, and prescribes a URL count | fixed | Draft: "you don't need a page for every phrasing"; "a page whose title and a paragraph answer it", no count (READ 4) |
| F5 | RISK | codex, melious | 1 | ChatGPT retrieval result stated without the API-replay limit; limits row dropped the replay and the third of URLs not analysed | fixed | Draft: "When the authors replayed the questions through ChatGPT's API … the API need not behave like the ChatGPT app"; limits row adds both (READ 2) |
| F6 | RISK | fresh-eyes | 1 | Draft dropped the across-site half: FAQ blocks etc. did go with more citations across websites | fixed | Draft: "went with more citations only when different websites were compared, not between pages of one site"; How 6 likewise |
| F7 | RISK | fresh-eyes | 1 | GEO paper's Perplexity test may not have handed the engine the pages | refuted | READ 6: "we instead provide source text as file uploads to perplexity.ai while ensuring all answers are generated only using the file sources provided"; READ 7: "texts uploaded as files rather than web pages retrieved organically". Source table gains a GEO-paper row |
| F8 | RISK | fresh-eyes | 1 | Martinez's "foundational paper" assumed to be the 2023 GEO paper | fixed | READ 7: section 4 "The Foundational Paper", "Aggarwal et al. [2024] introduced …"; the source row says so |
| F9 | RISK | fresh-eyes | 1 | "A read of every new sentence against the table" credited with more than it catches | fixed | How it is tested: the sweep's words, the hand check, and what passes both (a narrowing with no such word) are named; DIFF gate covers the rest |
| F10 | NIT | fresh-eyes | 1 | "No figure is deleted" vs two bullet headings losing figures | fixed | What and why says so |
| F11 | NIT | fresh-eyes | 1 | New Step 3 row beside "Clear definition in first paragraph?" may read as mixed advice | fixed | Row reads "Title and one paragraph (anywhere on the page) …" |
| F12 | NIT | fresh-eyes | 1 | Eval 1 assertions could demand two first things | fixed | How 7 names the replaced assertion |
| F13 | NIT | melious | 1 | "Scaled-content note" label not in the evidence | fixed | READ 4 extended to the line "scaled content abuse spam policy"; quoted in the Google row |
| F14 | NIT | melious | 1 | "158,099 answers … to English buying questions" reads as one consumer corpus | fixed | Draft: "two 90-day collections of English commercial questions about the US market, one of them about small B2B vendors" |
| U1 | — | codex (UNVERIFIABLE) | 1 | Blank venue does not establish "not yet peer reviewed" | fixed | Draft and plan say "preprints on arXiv with no venue listed" |
| U2 | — | codex (UNVERIFIABLE) | 1 | Cost estimate has no cited rows | fixed | Review section names the log rows it is guessed from (2026-11-09 Normal rounds) and stays labelled a judgment |
