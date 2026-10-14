# DIFF review — karero/croftweaver#301 — BUGLOG: 58 rows for website-brand-kit's follow-ups

Base `cb1f867` · depth: Light (rows in the bug log, prose no agent follows; Codex alone, one round and one more after a BUG; the depth the maintainer named for this change) · verdict: CLEAN after round 2's RISK was answered by narrowing one row (that edit not re-read) · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `bad97ec` | full (31,717 bytes: a context note of statements, then the bug log's diff) | Codex: gpt-6.1-sol, effort medium, read-only sandbox | 290 s, 102,023 tokens | 4 / 1 / 0 |
| 2 | `5967ee1` | delta since `bad97ec` (18,446 bytes), round 1's findings and the author's record as `--verify` | the same | 128 s, 44,559 tokens | 0 / 1 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| L1 | BUG | Codex | 1 | the `_read_attrs` row's example, a title holding `url(#a)`, reaches the title's own refusal: fragment URLs pass the CSS check | fixed, externally_reverified (round 2) | the example is now `url(a)`; both reproduced with `_svg.clean_svg` by the author and by Codex |
| L2 | BUG | Codex | 1 | "No browser runs in the suite" overlooks `test_e2e_site.py`, which runs the starter's Playwright tests after an install | fixed, externally_reverified (round 2) | the row now says nothing automated compares how a browser draws the original and the cleaned SVG |
| L3 | BUG | Codex | 1 | the `_set_manifest` row's example has two plainly spelled keys, which gives the duplicate-name refusal, not the escaped-key branch | fixed, externally_reverified (round 2) | the example now has `"theme_color"` at the top and the nested key on its own lines; the advice points at line 3, reproduced by both |
| L4 | BUG | Codex | 1 | `_set_config` is in `_install.py` (line 496), not `_site.py` | fixed, externally_reverified (round 2) | — |
| L5 | RISK | Codex | 1, 2 | the eval-files row said two of eval 4's assertions "pass whatever a run does"; round 2 found the first rewording still claimed more than the eval shows | fixed after round 2, not re-read | the row now says only that eval 4 does not test what a run does with a PNG it is given; the plan's eval section (separate change) was narrowed the same way |

Waivers and deferrals: none.

Follow-ups: none from this review. Both rounds left UNVERIFIABLE groups as questions, not findings: browser behaviour (transitions, `--!>`, namespaces, opacity clamping, clip timings), drawing-tool exports, Windows, Linux and Node versions, the eval transcripts (kept outside the repo), and the list the gate's author gave after #283 merged. The rows state these as the trail or that list gives them; several rows say what was not checked.

Notes: rows 56 to 58 come from the skill's first eval run (2026-10-14), whose record goes into `docs/reviews/SKILL-PLAN-website-brand-kit.md` in a separate change, so Codex could not check their eval facts here and said so. Main moved twice while this PR waited; neither move touched `docs/BUGLOG.md` or any file of this PR, so no merge link was read. Codex took the whole branch as its tree and confirmed the claims it could run (the 256- and 32-pixel probes, the dashed-path and escaped-class refusals, the `&AMP;` advice, the three temporary files, the SIGINT replay, the `--!>` reader, the alpha clamp, the order of the needs-decision stop, the dry-run sentence, the counts).
