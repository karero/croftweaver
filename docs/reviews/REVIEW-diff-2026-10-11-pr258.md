# DIFF review — PR #258 — pre-release: facts-check finds its script, the Cloudflare bot line agrees with ai-seo, the trackers stay out of the zip
Base `35e9b42` · depth: Normal (two `SKILL.md` instruction files and the logic of the packaging check) · verdict: CLEAN, with three follow-ups · authority used: POST AUTHORITY — atom A (this session opened #258); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — atom A (the chain below, held by the Codex seat)

Data consent: a public diff of two skill files, the packaging script, its test and the README. A grep of each brief for keys, tokens, passwords and private names found nothing. Codex and Melious (GLM 5.3) have both read this repo in earlier gates; no new OK was asked.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `167268e` | full: `origin/main...167268e`, 5 files (`docs/reviews/` and `docs/BUGLOG.md` left out), with context excerpts for the text-only seat | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction, allowed to fetch the one cited page | codex 272 s / 67,302; melious 355 s / 25,251; fresh-eyes 110 s / 108,051 | 0/1/0 (codex), 0/0/3 (melious), 0/2/3 (fresh-eyes); 0/3/4 after dedup |
| 2 | `4d67057` | delta `167268e..4d67057`, with round 1's dispositions (`--verify`) | codex-cli 0.162.1, gpt-6.1-sol, medium, read-only; melious glm-5.3, text only | codex 122 s / 37,353; melious 135 s / 15,406 | 0/0/0 (codex), 0/0/1 (melious) |
| wording pass | `00d6b90` | prose only: the `docs/BUGLOG.md` rows against `origin/main`, and the delta `4d67057..00d6b90` | codex-cli 0.162.1, gpt-6.1-sol, medium, read-only | codex 168 s / 67,596 | 2 contradictions, 1 RISK |
| confirmation | `ed8bdff` | delta `00d6b90..ed8bdff` | same seat | codex 123 s / 51,682 | the fix was wrong in one sentence |
| confirmation | `29470a0` | delta `ed8bdff..29470a0` | same seat | codex 100 s / 55,476 | fix confirmed; 2 follow-ups |

Round 1: `reviewers: codex OK, melious OK`. Round 2: `reviewers: codex OK, melious OK`. Unverifiable entries: 7 asked in round 1, 4 in round 2; none confirmed as a finding. The dashboard's real labels stay unobserved and have a BUGLOG row.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | codex | 1 | Both facts-check commands left the script path unquoted; a toolkit folder with a space would split it | fixed — externally_reverified (round 2) | `4d67057`: both commands call `~/.claude/skills/facts-check/scripts/facts_check.py`, the installed path, as `website-contact-form` and `website-permissions` write theirs; codex's probe gave `argc=1` in bash and zsh |
| F2 | RISK | fresh-eyes, melious | 1 | The Cloudflare bullet treated its label "Block AI training bots" and the page's "Block AI bots" as one control without saying the names differ | fixed — externally_reverified (round 2) | `4d67057`: the bullet gives the page's name and says the dashboard name may differ and was not re-checked |
| F3 | RISK | fresh-eyes | 1 | "from 15 September 2026, also crawlers that combine search and training" read as a plain fact; the page (last updated 1 July 2026) announces it | fixed — externally_reverified (round 2) | `4d67057`: page date beside the read date, "would also cover", "look at what yours shows" |
| F4 | NIT | fresh-eyes | 1 | `<skill-dir>` was a placeholder no other skill uses | fixed — externally_reverified (round 2) | `4d67057`, with F1 |
| F5 | NIT | fresh-eyes | 1 | "set all three to Allow" made the kit's posture an instruction for Agent bots too | fixed — externally_reverified (round 2) | `4d67057`: "this kit leaves all three on …" |
| F6 | NIT | fresh-eyes, melious | 1 | Two shipped files name `docs/BUGLOG.md` in a comment, and the zip no longer holds it | fixed in the README only — externally_reverified (round 2) | `4d67057`: the README's BUGLOG row says so and where to read it; `mail-form-text.ts` is a site template and a site never held that file, so the two comments stay |
| F7 | NIT | melious | 1 | The README's `test_package_leak.sh` line no longer described the whole test | fixed — externally_reverified (round 2) | `4d67057` |
| F8 | NIT | melious | 2 | "(Codex: `~/.agents/skills/…`)" left the Codex reader to build the path | fixed — externally_reverified (wording pass) | `00d6b90`: the path in full; codex checked it against `scripts/install-codex.sh` |
| W1 | prose | codex | wording pass | The release-read BUGLOG row said none of its items breaks a command; item (3) leaves `npm test` red | fixed — confirmed | `ed8bdff`, then `29470a0`: the row makes no such claim, and item (3) names its consequence |
| W2 | prose | codex | wording pass | Item (7) called two Keystatic passages contradictory; one is about package metadata, the other about the integration | fixed — confirmed | `ed8bdff`: the item is removed |
| W3 | RISK | codex | wording pass | The row for #255 says Claude Code "still asks for approval at each merge", which holds only while nothing else allows `gh pr merge` | follow-up | the row is #255's, not this change's; the release notes will say it with that limit |
| C1 | prose | codex | confirmation 1 | "Only (3) can leave a command red" was wrong: item (2) can fail too | fixed — confirmed (confirmation 2) | `29470a0` |
| C2 | NIT | codex | confirmation 2 | Items (1) and (6) of the release-read row shorten paths to `templates/…`; the folder is `skills/new-website/templates/…` | follow-up | to be written out in the next docs PR that touches the row |
| C3 | RISK | codex | confirmation 2 | Item (6) says `settings.json` "denies" the destructive commands; that a `deny` entry blocks rather than asks was not observed | follow-up | the row states the configuration; whoever fixes it checks the behaviour first |

14 findings (0 BUG in the change, 5 RISK, 6 NIT, 3 contradictions in record prose) in 2 rounds, a wording pass and two confirmations: 11 fixed, 3 follow-ups. No waiver, no deferral, nothing refuted.

Checked by the author: `scripts/test_package_leak.sh` has five new cases; four fail with `main`'s `package.sh` and pass with this one. `make smoke` passed on `167268e` and on `4d67057`; the real zip has 328 entries (330 on `main`) and neither tracker. The documented `--init` command wrote `facts.json` from a scratch folder.

Follow-ups: W3, C2, C3 above.

Notes:
- The Cloudflare sentences come from the page's own text (fetched 2026-10-11; the fresh-eyes seat fetched it too). No dashboard was opened; a BUGLOG row records that.
- The stamp relies on the Codex seat's unbroken chain from round 1 to `29470a0`. Melious's chain ends at `4d67057`; fresh-eyes' at round 1, by design.
- The commit that adds this file changes nothing outside `docs/reviews/`, so the stamp names that commit: the reviewed diff-scope is the one at `29470a0`.
- Codex listed the prepended scope paragraph of the wording pass as a prompt-injection attempt. It is the scope the skill prescribes for a prose-only pass.
- The machine was under heavy load from another session's simulator during round 1 (load average near 280); the seats ran slower, none failed.
