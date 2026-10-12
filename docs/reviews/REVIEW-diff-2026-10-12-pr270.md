# DIFF review — PR #270 — website-tagline: an optional skill for the short line under the logo
Base `d382cbe` · depth: Normal (a new instruction file an agent loads, and edits to three other skills' instruction files) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened #270); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — atom A (the chain below, unbroken for Codex)

Normal gate: Codex and GLM 5.3 on melious.ai as the pair, and a fresh-eyes pass on a mid-tier host-family model in round 1.

Data check before round 1: the diff holds no key, token or password (searched for `api key`, `secret`, `token`, `passw`, `PRIVATE`; no hit). Destinations: Codex and melious.ai. The owner approved a plan in this session whose third step read "run the Normal review (Codex plus GLM 5.3 on melious)", with the words "go with steps 1 and 2 then push & merge".

Test record: `make check`, exit status 0, 1,084 lines of output, ending `all checks passed` / `LF checkout OK — every text file checks out LF even with core.autocrlf=true`. Run twice: at `169ad0a` before round 1 and at `9d4390f` after the last fix. The whole output of the second run is in a comment on the PR. The three evals in `skills/website-tagline/evals/` are written and have not been run; nothing in the Makefile or in CI runs evals.

Before the gate, not a round: Codex and a second model each answered four design questions on head `1f26d1f` (offer or on request, how long a liked line stays, evals now or later, scope). Four defects they named were fixed in `ae82914`; their answers changed two decisions (`d6b78d4`). A claims sweep (`sweep_claims.sh --base origin/main`) then led to `169ad0a`, which turns seven general claims the skill could not back into instructions.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `5284c4b` | full: `origin/main...5284c4b` without `docs/reviews/`, 8 files | codex-cli 0.162.1, gpt-6.1-sol, config.toml's effort, read-only · melious: glm-5.3, HTTP API, text only · fresh-eyes: host sub-agent, sonnet, read-only | 326 s / 86,370 · 187 s / 24,580 · 152 s / 128,926 | 4/2/9 |
| 2 | `c6e9457` | delta `5284c4b..c6e9457`, with round 1's dispositions (`--verify`) | codex as above at medium · melious as above | 121 s / 53,874 · 202 s / 30,220 | 2/0/4 |
| 3 | `1803919` | delta `c6e9457..1803919`, with round 2's dispositions | codex at medium · melious | 75 s / 75,046 · 47 s / 9,450 | 1/0/1 |
| confirmation, not a round | `9d4390f` | delta `1803919..9d4390f`, one assertion string | codex at medium | 38 s / 34,629 | 0/0/0 |

Round 1's count is after merging duplicates; as filed: Codex 4/2/0, melious 0/1/4, fresh-eyes 0/1/6.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| B1 | BUG | codex | 1 | Eval 3's liked line said "backache", an outcome the fixture lacks | fixed — externally_reverified (round 2, both seats) | `c6e9457`: "Still your garden, without the heavy part."; "the heavy part" is in the fixture's human version. The finding's second half (re-check carried lines) is unchanged: a carried line passed the rules when written |
| B2 | BUG | codex | 1 | §6: a site with no header got "steps 1 and 2 only", which skipped the tests and the README note | fixed — externally_reverified (round 2) | `c6e9457`: "skips this item only ... Items 4 and 5 still apply" |
| B3 | BUG | codex | 1 | Fixture: statement, human version and boilerplate promised the same gardener on the agreed day without the 94% and 97% | fixed in part in round 2, in full as B5 | `c6e9457`, `1803919` |
| B4 | BUG | codex, fresh-eyes (as RISK) | 1 | "No em dashes" does not make a line pass the tone test; the helper also fails English contractions and a buzzword list | fixed — externally_reverified (round 2: Codex ran the helper's patterns over all 20 example lines, no hit) | `c6e9457`: rule "Passes the site's tone rules"; evals 2 and 3 assert no contraction |
| R1 | RISK | codex | 1 | The example's "Every return on time" turned a record since 2019 into a promise | fixed — externally_reverified (round 2) | `c6e9457`: "A record is not a promise"; line 7 is "Deadlines are our worry, not yours." |
| R2 | RISK | codex; melious in another form | 1 | A green test does not show the line's contrast was assessed (Codex); nothing shows a contrast check exists (melious) | Codex's form fixed — externally_reverified (round 2); melious's form refuted | `c6e9457`: §6 item 4 asks for a look in both themes. `a11y.spec.ts` runs `AxeBuilder({ page }).withTags([... 'wcag2aa' ...])` on every page in light and dark |
| N1 | NIT | fresh-eyes | 1 | The number of rounds was not pinned down | fixed — externally_reverified (round 2) | `c6e9457`: §4 defines a round, "at most three"; §5 "There is no fourth round" |
| N2 | NIT | fresh-eyes | 1 | The stop after three rounds recorded nothing | fixed — externally_reverified (round 2) | `c6e9457`: §5, §6, "Done means", the template |
| N3 | NIT | fresh-eyes | 1 | No branch for an assistant that cannot search the web | fixed — externally_reverified (round 2) | `c6e9457`: §5 |
| N4 | NIT | fresh-eyes | 1 | "step 5" could mean §5 | fixed — externally_reverified (round 2) | `c6e9457`: §6 says "item" |
| N5 | NIT | fresh-eyes, melious | 1 | Eval 1 named section 3 for wording that sits in section 4 | fixed — externally_reverified (round 3, Codex) | `c6e9457` |
| N6 | NIT | fresh-eyes | 1 | Trigger "claim" in lower case is a common word here; `copywriting` also answers to "tagline" | fixed — externally_reverified (round 2) | `c6e9457` |
| N7 | NIT | melious | 1 | README entry indented one column off its neighbours | refuted; Codex measured the same in round 2 | the continuation lines have 19 leading spaces, as have those of `website-story` and `website-scorecard` |
| N8 | NIT | melious | 1 | "about 50 characters" cannot be graded | fixed — externally_reverified (round 2) | `c6e9457`: "50 characters" |
| N9 | NIT | melious | 1 | An existing site may have no decision-interview section | fixed — externally_reverified (round 2) | `c6e9457`: §6 item 5 |
| B5 | BUG | codex | 2 | B3 half done: the boilerplate still promised "a gardener you know" and gave 97% as how the service will run | fixed — externally_reverified (round 3, both seats) | `1803919`: both figures dated to 2025 |
| B6 | BUG | melious | 2 | §6 item 4 told the assistant to look at the line in the header on a site that does not show it. `caused-by: B2 (introduced)` | fixed — externally_reverified (round 3) | `1803919`: "Where the site shows the line, also look at it yourself" |
| N10 | NIT | melious | 2 | Eval 3 did not grade the 50 characters or the em dash for new lines | fixed in part in round 3, in full as B7 | `1803919`, `9d4390f` |
| N11 | NIT | melious | 2 | "The line will sit on every page" is false where the line is stored only | fixed — externally_reverified (round 3) | `1803919` |
| N12 | NIT | melious | 2 | The template did not say where the shown lines go when no line was picked | fixed — externally_reverified (round 3) | `1803919` |
| N13 | NIT | melious | 2 | The description said "until they pick ONE", against the three-round limit | fixed — externally_reverified (round 3) | `1803919` |
| B7 | BUG | melious | 3 | Eval 3: "eight words and 50 characters or fewer" can be read as exactly eight words. `caused-by: N10 (introduced)` | fixed — externally_reverified (confirmation, Codex) | `9d4390f`: "eight words or fewer and 50 characters or fewer" |
| N14 | NIT | melious | 3 | The same assertion does not grade the buzzword list | follow-up | the eval's fixture holds no tone-rule file, so a grader has no list; Codex confirmed the fixture folder holds only `POSITIONING.md` |

23 findings in 3 rounds (7 BUG, 2 RISK, 14 NIT): 21 fixed, 1 refuted, 1 follow-up; one RISK was fixed in one seat's form and refuted in the other's. No waiver, no deferral.

Questions the seats could not settle, looked at by the host: round 1, 12 asked, none became a new finding (two were the grounds of R1 and R2); round 2, 12 asked, none; round 3, 4 asked, none; the confirmation, 1.

Follow-ups:
- N14: the evals do not grade the buzzword list.
- The three evals have not been run.
- "Claim" as the German word for a tagline is common usage and is not sourced in the repo.
- Codex, round 1: the starter's `a11y.spec.ts` fails on `results.violations` only, so a contrast the engine could not assess would pass. Not checked here; it concerns the starter, not this change.
- The opt-in test (the line on the page equals `SITE.tagline`, a `<p>`, typed once) follows as its own change.

Notes:
- Rounds 2 and 3 were owed by fixes to instruction text and to eval files. No round ran past 3.
- The round 2 and round 3 BUGs were a fixture sentence, a step nobody could carry out, and the wording of an assertion; none changed what the skill tells an assistant to do. That is the host's reading.
- Chain for the stamp: Codex saw the full pair in round 1 and each delta since, the last at `9d4390f`. The melious chain ends at `1803919`; the fresh-eyes chain ends at round 1, by design at Normal depth.
- The commit that completes this file changes nothing else; the reviewed scope is the one at `9d4390f`.
