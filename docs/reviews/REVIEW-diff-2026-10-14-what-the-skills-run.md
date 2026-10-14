# DIFF review — docs/WHAT-THE-SKILLS-RUN.md, a checked account of what the skills run; a pointer in SECURITY.md; one BUGLOG row

Base `e038603` · depth: Normal (the page holds commands a person may run, such as the two telemetry off switches, so Light does not apply; not High: a docs page, no code, guard or deploy changes) · verdict: CLEAN — four rounds of the pair and a Codex confirmation; 37 findings before dedup as the table counts them (17 labelled BUG, 8 RISK, 12 NIT; the outside-scope BUG is counted in rounds 2 and 3), each fixed, deferred by the owner or kept with a reason; the confirmation found nothing

Data check: the diff holds no key, token or password. Destinations: Codex and GLM 5.3 on melious, the standing pair for this repo (earlier pull requests #249, #250, #282, #284 used it). Not a fresh yes for this change.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `8be5f15` | full: `e038603...8be5f15`, 2 files, with code excerpts and the author's outside facts as context | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only; melious glm-5.3 (HTTP API, text only) | codex 748 s / 189,831; glm 417 s / 39,365 | codex 9/3/0; glm 0/1/5 |
| 2 | `e0647bd` | delta `8be5f15..e0647bd`, the whole page as context, the author's record of round 1 | same | codex 558 s / 113,519; glm 357 s / 33,164 | codex 4/2/0 (+1 BUG outside scope); glm 0/0/3 (+2 NIT outside scope) |
| 3 | `548b451` | delta `e0647bd..548b451`, record of round 2 | same | codex 345 s / 69,918; glm 218 s / 24,140 | codex 0/2/0 (+1 BUG outside scope, the same as round 2's); glm 1/0/1 |
| 4 | `df21e83` | delta `548b451..df21e83` (page and the BUGLOG row), record of round 3 | same | codex 210 s / 67,885; glm 157 s / 21,023 | codex 1/0/0; glm 0/0/1 |
| Confirmation (not a round) | `f139108` | delta `df21e83..f139108`, two hunks, record of round 4 | codex (medium), alone | 83 s / 46,643 | 0/0/0 |

What the rounds changed, in short:

- Round 1 (Codex C1 to C13, GLM G1 to G6): the telemetry search was widened to the skill texts and found the one opt-in read of croftweaver.com (`new-website`'s footer credit step); `fetch.prune` in `~/.gitconfig` and the scorecard's temp folder joined the writes list; 26 skills, not 25; install hosts, image services and documentation sites joined the network table; the installer's CRC check, `make smoke`, hook wiring, analytics and the read-only scope were stated exactly; `.dev.vars` as a token store marked unchecked. Codex's call for a live test of Claude Code's permission rules: not done, out of scope for a docs page; every such sentence is marked "read, not tried in a live session" and cites https://code.claude.com/docs/en/permissions, which the author read on 2026-10-14.
- Round 2: the marker file under `.git/worktrees/` for a worktree; deletion-only pushes of tags too; `git clone` as a read from GitHub; the badge cannot be fetched from croftweaver.com by a browser that applies the starter's `img-src 'self' data:`; the request shows in croftweaver.com's server logs.
- Round 3: `website-permissions` moved to "Skills that run scripts" (it ships the sync hook); the permissions section says once that it describes Claude Code's documentation, not a live test; `data:` named.
- Round 4: the BUGLOG row's claim that nothing else states the count (the new page does); one hedge reworded.

Deferred by the owner: `skills/new-website/SKILL.md:349` says "twenty-five" skills while its copy command names 26 (Codex, rounds 2 and 3). The owner said in chat on 2026-10-14: "log the twenty-five fix in BUGLOG". Row added in `df21e83`.

Kept with a reason: the page's header names `e038603` as the commit checked (GLM, round 2); every later commit of this change touches only `docs/`, as `git diff --stat 8be5f15 f139108` shows. The dated line that `stable` does not exist yet (GLM, round 2) stays: it is dated.

Facts gathered outside the repository on 2026-10-14, as the page states them: `gh release view v0.31` (two assets, one digest, not immutable), `git cat-file -t` on the tags, `gh api …/branches/stable` (404), `npm view create-croftweaver` (no attestations), skills.sh pages for both repository names and each skill's audit page, Astro's and Wrangler's telemetry pages, and Claude Code's permission documentation.

Check records: `make check` on `8be5f15`: exit 0, "all checks passed", one step skipped as on `main` (the minimum-Perl check needs `Perl::MinimumVersion`; CI runs it). `bash scripts/check_clean.sh` on `f139108`: exit 0, "OK — no private names in … no contact info or credentials in …". Every commit after `8be5f15` changes only `docs/WHAT-THE-SKILLS-RUN.md` and `docs/BUGLOG.md`.
