# DIFF review — `ai-seo` says the 85% figure is one vendor's study

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`, two sentences in
`skills/ai-seo/SKILL.md` (Critical stats, Pillar 3). A wording change, so no plan; the follow-up
was noted in the private feature hub's GEO ideas. Depth: Normal (an instruction file an agent
loads). Seats: Codex + GLM 5.3 on melious, fresh-eyes (Sonnet 5.5 sub-agent, read-only) in round
1. Melious was out of balance in round 1, so every round stands on Codex alone (the owner's rule
of 2026-10-27). Gate id 20261110T111055Z-47989. Evidence: the AirOps report re-opened on
2026-11-10 with curl, quoted as READs 1–5, plus the `check_clean.sh` record.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 0e36472b | full diff | codex · melious (out of balance) · fresh-eyes | codex 92 s, 48,409 · fresh-eyes 31 s, 90,505 | 0/1/2 (after dedup) |
| 2 | 4fe1c67a | delta, `--verify --base 0e36472b` | codex | codex 56 s, 21,953 | 0/1/0 |
| 3 | 15ae6a9b | delta, `--verify --base 4fe1c67a` | codex | codex 64 s, 29,009 | 0/0/0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | RISK | codex, fresh-eyes | 1 | Called all 500+ queries business-software questions asked in the ChatGPT, Claude and Perplexity apps; the report names four of its six categories and tested models | fixed | READ 2: "six verticals: MarTech, Sales, HR/Finance, and Productivity/Collaboration"; "GPT-5, Claude Sonnet 4.5, and Perplexity Sonar". Now "the categories and examples it names are business software" and the three models |
| A2 | NIT | fresh-eyes | 1 | The stat bullet reads long | no action | The scope is the point of the change |
| A3 | NIT | fresh-eyes | 1 | "Questions" where the source says "queries" | fixed | Both passages say "queries" |
| B1 | RISK | codex | 2 | "Queries from people comparing products" claims who wrote them; the report gives their intent only | fixed | READ 2: "commercial-intent queries tied to brand discovery and early vendor evaluation". Now "queries about finding and comparing brands before buying" |

UNVERIFIABLE (rounds 1–3, Codex): the capture's authenticity and AirOps's vendor status, since
the capture sits outside the project. The host fetched the live page on 2026-11-10 and quotes it
verbatim; READ 5 quotes its own Platform and Pricing navigation. The claims sweep flagged
"software questions only" before round 1; "only" was cut, because two categories are unnamed.

A first round 2 run was stopped before it finished: its `--base` named a17812ff, one commit
before the head round 1 reviewed. It logged no tokens. `check_clean.sh` passed at 4fe1c67a; the
last fix changes six words and names nobody.

Result: CLEAN, 3 rounds, 4 findings (0 BUG, 2 RISK, 2 NIT), 189,876 tokens logged (fresh-eyes
included).
