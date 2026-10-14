# PLAN review — karero/croftweaver#320 — Cloudflare setup plan: the second trial's results
Base `6c4c38d` · depth: High (the maintainer chose High for this plan; the script changes an account with a token and can make a site public) · verdict: OPEN, round 3 under way · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `docs/reviews/SKILL-PLAN-cloudflare-setup.md`, whole, with the sections this change touches named. The plan passed its own gate in karero/croftweaver#303 (`docs/reviews/REVIEW-plan-2026-10-14-pr303.md`); this is a new gate on the change. Raw reviewer output is in the pull request's review comment.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `72e652d` | full, changed sections named | Codex CLI, gpt-6.1-sol, config effort, read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only | Codex 508 s, 132,079 · Melious 370 s, 44,996 · fresh-eyes 285 s, 157,218 | 4 / 12 / 7 after merging duplicates (Codex 2/5/0, Melious 1/2/3, fresh-eyes 1/8/6) |
| 2 | `12ea3a0` | full, as a verification round (prior findings V1 to V23) | the same three seats, same versions and effort | Codex 355 s, 105,755 · Melious 557 s, 49,908 · fresh-eyes 332 s, 157,862 | 3 / 3 / 12 after merging duplicates (Codex 1/2/0, Melious 1/1/4, fresh-eyes 1/2/11), and outside scope 3 RISK, 1 NIT. V1, V2, V4, V6, V10 to V12, V14, V17, V18, V20, V22, V23 confirmed; V3, V5, V9, V13 in part |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| V1 | BUG | Codex (fresh-eyes as RISK) | 1 | The checklist's script monitor switch (section 3, step 5, from karero/croftweaver#313) is in no by-hand list, report or hook | fixed, locally_verified | "Afterwards, by hand"; the report paragraph; scenario 36; "Hooks" (`CLOUDFLARE_CHECK.md`'s "By hand, always" lacks it); `docs/CLOUDFLARE-CHECKLIST.md:156` read |
| V2 | BUG | Codex | 1 | "A new commit gives a new question" is false for `setup`, whose code names no commit | fixed, locally_verified | "A yes is a second run with a code": scoped to `launch`; setup's first build is of the head when it runs |
| V3 | BUG | Melious | 1 | "No read shows which accounts a token reaches" overstates: with Account Settings Read the list showed two | fixed, locally_verified | "The token": both results, and that Account Resources at T2-031 was not recorded |
| V4 | BUG | fresh-eyes | 1 | "Tests" cut the rule for answers made from the reference, which scenarios 14, 25 and 39 need | fixed, locally_verified | "Tests": the domain statuses, a refused write and a slow answer are made from the reference, marked so |
| V5 | RISK | Codex, fresh-eyes | 1 | `is_robots_txt_managed` "always false" clashes with "as read" and `--skip ai`, and changes a setting no line names | fixed, locally_verified | cut: the field is left out of the PUT (a field left out keeps its value, T2-061, T2-062); scenario 13 |
| V6 | RISK | fresh-eyes | 1 | No capture shows a PUT that writes `bot_preference_sync_enabled` | fixed, locally_verified | T2-063: a PUT with it `false` was accepted; now cited in script step 5 |
| V7 | RISK | Melious | 1 | No capture shows `ai_training: disabled` accepted in a PUT | refuted | T2-073 changed `ai_training` from `disallow` to `disabled` and was accepted, read back in T2-077; now cited |
| V8 | RISK | Melious (fresh-eyes as NIT) | 1 | A token narrowed just now can show extra zones for minutes; the refusal would confuse | fixed, locally_verified | "The token" |
| V9 | RISK | fresh-eyes | 1 | "The apex behaves as a host below" overstates: the apex held only an A record, no MX or TXT | fixed, locally_verified | "Not verified" 3 narrowed; plan step 10 is the first try with mail records |
| V10 | RISK | fresh-eyes | 1 | The `is_skipped` exclusion has no test | fixed, locally_verified | scenario 11 |
| V11 | RISK | fresh-eyes | 1 | The status header names `de64ec8`; the kit has moved and gained the script monitor | fixed, locally_verified | header `6c4c38d`; V1 |
| V12 | RISK | fresh-eyes | 1 | karero/croftweaver#319 is not merged, so the checklist still names the wrong field | fixed, locally_verified | "Hooks" and status row 9 say it is open; plan step 6 waits for it |
| V13 | RISK | Codex (fresh-eyes as NIT) | 1 | Creating the ruleset by PUT can replace one another person created in between | fixed, locally_verified | script step 12 names it as not tried and reads the phase again just before; "Hooks" |
| V14 | RISK | Codex | 1 | The zone list's pagination is unstated, so a long list could hide zones | fixed, locally_verified | "The token": read page by page to its end |
| V15 | RISK | Codex | 1 | Pages PATCH preservation, snapshots and push behaviour rest on capture summaries | refuted | re-raise of the earlier gate's J20, K13 and N10 without new evidence; the captures will be committed, cleaned, in plan step 6 |
| V16 | RISK | Codex | 1 | The apex attach and PATCH rest on capture summaries | refuted | on the author's read of T2-042 to T2-056 (new captures, not a re-raise); they will be committed, cleaned, in plan step 6 |
| V17 | NIT | Melious | 1 | Status row 9 claims an answer to which switch `is_robots_txt_managed` is | fixed, locally_verified | row 9: it stays unknown |
| V18 | NIT | Melious, fresh-eyes | 1 | The opening still speaks of plan step 9 in the future; status row 4 points to "Not verified" 2, now settled | fixed, locally_verified | opening paragraph; status row 4 |
| V19 | NIT | Melious | 1 | Scenarios 41 and 42 sit out of numeric order | refuted | they sit in the `launch` block where they belong; the table is grouped by stage, not sorted by number |
| V20 | NIT | fresh-eyes | 1 | "A new zone's defaults" cites the zone in use | fixed, locally_verified | the row cites the empty zone first and names the other |
| V21 | NIT | fresh-eyes | 1 | T2-065 is cited for "`true` refused", but T2-066 isolates the field | refuted | T2-065 is the PUT with `is_robots_txt_managed: true` alone, refused; T2-066 is the read after it |
| V22 | NIT | fresh-eyes | 1 | "Not verified" 2 counts three fields left out where the PUT now sends one of them | fixed, locally_verified | with V5's cut, the three left out are named |
| V23 | NIT | fresh-eyes | 1 | "Hooks" says the script sends nothing back, but creating the ruleset writes the whole list | fixed, locally_verified | "Hooks" |
| X1 | BUG | fresh-eyes | 2 | V3 in part: the trial table and "Not verified" 9 still say the accounts list does not show a token's reach | fixed, locally_verified | both reworded as "The token" is: empty with the plan's rows, two accounts with Account Settings Read, Account Resources not recorded |
| X2 | BUG | Codex (fresh-eyes as NIT) | 2 | V2's sentence promises a new code for any new host or flag, beyond the listed inputs | fixed, locally_verified | "a change to any input listed above", with the hosts only where the code names them |
| X3 | BUG | Melious (fresh-eyes as NIT) | 2 | The opening and status row 1 call the plan's gate clean while this change's gate is open | fixed, locally_verified | both name this gate and its state |
| X4 | RISK | Codex, Melious (fresh-eyes as NIT) | 2 | V13 in part: creating the ruleset still has a race with no detection | fixed, locally_verified | a judgment call, with the case against: create, read the phase just before, read back after, report foreign rules with 1; R7 names the case as its one exception. Same ground as V13, so decided rather than patched again |
| X5 | RISK | fresh-eyes (Codex as RISK) | 2 | V5 in part: no PUT of the trials left `is_robots_txt_managed` out | fixed, locally_verified | "Not verified" 2 says so; the read-back shows it; plan step 10 first tries it. T2-061's body read: it sent the field as `false` |
| X6 | RISK | fresh-eyes | 2 | V9 in part: the trial table still headlines the apex without a qualifier | fixed, locally_verified | "An apex holding only an A record" |
| X7 | NIT | Melious, fresh-eyes | 2 | Status row 4 says "Not verified" 2 settled; it is settled in part | fixed, locally_verified | row 4 |
| X8 | NIT | Melious | 2 | The table does not carry the `ai_training: disabled` PUT | fixed, locally_verified | Bot Management row: T2-073, T2-077 |
| X9 | NIT | Melious, fresh-eyes | 2 | V19's and V16's refutations give the wrong reasons; V15 states a future step as done | fixed, locally_verified | V15, V16, V19 rows |
| X10 | NIT | fresh-eyes | 2 | "Tests": the list of answers made from the reference reads as complete | fixed, locally_verified | "for example", with more cases |
| X11 | NIT | fresh-eyes | 2 | Status row 6 does not say it waits for karero/croftweaver#319 | fixed, locally_verified | row 6 |
| X12 | NIT | fresh-eyes | 2 | Scenario 33 lacks the minutes message and a second page | fixed, locally_verified | scenario 33 |
| X13 | NIT | fresh-eyes | 2 | The trial section says the two rules were removed; they are the maintainer's to remove | fixed, locally_verified | "Seen in the second trial" |

Waivers and deferrals: none.

Follow-ups: X14 (RISK, Melious, round 2, outside scope) what `disabled` does in the four AI policies rests on Cloudflare's field descriptions; the check's `ai` item sends six crawler-named requests after launch and shows a refusal as a `look`. X15 to X17 (RISK, Codex, round 2, outside scope) re-raises of V15, V16 and the zone list's completeness. X18 (NIT, Melious, round 2, outside scope) the trial wrote to the first zone before reading its records; for trial practice, read a zone's records before the first write.

Notes:
- The trial's own record: 78 captures (T2-001 to T2-078) kept outside every repository. The first domain the maintainer named held live services; two header rules written there are being removed by hand. The maintainer has not yet said what the token's Account Resources named at T2-031.
