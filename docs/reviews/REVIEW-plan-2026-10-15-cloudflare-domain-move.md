# PLAN review — karero/croftweaver#329 — moving an existing domain to Cloudflare, led by the assistant
Base `8f7c98b` · depth: High (mail and the whole domain are at stake; the maintainer chose High in the brief) · verdict: CLEAN (2026-10-15). Three rounds, a final full read and a wording pass; 57 findings in the rounds and the final read (4 BUG: 3 in round 1, 1 in round 2), none in round 3 or the final read; no BUG open; nothing waived; one follow-up (W1) · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `docs/reviews/SKILL-PLAN-cloudflare-domain-move.md`, whole. Raw reviewer output is in the pull request's review comment. Destinations: Codex and melious.ai, on the maintainer's brief for this gate (2026-10-15): "`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3 OLLAMA_MODEL=glm-5.3:cloud CODEX_EFFORT=config`, plus a fresh-eyes sub-agent on the host's own model in rounds 1 to 3". The clean check passed before round 1; the repository is public.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `82bb45b` | full | Codex CLI 0.162.1, gpt-6.1-sol, high (config), read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only | Codex 371 s, 90,887 · Melious 508 s, 23,885 · fresh-eyes 314 s, 148,165 | 3 / 10 / 10 after merging duplicates (Codex 2/3/0, Melious 0/3/3, fresh-eyes 2/5/8). Unverifiable entries: 13 asked (Codex 7 groups, Melious 3, fresh-eyes 3); none led to a change beyond the findings |
| 2 | `a45204f` | full, as a verification round (prior findings A1 to A23, the maintainer's correction named) | the same three seats, same versions and effort | Codex 383 s, 169,823 · Melious 826 s, 42,313 · fresh-eyes 267 s, 157,499 | 1 / 3 / 11 after merging duplicates (Codex 0/2/0, Melious 0/0/6, fresh-eyes 1/3/7). A1 to A3, A5 to A12, A14 to A20, A22, A23 confirmed; A4, A13, A21 in part (B2, B3, B13) |
| 3 | `e768044` | full, as a verification round (prior findings B1 to B15) | the same three seats | Codex 239 s, 86,506 · Melious 528 s, 30,576 · fresh-eyes 273 s, 154,445 | 0 / 5 / 9 after merging duplicates, two of them refuted (C5, C13) (Codex 0/1/0, Melious 0/1/4, fresh-eyes 0/3/6). B1 to B3, B6 to B10, B12, B14 confirmed; B4, B5, B11, B13, B15 in part (C1, C2, C6, C9, C11) |
| final full read (not a round) | `40236a9` | full | ollama cloud, kimi-k3:cloud, text only (has not reviewed this plan before) | 235 s, tokens not reported | 0 / 2 / 3 (F1 to F5) |
| wording pass (not a round) | `ae2bf80` | delta since `e768044`, both files, prose | Codex CLI 0.162.1, gpt-6.1-sol, high (config), read-only | 206 s, 79,561 | 2 contradictions in this record (round 3's counts, the verdict line), fixed; RISK W1 a follow-up. It confirmed C1 to C14 and F1 to F5 as landed |
| confirmation (not a round) | `f4ce8bc` | delta of that fix | the same seat | 80 s, 53,235 | No BUG/RISK/NIT findings |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex, fresh-eyes | 1 | Node's resolver cannot ask for DS, and DS is served by the parent zone, so the DNSSEC gate cannot run as written | fixed, locally_verified | `new dns.promises.Resolver().resolve('example.com','DS')` throws `ERR_INVALID_ARG_VALUE` (run 2026-10-15, Node 26); Shape step 1 drops DS from Node's list, a failed lookup counts as DNSSEC on; "Not verified" 13 names the candidate tools |
| A2 | BUG | fresh-eyes | 1 | Hooks would reduce "Going live" to a pointer, while karero/croftweaver#328 makes it the by-hand attach steps for launch day; the not-active stop is missing | fixed, locally_verified | `cloudflare-setup.mjs` at `fce71bd`: lines 130, 502, 504, 862 read; #328's `CLOUDFLARE_FIRST_DEPLOY.md` lines 12, 37, 85 read; "Hooks" keeps the attach part and lists each line |
| A3 | BUG | Codex | 1 | J6 says the token can never delete or overwrite, while its DNS Edit row allows both | fixed, locally_verified | J6: the guide's rule, not the token's limit (J6 rewritten again for the maintainer's correction, Notes) |
| A4 | RISK | Codex, fresh-eyes | 1 | "A way back that takes minutes" is unsupported: the top-level domain's nameserver TTL bounds a switch back | fixed, locally_verified | M8: the quick way back is fixing the record in Cloudflare; switching back can take the parent's TTL; "Not verified" 13 reads it in the trial |
| A5 | RISK | Codex | 1 | Token verify and the zone list cannot show the rows, or tell one zone from all while the account has one | fixed, locally_verified | "Under (b)": the owner's screenshot of Cloudflare's token summary before it is created; scenario 14; "Not verified" 5 |
| A6 | RISK | Codex | 1 | The CAA trial checks the zone's certificate, not the Pages custom domain's that launch needs | fixed, locally_verified | "Not verified" 11: a throwaway Pages custom domain before and after the CAA records |
| A7 | RISK | fresh-eyes | 1 | Asking the top-level domain for the nameservers through Node's resolver reads a referral as "no data" | fixed, locally_verified | Shape step 1 and "Not verified" 13, with A1. On fresh-eyes' measurement against a loopback stub (ENODATA); not repeated here |
| A8 | RISK | fresh-eyes | 1 | An old site's apex A and AAAA, or `www` A and TXT, which the move keeps, make the setup plan's `launch` refuse and point to "Going live" | fixed, locally_verified | scenario 31; "Hooks": the attach part gains how to handle such a host. Setup plan scenario 24 read |
| A9 | RISK | fresh-eyes | 1 | DNSSEC is never turned back on, so J4's cost is understated | fixed, locally_verified | M9, scenario 25, Shape step 6, J4 |
| A10 | RISK | fresh-eyes | 1 | "Within seven days" refuses a token the setup script accepts (eight days, `MAX_TOKEN_MS`) | fixed, locally_verified | M10 reads it as the setup script does; `cloudflare-setup.mjs:27` at `fce71bd` |
| A11 | RISK | Melious | 1 | Whether the API shows a token's end date is unsupported | fixed, locally_verified | "Under (b)" cites the setup plan, "The token": verify omits `expires_on` without an end date (captures 001, 003); the summary screenshot too |
| A12 | RISK | Melious | 1 | "A proxied `autodiscover` breaks Outlook" has no support in the plan | fixed, locally_verified | scenario 5 cites "Going live" step 3 ("A stray orange cloud on any of these breaks the service"), marked the kit's checklist, not tried |
| A13 | RISK | Melious (fresh-eyes as NIT) | 1 | How the token reaches `CLOUDFLARE_API_TOKEN` is unsaid, against "none of it in a terminal" | fixed, locally_verified | M10: the checklist's section 6 handover (`docs/CLOUDFLARE-CHECKLIST.md:398-400`), with the git-ignore check |
| A14 | NIT | Melious, fresh-eyes | 1 | M6's clause about Cloudflare's nameservers lacks its verb and hides its dependency | fixed, locally_verified | M6 rewritten (also for the correction) |
| A15 | NIT | fresh-eyes (Codex verified) | 1 | Node's resolver takes addresses, not nameserver names | fixed, locally_verified | Shape step 1 |
| A16 | NIT | fresh-eyes | 1 | The trial does not settle every "Not verified" item; scenario 29 cannot be tried | fixed, locally_verified | opening paragraph, status row 3, scenario 29 "guide review" |
| A17 | NIT | fresh-eyes | 1 | The trail file the plan names does not exist | fixed, locally_verified | this file |
| A18 | NIT | fresh-eyes | 1 | Hooks miss `new-website/SKILL.md` §1, question 6 | fixed, locally_verified | "Hooks"; `skills/new-website/SKILL.md:188` read |
| A19 | NIT | fresh-eyes | 1 | "Missed the Microsoft 365 entries" goes beyond the repo's record, which names `autodiscover` | fixed, locally_verified | "Why": the maintainer's account, and what "Going live" records |
| A20 | NIT | fresh-eyes | 1 | The way back needs the old provider to keep serving the zone; nobody asks | fixed, locally_verified | M8 |
| A21 | NIT | fresh-eyes | 1 | An apex ALIAS or ANAME at the old provider would be copied as fixed addresses | fixed, locally_verified | scenario 30 |
| A22 | NIT | Melious | 1 | Scenario 9 does not say the wildcard stays DNS only | fixed, locally_verified | scenario 9 |
| A23 | NIT | Melious | 1 | The setup script's stop lives in an open pull request, while the header names only `main` | fixed, locally_verified | header names karero/croftweaver#328's branch at `fce71bd` |
| B1 | BUG | fresh-eyes | 2 | Hooks count #328's `CLOUDFLARE_FIRST_DEPLOY.md` line 37 as an attach pointer; it sends a domain not on Cloudflare to the move | fixed, locally_verified | line 37 at `fce71bd` read: "The domain is on Cloudflare already ('Going live' below if it is not)"; "Hooks" points it to the new guide |
| B2 | RISK | fresh-eyes, Codex | 2 | A4 in part: scenario 20 still promises a way back in minutes from the old TTLs; the rollback box moves with that wording | fixed, locally_verified | scenario 20 gives M8's reason and promises no quick switch back; "Hooks": the box's wording rewritten to M8 |
| B3 | RISK | fresh-eyes | 2 | A13 in part: M10 allows a file, while "Under (b)" reads the environment only | fixed, locally_verified | M10 names `.dev.vars`; "Under (b)" reads it when the variable is unset and refuses it if git tracks it or does not ignore it, as `cloudflare-setup.mjs` at `fce71bd` does |
| B4 | RISK | fresh-eyes, Codex | 2 | Turning DNSSEC on right after the mail test ends M8's way back early, and old delegations may still be cached | fixed, locally_verified | M9: only once the old setup is retired; scenario 25; "Not verified" 10 adds a validating resolver after the switch |
| B5 | NIT | fresh-eyes | 2 | Hooks keep "the way back" in "Going live" while moving its parts; the kept heading still says "moving" | fixed, locally_verified | "Hooks": which box moves, the heading renamed for the attach step |
| B6 | NIT | fresh-eyes | 2 | Scenario 16a: the move uses Zone Read too | fixed, locally_verified | scenario 16a |
| B7 | NIT | fresh-eyes | 2 | Scenario 24: under (b) the assistant also changes records | fixed, locally_verified | scenario 24 |
| B8 | NIT | fresh-eyes, Melious | 2 | Shape step 1 no longer says where the old nameservers' names come from | fixed, locally_verified | Shape step 1: an NS lookup through the computer's own resolver |
| B9 | NIT | fresh-eyes | 2 | Status row 2 names one correction of three | fixed, locally_verified | status row 2 |
| B10 | NIT | fresh-eyes, Melious | 2 | Scenarios run 28, 30, 31, 29 | fixed, locally_verified | 29 moved before 30 |
| B11 | NIT | fresh-eyes | 2 | "Nothing in this plan has been tried", while a local Node run backs Shape step 1 | fixed, locally_verified | opening: "Nothing of Cloudflare's side" |
| B12 | NIT | Melious | 2 | Shape step 5 drops the API read that M6 and scenario 18 keep; decision 4's note reads as dropping it | fixed, locally_verified | Shape step 5; decision 4's note: the read stays beside the owner's check |
| B13 | NIT | Melious | 2 | A21 in part: an ALIAS looks like a plain A record from outside, so nothing prompts the question | fixed, locally_verified | scenario 30: without an export, the assistant asks |
| B14 | NIT | Melious | 2 | Scenario 5's "settled by: trial" cannot show that a proxied `autodiscover` breaks Outlook | fixed, locally_verified | scenario 5: guide review |
| B15 | NIT | Melious | 2 | "Not verified" 7 needs a second pending zone the trial does not have | fixed, locally_verified | "Not verified" 7: the trial zone removed and added again |
| C1 | RISK | fresh-eyes | 3 | B4 in part: Shape step 6 still offers DNSSEC right after the switch | fixed, locally_verified (not externally re-verified) | Shape step 6: the offer waits for the old setup's retirement, written down |
| C2 | RISK | fresh-eyes | 3 | B5's rename leaves pointers out of "Hooks": #328's `CLOUDFLARE_FIRST_DEPLOY.md` lines 12 and 85, the setup plan's scenario 24 and its "moved there as 'Going live'" | fixed, locally_verified (not externally re-verified) | "Hooks": each named; the setup plan's pointer is plan step 4's one link; at `a31c4ca` |
| C3 | RISK | fresh-eyes | 3 | The later DNSSEC offer is written nowhere a later session reads | fixed, locally_verified (not externally re-verified) | M9; scenario 32; "Hooks": `CLOUDFLARE_CHECK.md` "By hand, always" and the setup plan's scenario 36 |
| C4 | RISK | Codex | 3 | "Resolvers have long dropped the old delegation" is unsupported | fixed, locally_verified (not externally re-verified) | cut: M9 waits the longer of the top-level domain's and the old zone's NS TTLs, read before the switch ("Not verified" 13) |
| C5 | RISK | Melious | 3 | The eight-day reading of `MAX_TOKEN_MS` is unsupported | refuted | `cloudflare-setup.mjs:27` at `a31c4ca`: `MAX_TOKEN_MS = 8 * 86_400_000`, read 2026-10-15 (fresh-eyes read it too, rounds 2 and 3); the text-only seat could not open it |
| C6 | NIT | fresh-eyes | 3 | The opening's two categories leave out what the setup plan's trial saw (captures 001, 003, 132) | fixed, locally_verified (not externally re-verified) | opening: a third category |
| C7 | NIT | fresh-eyes | 3 | Scenario 24: an API write under (b) without a yes | fixed, locally_verified (not externally re-verified) | scenario 24: on her yes to that record |
| C8 | NIT | fresh-eyes | 3 | Scenario 24 offers the switch back without M8's caveat | fixed, locally_verified (not externally re-verified) | scenario 24 |
| C9 | NIT | fresh-eyes, Melious | 3 | B13 in part: an export may flatten an ALIAS too; ask in both cases | fixed, locally_verified (not externally re-verified) | scenario 30 |
| C10 | NIT | Melious | 3 | Scenario 30's "settled by: trial", while the trial has no ALIAS | fixed, locally_verified (not externally re-verified) | scenario 30: guide review |
| C11 | NIT | fresh-eyes | 3 | B15 in part: adding the zone again scans again | fixed, locally_verified (not externally re-verified) | "Not verified" 7: scanned records removed first |
| C12 | NIT | fresh-eyes | 3 | #328's branch moved to `a31c4ca`; line 862 is now 859 | fixed, locally_verified (not externally re-verified) | header re-pinned; "Hooks" cites line 859 and the message text; lines 12, 37, 85, 130, 502, 504 read at `a31c4ca` |
| C13 | NIT | Melious | 3 | Scenario 5 cites "Going live", which moves | refuted | the plan cites the kit as it stands at `8f7c98b`, which holds the rule; "Hooks" moves the DNS-only points into the guide, so the guide carries it |
| C14 | NIT | Melious | 3 | "The checklist" does not name its file | fixed, locally_verified (not externally re-verified) | M10: `docs/CLOUDFLARE-CHECKLIST.md`, section 6 |
| F1 | RISK | Kimi (final full read) | — | The later DNSSEC offer has no per-site record to live in; the by-hand lines are the same for every site | fixed, locally_verified (not externally re-verified) | M9, Shape step 6, scenario 32: a dated line in the site's README (beside "Deploy", as `CLOUDFLARE_FIRST_DEPLOY.md:133` already writes one); the by-hand lines point to it |
| F2 | RISK | Kimi (final full read) | — | A domain on Cloudflare in another account is treated as "already on Cloudflare" | fixed, locally_verified (not externally re-verified) | scenario 26 narrowed to the owner's own account; scenario 26a; "Not verified" 14 |
| F3 | NIT | Kimi (final full read) | — | The token summary screenshot is only on the happy path, though it is the one check for rows and zones | fixed, locally_verified (not externally re-verified) | M10: no token used without it |
| F4 | NIT | Kimi (final full read) | — | No fallback where the old provider fixes TTLs | fixed, locally_verified (not externally re-verified) | scenario 20 |
| F5 | NIT | Kimi (final full read) | — | Line anchors into #328 drift before it merges | fixed, locally_verified (not externally re-verified) | "Hooks": numbers at `a31c4ca`, found again by quoted text in plan step 5 |

Waivers and deferrals: none.

Follow-ups: W1 (RISK, Codex, wording pass) the wait before DNSSEC goes back on (the longer of the top-level domain's and the old zone's NS TTLs, M9) is reasoned, not shown: "Not verified" 13 reads the TTLs, but no trial yet watches a resolver that holds the old delegation across the switch and the new DS. Plan step 3 can add it; until then the guide states the wait as the plan's rule, not as seen.

Notes:
- The maintainer's correction arrived between rounds 1 and 2 (2026-10-15): "suggest b but also offer a, the User still has to do the final verification, so b is fine"; either way the owner checks all entries on a final screenshot looked at with the assistant; the (b) token may serve setup day inside its life. Decisions 3 and 4 rewritten, decision 6 added, M5, M6, M10, J5, J6, scenarios 12, 14 to 18 and 25 changed with round 1's fixes. Round 2 sees both.
- Round 3 found no BUG (series 3, 1, 0), so no round 4 is owed (skill step 6(b)). Its RISKs and NITs were fixed locally, the author's recommendation, not externally re-verified; the final full read and the wording pass read them.
- Final full read (Kimi K3 on ollama, which had not seen the plan): no BUG, so no verification round earned; its findings fixed locally.
- Wording pass: Codex again called the scope note sent with `--verify` a prompt injection and reviewed past it (as on karero/croftweaver#303); the scope still needs another way in.
- The review stamp names `f4ce8bc`, the last head a reviewer saw (the confirmation); the commit after it adds only these closing rows to this record.
- Cost: Codex 1,279 s over five runs, Melious 1,862 s over three, Kimi 235 s; fresh-eyes 854 s over three rounds; tokens: 576,786 for Codex and Melious, 460,109 for fresh-eyes, 1,036,895 in all as logged (Kimi gave no figure).

## Gate 2 — the three stages (decisions 1 and 7), the trial domain, hooks re-pinned after #328

Base `8f7c98b` (the branch is not rebased; `main` read at `5d35db1`) · depth: High, as gate 1 · verdict: OPEN (rounds 1 and 2 done, round 3 owed) · authority used: as gate 1

The maintainer reversed the order after gate 1 closed (preview first, the move just before launch) and said yes to three stages. A change to a decision, so a gate of its own, on the whole plan with the change named.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `39ff019` | full, changed sections named (`--verify`, with gate 1's refuted C5 and C13) | the same three seats as gate 1 | Codex 321 s, 130,990 · Melious 485 s, 33,195 · fresh-eyes 223 s, 154,832 | 4 / 2 / 4 after merging duplicates (Codex 4/1/0, Melious 0/1/3, fresh-eyes 2/1/3), and outside scope 2 RISK, 2 NIT. C5 and C13 refutations held |
| 2 | `08d1cc8` | full, as a verification round (G1 to G10) | the same three seats | Codex 300 s, 95,867 · Melious 759 s, 42,373 · fresh-eyes 253 s, 156,838 | 2 / 4 / 7 after merging duplicates (Codex 1/1/0, Melious 0/1/4, fresh-eyes 1/4/4), and outside scope 1 BUG, 2 NIT. G1 to G5, G7, G10 confirmed; G6, G8, G9 in part (H4, H7, H2) |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| G1 | BUG | fresh-eyes, Codex (Melious as NIT) | 1 | The opening still puts the move "before the setup script runs" | fixed, locally_verified | opening: "in launch prep: after the site's preview, before it goes live" |
| G2 | BUG | fresh-eyes, Codex | 1 | `main.<project>.pages.dev` as everyone's preview is wrong for a single-stage site, where `main` is live | fixed, locally_verified | M1 and decision 7: two-stage only; single-stage has pull-request previews |
| G3 | BUG | Codex | 1 | `CLOUDFLARE_FIRST_DEPLOY.md:37` keeps "The domain is on Cloudflare already" as a condition of `setup`, which the preview no longer meets | fixed, locally_verified | "Hooks": the condition holds only for launch prep's run; line 37 at `5d35db1` read |
| G4 | BUG | Codex (fresh-eyes as NIT) | 1 | Shape still turns all of "Going live" into a pointer and keeps the script's stop, against "Hooks" | fixed, locally_verified | "Where it lives" |
| G5 | RISK | fresh-eyes, Codex | 1 | The setup-script hook leaves out that the account comes only from the zone, that a preview token cannot be limited to an unborn zone, and section 6's two days | fixed, locally_verified | "Hooks": all three named; `cloudflare-setup.mjs:495-510` at `5d35db1` read; the checklist's section 6 added |
| G6 | RISK | Melious | 1 | The script change stage 1 depends on is tracked nowhere | fixed, locally_verified | status row 5a: not this plan's work; plan steps 5, 7 and 8 wait for it |
| G7 | NIT | fresh-eyes | 1 | Scenario 20a's lead time stops at the zone turning active, leaving launch prep's `setup` run on launch day | fixed, locally_verified | scenario 20a |
| G8 | NIT | fresh-eyes | 1 | M1 has `launch` attach the domain, while the launch stage is not in the script yet | fixed, locally_verified | M1: by hand, as "Going live" says, until it ships |
| G9 | NIT | Melious | 1 | Scenario 26a: the TTLs and keeping the old zone also need the other account's holder | fixed, locally_verified | scenario 26a |
| G10 | NIT | Melious | 1 | Lines 502 and 504 are anchored by number only | fixed, locally_verified | "Hooks" quotes both messages |
| H1 | BUG | fresh-eyes | 2 | Scenario 14 sizes the (b) token to the last check, which comes before the DNSSEC wait, while scenario 24 writes with it after the switch | fixed, locally_verified | scenario 14: through the mail test, a second token for a later fix |
| H2 | BUG | Codex (fresh-eyes as NIT and RISK) | 2 | G9 in part: scenario 26a gives scenario 20's fallback for every refusal, and promises a way back nothing backs | fixed, locally_verified | scenario 26a: one consequence per refusal, no switch back without the old zone; "Not verified" 14 asks after the old zone |
| H3 | RISK | fresh-eyes, Codex | 2 | `CLOUDFLARE_FIRST_DEPLOY.md` lines 28 to 33 and 38 to 43 still tie the preview's run to a zone | fixed, locally_verified | "Hooks"; both read at `4c890f6` |
| H4 | RISK | fresh-eyes | 2 | G6 in part: nothing hands row 5a's request to the setup plan | fixed, locally_verified | rows 4 and 5a: plan step 4 hands it over in the setup plan |
| H5 | RISK | fresh-eyes (Melious as NIT) | 2 | "A preview token cannot be limited to a zone not yet added" is unsupported and invites dropping the one-zone guard | fixed, locally_verified | "Hooks": not said ("Not verified" 5); the guard stays |
| H6 | RISK | Melious | 2 | That launch prep's settings change nothing visible rests on M4 alone | fixed, locally_verified | M1 hedged; "Not verified" 15 with a trial |
| H7 | NIT | fresh-eyes | 2 | G8 in part: the 301 is in "After go-live", not "Going live" | fixed, locally_verified | M1 |
| H8 | NIT | fresh-eyes | 2 | Decision 7 amended without a note | fixed, locally_verified | decision 7 |
| H9 | NIT | fresh-eyes | 2 | Row 5 does not wait on row 5a | fixed, locally_verified | row 5 |
| H10 | NIT | fresh-eyes | 2 | The opening's "the files win until plan step 5" misses row 5a; an unwrapped line | fixed, locally_verified | opening |
| H11 | NIT | Melious | 2 | Several anchors still by number only | fixed, locally_verified | "Hooks" quotes lines 12, 85, 130, 498, 505 |
| H12 | NIT | Melious | 2 | Section 6's change is tracked nowhere | fixed, locally_verified | row 5a |
| H13 | NIT | Melious | 2 | Two names for the script change's owner | fixed, locally_verified | "the setup plan" throughout |
| H14 | BUG | fresh-eyes (outside scope) | 2 | Status row 4 says #331 is open; it merged | fixed, locally_verified | row 4; header re-pinned to `4c890f6` |

Follow-ups (outside scope): G11 (RISK, Codex) scenario 26a: an old site that relies on Cloudflare's proxy in the other account would lose it if copied as DNS only; the trial's item 14 can look at one. G12 (RISK, Codex) re-raise of W1. G13 (NIT, Melious) a three-day token could expire in the DNSSEC wait: fixed anyway, scenario 14 now a week. G14 (NIT, fresh-eyes) "#328's lines" after a header naming `main`'s: fixed anyway. H15 (NIT, Melious, round 2) Shape step 1's Node claims lacked a citation: fixed anyway, measured on 2026-10-15 (A1, A7).
