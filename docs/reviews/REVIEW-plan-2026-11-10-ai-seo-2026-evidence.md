# PLAN review — `ai-seo` leads with being found, then the GEO table

Artifact: `docs/reviews/SKILL-PLAN-ai-seo-2026-evidence.md`. Depth: Normal (an instruction file an
agent loads; no High-row item). Seats: Codex (gpt-6.1-sol) + GLM 5.3 on melious; fresh-eyes
(Sonnet 5.5 sub-agent, read-only) in round 1. Gate id 20261110T065111Z-28235. Evidence: the
sources re-opened on 2026-11-10, as READs (curl of arXiv abstract pages, PDFs through `pdftotext`,
Google's guide), sent with `--evidence` every round.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | bcf7ade7 | full plan | codex · melious · fresh-eyes | codex 141 s, 54,180 · melious 187 s, 21,203 · fresh-eyes 56 s, 110,426 | 3/6/5 (after dedup) |
| 2 | ad98e60e | full plan, --verify | codex (medium) · melious | codex 145 s, 56,041 · melious 347 s, 32,742 | 0/1/6 (codex: none) |
| 3 | 34fc6e99 | full plan, --verify | codex · melious | codex 122 s, 67,027 · melious 415 s, 39,227 | 1/1/4 |
| 4 | 040595a8 | full plan, --verify, earned by cost-arithmetic, corpus-description | codex · melious | codex 85 s, 45,753 · melious 389 s, 33,679 | 0/0/5 (codex: none) |
| wording pass | 9ab36a11 | delta of round 4's fixes (`--diff --base 040595a8`), --verify | codex | codex 113 s, 48,064 | none |

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
| R2-1 | RISK | melious | 2 | Sweep credited with a word list it does not match; sentences with other words pass unchecked | fixed | How it is tested: every new sentence is hand-checked; the sweep is an aid with its own list |
| R2-2 | NIT | melious | 2 | "Associations, not tested causes" is false for the paper's controlled brand experiments | fixed | Scoped: "These citation and retrieval findings are associations, not experiments" |
| R2-3 | NIT | melious | 2 | "Limits it states: associations" not shown in a READ | fixed | READ 2c: "Limitations. The results are associations"; quoted in the row |
| R2-4 | NIT | melious | 2 | "Presence is part of being found" generalizes the small-vendor finding | fixed | Scoped to "a little-known business" in the draft and How 3 (READ 2b) |
| R2-5 | NIT | melious | 2 | Evals claim rests on a literal-string search | fixed | Searched "evals" case-insensitively (READ 5); sentence says a runner elsewhere would not show |
| R2-6 | NIT | melious | 2 | Cost estimate counted Codex only | fixed | Review section uses this gate's logged total, every seat |
| R2-7 | NIT | melious | 2 | Martinez bullet omits "or downstream behavior" | fixed | Draft adds "or on what readers do next" (READ 3) |
| U3 | — | melious (UNVERIFIABLE) | 2 | "A KDD paper" not in a READ | supported | READ 8: "Accepted to KDD 2024" |
| R3-1 | BUG | codex | 3 | Cost line said "about 385,000" for rounds 1–2; the logged seats sum to 274,592 (fresh-eyes was counted twice) | fixed | Review section: rounds 1–3 logged 380,846 tokens, every seat counted; projection 700,000–800,000 |
| R3-2 | RISK | melious | 3 | No READ shows both collections used all three engines | fixed | READ 2d: both datasets from "the public API of each engine" (GPT-5.4 nano, Gemini 3.1 Flash Lite, Sonar); draft says the answers came through the APIs, not the apps, and names each collection |
| R3-3 | NIT | melious | 3 | How 3 says headings, lists and length differ between datasets; READs show that for headings only | fixed | How 3: "differ between its two steps …, and for headings between its two datasets" |
| R3-4 | NIT | melious | 3 | "Pillars 1 and 2 improve a page once it is found" is an efficacy claim the evidence does not make for Pillar 1 | fixed | Draft and How 3: "are about a page once it is found" |
| R3-5 | NIT | melious | 3 | "Strongest numbers … +41%/+31%" and "honest about its setting" have no READ | fixed | What and why points to `SKILL.md:182–183` (the figures) and `:178` (the lead naming its setting); "honest" cut |
| R3-6 | NIT | melious | 3 | "Best combination" and "Princeton" left unchecked | no action | The plan says so; outside this change |
| R4-1 | NIT | melious | 4 | "Strongest numbers are the 2023 GEO paper's": `SKILL.md:182–183` shows the skill states them, not that the paper does | fixed | What and why: "are ones it credits to the 2023 GEO paper"; the plan makes no claim about the paper's figures |
| R4-2 | NIT | melious | 4 | Cost line names no log rows (U2's fix lapsed) | fixed | Review section names the gate id and the nine rows of 2026-11-10; total 460,278 summed from them |
| R4-3 | NIT | melious | 4 | "For small B2B software vendors" (plural); READ 2d says "written for a small vendor in that market" | fixed | Draft and source row: "one for a small B2B software vendor" |
| R4-4 | NIT | melious | 4 | Vishwakarma et al. characterised with no READ | fixed | Characterisation cut: "named in the research notes, was not re-read and is left out" |
| R4-5 | NIT | melious | 4 | The claims sweep catches nothing the hand check does not | no action | The independent-review skill, step 2: "A prose change gets the sweep at every depth"; it is an aid, as the plan says, and costs no review tokens |

Claims sweep (`sweep_claims.sh --file` on the plan at 9ab36a11): 42 sentences listed, each checked
against the READs. One narrowed: "the 2026 work answers that question" became "addresses". The
rest hold as written.

Gate total: rounds 1–4 and the wording pass, 10 seat runs, 508,342 tokens logged (fresh-eyes
included). Result: CLEAN. No BUG or RISK open; every NIT fixed, refuted with evidence, or answered.
