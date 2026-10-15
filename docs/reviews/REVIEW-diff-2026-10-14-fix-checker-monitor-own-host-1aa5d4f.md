# DIFF review — fix/checker-monitor-own-host — the checker names the script monitor when it reports to the site's own host
Base `054ed70` · depth: Normal (shipped checker code; no personal data, no auth) · verdict: CLEAN (3 rounds and a wording pass; 16 findings, 4 BUG; one RISK raised every round and refuted, kept as a follow-up) · authority used: POST AUTHORITY — atom A (the owner asked in chat to run the sweep of this session's four bug-log rows); WORKTREE-WRITE and BRANCH-COMMIT — atom A (a worktree and a branch this session created)

Data consent: Codex and melious.ai (GLM 5.3) have been cleared for this repo's content throughout this session. A grep for keys and tokens over each artifact found nothing.

| Round | Head | Reviewers | Seconds, tokens | BUG/RISK/NIT (new) |
|---|---|---|---|---|
| 1 | `7f1ccdd` | Codex (gpt-6.1-sol, config effort), GLM 5.3 on melious, fresh-eyes (Sonnet sub-agent) | codex 236 s / 69,893; melious 190 s / 20,766; fresh-eyes 104 s / 102,741 | 2/3/3 |
| 2 | `97d426b` | Codex (medium, `--verify`), GLM 5.3 | codex 87 s / 70,703; melious 191 s / 28,023 | 2/0/2 (and R2 again) |
| 3 | `271c1e4` | Codex (medium, `--verify`), GLM 5.3 | codex 112 s / 43,475; melious 158 s / 18,162 | 0/1/3 (and R2 again) |
| wording pass | `1aa5d4f` | Codex (medium, `--seat codex`) | 61 s / 38,450 | 0/0/0 (R2 again: follow-up) |

Findings:
- **B1 BUG (Codex; fresh-eyes RISK). FIXED in `a68df42`, then `271c1e4`.** Addresses on redirect hops were resolved against the final URL. First fix judged the final answer only; round 2 (C1, Codex) showed that lost a hop's own-host address while the Cloudflare host on a hop is still named. Now each answer keeps its URL (`chainUrls`) and its addresses are read against it. Tests: a hop-only address is named; a hop-relative address is read against the hop; the same relative address on `/de/` is not the path.
- **B2 BUG (GLM; fresh-eyes RISK). FIXED in `97d426b`.** The bug-log row this change fixes still read `open` as if nothing had changed. It now says the checker and the reference are fixed in #322 and step 3 of the checklist is still to say it.
- **R1 RISK (fresh-eyes; Codex, an ftp:// example). FIXED in `a68df42`, then `271c1e4`.** Host-only comparison let another scheme or port match. Round 2 (C2, Codex) found the first fix still stripped a trailing dot, so two different origins counted as one; the comparison is now `URL.origin`, pinned by a unit test (`1aa5d4f`).
- **R2 RISK (Codex, GLM; every round). REFUTED with evidence, follow-up.** The path `/cdn-cgi/script-monitor/report` rests on Cloudflare's settings page, which the offline seats cannot read. The page was read live twice on 14 October 2026, by the author and by the round 1 fresh-eyes seat (https://developers.cloudflare.com/client-side-security/reference/settings/index.md): "Customers with Client-Side Security Advanced can change the reporting endpoint so that the CSP reports are sent to the same hostname: <YOUR-HOSTNAME>/cdn-cgi/script-monitor/report?<QUERY_STRING>". The unsourced comment that /cdn-cgi/ is Cloudflare's alone was removed. A captured header from a zone with that setting would settle it for good; none is available.
- **R3 RISK (Codex; fresh-eyes and GLM NITs). FIXED in `a68df42`.** "Here the reports go to the site's own address" claimed delivery and exclusivity; it now says a header lists the address.
- **N1, N2 NIT (fresh-eyes, GLM). FIXED in `a68df42`.** `reporting-endpoints` negatives and a relative `reporting-endpoints` address are tested.
- **N3 NIT (fresh-eyes). DEFERRED (owner's choice in chat).** Step 3 and section 5 of `docs/CLOUDFLARE-CHECKLIST.md` still name only csp-reporting.cloudflare.com: another session's #319 is open on that file; the bug-log row stays open for it.
- **C4, C5 NIT (GLM). FIXED in `271c1e4`.** The reference names scheme and port; the three header names are written once.
- **D1 RISK (GLM). REFUTED.** That `h[name]` might miss a header written in another case: Node's `IncomingMessage.headers` keys are lower case, `values()` reads them the same way, and the tests send `Content-Security-Policy-Report-Only` and `Report-To` in mixed case and pass.
- **D2 NIT (GLM). FIXED in `1aa5d4f`.** The trailing-dot rule had no test (the suite's server is an IPv4 address, which a URL reads the same with a dot); `ownHostReport` is exported and unit-tested, and the old dot-stripping rule fails that test.
- **D3 NIT (GLM). FIXED in `1aa5d4f`.** The reference now says the origin of the answer that carries the header, not "the site's own".
- **D4 NIT (GLM). REFUTED.** That `chain` and `chainUrls` could diverge: both are filled in the same statement under the same condition in `getHome`, the only place they are made.

Test records: `node --test tests/` in `skills/new-website/scripts` on `1aa5d4f`: tests 97, pass 97, fail 0, skipped 0, exit 0; `make check` exit 0. Mutations of the committed checker, each failing the new tests (exit 1): the own-host check removed; startsWith for the path; no page as base; host instead of origin; no port check; no scheme check; the final URL for every hop; the final answer only; the own-host sentence removed or added for every monitor; the dot-stripping rule.

Notes: the rounds stopped after round 3 (no BUG in it), then one Codex wording pass on the closing edits; its one RISK is R2 again and is listed as a follow-up. This also closes the bug-log row "Nothing watches the script monitor" as the owner's choice (decided in chat; no scheduled run).
