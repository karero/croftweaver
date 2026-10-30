# DIFF review: warn before a Cloudflare Training setting shuts out Google and Bing

Plan: `docs/reviews/SKILL-PLAN-cloudflare-training-warning.md` (PLAN gate clean, 9 rounds).
Gate: independent-review DIFF, depth High (the setup script configures the owner's zone: the
review skill's "deploy or infra" row). Seats: Codex + GLM 5.3 on melious; fresh-eyes on the
host's model in rounds 1–3.

Evidence each round: the third trial's captures (fixtures T3-001 to T3-013 and
`T3-006-c5b-robots.txt`, from the maintainer's dashboard on a spare zone, 2026-10-30), the
dashboard labels the maintainer reported (C1), and Cloudflare's blog of 15 September 2026.

| Round | Findings | Disposition |
|---|---|---|
| 1 (Codex at High; melious out of balance, no rerun owed; fresh-eyes on the host's model) | Codex: 2 BUG (S5a's "nothing was written" is false after the yes, when other changes were written; the checklist's "the setup script says all this" claims notes it does not print), 2 RISK (enforcement and search claims not attributed to Cloudflare; NOARCHIVE stated as fact). Fresh-eyes: 6 NIT (the same "says all this"; a robots.txt claim with no committed capture; a missing Sync value worded unlike S10; "run this with --skip ai" to an owner already doing so; S2, S6 and S7-unread tests check text only; the older switch's raw value) | fixed: "this run did not change it" in both unread notes, with a test of the run after the yes; the checklist names what the script prints; the enforcement and NOARCHIVE lines say "Cloudflare says" in the checklist and `ai-seo`; the README row says the Sync-off reads are not committed; missing Sync worded as S10; "keep running this with --skip ai" when skipped; S2 and S6 compare codes, exits and the PUT, S7 unread and missing Sync tested. Not taken: the older switch's value stays raw, since the dashboard no longer shows that setting and has no word for it |
| 2 (Codex at High, verifying round 1; melious out of balance; fresh-eyes on the host's model) | Codex: 2 RISK (the same two as round 1: Cloudflare's enforcement and Bing's NOARCHIVE cannot be measured from here), 1 NIT (S2 and S6 compare exit statuses, not question codes, and one PUT field). Fresh-eyes: 2 NIT (the checklist's sentence names Block only; S5a does not show another write happened) | RISKs answered, not fixed: every such line now says Cloudflare says it, and nothing claims more; a crawler's real treatment cannot be measured without sending Google's or Bing's crawler, which no test can. NITs fixed: S2 and S6 compare question codes on one site and the whole PUT; S5a asserts the yes wrote something else; the checklist names both Block choices and the Sync note |

Checks before round 1: `make check` exit 0 ("all checks passed"; it runs `check_clean.sh`, not
the Cloudflare suites); `node --test tests/cloudflare-check.test.mjs` 101 of 101;
`node --test tests/cloudflare-setup.test.mjs` 109 of 109, none skipped.
