# DIFF review — PR #237 — Fix the ai-seo citation-rate line and the made-up examples
Base `abfbca1` (merge-base `12bbe18` after merging main at `be05281`; the merge link was empty) · depth: Normal (a reference file agents load; the owner's standing rule keeps those off Light) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened PR #237); WORKTREE-WRITE — atom A (this session's own worktree); BRANCH-COMMIT — atom A (this session created the branch)

Data consent: the owner asked for the Codex + GLM pair on this repo earlier in this session ("run the Codex + GLM review on #231") and asked for these fixes ("Do you want to fix them now?"). A grep of the brief for keys, tokens and passwords found nothing. The text-only GLM seat got the SKILL.md GEO table as marked context. ollama-cloud received nothing; Antigravity was not used.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `cc7e552` | full: `abfbca1...cc7e552`, 2 files, plus context | codex-cli 0.162.0, gpt-6.1-sol, effort from config, read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction, no shared context, fetched the paper | codex 66 s / 32,965; melious 16 s / 5,330; fresh-eyes 41 s / 90,707 | 0/4/7 |
| 2 | `471df53` | delta `cc7e552..471df53`, plus context | codex medium; melious glm-5.3 | codex 58 s / 30,684; melious 76 s / 6,378 | 0/0/2 |
| wording | `68c5e06` | delta `471df53..68c5e06`, one line | codex medium, `--seat codex` | codex 43 s / 18,746 | 0/0/0 |
| merge link | `be05281` | `merge_link.sh abfbca1 68c5e06 12bbe18`: empty (main brought PR #230, no shared files) | — | — | — |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| C1 | RISK | codex | 1 | eval 3 keeps the unsourced ~33% / ~15% content-type shares | follow-up: text this PR did not change; a separate session was offered for the whole content-type table | — |
| C2 | RISK | codex | 1 | "+31%" not checked against the paper | refuted | fresh-eyes fetched arXiv 2311.09735: Table 1 Overall, Statistics Addition 25.2 / No Optimization 19.3 = 1.306 |
| M1 | NIT | melious | 1 | ":174 omits that the study ran mostly on its own engine" | fixed, externally_reverified (r2) | `471df53` |
| M2 | NIT | melious | 1 | ":174 ignores the first-rank loss (statistics −21%)" | fixed, externally_reverified (r2) | `471df53`; Table 2 rank 1: −20.6 |
| M3 | NIT | melious | 1 | eval 3 mixes citation and visibility wording | follow-up, with C1 | — |
| M4 | NIT | melious | 1 | the quote note reads as if quoting always needs permission | fixed, externally_reverified (r2) | `471df53` |
| F1 | RISK | fresh-eyes | 1 | Self-Contained Answer example put "77% more backlinks" in HubSpot's mouth, unchecked | fixed, externally_reverified (r2) | `471df53`: labelled made up, "Example Research Co." |
| F2 | RISK | fresh-eyes | 1 | Definition example: "over 60% of Google searches now end without a click", unsourced | fixed, externally_reverified (r2) | sentence removed |
| F3 | NIT | fresh-eyes | 1 | Step-by-Step example: "snippets appear within 2-4 weeks", unsourced | fixed, externally_reverified (r2) | line removed |
| F4 | NIT | fresh-eyes | 1 | German FAQ example gave an unsourced national price | fixed, externally_reverified (r2) | "in unserer Praxis 95 Euro", labelled made up |
| F5 | NIT | fresh-eyes | 1 | Expert Quote lead-in "increases citation likelihood", unsourced | fixed, externally_reverified (r2); see W1, W2 | `471df53` |
| W1 | NIT | melious | 2 | the quotations line lacks the first-rank caveat (−22.9%) | fixed, externally_reverified (wording pass) | `68c5e06` |
| W2 | NIT | melious | 2 | "the most of any method" overstates scope | fixed, externally_reverified (wording pass) | `68c5e06`: "of the nine methods it tested" |

13 findings (0 BUG, 4 RISK, 9 NIT): 10 fixed, 1 refuted, 2 follow-ups. No waiver, no deferral.

Follow-ups: the content-type citation shares in `skills/ai-seo/SKILL.md` (~33%, ~15% …) and eval 3, which repeats two of them (C1, M3); offered as a separate session.

Notes: round 2 found no BUG or RISK, so the rounds stopped; its two NITs went to one Codex wording pass, which was clean. Codex marked the GEO figures UNVERIFIABLE in every pass (no network); fresh-eyes read the paper's Tables 1 and 2 in round 1.
