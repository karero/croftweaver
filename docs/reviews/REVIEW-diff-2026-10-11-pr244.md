# DIFF review — PR #244 — Match line 49 to the new Profound wording, log the other follow-ups
Base `fb25ad7` (where the branch left main; merge-base `0af174e` after main was merged in at merge time, see the merge-link row) · depth: Normal (line 49 sits in a reference file agents load, and a mixed diff takes the riskier file's depth) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened PR #244); WORKTREE-WRITE — atom A (this session's own worktree); BRANCH-COMMIT — atom A (this session created the branch). For the branch update, the re-stamp and the merge: BRANCH-COMMIT and POST AUTHORITY — atom B (the owner's answer of 2026-10-11 to "which one do you mean by push open Merge?": "PR #244", given in another session, which took the PR over)

Data consent: the owner's instruction earlier in this session named the pair for PR #241's gate: "Codex + GLM 5.3 on melious (SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3 OLLAMA_MODEL=glm-5.3:cloud; ...)". For this PR the owner said "go" (2026-10-11) to a plan that named the full review: two reviewers and a fresh-eyes pass. `grep -c SECOND_SEAT` on the script run from this worktree found 15. A grep of every brief for keys, tokens, passwords and secrets found nothing, and none names anything on the private-name list; they add only public source text. ollama-cloud received nothing (melious counted in both rounds); Antigravity was not used. The fresh-eyes agent was allowed to fetch four public Profound pages and nothing else.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `8568550` | full: `fb25ad7...8568550`, 2 files, plus source excerpts | codex-cli 0.162.0, gpt-6.1-sol, effort from config, read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction, no shared context | codex 141 s / 60,316; melious 288 s / 23,516; fresh-eyes 849 s / 260,756 | 1/3/9 after dedup (17 raw: 1/3/13) |
| 2 | `93f5a50` | delta `8568550..93f5a50`, plus source excerpts and the author's record of round 1 | codex medium; melious glm-5.3 | codex 76 s / 41,811; melious 118 s / 23,355 | 0/1/2 (the RISK repeats F2) |
| wording pass | `432e336` | delta `93f5a50..432e336`, prose only (the closing edits after round 2) | codex medium, `--seat codex` | codex 50 s / 29,352 | 0/0/0 |
| merge link | main `0af174e` | `merge_link.sh fb25ad7 6775f0d 0af174e`: empty (main brought PR #243, README and docs only; no file in common; the diff against main is still the same three files). Not sent to a seat: nothing to read | — | — | — |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex; melious, fresh-eyes (NIT) | 1 | row 3 said line 458 assumes a Wikipedia article, and its fix would put "if your business has an article" on it; line 458 is an either/or question that allows "no" | fixed, externally_reverified (r2) | `93f5a50`: row 3 covers lines 58 and 227 and says line 458 is left out; quoted: "Do you have a Wikipedia page or presence on review sites?" |
| F2 | RISK | codex | 1, again 2 | the rows' absence claims (the July page's text shows no Wikipedia or Reddit share; the study page does not say which countries or languages its data covers) rest on excerpts, not complete pages | refuted | the fresh-eyes seat fetched the live pages itself and found the same absences (no "wiki" in the July page's raw HTML; no hit for English, language, U.S. or United States on the study page); the author's searches agree. Codex has no network and asked twice. `93f5a50` dated the claims, `432e336` names the searches so anyone can repeat them |
| F3 | RISK | fresh-eyes | 1 | row 1 named `SKILL.md` lines 219 and 220 only, but line 49 carries the same figures | fixed, externally_reverified (r2) | `93f5a50`: the cell names all three places; "swap the figures in all three places" |
| F4 | RISK | fresh-eyes | 1 | row 3's "its later study does" named no study, and the July study says it does not account for region or language | fixed, externally_reverified (r2) | `93f5a50`: the February study named, the July note quoted |
| F5 | NIT | melious | 1 | "its page rounds to whole numbers": other tables on the page show decimals | fixed, externally_reverified (r2) | `93f5a50`: "its top-sources table shows whole numbers" |
| F6 | NIT | melious | 1 | row 2's AirOps paraphrase dropped the platforms line 71 names | fixed, externally_reverified (r2) | `93f5a50`: "in ChatGPT, Claude and Perplexity" |
| F7 | NIT | melious, fresh-eyes | 1 | "its prompts" presupposes a method the page does not describe; the "global" sentence is about domain endings; line 58 covers other studies too | fixed, externally_reverified (r2) | `93f5a50`: "its data covers"; the fix names the Profound figures and keeps the directional advice |
| F8 | NIT | fresh-eyes | 1 | "a later measurement put Wikipedia lower still" read as a second figure; the link goes to a study whose charts are images | fixed, externally_reverified (r2) | `93f5a50`: "lower than 7.8%", what was read, "the link does not point to it" |
| F9 | NIT | fresh-eyes | 1 | "asked for them as a separate change" is stronger than the record | fixed, externally_reverified (r2) | `93f5a50`: "agreed in #241 to decide ... as a separate change"; the #241 trail records "Waive it" in reply to that recommendation |
| F10 | NIT | fresh-eyes | 1 | "about 700,000 conversations": the methodology note says about 730,000 with at least one web citation | fixed, externally_reverified (r2) | `93f5a50` |
| F11 | NIT | fresh-eyes | 1 | the rows did not say where they were found | fixed, externally_reverified (r2) | `93f5a50`: each row ends with "Found in the review of #241 (record: ...)" |
| F12 | NIT | fresh-eyes | 1 | the glossary's URL appeared nowhere | fixed, externally_reverified (r2) | `93f5a50`: linked on first mention in rows 1 and 3 |
| F13 | NIT | fresh-eyes | 1 | row 2 did not say that Profound's nearer figures do not back "matter more than" | fixed, externally_reverified (r2) | `93f5a50`: "neither confirm nor refute it", with the any-company definition and the glossary's "as much as" |
| F14 | NIT | melious | 2 | row 1's "add a line under the two bullets" left line 49 out | fixed, externally_reverified (wording pass) | `432e336`: "and a matching note at line 49" |
| F15 | NIT | melious | 2 | row 2 fused the July study's overall ranking with its ChatGPT figure | fixed, externally_reverified (wording pass) | `432e336`: "the biggest source of AI citations overall, with 47% of ChatGPT's citations going to them" |

15 findings (1 BUG, 3 RISK, 11 NIT): 14 fixed, 1 refuted. No waiver or deferral.

Waivers and deferrals: none.

Follow-ups (outside the changed rows; one line each):
- `SKILL.md` lines 232 to 233 ("the sources above are US/English; German answers cite German sources"): the same US/English premise as row 3, plus a claim about how assistants behave.
- `SKILL.md` line 216 ("AI systems don't just cite your website — they cite where you appear"): a behaviour claim under the heading that row 2 covers.
- `references/platform-ranking-factors.md` line 34 ("an accurate Wikipedia entry helps"): assumes an entry exists.
- No BUGLOG rows were added for these three: the owner approved three rows. A fourth is one decision away.
- Main moved on while this PR was in review (PR #243: README and docs only, no file in common with this change). At merge time `main` was merged in (head `6775f0d` plus that merge); the merge link was empty, as expected.

Notes: UNVERIFIABLE entries asked / confirmed: round 1 codex 3 / 1 (F5), melious 5 / 1 (F9), fresh-eyes 5 / 1 (F8); round 2 codex 2 / 0, melious 3 / 0; wording pass codex 2 / 0. Round 1 had a substantive BUG (F1, a wrong claim in a row), so round 2 was owed; round 2 found no BUG and its one RISK repeated F2, so the rounds stopped. The closing edits after round 2 got one narrow pass by codex (`--seat codex`), which found nothing.
The claims sweep ran before round 1 (nine sentences; two narrowed on the spot), after round 1's fixes (eleven) and on the closing edits. Every sentence was checked against the pages and files.
Codex and melious called the brief's scope sentences prompt injection (low); they are the author's own and were treated as data. One line of the fresh-eyes report, about commit metadata, names a person and a company, so it is left out of the public comment.
Judgment calls the owner may reverse: cutting rather than sourcing the last sentence of line 49; three rows grouped by where the problem sits; the clause in row 2 about Profound's nearer figures; naming the searches in rows 1 and 3; no rows for the three new out-of-scope items.
