# PLAN gate: live analytics check after a publish

Plan: `docs/reviews/SKILL-PLAN-live-analytics-check.md` · branch `plan/live-analytics-check` ·
depth: High (the starter's publish script) · seats: Codex + GLM 5.3 on melious
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`) · red team: none (the plan's header says why).

| Round | Head | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|
| 1 | `5f0792ec` | codex alone; melious out of balance (no rerun owed, rule of 2026-10-27) | codex 229 s, 80,384 | 2 / 2 / 0 |
| 2 | `833da670` | codex alone; melious out of balance | codex 221 s, 70,750 | 2 / 4 / 0 |
| 3 | `eff6aa9a` | codex alone; melious out of balance | codex 195 s, 77,754 | 1 / 2 / 0 |
| 4 | `3bdb9892` | codex alone; melious out of balance; earned by server-mode-tags, page-freshness, stop-handling; cut: the second build.txt read | codex 187 s, 77,908 | 2 / 1 / 0 |

## Round 1

| # | Kind | Finding | Disposition |
|---|---|---|---|
| R1-1 | BUG | A matching `build.txt` does not show that the home page read next comes from the same build; another publish can follow (`ship.sh:995-1001`). | fixed: B reads `build.txt` again after the page and judges it only when it still shows `$id`; otherwise ⚠, not checked. The fromGitHub "newer publish" branch skips the judgment too. A new ship case covers it. The remaining window is named under "Not covered". |
| R1-2 | BUG | "Inline scripts that call `plausible.init(`" overclaims: the counter counts a mention, a comment included (Codex ran it: `1 1 0` on a commented call). | fixed: A says it counts a mention, as the gate's counter does, and claims only that the markup is there; whether the stub runs stays the gate's `stub_runs`. |
| R1-3 | RISK | "The two counters cannot drift apart unnoticed" is more than three captures can show. | fixed: the claim now says the two agree on these inputs only; the comparison takes the "other" count too, and adds a comment-only stub page. |
| R1-4 | RISK | That the real Plausible loader needs the init stub rests on repo comments. | answered by reading (not running) the real loader, fetched 2026-11-09 from `analytics.m-squad.com` (6,188 bytes), ends `plausible.o&&S(plausible.o),plausible.init=S`. It starts only when the stub's `init()` has set `plausible.o`, or when `plausible.init` is called later. Quoted in A. |

Codex's "unsupported claims" list: the cache-bust claim is now limited to Cloudflare's default
cache key, citing `PUBLISHING.md:368-370`; a zone rule that ignores the query string is listed as
not covered. The guide's state, the open PRs and the branch check were read on 2026-11-09 and are
named in the plan; the captures and tests do not exist yet (build steps 3 and 4).

## Round 2

Head `833da670` · codex alone; melious out of balance · codex 221 s, 70,750 tokens · 2 BUG, 4 RISK.

| # | Kind | Finding | Disposition |
|---|---|---|---|
| R2-1 | BUG | "Another build went live meanwhile" is wrong for the fromGitHub branch: a different GitHub `production` shows a newer push, not a live change. | fixed: two messages, one for a changed live `build.txt`, one for a newer push. |
| R2-2 | BUG | "The gate's own `/js/script*.js`" misstates the gate's expression (`check_analytics_gate.sh:214` does not match `scriptfoo.js`; Codex ran it: `0 0 0`). | fixed: A quotes the expression and what it matches. |
| R2-3 | RISK | The gate's patterns read the whole file, so another object's `mode:` makes a healthy publish fail. | fixed: `scriptHost`, `scriptId` and `mode` are read inside the `ANALYTICS` block only; a test case with an unrelated `mode:`. The gate has the same whole-file read; not changed here (a gate change is out of this plan's scope). |
| R2-4 | RISK | A failed second `build.txt` read had no outcome. | fixed: ✗, exit 1, with its own line and a ship case. |
| R2-5 | RISK | The loader claim is still a quoted suffix, not a traced run. (Second time raised.) | fixed by narrowing: "1 script and 1 stub" is now the starter's markup contract (`Base.astro:174-177`, which the gate also requires); the loader reading is kept as "read, not run". |
| R2-6 | RISK | The cache claim rests on `PUBLISHING.md` repeating itself. (Second time raised, so tested.) | measured, 2026-11-09, `curl -I`: croftweaver.com (Pages) `DYNAMIC` for `/` and `/?cb=`; guide.croftweaver.com (Workers static assets) `HIT` for both, so on Workers the query makes no fresh key. The plan now names the one assumption the read rests on (a Workers deployment serves `build.txt` and the HTML from one version) and adds test 6, a live leg on a webcroft.dev throwaway, before the DIFF gate. |

## Round 3

Head `eff6aa9a` · codex alone; melious out of balance · codex 195 s, 77,754 tokens · 1 BUG, 2 RISK.

| # | Kind | Finding | Disposition |
|---|---|---|---|
| R3-1 | RISK | Freshness, third time: `build.txt` reads do not show which build the HTML came from, and two `HIT` headers prove nothing about the cache key. A stale page could pass a build that lost its tag (a silent wrong result). | fixed by design: `build-marker.mjs` stamps `<!-- build: <sha> -->` into `dist/index.html`; the check judges only a page stamped `$id`, retries a page from another build 6 times, 10 s apart, then ✗. The second `build.txt` read is gone. Test 6 now samples how often the page lags; the stamp is the guard. |
| R3-2 | BUG | The server-mode row accepted an older analytics tag (`0 0 1`, Codex ran the gate's counter). | fixed: server mode requires `0 other` too; a test case. |
| R3-3 | RISK | The new fetches, Node run and waits had no stop handling; `ship.sh:446` only notes a signal. | fixed: `stop_asked` is looked at after each, as the `build.txt` loop does; the stop line; TERM cases during the fetch and the wait. |

Follow-on changes from the host's own check: the captures carry no stamp, so the test stamps a
temporary copy and leaves the committed captures as fetched; a build with no `dist/index.html`
warns and goes on; a `/` that redirects to a page with no stamp is ⚠, not checked.

## Round 4

Head `3bdb9892` · codex alone; melious out of balance · codex 187 s, 77,908 tokens · 2 BUG, 1 RISK.
Earned by round 3's kinds `server-mode-tags`, `page-freshness`, `stop-handling`; cut logged:
"the second build.txt read, replaced by the build stamp".

| # | Kind | Finding | Disposition |
|---|---|---|---|
| R4-1 | BUG | A commit id names a commit, not a build: two builds of one commit with different variables carry the same stamp (Codex ran the marker twice: identical). | fixed by narrowing, a cut of the claim: the plan says the stamp names the commit; a same-commit rebuild (a dashboard Retry) is outside ship's flow, which always pushes a new commit, and is listed as not checked. |
| R4-2 | RISK | The launch check would judge the live page against the working copy's `src/config.ts`, not the stamped commit's. | fixed: `--config <path>`; the launch check passes `git show <id>:src/config.ts` (fetching first), 🟡 when the commit cannot be read; a test case. Ship already reads the published copy. |
| R4-3 | BUG | "Counted twice" for a tag in server mode overclaims: `functions/_middleware.ts:85-98` skips server counting when its variables are missing. | fixed: the message says visits "may be" counted twice. |
