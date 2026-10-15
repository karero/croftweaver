# Review trail: Cloudflare setup script, the setup stage (karero/croftweaver#328)

Base `8f7c98b` · depth: High (the maintainer chose High for this plan: the script changes a Cloudflare account with a token and can make a site public) · verdict: in progress

The diff is over the gate script's 117 KB limit, so each round goes in two parts: A (the script, Makefile, CI, the check script's line, and the plan's requirements, scenarios and setup stage as an excerpt for the text-only seat) and B (tests, stub, fixture cleaner, fixture index, prose). The 81 fixture files are read in the tree by the seats that can open files. Part A's run starts the gate (`--round 1`); part B's run attaches to it.

Explicit item of this gate (the maintainer's waiver of Z3, with V15 and V16, in `REVIEW-plan-2026-10-14-pr320.md`): the plan's capture-based claims are checked against the committed fixtures: PATCH preservation, deployment classification by stages, the Bot Management fields, the ruleset calls.

## Rounds

| Round | Head | Scope | Seats | Time, tokens | Findings (BUG / RISK / NIT) |
|---|---|---|---|---|---|

## Findings

| Id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
