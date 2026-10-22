# DIFF review — fix/gsc-publish-app-followup — the Publish check reaches owners who already have a sign-in (follow-up to #363)
Base `22ae4e4` · depth: Normal (instructions an assistant follows; a sign-in set-up for the owner's own read-only Search Console data, no secret stored or sent by the change — a judgment: it moves `token.json` aside, which would make it High if it deleted anything) · verdict: OPEN until the wording pass lands · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created this worktree and branch); POST AUTHORITY — not used, no PR yet

Seats: Codex CLI 0.163.0 (gpt-6.1-sol, read-only; config effort in round 1, medium after), GLM 5.3 on melious, a fresh-eyes Sonnet sub-agent in round 1 (by design at Normal depth). The text of #363 is public, and no secret is in the diff (grep: one env-var name).

| Round | Head | Artifact | New findings (BUG/RISK/NIT) | Seats |
|---|---|---|---|---|
| 1 | `5649f77` (#363 as merged) | full, `f037c24...5649f77` | 1/4/7 | codex 132 s / 61,355; melious 226 s / 14,970; fresh-eyes 337 s / 133,594 |
| 2 | `34982a6` | full follow-up, `22ae4e4...34982a6` | 0/2/6 | codex 293 s / 59,810; melious 500 s / 32,771 |
| 3 | `80e1712` | delta since `34982a6` | 0/1/1 | codex 82 s / 57,882 (none); melious 199 s / 21,091 |
| wording pass | `a7dacf2` + record | delta since `80e1712`, prose only | 0/0/2 (one wrong line count in this record, one overclaim, "never replaced"; both fixed) | codex 169 s / 65,054 |
| confirmation | pending | the two fixes alone | | |

Round 1 (on #363's merged text):
- R1-01 BUG (Codex, fresh-eyes) FIXED, `locally_verified` and `externally_reverified` in round 2: SKILL.md loads onboarding.md only when there is no token, so the Publish check for an owner who has one could not fire. Now the schedule paragraph of SKILL.md asks every owner it asks about scheduling to read the Audience tab. Evidence: `SKILL.md` "Before the yes".
- R1-02 RISK (Codex, GLM, fresh-eyes) FIXED, re-verified: after publishing, an old sign-in is refreshed silently, with no new consent, and "reconnect" was defined nowhere. "Signing in again" now says: move `token.json` aside, run `gsc_query.py` by hand. Invariant: a sign-in Google still accepts gets no new consent (`load_credentials`, `gsc_query.py:101-131`). The first wording said "never replaced"; the wording pass pointed out that google-auth 2.55.1 (`_perform_refresh_token`) stores a new refresh token if Google sends one, so the claim was cut to the consent. Whether the old sign-in keeps its 7-day limit after publishing is UNVERIFIABLE; the text says it was not checked.
- R1-03 RISK (fresh-eyes) FIXED, re-verified: an app already In production, or Internal, needs nothing; never switch Internal to External. Google's page, read 2026-10-20, names only "an external user type" with status "Testing".
- R1-04 RISK (fresh-eyes) FIXED, re-verified: the exit-2 line no longer says "most likely Testing".
- R1-05 RISK (GLM) REFUTED: "then reconnect" needs #352 on the branch. `git merge-base --is-ancestor 89f965b5 5649f77a` is true; `load_credentials` writes the new token after a refused refresh. Confirmed by Codex in round 2.
- R1-06 to R1-10 NIT (fresh-eyes, GLM) FIXED, re-verified: "Step 3c" wording and the eval carve-out; the stale "three clicks" and "single consent click"; no control named on the unverified-app screen, and what the assistant checks on it; the "not yet checked" sentences are to go after the live check; the BUGLOG status named a branch.
- R1-11 NIT (GLM) REFUTED: ask the Publish check only if the weekly job has not run twice. `load_credentials` rewrites `token.json` on every refresh (`gsc_query.py:131-133`), so its age says nothing about when the sign-in was given.
- R1-12 NIT (fresh-eyes) FOLLOW-UP: SKILL.md is over its 500-line soft budget (522 at #363's head, 548 now); `check_skill_budgets.sh` warns and exits 0.

Round 2 (verification, 0 BUG):
- R2-01 RISK (Codex, GLM) FIXED, re-verified in round 3: eval 1 required publishing unconditionally.
- R2-02 RISK (Codex) FIXED, re-verified: "already In production" cannot rule out a sign-in given before publishing; the paragraph now names it first.
- R2-03 to R2-06 NIT (GLM) FIXED, re-verified: "sign in again" cannot fix a deleted client or removed access; BUGLOG "repeated"; eval carve-out; "every owner".
- R2-07 NIT (GLM) REFUTED: `--no-browser` may not exist. `gsc_query.py --help` lists it, `track.sh` passes it, and Codex ran `--help` and read `main():517-529`.
- R2-08 NIT FOLLOW-UP: the budget again (R1-12).

Round 3 (verification, Codex clean, 0 BUG):
- R3-01 RISK (GLM) FIXED, `locally_verified`, not externally re-verified: the schedule check let through an owner who published only after signing in. Now that owner signs in again.
- R3-02 NIT (GLM) FIXED, same status: the exit-2 paragraph names Internal beside In production.

Waivers and deferrals: none.
Follow-ups: R1-12/R2-08, SKILL.md over its soft line budget.
Notes:
- Round 1 read #363's merged text: the owner merged it (2026-10-21 21:48 UTC) before these fixes, so R1-01's BUG was on `main` until this PR. #363's earlier "3 rounds, 15 findings" left no trail and are not counted here.
- No round 4 was earned (round 3 had no BUG). Round 3's two fixes are `locally_verified`; the wording pass below is the last read.
- Not run: the "Signing in again" command (it would touch a live token; its flags come from `gsc_query.py --help`) and the Python tests (no code changed). The first-consent check and the 8-day run stay open in the BUGLOG row.
