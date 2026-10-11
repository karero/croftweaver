# DIFF review — PR #251 — ai-seo: give the unsourced platform claims a source, or say them as advice
Base `40e018c` (the stack base: `main` at `dbd6134` with #249 at `379ee0d` and #250 at `93fce3f` merged in; the artifact is `40e018c..11c4de6`, this change's own commits; `main` has since taken #249 and #250 and is merged in) · depth: Normal (instruction files an agent loads, and the evals that grade them) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened PR #251); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — captured reviewer input against `(base, head)` pairs that match, by the verification chain below; opening the PR — atom B (the owner's "Do 1-5" and "Start with a, then B, then 5", 2026-10-11)

Data consent: the owner's standing instruction in his global CLAUDE.md names the pair, quoted: "The second seat is GLM 5.3 on melious.ai" (2026-10-06); earlier PRs of this repo (#241, #244) went to Codex and melious with his OK. Not a fresh yes for this PR: it relied on that standing instruction. The artifact is a public diff plus public page text. A grep of every brief for keys, tokens and passwords found nothing, `check_clean.sh` passed, and nothing names anything on the private-name list. ollama-cloud received nothing.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `c4182f0` | full: `40e018c..c4182f0`, 3 files, plus excerpts copied from six public pages | codex-cli 0.162.0, gpt-6.1-sol, effort from config, read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction, no shared context, leave to fetch six public pages | codex 256 s / 71,827; melious 221 s / 18,388; fresh-eyes 411 s / 191,418 (26 tool calls) | 2/11/15 after dedup (raw: codex 0/5/0, melious 0/1/4, fresh-eyes 2/8/14) |
| 2 | `410b580` | delta `c4182f0..410b580` (5 files) plus excerpts and the author's record of round 1 | codex medium, read-only; melious glm-5.3 | codex 159 s / 58,471; melious 67 s / 22,049 | 1/1/3 |
| wording pass | `11c4de6` | delta `410b580..11c4de6`: prose only (three files) | codex medium, `--seat codex` | codex 102 s / 39,156 | 0/1/0 (the RISK refuted) |
| merge link | `922855f` | `main` merged in after #249 and #250 landed (`ab88a62`). The tree outside `docs/reviews/` is byte-identical to the last reviewed head `3d58085` (`git diff 3d58085 HEAD` empty), and this change's added and removed lines are identical to the reviewed `40e018c..11c4de6` (same hash); main's only new content for this branch is one added line in #250's trail. Checked mechanically, no model seat | — | — | — |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| C1 | BUG | fresh-eyes | 1 | The reference said each section gives what a company's page or a study says, with the source beside each figure; the Copilot section says no page was checked | fixed, externally_reverified (r2) | `32f456e`: "Where a company's page or a study backs a statement, the source is beside it; the rest is advice." |
| C2 | BUG | fresh-eyes (melious NIT) | 1 | The table intro said each row is what the company's page lets you act on; the Copilot row has no page | fixed, externally_reverified (r2) | `32f456e` |
| C3 | RISK | fresh-eyes | 1 | The change cites Google's AI-features page, which also says no special schema.org data, machine-readable files or AI text files are needed; the guide said "add schema markup", "at minimum" and listed "No structured data" as a mistake | fixed, externally_reverified (r2) | `32f456e`: the page's sentences quoted in the brief; Google section, schema bullet, Where to Start, the schema paragraph, the pitfall |
| C4 | RISK | fresh-eyes | 1 | llms.txt is presented as context for AI systems; no linked company page says an assistant reads it | fixed, externally_reverified (r2) | `32f456e`: one sentence after the paragraph; the starter's own llms.txt is unchanged |
| C5 | RISK | fresh-eyes | 1 | The reference's title and opening, and SKILL.md's pointer, promised how each platform picks sources | fixed, externally_reverified (r2) | `32f456e`; the title lost "Each" in `11c4de6` (R2-4) |
| C6 | RISK | fresh-eyes, codex | 1 | "Every AI platform shares three baseline requirements": an unsourced universal | fixed, externally_reverified (r2) | `32f456e`: "Three things to do for every platform"; item 2 reworded in `11c4de6` (R2-2) |
| C7 | RISK | fresh-eyes (melious NIT) | 1 | The 40-60 word rule of thumb stayed in SKILL.md | fixed, externally_reverified (r2) | `32f456e` |
| C8 | RISK | fresh-eyes, codex | 1 | "A crawler cannot get past a login or a form" | fixed, externally_reverified (r2) | `32f456e`: "keep your most authoritative content open, outside any login or form" |
| C9 | RISK | fresh-eyes, codex | 1 | Evals 3 and 4 expected the explanations this change removed | fixed, externally_reverified (r2) | `32f456e`: expected output and assertions check what the skill now says |
| C10 | RISK | fresh-eyes | 1 | An unlinked quotation of Google's rater guidelines as an example | fixed, externally_reverified (r2) | `32f456e`: replaced by a made-up example, labelled as made up |
| C11 | RISK, outside scope | codex | 1 | `skills/search-console-setup/SKILL.md` line 96 says Cloudflare's training-bot switch stops assistants citing you | follow-up | A BUGLOG row in this change: another skill, and what the switch covers is unchecked |
| C12 | RISK | codex | 1 | "A markdown file needs ... no login" without a publication condition | fixed, externally_reverified (r2) | `410b580` |
| C13 | RISK | melious | 1 | Where to Start states the Bingbot-to-Copilot mapping as fact | fixed, externally_reverified (r2) | `32f456e` |
| C14 | NIT | fresh-eyes, melious | 1 | Gemini row said "keep Google Search access open", not on the linked page | fixed, externally_reverified (r2) | `32f456e` |
| C15 | NIT | fresh-eyes, melious | 1 | The Copilot section carried Google's LCP bullet | fixed, externally_reverified (r2) | `32f456e`: removed there; the Where to Start action has web.dev's 75th-percentile condition |
| C16 | NIT | fresh-eyes | 1 | "OAI-SearchBot decides whether a site is shown" overstates the OpenAI page | fixed, externally_reverified (r2, wording pass) | `32f456e`; two remaining copies fixed in `11c4de6` (R2-3) |
| C17 | NIT | fresh-eyes | 1 | "surfaces and links" drops "designed to" | fixed, externally_reverified (r2) | `32f456e` |
| C18 | NIT | fresh-eyes | 1 | "indexes pages for Claude's search results" is stronger than the Anthropic page | no change | The page says Claude-SearchBot analyses content to improve search results and that disabling it prevents indexing for search; the same wording passed three rounds on #249 |
| C19 | NIT | fresh-eyes | 1 | "a link and not a tested cause" reads as a hyperlink | fixed, externally_reverified (r2) | `32f456e`: "a correlation, not a tested cause", three places |
| C20 | NIT | fresh-eyes | 1 | A redundant sentence under the Google advice line | fixed, externally_reverified (r2) | `32f456e` |
| C21 | NIT | fresh-eyes | 1 | "what you add on top" lacked Google's caveat | fixed, externally_reverified (r2) | `32f456e` |
| C22 | NIT | fresh-eyes | 1 | "Content habits worth adopting here" ties habits to Perplexity | fixed, externally_reverified (r2) | `32f456e`: "Habits worth adopting" |
| C23 | NIT | fresh-eyes | 1 | "within 6 months" against three months elsewhere | fixed, externally_reverified (r2) | `32f456e` |
| C24 | NIT | fresh-eyes | 1 | Removed claims left bullets without a rationale; "What Makes It Citable" kept the removed premise | fixed in part, externally_reverified (r2) | `32f456e`: the two column headings changed; the bullets stay as advice |
| C25 | NIT | fresh-eyes | 1 | "now show" for a late-2025 figure | fixed, externally_reverified (r2) | `32f456e` |
| C26 | NIT | fresh-eyes | 1 | "for this change" in a skill file | fixed, externally_reverified (r2) | `32f456e` |
| C27 | NIT, outside scope | fresh-eyes | 1 | search-console-insights, `bing_query.py` and schema-markup still say Bing's index feeds Copilot and ChatGPT search, and that schema helps AI understand content | follow-up | A BUGLOG row in this change |
| C28 | NIT | fresh-eyes | 1 | The author's complete list of remaining unsourced statements | follow-up | A BUGLOG row lists them for the next pass |
| R2-1 | BUG | codex | 2 | The new BUGLOG row said each remaining statement is advice or general, but two name assistants or tool coverage | fixed (wording pass) | `11c4de6`: "Some are advice or general statements; some name an assistant or a tool's coverage (`content-patterns.md` line 168, the tool table)". caused-by: C28 (introduced) |
| R2-2 | RISK | codex | 2 | Reference line 14 kept "each platform's search bot needs access via robots.txt" | fixed (wording pass) | `11c4de6`: "allow each company's search bot in robots.txt ...; Microsoft's is unchecked" |
| R2-3 | NIT | codex | 2 | Two copies of "decides whether you appear" survived | fixed (wording pass) | `11c4de6` |
| R2-4 | NIT | melious | 2 | The title's "Each" claims coverage the Copilot section disclaims | fixed (wording pass) | `11c4de6` |
| R2-5 | NIT | melious | 2 | "Add FAQ schema, publish PDF resources" strips the section's hedges | fixed (wording pass) | `11c4de6` |
| W1 | RISK | codex | wording pass | The OpenAI exclusion and bot roles lack an independently checked source | refuted | The raw OpenAI page text was read by the author; the fresh-eyes seat read the live page in #249 round 1 and in round 1 here and found the sentences the diff uses |

34 findings (3 BUG, 13 RISK, 18 NIT): 29 fixed, 1 refuted, 1 no change, 3 follow-ups. No waiver or deferral. (Codex's wording-pass note that `docs/BUGLOG.md:49` cites a record that was absent is settled by this file.)

Waivers and deferrals: none.

Follow-ups (one line each):
- C11 and C27: other skills still carry statements this change removed from `ai-seo` (Cloudflare's training-bot switch, Bing's index feeding Copilot and ChatGPT search, "schema helps AI understand content"); BUGLOG rows say where.
- C28: the remaining statements in `ai-seo` for the next pass: E-E-A-T alignment, the Pillar 3 "where they look" list, JavaScript-rendered content implied unreadable, the tool table's per-tool coverage, "Maximize factual density" and the E-E-A-T bullets, "Often recommended for Perplexity", the PDF advice, and the pattern descriptions in `content-patterns.md`.
- The Bingbot line and the Copilot section stay unchecked against Microsoft's pages.
- #249 and #250 merged (`d204c75`, `ab88a62`); `main` is merged in here (see the merge link row).

Notes: the change is stacked on #249 and #250, whose own gates are in their trails; its artifact excludes them. Round 1 had two BUGs about what the text said of itself, and round 2's one BUG was in the new log row, so none changed what runs; the second round was owed by the fixes that changed what a reader acts on (schema advice, evals), and the wording pass followed. The fresh-eyes seat fetched six public pages (leave given in the prompt) and listed the statements left; the author put them in the log. Codex and melious called the brief's scope sentences prompt injection (low); they are the author's own and were treated as data. The claims sweep ran before round 1 and after each fix.
