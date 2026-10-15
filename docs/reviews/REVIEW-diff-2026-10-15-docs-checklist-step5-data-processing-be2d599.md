# DIFF review — docs/checklist-step5-data-processing — step 5: the monitor's data setting for the privacy page; look at the switch on each domain
Base `f640ec8` (main merged in at `f535994`) · depth: High (runbook text and privacy-page advice) · verdict: CLEAN (3 rounds and a wording pass; 37 findings, 1 BUG) · authority used: POST AUTHORITY — atom A (the owner asked in chat: "Start step 5"); WORKTREE-WRITE and BRANCH-COMMIT — atom A

Seats: Codex (gpt-6.1-sol, config effort; medium for the wording pass), GLM 5.3 on melious, a fresh-eyes sub-agent on the host's model in rounds 1 to 3. Data consent as in this session's earlier trails.

| Round | Head | New findings (BUG/RISK/NIT) | Seats |
|---|---|---|---|
| 1 | `ae1de2f` | 0/5/9 | codex 95 s / 46,888; melious 92 s / 12,537; fresh-eyes 132 s |
| 2 | `eeb2bc1` | 1/5/4 | codex 142 s / 56,594; melious 176 s / 20,842; fresh-eyes 123 s |
| 3 | `f535994` | 0/5/8 | codex 154 s / 59,932 (none); melious 128 s / 19,546; fresh-eyes 156 s |
| wording pass | `be2d599` | 0/0/0 new (vendor text again) | codex 64 s / 45,356 |

What changed because of the review (all in this branch):
- Round 1 (F1 to F14): "the switch is set for each domain on its own" was more than was seen (Codex, GLM): now only what was seen, and the owner looks at each other domain. The settings describe what Cloudflare analyses and logs, not what the browser sends (fresh-eyes). The route actually seen (the Global tag, the panel "Connection target details") moved to where the owner sets it. The intro, section 6 and Sources now say what was read and seen. The bug-log row stays open for what is still unknown.
- Round 2 (G1 BUG, fresh-eyes): "don't write it on the privacy page" could be read as undoing "say so on your privacy page". Fixed by rewriting *Why off* (`2ccffe7`); G2 to G10 (naming the chosen setting, a recommendation, the API source, the row's Fix, wording) fixed there too.
- Round 3 (no BUG): more findings on *Why off*'s claims (the host-name wording, a dashboard label on a privacy page, the per-domain API claim, "look at" with no action). After three rounds on the same paragraph it was cut to fewer claims (`be2d599`): the privacy page says that browsers send Cloudflare reports about the page's scripts; Cloudflare's own name and path for the Data processing setting; keep Log host only, and say so on the privacy page if Log full URI is chosen; *Check* says to switch the monitor off where it is on. Section 6 names `PUT /zones/{zone_id}/page_shield`.

Judgment flagged to the owner: the text recommends Log host only (Cloudflare's default, and the choice that logs less). Asked for by the round 2 fresh-eyes seat.

Refuted or follow-up:
- The vendor text (Codex, GLM; every round, and the wording pass): the offline seats cannot read Cloudflare's pages. The fresh-eyes seat fetched https://developers.cloudflare.com/client-side-security/reference/settings/ and https://developers.cloudflare.com/api/resources/page_shield/methods/update/ in each round and found the cited text; the author read both on 14 and 15 October 2026. Kept as a follow-up: nobody has captured the monitor's reports under either setting.

Main was merged in once (`f535994`, #324 had changed the two neighbouring bug-log rows); the conflict was resolved with main's rows and this branch's one row, checked for markers before committing. `make check` exit 0 on every head.
