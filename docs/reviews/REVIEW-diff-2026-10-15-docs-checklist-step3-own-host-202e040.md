# DIFF review — docs/checklist-step3-own-host — step 3 (and section 5) name the script monitor's own-domain address
Base `f640ec8` · depth: High (a runbook step about a privacy setting) · verdict: CLEAN (3 rounds and a wording pass; 21 findings, no BUG) · authority used: POST AUTHORITY — atom A (the owner asked in chat: "Do step 3"); WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session's worktree and branch)

Seats: Codex (gpt-6.1-sol, config effort; medium for the wording pass), GLM 5.3 on melious, a fresh-eyes sub-agent on the host's model in rounds 1 to 3. Data consent as in this session's earlier trails.

| Round | Head | New findings (BUG/RISK/NIT) | Seats |
|---|---|---|---|
| 1 | `510cea3` | 0/3/4 | codex 120 s / 63,273; melious 71 s / 8,870; fresh-eyes 111 s |
| 2 | `9fcc5e0` | 0/1/4 | codex 138 s / 62,431; melious 88 s / 14,240; fresh-eyes 94 s |
| 3 | `d97890c` | 0/3/6 | codex 100 s / 52,154 (none); melious 135 s / 15,981; fresh-eyes 109 s |
| wording pass | `202e040` | 0/0/0 new (the source point again) | codex 51 s / 40,724 |

Round 1:
- F1 RISK (fresh-eyes) FIXED in `9fcc5e0`: section 5's reading guide still named only csp-reporting.cloudflare.com and called other report-to lines the owner's own, so it disagreed with step 3. The same clause is there now. (Beyond "step 3" as asked; without it this PR would have left the two disagreeing.)
- F2 RISK (GLM) REFUTED: the path and plan name rest on Cloudflare's settings page. The fresh-eyes seat read it live in rounds 1, 2 and 3: "<YOUR-HOSTNAME>/cdn-cgi/script-monitor/report?<QUERY_STRING>", "Only available to customers with Client-Side Security Advanced". Raised again by Codex in the wording pass: a follow-up, since no captured response exists.
- F3 RISK (GLM) REFUTED: the BUGLOG closure's claim about #322; Codex read `ownHostReport` in the checkout and reproduced it.
- F4 NIT (fresh-eyes) FIXED: the address is marked as Cloudflare's documentation, not seen live.
- F5 NIT (fresh-eyes) FIXED: the open pages.dev row's planned sentence includes the path.
- F6, F7 NIT (fresh-eyes, GLM) FIXED, then cut in `202e040`: "on your own domain" was loose.

Round 2:
- G1 RISK (fresh-eyes) FIXED in `d97890c`, then `202e040`: the pages.dev row named the owner's domain for lines read on the alias; the capture now looks for the path on any host and says it shows only on a zone with Client-Side Security Advanced.
- G2 to G5 NIT (all seats) FIXED, then cut: two descriptions of the address, the query, section 5's source, the "with Advanced" reading.

Round 3:
- H1 RISK (fresh-eyes) CUT in `202e040`: the literal `https://yourdomain.com/...` would not match a relative address the checker accepts. Now "an address on your own domain whose path is ...".
- H2 RISK (fresh-eyes) FIXED in `202e040`: the pages.dev capture looked only on the alias; now any host, noting which.
- H3 RISK (GLM) REFUTED, and the claim is gone: that a query on the own-host address does not change the reading; #322's tests use `?m=1` on the full-address forms, and the cut text no longer mentions a query.
- H4, H5, H7, H8, H9 NIT (fresh-eyes, GLM) CUT in `202e040`: the "?" gloss, section 5's query, section 5's source (it now points to step 3, which links the page), substituting the alias host, "which lines carry it".
- H6 NIT (fresh-eyes) REFUTED: the open pages.dev row (dated 2026-10-14) describes step 3 as it read on that date.

Notes: the same clause drew wording findings in all three rounds; after round 3 it was cut to fewer claims rather than patched again (see docs/reviews/RETRO-2026-10-14-brand-kit-review-cost.md on cuts). `make check` exit 0 on every head.
