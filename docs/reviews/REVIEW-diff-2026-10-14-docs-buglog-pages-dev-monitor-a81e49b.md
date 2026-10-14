# DIFF review — docs/buglog-pages-dev-monitor — one BUGLOG row for the pages.dev address and Cloudflare's script monitor
Base `afece4b` · depth: Light (one BUGLOG row: prose no agent loads and no person runs; no code and no user data; one cross-model seat, Codex at medium effort, one round, by the standing rule for prose nobody runs and by the owner's chat message "Do docs-only PR with a Light review.") · verdict: CLEAN after 2 RISK fixed · authority used: POST AUTHORITY — atom A (the owner asked in chat for the row and a docs-only PR); WORKTREE-WRITE and BRANCH-COMMIT — atom A (a worktree and a branch this session created)

Data consent: Codex has been cleared for this repo's content throughout this session (the review of #299, #310 and #313 used it). This diff is one docs row, and a grep for keys and tokens over the review artifact found nothing.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `0d1351c` | `afece4b...0d1351c`, 1 added line, with six records copied in: the capture's command and tally, two checklist passages, Cloudflare's sentence, the older row and the trail lines that raised the question | codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only, `--seat codex` | codex 81 s / 37,588 | 0/2/0 |

Findings:
- **F1, RISK (Codex). FIXED in `a81e49b`.** The row's fix said to "read the group name of each `report-to` line". An answer that carries only the CSP header, or only `reporting-endpoints`, has no group name, and a group name does not carry the address that identifies the monitor. The fix now reads all three headers for a group name and for an address on `csp-reporting.cloudflare.com`, which is what the checker's `cloudflareMonitor` does.
- **F2, RISK (Codex). FIXED in `a81e49b`.** The 100-on, 100-off capture had no positive control and no rule for an empty result: none in both phases could be read as "the switch does not reach the alias". The fix adds the project's own domain as the control in both phases, and says the captures speak about the zone switch only if the control showed the monitor.

No waivers, deferrals or follow-ups.
UNVERIFIABLE entries: 1 grouped entry asked, 0 confirmed. It asks for provider evidence for Cloudflare's sampling statement and for raw captures of the 18:45Z run. The sentence the row paraphrases was re-read from the live page the same day (`developers.cloudflare.com/client-side-security/how-it-works/`: "adds a content-security-policy-report-only HTTP header to a sample of HTML responses"). The capture's command and its tally are in the review artifact. Raw header dumps were not kept, and the row reports counts only.
Notes:
- Before the round the author checked every sentence of the row against the live checklist, the capture's script and the page. That caught three errors in the first draft, fixed before the round: the split between NEL's line and the monitor's is in step 3 and not step 5; the checklist says "we have found no way to remove them", not "cannot"; and "none carried one of the monitor's three headers" was false, since all 120 carried NEL's `report-to` line. The count was of header lines naming an address on `csp-reporting.cloudflare.com`.
- No second round. A Light gate runs one more only after a BUG, and round 1 found none. The sentences the fix commit changed were checked by the author (the claims sweep and `make check`, exit 0), not by a second model.
- One seat only, by the Light choice, so the script's "fewer than 2 reviewers" warning is expected.
- The capture also answers the first half of the row of 2026-10-12 (its 301 answer carries `nel` and `report-to`). That row is unchanged.
