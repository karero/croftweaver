# DIFF review — bug sweep 6 of 2026-11-23 (four BUGLOG rows)

Base `501b26e6` (origin/main) · depth: Normal (shipped scripts, so not Light) · seat: Codex alone (REVIEW-RULES; no
High-row topic) · fresh-eyes: a read-only Sonnet subagent at round 1 (this session's own, logged). Artifact: the whole
diff against the base (round 1) and the delta since the reviewed head (round 2, `--verify`), with a brief as evidence.

Rows fixed (all four checked on `main` before the fix): `check_page_text.py` `VOID` and `INLINE` (2026-11-20),
`whats-new.sh` no-`SUITE-VERSION` branch (2026-11-20), `cloudflare-check.mjs --preview` with a config not named
`wrangler.json(c)` (2026-11-16), and where the token lives reads two ways (2026-11-13).
Rows looked at and left: a list in the PR description.

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex (base `501b26e6`, head `db9b0b67`) | 0 / 1 / 0 | the "Wrangler does not read `.dev.vars`" sentence was backed only for 4.151.0 |
| 1 | fresh-eyes (Sonnet subagent) | 0 / 0 / 3 | wording ("Only the script"), a long line, a redundant hint when `--config` was given |
| 2 | Codex (`--verify`, base `db9b0b67`, head `daf70296`) | 1 / 1 / 0 | my record said a test was missing that exists; the Wrangler claim is still not probed on the pinned 4.164.0 |

Tokens and time: round 1 Codex 90,535 (299 s); fresh-eyes 114,914 (97 s); round 2 Codex 54,179 (134 s). Codex alone
(REVIEW-RULES); the script's warning that the standard pair was not met applies.

## Findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | RISK | Codex | the two token docs said Wrangler does not read `.dev.vars`; Wrangler does load it as Worker bindings, and the probe was 4.151.0 | fixed: both now say Wrangler does not take its login token from the file; probed on three versions (below) |
| F-01 | NIT | fresh-eyes | `CLOUDFLARE_MOVE.md` said "Only the script reads that file", which can rule out the setup script | fixed: the sentence is about Wrangler's login token |
| F-02 | NIT | fresh-eyes | that paragraph's line ran about 137 characters | fixed: wrapped |
| F-03 | NIT | fresh-eyes | `--preview` refusal still says "give it with --config" when `--config` was given and names a non-Workers file | left: still true advice (the refusal exits 2 either way), no wrong result |
| F-04 | NIT | fresh-eyes | `_SchemaText` shares `INLINE`, so an `<img>` in a FAQ answer now leaves no gap, and no test covers it | left: the intended effect the row names; the FAQ reader's gap handling is the same as for any inline tag |
| F-05 | NIT | fresh-eyes | no test for the exit-1 path after the new loop | withdrawn: `test_whats_new.sh` lines 149–152 (an unusable tests baseline with an unstamped skills folder, exit 1) already run it; my round-2 prior-findings text was wrong, Codex's BUG (R2-01) |
| R2-01 | BUG | Codex | the round-2 record said that test was missing | fixed: this table; no code changed |
| R2-02 | RISK | Codex | the Wrangler claim is still not shown on the pinned 4.164.0 | accepted with evidence: three versions agree; 4.164.0 is not installed here (installing it is a download); the claim is about the login token only, and the only harm if it were false is a token the owner placed in that file being used |

## Test evidence

- Row 442: `python3 -m unittest discover -s skills/website-new-page/scripts/tests` 41 tests OK; `img` and `input` taken
  out of `INLINE` by hand, 1 failure. Row 436: `bash scripts/test_whats_new.sh` all passed; the old script restored by hand,
  `FAIL and so is the second`. Row 385: `node --test …/cloudflare-check-workers.test.mjs` pass 32, fail 0; the old
  `cloudflare-check.mjs` restored by hand, pass 31, fail 1.
- `make check`: exit 0 at `db9b0b67` (only SKIP: the Perl minimum-version check, which CI runs). A second run after the
  last edit follows this trail (see the PR).
- Wrangler probe, 2026-11-23: an empty HOME, `CI=true`, a `.dev.vars` holding `CLOUDFLARE_API_TOKEN=<made-up value>` and
  no variable in the environment: `wrangler whoami` printed "You are not authenticated" on 4.90.1, 4.156.0 and 4.162.0; with
  the same value in the environment it tried the API instead (4.162.0). Not probed: 4.164.0 (the starter's pin) and Worker
  bindings (the docs make no claim about them).
