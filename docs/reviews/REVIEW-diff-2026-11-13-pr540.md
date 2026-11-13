# DIFF review — karero/croftweaver#540 and #544 — ship.sh: an unreachable live site no longer reads as an OLD build

Base `c3f082a8` · depth: Normal (shipped template code that publishes; not auth, data or deploy
wiring) · verdict: OPEN (one BUG the change introduced, one older BUG) · authority used:
WORKTREE-WRITE and BRANCH-COMMIT — this session created the worktree and the branch
`docs/review-ship-unreachable`.

A review after the merge. #540 merged on 2026-11-12 and #544 on 2026-11-13 with no review on
record: no GitHub review, no row in the cost log, no trail. Both came from cloud sessions. No
marker is stamped: nothing is left to gate. POST AUTHORITY on #540 and #544: none, so the raw
reviewer output is a comment on this trail's own PR.

Artifact: `git diff c3f082a8 6e8e98c8 -- skills/new-website/templates/astro/scripts/ship.sh
skills/new-website/templates/astro/tests/check_ship_push.sh` (174 lines; no other commit touched
the two files in that range). Gate id 20261113T112929Z-44988.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `6e8e98c8` | full, `--base c3f082a8` | Codex (codex-cli 0.168.0, gpt-6.1-sol, config effort, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 181 s, 45,183; melious 495 s, 29,281; fresh-eyes 514 s, 99,094 | 2 / 2 / 1 after dedup |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| S1 | BUG | Codex (BUG), melious (NIT), fresh-eyes (NIT) | 1 | A curl exit other than 0 counts as "no reply" even when an HTTP status came back (a cut-off transfer, a timeout after the headers, a redirect loop). If every look ends that way, ship says the site "could not be reached from this machine: no reply", though it answered. | open, BUGLOG row 2026-11-13 | `ship.sh:1133`: `if [ "$crc" != 0 ] \|\| [ "$last_code" = 000 ] \|\| [ -z "$last_code" ]; then last_look=noreply`. Codex fed the classifier HTTP 503 with exit 18 and HTTP 200 with exit 28 and got `noreply`. Read here, not rerun. |
| S2 | BUG | Codex (BUG), fresh-eyes (NIT) | 1 | Any 200 whose body is not this commit id reads as "serves an OLD build", an empty or HTML body included; the new comment says only another commit does. | open, BUGLOG row 2026-11-13; not introduced | Before #540 the poll was `curl -sfL … \|\| true` and every non-matching body got the same verdict. No KNOWN WRONG test, so not deferred under the skill's step 5. |
| S3 | RISK | Codex (RISK), fresh-eyes (NIT) | 1 | The Cloudflare steps still follow an HTTP error and a late lapse in replies. | follow-up, in S2's row | Before #540 these cases got "OLD build" and the same steps. |
| S4 | RISK | melious | 1 | A stop during the wait on an unreachable site would be told "no reply in 6 minutes". | refuted | `ship.sh:1146-1152`: a stop prints "Stopped during the live-site check" and exits 1 inside the loop; the text after the loop is never reached. |
| S5 | NIT | melious | 1 | L3f checks the 503 wording but not that the push landed, as L3d does. | follow-up, in S1's row | `tests/check_ship_push.sh`, L3f. |

Follow-ups: S3 and S5, in the two BUGLOG rows.

Notes:
- UNVERIFIABLE: 7 asked (Codex 2, melious 5), 0 confirmed. melious's question on the stop block
  became S4, refuted. Cloudflare's own behaviour (why a build is missing, the dashboard paths) was
  not checked by any seat.
- The tests: `bash tests/check_ship_push.sh` on macOS `/bin/bash` 3.2.57 was started for this
  review; its result is in this trail's PR.
- No round 2: nothing was fixed in this gate. S1 and S2 need a fix PR with its own review.
