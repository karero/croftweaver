# DIFF review — docs/buglog-pages-dev-not-pursued — the pages.dev and script-monitor row closed, not pursued
Base `74b3a2d` · depth: Light (one BUGLOG row's status; prose no agent follows and no person runs) · verdict: CLEAN after 1 RISK fixed · authority used: POST AUTHORITY — atom A (the owner said in chat "follow your reco": close the row with a Light review); WORKTREE-WRITE and BRANCH-COMMIT — atom A

| Round | Head | Reviewer | Seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|
| 1 | `1676f33` | Codex (gpt-6.1-sol, medium, `--seat codex`) | 55 s / 38,029 | 0/1/0 |

- **R1, RISK (Codex). FIXED in `119d732`.** "which the owner could not switch off there either, as with NEL" was an untested claim about the alias. The status now says that whether the zone's switch reaches the alias, and whether Cloudflare adds the monitor to an alias on its own, are not known and not tested.

No second round: a Light gate runs one more only after a BUG. The changed sentence was checked by the author (`make check`, exit 0), not by a second model.

Why not pursued (the owner's decision in chat, on the author's recommendation): Cloudflare's API documents the switch as a setting for the zone; with the redirect set the alias answers 301 and serves no page; step 5 says to switch the monitor off whatever a capture would show. The owner's two Cloudflare trials (13 and 14 October 2026, `docs/reviews/SKILL-PLAN-cloudflare-setup.md`) did not look at the monitor, so they do not answer it either.
