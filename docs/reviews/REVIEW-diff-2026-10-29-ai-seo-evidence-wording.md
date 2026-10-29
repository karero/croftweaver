# DIFF review: ai-seo evidence wording (monitoring, llms.txt, Bing, Search generative AI)

No plan: wording corrections to skill instructions, which go straight to the DIFF review. Gate:
independent-review DIFF, depth Normal (skill instruction text and a starter comment). Seats:
Codex + GLM 5.3 on melious.

Sources were fetched on 2026-10-29 and quoted verbatim in the evidence file each round: Bing's
AI Performance post (10 Feb 2026), Google's AI optimization guide, Search Console's "Search
generative AI control" help page, the OpenAI, Perplexity and Anthropic crawler pages, and
arXiv 2604.07585.

| Round | Findings | Disposition |
|---|---|---|

Checks before review: `make check` exit 0 ("all checks passed"; the usual local warning on
`website-review`'s description length, which this diff does not touch). `scripts/check_clean.sh`
OK; `scripts/check_buglog_rows.sh` OK.
