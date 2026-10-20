# Review trail: Plausible server mode (`feat/plausible-server-side`, karero/croftweaver#339)

Base `688164f`, after the merge of origin/main `16b4a4f` · depth: High (privacy and legal text in two languages, data a live site sends about its visitors, runtime code in the starter's Function, a CI step) · verdict: **CLEAN** (2026-10-16), with F6 waived by the owner and F11 open until the live test after merge. Five rounds, a final full read and a merge-link round. Produced by Claude Code session "silly-spence-43e9b4" (worktree `website-builder-plausible-server`).

## Rounds

| Round | Head | Scope | Seats | Time, tokens | Findings (BUG / RISK / NIT) |
|---|---|---|---|---|---|
| 1 | `b154b2f` | full (`688164f...b154b2f`, docs/reviews/ and the BUGLOG row left out) | Codex (gpt-6.1-sol, config effort, read-only); Melious (glm-5.3, text only); fresh-eyes (Claude Opus, read-only) | Codex 348 s, 124,756 · Melious 305 s, 52,321 · fresh-eyes 311 s, 181,034 | 7 / 4 / 2 (after dedup: F1 to F12) |
| 2 | `8dfb481` | fixes since `b154b2f` | same | Codex 311 s, 113,655 · Melious 193 s, 25,534 · fresh-eyes 221 s, 129,883 | 2 / 3 / 3 (G1 to G8), 3 refuted |
| 3 | `08da868` | fixes since `8dfb481` | same | Codex 290 s, 119,337 · Melious 180 s, 23,996 · fresh-eyes 206 s, 114,176 | 1 / 1 / 2 (H1 to H4) |
| 4 (earned by `stub-detection`; cut) | `e6b1c01` | the cut since `08da868` | Codex, Melious | Codex 196 s, 84,827 · Melious 63 s, 7,869 | 0 / 1 (F6 again) / 1 refuted |
| final full read (not a round) | `e6b1c01` | full (`origin/main...e6b1c01`) | Claude Opus, a new reader; Kimi on ollama FAILED (quota) | 516 s, 202,530 | 0 / 2 / 6 (FR1 to FR7) |
| merge link (not a round) | `7c75855` | `merge_link.sh 688164f e6b1c01 16b4a4f`: the change's files after merging #336 and #338 | Codex, Melious | Codex 424 s, 145,019 · Melious 736 s, 46,132 | 2 / 2 (outside scope) / 3 (L1, L2) |
| 5 (earned by `checklist-contradiction`) | `67b6800` | `7c75855..67b6800`: final-read and merge-link fixes, the BUGLOG row included | Codex, Melious | Codex 261 s, 98,826 · Melious 248 s, 19,628 | Codex: none · Melious 0 / 1 / 3 (R5-1 to R5-4) |
| wording pass (not a round) | `1ecd109` | `67b6800..1ecd109`, prose only (round 5's fixes) | Codex (config effort) | 190 s, 57,642 | 0 / 0 / 0 |

## Findings

| Id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Melious, Codex, fresh-eyes (RISK each) | 1 | `/go/email` required `Sec-Fetch-User`, which Safari never sends: every Safari visitor got the hint page | fixed, externally_reverified (2) | MDN browser-compat-data `Sec-Fetch-User.json`: safari false; Site/Mode/Dest 16.4. Test "a click in Safari … and one in Chrome"; re-adding the header fails 7 tests |
| F2 | BUG | Codex; fresh-eyes (NIT) | 1 | a subject over 200 characters built, then answered 400 on the live site | fixed (G4 widened it), locally_verified | a 201-character subject fails a server-mode build with a clear error, builds in script mode; no automated test (H4) |
| F3 | BUG | Codex; fresh-eyes (NIT) | 1 | a 304 counted before the HTML check (an image or `build.txt` reload) | fixed, externally_reverified (2) | a 304 counts only for a path with no extension or `.html`; removing the rule fails 2 tests |
| F4 | BUG | Codex; Melious, fresh-eyes (NIT) | 1 | gate compared two counts per page; `data-href` read as `href` | fixed, externally_reverified (2); see G2 | per-anchor check; fixtures apart, datahref, dataclass |
| F5 | BUG | Codex | 1 | "answered before the event is sent" untrue | fixed, externally_reverified (2) | "the page does not wait for Plausible"; the test reads the whole body before Plausible replies |
| F6 | RISK | Melious; Codex, Melious again in 4 | 1 | `ANALYTICS.mode` and the two variables can disagree (double count) | **waived by the owner 2026-10-16** ("Waive, docs carry it") | a guard was added in 1, cut in 3 (H1); README, config.ts and the launch checklist say to set the variables only with analytics on and in server mode |
| F7 | BUG | fresh-eyes | 1 | WHAT-THE-SKILLS-RUN said a tap sends only name and page | fixed, externally_reverified (2, 3) | user agent and IP added, "read from the code" |
| F8 | RISK | fresh-eyes | 1 | "numbers run higher" unsupported; prefetched pages never counted | fixed, externally_reverified (2) | both differences named in SKILL.md and README |
| F9 | RISK | Codex | 1 | quota text unconditional | fixed (G5 corrected it) | names "Fail open", what the deploy guide sets |
| F10 | NIT | Melious | 1 | browsers without Fetch Metadata headers not named as lost | fixed | SKILL.md, README |
| F11 | RISK | Codex, fresh-eyes | 1 | Plausible Cloud and a real mail program opening not observed | **half closed 2026-10-20**: the mail-program half is closed by plan row 6 (server mode on the throwaway site `e2e.webcroft.dev`: `302` to `mailto:`, Apple Mail opened a draft, `Email Tap` counted; owner's screenshots). The Plausible Cloud half stays **open** (plan row 11); it is not waived | IP precedence and bot drops rest on Plausible CE v3.2.1 source and the 2026-10-15 trial (plan "Facts") |
| F12 | NIT | fresh-eyes | 1 | website-qa spec list | fixed | entry added; G8 reworded |
| G1 | BUG | Codex; Melious (NIT), fresh-eyes (RISK) | 2 | the stub check matched `plausible.init(` in any text | fixed in 2, then cut (H1) | — |
| G2 | BUG | Codex | 2 | gate reader fooled by `href=` inside another quoted value | fixed, externally_reverified (3) | attributes read one at a time; fixtures inquote, unquoted |
| G3 | RISK | Codex, fresh-eyes | 2 | reloads still double-counted in the mismatch | superseded by the cut (H1); part of F6 | — |
| G4 | RISK | fresh-eyes | 2 | subject check only on the live build | fixed, externally_reverified (3) | every server-mode build (now `USE_ANALYTICS && mode === 'server'`) |
| G5 | RISK | fresh-eyes | 2 | "Cloudflare's default" contradicted the deploy guide | fixed, externally_reverified (3) | "what the deploy guide sets; Cloudflare names no default, so check it" |
| G6 | NIT | Melious | 2 | share MAX_SUBJECT via `obfuscate.ts` | refuted | `obfuscate.ts` is site-owned (`check_template_coverage.sh` SITE_SOURCE), the Function template-tracked (`whats-new.sh` TEMPLATE_TRACKED); a new import breaks existing sites |
| G7 | NIT | Melious | 2 | gate "all" should reject hand-made `/go/email` links | refuted | such a link works on the live server build |
| G8 | NIT | fresh-eyes | 2 | three wording items | fixed | — |
| — | NIT | fresh-eyes | 2 | "the gate is not run in CI" | refuted | `.github/workflows/template-tests.yml` runs it, now in three states |
| H1 | BUG | Codex | 3 | the stub check still matched the stub's text in a comment, attribute or JSON-LD | **cut**: the guard removed (round 4 `--cut`) | a text scan cannot tell a script element from its text; F6 reopened and waived |
| H2 | RISK | Melious | 3 | stub regex rests on Astro writing it verbatim | moot (cut) | had been checked on a real live build |
| H3 | NIT | Melious | 3 | subject check fires before analytics is on | kept on purpose; comment names it | — |
| H4 | NIT | fresh-eyes | 3 | build-time subject check untested | follow-up | needs a server-mode build; said in the PR |
| FR1 | RISK | final full read | full | an existing site switching gets no word that site-owned files must be taken too | fixed | README step 4 and Q5 name the files and the gate |
| FR2 | NIT | final full read | full | German slot left "Seitenaufrufsowie" when its marker is removed | fixed | ": , dazu Scrolltiefe …" |
| FR3–FR7 | NIT | final full read | full | PLAUSIBLE_HOST wording, `plausible_ignore` loss, middleware header, config comments, Cloudflare named in the email slots | fixed | — |
| L1 | BUG | Codex | merge link | launch checklist asked for the host in `_headers` in every Plausible setup, server mode excludes it | fixed | script mode only |
| L2 | BUG | Codex | merge link | config.ts "count a tap only when Plausible is on the page" wrong in server mode | fixed | says how each mode counts |
| L3–L5 | NIT | Melious | merge link | BUGLOG order, a misplaced note, a line break | fixed | — |
| — | RISK ×2 | Melious | merge link | `main`'s launch-stage runbook claims (#334); `main`'s live email-link CI step (#338) | follow-up, outside this change | — |
| R5-1 | RISK | Melious | 5 | FR1 landed in README step 4 but not in Q5 | fixed, locally_verified; read by the wording pass | Q5: "an existing site also takes the site-owned files that step names … or it keeps counting with the script too" |
| R5-2–R5-4 | NIT | Melious | 5 | Q5 loss list's grammar; mail-form.js counts in script mode only; README overbroad on which missing file double-counts | fixed; read by the wording pass | — |

## Checks run by the author

- Starter (`skills/new-website/templates/astro`), after the merge: `npm run check` clean; Playwright 91 passed, 1 skipped (positioning, by design); `tests/check_analytics_gate.sh` green off (as shipped), on in script mode (host added to `_headers` as CI does) and on in server mode.
- Every new rule broken on purpose once and caught by a test (Sec-Fetch-Dest, prefetch, `/go/`, HTML type, previews, https host, `waitUntil`, the redirect, same-origin, address check, `%` escape, 304 rule, Safari rule); the gate caught an email link that ignores server mode and one that uses `/go/email` in script mode.
- `make check` (with `node_modules` moved aside): green except `scripts/test_mktemp_guard.sh`'s self-test, which fails the same way on a clean `origin/main` on this Mac.
- Deployed once to a throwaway Pages project (`cw-plausible-e2e`): the Functions bundle compiled with `go/email.ts`'s imports; the route answered crawlers with the hint, a broken link with 400.

## Notes

- Data check: no keys or customer data in the diff. Consent this session, verbatim: "Codex + melious (Recommended)".
- Final full read: Kimi on ollama was out of quota; nothing else was sent to melious in its place. A new Claude Opus reader ran instead (a host-family pass). A first attempt died on a network error and was rerun.
- The fresh-eyes chain ends at round 3, by design at High depth. Codex holds an unbroken chain from round 1 through the merge link, round 5 and the wording pass at `1ecd109`; the stamp rests on it. Melious's chain ends at round 5 (`67b6800`). The commit after `1ecd109` adds only this trail (`docs/reviews/`, outside the reviewed scope).
- Owner decisions: F6 waived; F11's mail-program half closed 2026-10-20 (plan row 6), Cloud half open (plan row 11); the merge came before the test ("Integrate, review, merge").
