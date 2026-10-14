# DIFF review — karero/croftweaver#309 — brand-kit plan: row 8 done, the evals run with and without the skill

Base `661ec0e` · depth: Normal (a plan file is never Light) · verdict: CLEAN after round 2, with the carried BUG answered by #301's merge and one NIT's edit not re-read · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f1f94c2` | full (13,010 bytes: a context note with the run's timings, the plan's diff, and the grading notes the section rests on) | Codex: gpt-6.1-sol, config effort, read-only; GLM 5.3 on melious.ai (text only) | codex 198 s, 70,486 tokens; glm 183 s, 16,634 tokens | 1 / 1 / 4 |
| 2 | `682e136` | delta since `1dfb1bc` (5,023 bytes), round 1's findings and the author's record as `--verify` | the same, Codex at medium | codex 62 s, 39,623 tokens; glm 92 s, 10,903 tokens | 1 (carried) / 1 / 1 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| P1 | BUG | Codex (1, 2), GLM (2) | 1, 2 | row 8 and the section say the follow-ups are BUGLOG rows, and on this branch they are not | answered by merge order | the three rows are in #301, merged before this PR (auto-merge, pinned to its reviewed head); on main both citations hold |
| P2 | RISK | GLM | 1 | the zsh `=====` failures in the grading notes were left out of the follow-ups | refuted | the four runs' records show the separator came from their own shell lines (`cat a; echo =====; cat b`); a grep of the skill's SKILL.md, templates and references finds no `=====`; the section now says so |
| P3 | RISK | GLM | 2 | that sentence rests on the author's grep, which the diff does not show | stands as stated | the grep is the evidence named in P2; no skill command prints a separator |
| P4 | NIT ×4 | GLM | 1 | singular "a negative assertion" where six were strict; the pass-both sentence named evals 1 and 2 only; row 8 lacked the literal range; eval 3's proposals file not named | fixed, externally_reverified (round 2) | — |
| P5 | NIT | GLM | 2 | "which the skill allows" was a new claim about SKILL.md with no support | fixed after round 2, not re-read | the words are gone |

Waivers and deferrals: none.

Follow-ups: none from this review. Both rounds left the run's own records (the ten replies and actions, the grades) as UNVERIFIABLE: the workspace was kept outside the repository, as `website-story`'s was, and only its grading notes went into the artifact.
