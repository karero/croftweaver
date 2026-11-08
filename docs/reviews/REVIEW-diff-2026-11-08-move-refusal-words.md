# DIFF review: branch `fix/move-refusal-words-035`, the move script's refusal words and stage 1 gaps

Plan: `workers-for-new-sites/PLAN-move-script-0.35-rows.md` in the maintainer's planning hub (PLAN
gate clean at round 3, no BUG open; the owner's go to build, 2026-11-08). Base `e7c68dbe` · depth:
Normal (a tooling script's logic is never Light) · no red team (no box, user data, login, money,
deletion or schema; the owner's choice, 2026-11-08). Seats: Codex and GLM 5.3 on melious in one
command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet in round 1. The artifact
leaves out `docs/reviews/`. The runs, the evidence and the mutation record sit in the session's
scratchpad; the figures below are copied from them.

**Verdict: CLEAN at round 5** (no BUG or RISK; of its two NITs one fixed in `0e506e01`, with test S1g and
mutation M15, not externally re-verified, and one accepted as designed). Gate `20261108T201342Z-15892`: 5 rounds, 31 findings,
440,358 tokens logged over 11 seat runs (fresh-eyes included).

## Mutation check

Each mutation ran in a throwaway copy of `skills/new-website/scripts`, with the template's
`src/config.ts` beside it and the plan's S tests picked by name; the harness refuses a run where
one of them did not run. The last run is on `0e506e01` (14 S tests).

| Id | Mutation | Killed by |
|---|---|---|
| M0 | none | — (all pass) |
| M1 | `siteAddress` returns nothing | S1, S1b, S1d, S2, S3, S4, S4b, S7 |
| M2 | no permissions line | S3, S7 |
| M3 | no gaps after a refused token | S4 |
| M4 | only the first gap is listed | S5 |
| M5 | the address can refuse a token that reaches one zone | S6 |
| M6 | the first block pattern (`^\};`) | S1, S1b, S1d, S2, S3, S4, S4b, S7 |
| M7 | no pages.dev words | S2 |
| M8 | the site's zone is looked for among the reaching zones only | S1b |
| M9 | no CRLF strip (at `8943610b`) | survived, so the strip was dropped |
| M10 | the placeholder counts as an address | S1c |
| M11 | the token catch in every command | S4b |
| M12 | gaps listed during an open move | survived, expected (finding A6) |
| M13 | no flat-form guard (a block with braces or a backtick is read) | S1e, S1f, S1g |
| M14 | no url on the brace line | S1d |
| M15 | the guard lets a template string through | S1g |

Before the fix, on base `e7c68dbe`: S1 to S5 and S7 fail, S6 passes (S1b to S1g were written
later).

## Rounds

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `3ad7fd4` | whole change; evidence (32,521 bytes) | Codex; melious glm-5.3; fresh-eyes Sonnet | Codex 155 s, 64,587 · melious 182 s, 40,975 · fresh-eyes 75 s, 110,415 | 2 / 6 / 6 (Codex 2/2/0, melious 0/1/4, fresh-eyes 0/4/3; two shared) |
| 2 | `4d016e36` | round 1's fixes | Codex; melious glm-5.3 | Codex 139 s, 49,343 · melious 197 s, 26,953 | 0 / 2 / 3 (one RISK outside scope) |
| 3 | `c786899d` | round 2's fixes | Codex; melious glm-5.3 | Codex 100 s, 32,440 · melious 139 s, 17,885 | 2 / 1 / 4 (one NIT outside scope) |
| 4 | `07cb8a8d` | round 3's fixes; earned by `site-address-read`, with a cut | Codex; melious glm-5.3 | Codex 105 s, 29,383 · melious 171 s, 20,036 | 2 / 0 / 1 (Codex 2/0/0, melious 1/0/1; one shared) |
| 5 | `1c3d3678` | round 4's fixes; earned by `site-address-read`, with a second cut | Codex; melious glm-5.3 | Codex 116 s, 30,884 · melious 152 s, 17,457 | 0 / 0 / 2 (melious) |

Rounds 4 and 5 were earned by BUGs of one kind, `site-address-read`: `siteAddress` taking another
object's url for the site's. Round 4's cut dropped round 2's wider read of `SITE`. The kind came
back, so round 5's cut replaced the read by a strict rule: a block holding any other brace (or,
after round 5, a backtick) gives today's words. Round 5 found no BUG or RISK, so the rounds end.

## Round 1 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| A1 | BUG | Codex | Guide: the four gaps are said to come together and to be lifted during an open move, but the Worker-domain check comes first and every run reads the Workers config | Fixed: the guide names the Worker-domain check first |
| A2 | BUG | Codex | Guide: a pages.dev address is said to mean the site has no domain yet; it may be a stale `SITE.url` | Fixed: the guide gives the script's conditional words |
| A3 | RISK | Codex, fresh-eyes | `siteAddress` depends on exact formatting (no newline after `SITE = {`; CRLF) | Fixed: the url may sit on the brace line; test S1d. A CRLF strip was added, then dropped (M9) |
| A4 | RISK | Codex | Cloudflare's listed permissions are taken as real DNS authority | Refuted: the accept rule is not in this diff; the guide says edit ability was not tested |
| A5 | RISK | melious | Row 239's closing note is broader than the code | Fixed: the note says the new words need an address in `src/config.ts` |
| A6 | RISK | fresh-eyes | An open move whose commit has a bad Workers config would list the lifted gaps | Fixed: with a move open, the config's own Stop is thrown unchanged. No test (M12 survives): `record` reads the config at that commit, so ordinary use does not produce it |
| A7 | RISK | fresh-eyes | The pages.dev words print the raw `SITE.url` | Fixed: only the parsed host is printed |
| A8 | RISK | fresh-eyes | No test shows the catch is in `check` only; the placeholder fallback is untested | Fixed: S4b and S1c (M11, M10) |
| A9 | NIT | melious, fresh-eyes | `gapsStop` with no gaps prints a bare header | Fixed: an empty list rethrows the first Stop |
| A10 | NIT | melious | A garbled guide sentence; long lines | Fixed |
| A11 | NIT | fresh-eyes | The placeholder with a slash or a trailing dot | Fixed: the host is compared, a trailing dot dropped |
| A12 | NIT | melious | Address read at HEAD, gaps at the tip | Refuted: the guide says to run on a clean checkout of the live branch |
| A13 | NIT | melious | The describe number "1:" repeated | Refuted: the numbers are the plan's test groups |
| A14 | NIT | fresh-eyes | A token refused for another reason also waits on `ls-remote` in `check` | Accepted as is: the read started beside the token check and is capped at 15 s |

## Round 2 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| B1 | RISK | Codex | `SITE` on one line, or the url after another key, is not read | Fixed in round 2 by a wider read; that read caused round 3's BUGs and was dropped. Re-sorted: rare, with a BUGLOG row (a missed address gives today's words, never wrong ones) |
| B2 | NIT | melious | "Every run reads the Workers config" is wider than true | Fixed: "Every run that gets that far" |
| B3 | NIT | melious | S1d's rewrite could do nothing without a word | Fixed: S1d asserts the rewrite landed |
| B4 | NIT | melious | A bare host in one sentence, `https://host` in the other | Refuted: the plan's wording, on purpose |
| B5 | RISK (outside scope) | Codex | Listed permissions taken as DNS authority | Refuted as A4 |

## Round 3 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| C1 | BUG | Codex | A nested `url:` inside `SITE` was read as the site's | Fixed in round 3 by an indent rule; D2 showed indentation does not prove depth, and round 5's cut replaced it. Test S1e |
| C2 | BUG | Codex | Reading to the next export takes a url from a later declaration | Fixed by the same cut (M6) |
| C3 | RISK | melious | The same over-read as C2 | Fixed with C2 |
| C4 | NIT | melious | `[{,]` before `url:` can match inside a quoted value | Gone: `url:` is matched only at a line start |
| C5 | NIT | melious | The brace-line `{ url:` form has no direct test | Fixed: S1d writes it, with CRLF ends (M14) |
| C6 | NIT | melious | The comment "to the next export" is incomplete | Gone with the cut |
| C7 | NIT (outside scope) | melious | A typed `SITE: Site =` is not read | Re-sorted: rare, in the same BUGLOG row as B1 |

## Round 4 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| D1 | BUG | Codex, melious | A `SITE` on one line has no closing line of its own, so the block runs on to a later object's, and that object's `url:` is read (C2 again) | Fixed by the cut: a block holding another brace gives the old words. Test S1f (M13) |
| D2 | BUG | Codex | Indentation does not prove depth: a `support:` at one space with its `url:` at two is read (C1 again) | Fixed by the same cut; the indent rule is gone. S1e uses this case (M13) |
| D3 | NIT | melious | The comment "a top-level key, not a nested one" overclaims | Gone with the cut |

## Round 5 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| E1 | NIT | melious | A brace inside a string value of a flat `SITE` trips the guard, so the refusal loses the address | Accepted as designed: it falls back to today's words, and the BUGLOG row says so |
| E2 | NIT | melious | A multi-line template string in a flat `SITE` with a line starting `url:` is read ahead of the real key | Fixed in `0e506e01`: a backtick in the block gives the old words. Test S1g (M15) |

## Checks

The move suite (which `make check` does not run) and `make check` ran after the last edit:
CHECKS_LINE. `make check` skips one check here, the Perl minimum version (Perl::MinimumVersion is
not installed on this machine; CI runs it); the diff touches no Perl.
