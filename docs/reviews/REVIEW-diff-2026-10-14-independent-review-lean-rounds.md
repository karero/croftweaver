# DIFF review — independent-review: the earned-by kind and the cut, checked by the script; a running cost line; fresh-eyes at High in rounds 1 to 3; a shorter SKILL.md
Base `321d26f` · depth: Normal (the logic of a check script and an instruction file; nothing that touches user data, sign-in or deploy) · verdict: CLEAN — the rewrite (the artifact that merges) had three rounds; round 3 had no BUG and no RISK from either seat, its one NIT fixed after it ("closing edit not externally re-verified"). Round 2 had one cross-model seat, not two (see the table).

**Two artifacts.** The first draft (commits `73a9863` to `e8fffc4`) added five rules in prose. It passed three Normal rounds, about 37 findings, all fixed. The owner then asked for a thorough review of whether it makes reviews better. Two checks said it does not:
- a replay of its rules on every gate with four or more rounds (45 gates, 303 rounds) showed its severity bar would have saved one round, and that the old stop rule's trigger had been met in 34 of those gates with the rounds going on in about 30;
- an independent design critique on the host's strongest model found the bar re-opened a filter the rationale had rejected, and the cheaper-rounds rule would save almost nothing.
The owner chose (2026-10-14) "Rewrite, with checks" and, for a kind that comes back, "Refuse without --cut". The rewrite (`eafb571` on) is a new artifact; its rounds count from 1.

Data check: no key, token or password. Destinations: Codex and GLM 5.3 on melious, the repo's standing pair.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT (all seats) |
|---|---|---|---|---|---|
| draft 1–3 | `a7ba185`, `4d4eb9f`, `06d3074` | the first draft and its fixes | the pair; fresh-eyes one size down in round 1 | about 363,000 tokens in all | 9 / 13 / 15 |
| design check | `e8fffc4` | the first draft whole, SKILL.md whole, the scripts, the brand-kit trail | a sub-agent on the host's strongest model (critique) and a sub-agent replaying 45 trails | critique 249 s / 154,768; replay 978 s / 268,313 | verdict: merge with changes, not as is |
| 1 | `eafb571` | full: the rewrite, `321d26f...eafb571` without `docs/reviews/` | codex-cli 0.162.1 at config effort; melious glm-5.3; fresh-eyes on the host's strongest model (tests run on bash 3.2 and on bash 5 in a Linux container) | codex 467 s / 106,402; glm 565 s / 58,981; fresh-eyes 515 s / 191,960 | 3 / 16 / 17 |
| 2 | `80c90a2` | `eafb571..80c90a2`, with round 1's record | codex at medium; the second seat FAILED (melious timed out at 600 s; ollama out of quota) | codex 242 s / 74,490 | 2 / 0 / 0 |
| 3 | `5c54f30` | round 2's two fixes, with its record | codex at medium; melious glm-5.3 | codex 135 s / 37,652; glm 967 s / 50,453 | 0 / 0 / 2 |

| Round | Finding — one line | Status |
|---|---|---|
| 1 | the checks can be satisfied without changing anything: another kind of the same round, a renamed kind, alternating kinds, a restart at round 1, no `--round`, a repeated round number, a refusal of the latest input called a cut | fixed: several kinds per round, compared normalised against every earlier round since that kind's cut; a note for look-alike names; round numbers below or equal said; the gate a restart follows recorded; and the gate line the owner reads shows the kinds, the cuts, the runs without a round and the gate followed. A host that names kinds dishonestly is made visible, not stopped |
| 1 | `--cut --local-only` took the flag as the cut text and dropped local-only mode | fixed: option-shaped, blank or tabbed text refused; regression test |
| 1 | the cut defined as "refuse that input by name"; step 6 and step 7 competing; "a round without one" misread; the Codex sandbox called read-only; precondition 4 incomplete; the fresh-eyes figure; the total understating the cost; checks-only exiting 0 | fixed |
| 1 | GLM: the test's expected string holds literal backslashes and can never pass | refuted: single-quoted without backslashes; passes on bash 3.2 and 5 |
| 2 | a cut cleared another seat's uncut kind in the same round; the gate line showed only a round's last cut | fixed: a cut settles only the kinds on its own row; every cut shown |
| 3 | a test picked the kinds line by position | fixed after the round |

Open, by the owner's rule that bookkeeping never fails a review: with `REVIEW_LOG=off` or a log that cannot be written, the cut check warns instead of refusing. Follow-up: `gate`'s summary covers rounds up to 100.

Not run: a final full read (Normal depth does not call for one); the checks have not yet been used in a real gate past round 3, where they start to refuse.
