# DIFF review — docs/buglog-whats-new-removed-skill — one BUGLOG row

Base `origin/main` (`cc6f1f2`) · depth: **Light** (one tracker row, no code) with a cross-model seat · verdict: **CLEAN**: 3 BUGs and 1 RISK, all wording in the row, all fixed; the last fix closed locally, not externally re-verified. Authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session, at the owner's "add a BUGLOG row for the whats-new refresh"); GATED

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `30f4ee8` | `origin/main...30f4ee8` | Codex (config effort), `--seat codex` | codex 203 s/73,514 | 2 / 1 / 0 |
| 2 `--verify` | `6303a90` | delta since `30f4ee8` | Codex (medium) | codex 90 s/33,767 | 1 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| B1 | BUG | codex | 1 | pinning alone does not stop the repeat: the report lists the skill until `--refresh` advances the stamp | fixed `6303a90`; externally_reverified r2 | `whats-new.sh:223–235`, reproduced by Codex |
| B2 | BUG | codex | 1 | "only the removal commit" is wrong for an older stamp | fixed `6303a90`; externally_reverified r2 | `git log 96d4a61..HEAD -- skills/website-forms` lists earlier updates |
| R1 | RISK | codex | 1 | "keep working" is unsupported: the old form's mail call never ran live | fixed `6303a90`; externally_reverified r2 | "stay in place but are no longer maintained" |
| B3 | BUG | codex | 2 | the fix said deleting the copy also needs `--refresh`; it does not, a skill the site no longer holds is never listed | fixed `f451fbe`; locally_verified, closing edit not externally re-verified | `whats-new.sh` builds `stale` only from skills present in the site's skills dir (`[ -d "$skills_dir/$s" ]`), and returns "Up to date" when none are |

Waivers: none. Deferrals: none. Follow-ups: none.

Notes: a Light gate runs one round plus one after a BUG; B3 was a wording BUG in the row, fixed against the code without a third round.
