# DIFF review — `ai-seo` leads with being found, then the GEO table

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'` (the skill, its two
references and eval 1). Plan: `docs/reviews/SKILL-PLAN-ai-seo-2026-evidence.md`, PLAN gate clean
(trail `REVIEW-plan-2026-11-10-ai-seo-2026-evidence.md`). Depth: Normal. Seats: Codex + GLM 5.3 on
melious; fresh-eyes (Sonnet 5.5 sub-agent, read-only) in round 1. Gate id 20261110T083952Z-3816.
Evidence: the PLAN gate's READs, plus READs 2e, 2f, 7c and 9 and the `make check` record.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 7cab775a | full diff | codex · melious · fresh-eyes | codex 120 s, 52,508 · melious 221 s, 21,758 · fresh-eyes 36 s, 107,148 | 0/2/6 |
| 2 | ccdf0b67 | full diff, --verify | codex · melious | codex 95 s, 39,790 · melious 343 s, 29,421 | 0/1/1 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| D1 | RISK | fresh-eyes | 1 | "A title and a paragraph that answer the question went with more citations" hides that the title effect did not hold for ChatGPT | fixed | READ 2e: "the best-paragraph effect holds for each engine …, whereas title match goes with more citations from Gemini (+16.8%) and Perplexity (+4.7%) but not from ChatGPT (−0.2%), which rewrites a question into its own searches". The bullet now says so |
| D2 | RISK | codex | 1 | "Not the main lever" (Pillar 2 lead) claims a comparison of interventions no study made | fixed | Lead now: "ways to improve a page once it is found; they do not get a page found", which READ 6 supports (both tests handed the engine the pages). "The first job is a page the engine's search finds" stays: it is advice after "So", resting on READ 2f ("a page is cited only after it has been retrieved") |
| D3 | NIT | melious | 1 | "Read in full" not shown by the READs, which quote passages | refuted | READ 9: the whole 11-page PDF was converted to text (1,467 lines) and read; the READs quote only what each sentence rests on |
| D4 | NIT | melious | 1 | FAQ/schema finding drops the paper's hedge and the equal-rank result (×0.93, ×0.92, ×0.77) | fixed | READ 2f. Chen & Koudas bullet adds "In that replay, at equal search rank, author boxes, FAQ blocks and schema markup went with slightly fewer citations"; Common Mistakes adds "and with slightly fewer at equal search rank". The hedge is carried by the bullet's "associations, not experiments" |
| D5 | NIT | melious | 1 | "Reviewed 45 GEO studies" overstates the corpus | fixed | READ 7c: "reviews 45 studies selected under a November 2023–July 2026 publication window … plus relevant RAG and evaluation work". Now: "reviewed 45 studies published from November 2023 to July 2026" |
| D6 | NIT | melious | 1 | Eval 1's edit is read by no runner in the repo | no action | The plan says so (How it is tested; READ 5); wiring evals is outside this change |
| D7 | NIT | fresh-eyes | 1 | `content-patterns.md` +31% and +41% blocks lack the "already retrieved" wording | no action | The section's lead (`content-patterns.md:168`) now carries it for every block below it |
| D8 | NIT | fresh-eyes | 1 | Critical-stats bullet ends without a period | no action | No bullet in that list ends with a period; matches the list |
| D9 | RISK | codex | 2 | D2's fix "they do not get a page found" claims the edits cannot help retrieval; READ 6 shows only that it was not tested | fixed | Lead now: "ways to improve a page once it is found. Whether they help a page get found was not tested" |
| D10 | NIT | melious | 2 | Eval 1 keeps the per-method GEO figures that no READ backs, while the diff drops them from two SKILL.md headings | follow-up | The figures are not this change's: the diff appends one clause to that line, and the table (`SKILL.md`, Pillar 2) keeps the same figures. READ 6b, Table 1's caption: "The best methods improve upon baseline by 41% and 28% on Position-Adjusted Word Count and Subjective Impression"; a per-row check of Table 1 is outside this change |

UNVERIFIABLE (round 1): Codex 5, melious 3. Pre-existing figures the diff does not touch
(BrightEdge, Ahrefs, AirOps, the GEO table's numbers, Google's ai-features page) are outside this
change. "Read in full" became D3. The test record now carries its head line (7cab775a). Codex's
note that the budget self-test could not write in its sandbox is about its sandbox, not the
change: the full `make check` run passed.
