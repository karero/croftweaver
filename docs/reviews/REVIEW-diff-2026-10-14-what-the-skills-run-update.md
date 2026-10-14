# DIFF review — WHAT-THE-SKILLS-RUN.md: the brand kit, the weekly fix proposal, the analytics folder

Base `edf97ba` (origin/main) · depth: Normal (the page holds commands a person may run, so Light does not apply; not High: docs only) · verdict: open

Owner's decision (2026-10-14, in chat): "Yes to: one small pull request, done the same way as before (read the scripts, review at Normal depth), before the 'safe to install' section goes live and ideally before 0.32."

Data check: the diff holds no key, token or password. Destinations: Codex and GLM 5.3 on melious, the standing pair for this repo.

## Evidence records

- A read-only sub-agent read `skills/website-brand-kit/` (SKILL.md, scripts, render.mjs), `fix_proposal.py`, `search_report.py`'s fix-proposal part, `_analytics.py`, `analytics_snapshot.py`, `ai_reports.py` and the starter `.gitignore`, with file:line for each claim. The author re-read the load-bearing ones: `grep -nE 'urllib|requests|https?://|fetch\(|socket'` over the brand kit's scripts and render.mjs (tests excluded) finds no network call; `_install.py:40` `DEFAULT_TEST_COMMAND = "npm run build && npm test"`, run with `shell=True` at :282; `fix_proposal.py:412` runs `gh pr view … --json state,mergedAt,closedAt`; `search_report.py:299` `read_live_page`, User-Agent `search-console-insights fix check` at :320; `analytics_snapshot.py:18` "reads only ~/.config/gsc-insights and fetches nothing"; `_analytics.py:58-86` refuses a tracked path unless `--commit-ok`; the starter `.gitignore` has `/analytics/`; `.agents/plugins/marketplace.json` installs from `https://github.com/karero/croftweaver.git` at `stable`.
- Telemetry, re-run on `edf97ba`: the analytics and tracking terms over every script, template and installer (tests and the Cloudflare checker's beacon detection left out) find only test cases in `skills/independent-review/scripts/test_failed_tier_report.sh`; `croftweaver.com` or the repository's GitHub address in executable code only in `packages/create-croftweaver/index.mjs:22` (the zip download) and `scripts/plugin.test.mjs:42` (a test); in Markdown and plugin files only the known links, the footer-credit step and the two plugin manifests.
- Release immutability: `gh api repos/karero/croftweaver/immutable-releases` read `{"enabled":true,"enforced_by_owner":false}` after `gh api -X PUT` on 2026-10-14. GitHub's documentation (Immutable releases; Preventing changes to your releases), read 2026-10-14: assets and tag locked after publication, title and notes still editable, a release attestation created, "immutability will only apply to future releases".
- `scripts/check_clean.sh` on `b242e8c`: OK.

| Round | Head | Artifact | Reviewers | BUG/RISK/NIT |
|---|---|---|---|---|
