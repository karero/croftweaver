# DIFF review — PR #235 — Match the ai-seo GEO table to the paper's Table 1
Base `d717d3e` · depth: Normal (a SKILL.md change an agent follows; the owner's standing rule keeps those off Light) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened PR #235); WORKTREE-WRITE — atom A (this session's own worktree); BRANCH-COMMIT — atom A (this session created the branch)

Data consent: the owner asked for the Codex + GLM pair on this repo earlier in this session ("run the Codex + GLM review on #231") and approved this PR ("yes"). A grep of the brief for keys, tokens and passwords found nothing. The text-only GLM seat got the paper's tables and prose as excerpts marked "context, not under review". ollama-cloud received nothing; Antigravity was not used.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `1b216ce` | full: `d717d3e...1b216ce`, 2 files, plus paper excerpts | codex-cli 0.162.0, gpt-6.1-sol, effort from config, read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction, no shared context, fetched the paper | codex 165 s / 45,700; melious 70 s / 11,997; fresh-eyes 73 s / 93,439 | 1/2/3 (after dedup) |
| 2 | `36834a5` | delta `1b216ce..36834a5`, plus paper excerpts | codex medium; melious glm-5.3 | codex 100 s / 29,731; melious 37 s / 13,417 | 1/1/1 |
| wording | `6da1ed2` | delta `36834a5..6da1ed2`, one paragraph | codex medium, `--seat codex` | codex 42 s / 12,437 | 0/0/0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | fresh-eyes; melious (NIT) | 1 | "a smaller test on Perplexity showed smaller gains" is wrong on the subjective measure (statistics +37%) | fixed, externally_reverified (r2) | `36834a5`; paper: "up to 9% and 37% on the two metrics"; Table 5 statistics 33.9 vs 24.7 (fresh-eyes) |
| F2 | RISK | codex | 1 | "how much of a page's wording shows up" mis-states the measure | fixed, externally_reverified (r2, wording) | `36834a5`, `6da1ed2`: Position-Adjusted Word Count, defined as in the paper |
| F3 | NIT | melious, fresh-eyes | 1 | the Table 1 sub-column was not named | fixed, externally_reverified (r2) | "Overall column of Table 1" |
| F4 | RISK | fresh-eyes | 1 | keyword stuffing "actively hurts" holds only on the word-count measure | fixed, externally_reverified (r2) | Table 1: 17.7 vs 19.3 word count, 20.2 vs 19.3 subjective |
| F5 | NIT | melious | 1 | the same edits hurt first-ranked sources; no caveat | fixed, externally_reverified (r2) | Table 2 rank 1: −30.3, −22.9, −20.6 |
| F6 | NIT | fresh-eyes | 1 | 27-41% / 13-28% differ from the paper's prose 30-40% / 15-30% | fixed, externally_reverified (r2) | the paper's lines: "30-40% on the Position-Adjusted Word Count metric and 15-30% on the Subjective Impression metric" |
| G1 | BUG | codex | 2 | the measure's definition omitted equal sharing between co-cited sources | fixed, externally_reverified (wording pass) | `6da1ed2` |
| G2 | RISK | melious | 2 | "statistics did best there" claims a ranking the paper's prose does not state | fixed, externally_reverified (wording pass) | `6da1ed2`: "gained up to 37%" |
| G3 | NIT | melious | 2 | "gains" introduces a table ending in a loss | fixed, externally_reverified (wording pass) | `6da1ed2` |

9 findings (2 BUG, 3 RISK, 4 NIT): all fixed. No refutation, waiver or deferral.

Follow-ups: `skills/ai-seo/references/content-patterns.md:174` speaks of citation rates and `skills/ai-seo/evals/evals.json:36` of citation probability, while the GEO study measured visibility in answers (codex r1 UNVERIFIABLE, r2 outside scope).

Notes: G1 changed a definition's precision, not what a reader does, so round 2 found no substantive BUG and the rounds ended; its three fixes went to one Codex wording pass, which was clean. All nine table figures were recomputed from Table 1 by the host and by all three seats.
