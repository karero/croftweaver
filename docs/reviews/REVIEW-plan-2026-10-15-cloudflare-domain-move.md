# PLAN review — karero/croftweaver#329 — moving an existing domain to Cloudflare, led by the assistant
Base `8f7c98b` · depth: High (mail and the whole domain are at stake; the maintainer chose High in the brief) · verdict: OPEN (round 1 done, round 2 owed) · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `docs/reviews/SKILL-PLAN-cloudflare-domain-move.md`, whole. Raw reviewer output is in the pull request's review comment. Destinations: Codex and melious.ai, on the maintainer's brief for this gate (2026-10-15): "`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3 OLLAMA_MODEL=glm-5.3:cloud CODEX_EFFORT=config`, plus a fresh-eyes sub-agent on the host's own model in rounds 1 to 3". The clean check passed before round 1; the repository is public.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `82bb45b` | full | Codex CLI 0.162.1, gpt-6.1-sol, high (config), read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only | Codex 371 s, 90,887 · Melious 508 s, 23,885 · fresh-eyes 314 s, 148,165 | 3 / 10 / 10 after merging duplicates (Codex 2/3/0, Melious 0/3/3, fresh-eyes 2/5/8). Unverifiable entries: 13 asked (Codex 7 groups, Melious 3, fresh-eyes 3); none led to a change beyond the findings |

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

Waivers and deferrals: none.

Follow-ups: none yet.

Notes:
- The maintainer's correction arrived between rounds 1 and 2 (2026-10-15): "suggest b but also offer a, the User still has to do the final verification, so b is fine"; either way the owner checks all entries on a final screenshot looked at with the assistant; the (b) token may serve setup day inside its life. Decisions 3 and 4 rewritten, decision 6 added, M5, M6, M10, J5, J6, scenarios 12, 14 to 18 and 25 changed with round 1's fixes. Round 2 sees both.
