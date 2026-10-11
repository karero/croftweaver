# DIFF review — karero/website-builder#233 — docs: close the flaky merge_link row; record #192's live run

Base `origin/main` · depth: **Normal**, owner's choice ("review them properly") over Light, for two prose edits · verdict: **CLEAN — no BUG open**; the remaining RISKs ask for evidence the review sandbox cannot reach, kept below.

| Round | Head | Artifact | Reviewers | BUG/RISK/NIT |
|---|---|---|---|---|
| 1 | `docs/close-dependabot-followups` (uncommitted) | both files, with the evidence brief | Codex `gpt-6.1-sol`, read-only; melious `glm-5.3`, HTTP API | 1 / 2 / 1 |
| 2 | same, after the fix | the BUGLOG sentence, with round 1's dispositions (`--seat codex`) | Codex | 0 / 2 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-1 | RISK | codex, glm | 1 | "no failed `clean.yml` run" does not show the check ran: cancelled runs fail nothing, and nothing tied `clean.yml` to the job | fixed | the Status now counts the job itself (below) |
| R1-2 | NIT | glm | 1 | the 100-run window started 2026-10-07 08:47 UTC, leaving a gap after the flake | fixed | the count starts 2026-10-06 13:40 UTC |
| R1-3 | BUG | codex | 1 | the review brief dated #193's merge 2026-10-07 | fixed (brief only) | merged 2026-10-06 15:57:46 UTC; the diff no longer mentions #193 |
| R2-1 | RISK | codex | 2 | the 169/38/1 tally has no retained evidence | settled here | the method and IDs below |
| R2-2 | RISK | codex | 2 | the live run has no retained evidence | settled here | the record below; the site repo is private and unnamed |

## Evidence

**The flake's job tally**, measured 2026-10-09 with `gh`. List every `clean.yml` run created since 2026-10-06 13:40 UTC (`actions/workflows/clean.yml/runs?created=>=2026-10-06T13:40:00Z`, all pages: 206 runs, newest 2026-10-09 11:47:55 UTC). For each attempt of each run, read the conclusion of its `macos-stock-tools` job (`actions/runs/<id>/attempts/<n>/jobs`): 169 success, 38 cancelled, 1 failure. The failure is run 37473540485, attempt 1, 2026-10-06 13:47:01 UTC; that run is `clean.yml`, and its attempt 2 passed. In `clean.yml`, `macos-stock-tools` runs every guard inside the unzipped handoff zip, `test_failed_tier_report.sh` among them; case 30 is the `merge_link` check. 126 of the green attempts came after #193 changed `merge_link.sh`, and 43 before, so #193 is not why it stopped failing.

**#192's live run**, on a private site repo built from the kit, with the owner's go in chat. On 2026-10-08 at 19:44:16 UTC, from the site's folder:
- the first line printed the site's repo;
- both `PUT`s exited 0, and the read-back printed `alerts: on` and `security updates: on`;
- at 19:44:26, alerts #1 to #3 were listed;
- from 19:45:41 to 19:45:50, Dependabot opened that repo's PRs #69 to #71 (`sharp`, `source-map-js`, `devalue`), each changing only `package-lock.json`;
- by 19:51, 9 alerts in all, `http-cache-semantics` among them: its advisory lists no patched version, and it got no PR;
- the site's CI (`test`, `Cloudflare Pages`) ran on all three PRs.

On 2026-10-09, a commit on the site ran `npm audit fix`, GitHub marked all 9 alerts fixed, and Dependabot closed the three PRs as no longer needed.

Waivers: none. Deferrals: none. Follow-ups: none.
