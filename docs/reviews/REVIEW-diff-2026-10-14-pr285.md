# DIFF review — PR #285 — Cloudflare checklist: three more AI switches set to off
Base `e038603` · depth: Normal (the checklist is a document a person follows, so not Light; it guards no user data, sign-in or deploy, so not High) · verdict: CLEAN — two rounds and a re-gate of the closing edits; 13 distinct findings (1 BUG, 4 RISK, 8 NIT), each fixed or refuted; the re-gate by Codex found nothing · authority used: POST AUTHORITY — atom A (this session opened #285); WORKTREE-WRITE — atom A (this session created the worktree `website-builder-checklist-ai`); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — atom A (Codex's chain below, unbroken from round 1 to `66ba944`)

Depth, as told to the owner before round 1: Normal, the owner's own words in the task ("this is not a Light review").

Data check: the diff holds no key, token or password; it is public documentation and one string in a script. Destinations: Codex and GLM 5.3 on melious, named by the owner in this session's task: "Run the `independent-review` skill at Normal depth (Codex plus GLM 5.3 on melious ...)".

| Round | Head | Artifact | Reviewer: CLI version, model, effort, sandbox | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `8c22484` | full: `e038603...8c22484` without `docs/reviews/`, 2 files | codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only; melious glm-5.3 (HTTP API, text only); fresh-eyes: a sub-agent of the host's model family, one size down (sonnet), read-only, with web access | codex 251 s / 63,375; glm 133 s / 7,208; fresh-eyes 134 s / 104,610 | codex 1/2/0; glm 1/0/3; fresh-eyes 0/2/3 · 11 distinct |
| 2 | `5f577ba` | delta `8c22484..5f577ba`, with the author's record of round 1 | codex (medium); melious glm-5.3 | codex 176 s / 49,036; glm 100 s / 8,297 | codex 0/2/0 (F10, F11 re-raised, no new evidence); glm 0/0/2 · F1 to F9 confirmed by both |
| Re-gate of the closing edits (not a round) | `66ba944` | delta `5f577ba..66ba944`, one prose line and one string literal, with the author's record of round 2 | codex (medium), alone | 62 s / 43,618 | 0/0/0 · F12, F13 confirmed |

Questions the seats listed as unverifiable, asked / confirmed as a finding: round 1, 9 / 0; round 2, 9 / 0; re-gate, 1 / 0. Nearly all asked for Cloudflare's pages, which the external seats could not open (no network) and the author read on 2026-10-14 (quotes in the PR description); the rest asked for a live dashboard, which no one checked (the checklist's header says so).

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex, glm | 1 | the script's AI hint and `lookFor` said all three switches Off, while the checklist keeps Bot Preference Sync on for a Training opt-out | fixed `5f577ba` — locally_verified, externally_reverified (round 2, both) | both strings now say "Off unless you block Training". No test: hint wording only, which no test pins |
| F2 | RISK | fresh-eyes | 1 | "leave it on" only for a Training Disallow; Cloudflare's page has Sync write lines for any Block, Block on pages with ads, or Training Disallow | fixed `5f577ba` — locally_verified, externally_reverified (round 2) | managed-robots-txt page: "when at least one policy is set to Block, Block on pages with ads, or, for Training, Disallow" |
| F3 | RISK | fresh-eyes | 1 | the alias "Instruct AI bot traffic with robots.txt" was stated as the same switch, without support | fixed `5f577ba` — locally_verified, externally_reverified (round 2) | now states only what the Security settings page shows: that row links to the managed-robots-txt page |
| F4 | NIT | fresh-eyes | 1 | Sync's `Content-signal` line not mentioned | fixed `5f577ba` — externally_reverified (round 2) | "Cloudflare includes the Content Signals Policy whenever Bot Preference Sync adds managed directives" |
| F5 | NIT | fresh-eyes | 1 | script strings implied the content-bot switch is in the dashboard | fixed `5f577ba` — externally_reverified (round 2) | `lookFor`: "which may show only through the API" |
| F6 | NIT | fresh-eyes | 1 | the Labyrinth's why was stated as fact | fixed `5f577ba` — externally_reverified (round 2) | Cloudflare's claims attributed (bots only, no SEO effect); "Off is the kit's choice" |
| F7 | NIT | glm | 1 | "Set each to off" contradicted the Sync exception | fixed `5f577ba` — externally_reverified (round 2) | "with the one exception under Bot Preference Sync" |
| F8 | NIT | glm | 1 | "Your site gives every crawler permission" too universal | fixed `5f577ba` — externally_reverified (round 2) | "the file the kit made lets every crawler in"; `skills/new-website/templates/astro/public/robots.txt`: `User-agent: *` / `Allow: /` |
| F9 | NIT | glm | 1 | "None can be read from outside" overbroad: Sync's effect shows in robots.txt | fixed `5f577ba` — externally_reverified (round 2) | hint now says "what it adds shows in robots.txt" |
| F10 | RISK | codex | 1, re-raised 2 | Sync = managed robots.txt, prepend and create, unverifiable | refuted | managed-robots-txt page (updated 2026-10-08, read 2026-10-14): "Bot Preference Sync generates managed robots.txt directives from your Search, Agent, and Training policies"; "Cloudflare will prepend our managed robots.txt before your existing robots.txt"; with none, Cloudflare creates one. API `is_robots_txt_managed`: "Enable cloudflare managed robots.txt", prepended to an existing file. Re-raise in round 2 brought no new evidence |
| F11 | RISK | codex | 1, re-raised 2 | the three field-to-switch mappings unverifiable | refuted | Bot Management update reference: `crawler_protection` "punish AI Scrapers and Crawlers via a link maze"; `content_bots_protection` "block content bots ... low bot scores, excluding safe verified bot categories"; all three in all four body variants. Re-raise brought no new evidence |
| F12 | NIT | glm | 2 | "the same page of its documentation" had no antecedent | fixed `66ba944` — externally_reverified (re-gate, codex) | "the documentation page for this switch" |
| F13 | NIT | glm | 2 | "names after them" misparses | fixed `66ba944` — externally_reverified (re-gate, codex) | "lists after the policies" |

Waivers and deferrals: none.

Follow-ups: none from the seats. The content-bot switch's dashboard place stays unknown until someone opens a live zone's Bot traffic list.

Notes: round 2 was owed by F1 (a fix to what the script prints). The re-gate covers a JS string literal, so it ran at full scope, not prose-only. melious's chain ends at `5f577ba`; the stamp relies on Codex's chain. Fresh-eyes ran in round 1 only, as Normal depth has it. No dashboard was opened by anyone.
