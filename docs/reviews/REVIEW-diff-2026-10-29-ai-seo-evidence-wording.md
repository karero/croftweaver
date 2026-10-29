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
| 1 (Codex alone; melious out of balance, no rerun owed) | BUG: "each buyer question 3 times" is wrong for Google's AI Mode and AI Overview, which get one answer (`geo_check.py` `samples_for`). RISK: the generative AI report gives site impressions, not which queries showed an AI Overview. RISK: "leave the control alone" assumes it is not already set to opt out, possibly by inheritance. RISK: "every 2 or 4 weeks is enough to see a trend" has no support | fixed: Google's engines named as one answer each; the report labelled as site impressions; both control lines say look at what the property shows, inheritance included; the trend sentence is replaced by "judge a trend over several runs" |
| 2 (Codex alone; melious out of balance) | BUG: the new BUGLOG row still said every 2 or 4 weeks "is enough", a claim the skill no longer makes. Unsupported: "every ask is a paid search" | fixed: the row says what the skill suggests; the line now says each Google answer costs a SerpApi search, as `geo_check.py` `samples_for` and `geo-check.md` count them |

Checks before review: `make check` exit 0 ("all checks passed"; the usual local warning on
`website-review`'s description length, which this diff does not touch). `scripts/check_clean.sh`
OK; `scripts/check_buglog_rows.sh` OK.
