# PLAN gate: live analytics check after a publish

Plan: `docs/reviews/SKILL-PLAN-live-analytics-check.md` · branch `plan/live-analytics-check` ·
depth: High (the starter's publish script) · seats: Codex + GLM 5.3 on melious
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`) · red team: none (the plan's header says why).

| Round | Head | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|
| 1 | `5f0792ec` | codex alone; melious out of balance (no rerun owed, rule of 2026-10-27) | codex 229 s, 80,384 | 2 / 2 / 0 |

## Round 1

| # | Kind | Finding | Disposition |
|---|---|---|---|
| R1-1 | BUG | A matching `build.txt` does not show that the home page read next comes from the same build; another publish can follow (`ship.sh:995-1001`). | fixed: B reads `build.txt` again after the page and judges it only when it still shows `$id`; otherwise ⚠, not checked. The fromGitHub "newer publish" branch skips the judgment too. A new ship case covers it. The remaining window is named under "Not covered". |
| R1-2 | BUG | "Inline scripts that call `plausible.init(`" overclaims: the counter counts a mention, a comment included (Codex ran it: `1 1 0` on a commented call). | fixed: A says it counts a mention, as the gate's counter does, and claims only that the markup is there; whether the stub runs stays the gate's `stub_runs`. |
| R1-3 | RISK | "The two counters cannot drift apart unnoticed" is more than three captures can show. | fixed: the claim now says the two agree on these inputs only; the comparison takes the "other" count too, and adds a comment-only stub page. |
| R1-4 | RISK | That the real Plausible loader needs the init stub rests on repo comments. | refuted with a run: the real loader, fetched 2026-11-09 from `analytics.m-squad.com` (6,188 bytes), ends `plausible.o&&S(plausible.o),plausible.init=S`. It starts only when the stub's `init()` has set `plausible.o`, or when `plausible.init` is called later. Quoted in A. |

Codex's "unsupported claims" list: the cache-bust claim is now limited to Cloudflare's default
cache key, citing `PUBLISHING.md:368-370`; a zone rule that ignores the query string is listed as
not covered. The guide's state, the open PRs and the branch check were read on 2026-11-09 and are
named in the plan; the captures and tests do not exist yet (build steps 3 and 4).
