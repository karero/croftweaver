# DIFF review — three starter BUGLOG rows: README "What's here", stale skill lists, axe contrast warning (0.35)

BUGLOG rows of 2026-10-06 (the starter README list), 2026-10-11 (stale counts, lists and dangling
skill names, items 1 to 7) and 2026-10-13 (`a11y.spec.ts` reads only `violations`). Depth: Normal
(skill text and a warn-only test; no box, user data, login, money, deletion or schema). No plan: a
fix that restores intended behaviour. Seats: Codex gpt-6.1-sol and GLM 5.3 on melious in one command
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`). Session "0.35 E: starter icons and file lists" (a subagent of it wrote
`c65f9bd2`) made the branch, the worktree and the PR. The artifact leaves out `docs/reviews/`; the
evidence files sit in the release manager's shared notes folder. Gate 20261109T103023Z-79702.

## Rounds

| Round | Head | Artifact | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|
| 1 | `e7e82d8d` | whole change | Codex 142 s, 73,556 · melious FAILED (curl exit 56 after 1291 s), rerun with `--seat melious` 328 s, 40,235 | 1 / 2 / 3 (the axe RISK raised by both) |
| 2 | `4f00e6a1` | verify: delta since `e7e82d8d` | Codex 133 s, 45,217 · melious 158 s, 13,809 | 1 / 0 / 2 |
| 3 | `51ed6806` | verify: delta since `4f00e6a1` | Codex 107 s, 40,080 · melious 145 s, 14,301 | 1 / 0 / 1 |
| 4 | `4a36eb03` | verify: delta since `51ed6806`; `--earned-by hook-guarantee --cut "…two copies outside this change go to a BUGLOG row…"` | Codex 93 s, 34,659 · melious 120 s, 10,310 | 0 / 0 / 2 |
| merge link (not a round) | `8b3e3da3` | `merge_link.sh 9bef0042 4a36eb03 49832edb` (#496, #499), `--seat codex --base 4a36eb03`; two Related Skills conflicts resolved | Codex 176 s, 88,003 | 0 / 1 / 0, outside this change |

Four rounds, 13 findings; with the merge link, 10 seat runs, 360,170 tokens (the script's running
total).

## Findings

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex | 1 | `programmatic-seo` still named in the `seo-audit` description and `site-architecture` eval 4 | fixed | `9d0cdaa8`; `grep -rn programmatic-seo skills` finds nothing |
| A2 | RISK | Codex and GLM | 1 | The claim that axe puts text over an image or gradient in `incomplete` rests on an in-repo fixture | refuted | Host probe from the starter's lockfile (axe-core 4.14.0, @axe-core/playwright 4.14.0, Playwright 1.64.1): `incomplete [["color-contrast","#bgimg"],["color-contrast","#grad"]]`, `violations [["color-contrast","#grey"]]` |
| A3 | RISK | GLM | 1 | website-qa: the hook makes "fails → does not ship" true "for every push" | fixed, then B1 | `4f00e6a1` |
| A4 | NIT | GLM | 1 | "Assistants never push to `main`" contradicted the new AGENTS.md first-upload exception | fixed | `4f00e6a1` |
| A5 | NIT | GLM | 1 | The fixture comment called an `incomplete`-only file "a real answer from axe" | fixed | `4f00e6a1` |
| A6 | NIT | GLM | 1 | The 2026-10-11 row's note did not say whether items 3 to 5 are closed | fixed | `4f00e6a1`; `website-contact-form/SKILL.md:149` already named all four values |
| B1 | BUG | Codex | 2 | The hook tests the files on disk, not the pushed commit, so "literally true" overclaims | fixed | `51ed6806`; `scripts/verify.mjs` runs in the site folder |
| B2 | NIT | GLM | 2 | The comment names an `<img>` case the host probe did not include | refuted | the fixture's third node is "Text over an img element." (`div:nth-child(4) > p`) |
| B3 | NIT | GLM | 2 | The row's Status opens `#TBD`; item 7's scope unclear | `#TBD` refuted (filled when the PR opens); scope fixed | `51ed6806` |
| C1 | BUG | Codex | 3 | website-qa:164 "a broken build never reaches the deploy branch"; `pre-push` lines 2–3 the same | website-qa fixed; the older copies logged | `4a36eb03`; BUGLOG row of 2026-11-09 (SETUP.md:189 and `pre-push`) |
| C2 | NIT | GLM | 3 | "before every push" ignores `--no-verify` | fixed | `4a36eb03` |
| D1 | NIT | GLM | 4 | `--no-verify` is not the only skip (`git -c core.hooksPath= push`) | declined: rare | — |
| D2 | NIT | GLM | 4 | The new line is not wrapped like its neighbours | fixed | `e0a992f0`, words unchanged |

C1's older copies predate this change and are not in it; they went to a BUGLOG row rather than a
fifth round. `templates/SETUP.md` line 189, an older copy outside the diff, is in the same row.

The merge link's one RISK is about the Microsoft training opt-out dates that #496 added to
`skills/ai-seo/SKILL.md` line 136: main's text, not this change's, so it is outside this gate and
was passed to the release manager.
