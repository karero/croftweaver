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

Checks before round 1: `make check` exit 0 ("all checks passed"; it runs `check_clean.sh`, not
the Cloudflare suites); `node --test tests/cloudflare-check.test.mjs` 101 of 101;
`node --test tests/cloudflare-setup.test.mjs` 109 of 109, none skipped.
