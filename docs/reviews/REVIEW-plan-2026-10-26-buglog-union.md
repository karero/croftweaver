# Review trail: plan for union merges of docs/BUGLOG.md and the row guard (PLAN gate, Normal)

Artifact: `docs/reviews/PLAN-buglog-union-merge.md`. Depth Normal: Codex (gpt-6.1-sol) + GLM 5.3.
No red team: the change touches no box, user data, login, money, deletion or schema.

## Round 1 (plan at 7f78be3e, 2026-10-26)

reviewers: codex OK, melious FAILED ("HTTP 200: Insufficient balance for request. Required: 97,
Available: 0"), ollama-cloud OK (glm-5.3:cloud stood in for melious).
timings: codex 448s (79,314 tokens), ollama-cloud 364s (tokens not reported).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | codex | RISK | Both scripts in `make check` but not in `package.sh`: the zip's `make check` calls absent files; case 1 needs the BUGLOG the zip leaves out. | Fixed: Wiring adds both to the zip's inputs and `REQUIRED`; case 1 skips in the zip. |
| F2 | codex | BUG | "Make their Where cells differ" cannot clear a match on What's opening. | Fixed: the message says to give them different Where cells and a different start to What. |
| F3 | codex | RISK | An edit of only the Found date passes both rules; the stated blind spot understates it. | Fixed: rule (b) now ignores the date (no false alarm in any version since 2026-09-20, checked); Not in scope states the remaining miss set exactly. |
| F4 | codex | RISK | `-c user.name … core.attributesFile` leaves the runner's other git config live. | Fixed: hermetic pattern of `test_whats_new_removed_skill.sh` (GIT_CONFIG_GLOBAL/SYSTEM=/dev/null, gpgsign off, hooksPath). |
| F5 | codex | BUG | The phone-image What cells share 63 words, not 76. | Fixed: 76 counted from the row's start; re-counted in What with awk's split on blanks: 63. Word rule stated. |
| F6 | glm | RISK | Miss set wider than stated (date-only edit; Where and What opening both changed). | Same as F3; fixed there. |
| F7 | glm | RISK | "Guard starts green" unsupported: the `SCAN_BASE` pair may still match. | Refuted with evidence, now in the plan: on 428b7ba1 the second row's Where reads `SCAN_PRESENT`; only the phone-image pair matches either rule (Codex found the same). |
| F8 | glm | RISK | If GitHub's merge does honour union, the PR merge itself can keep a row twice, unchecked. | Fixed: `clean.yml` runs `make check` on every push to main; the plan names that after-the-fact detection. |
| F9 | glm | NIT | "Where alone a few more" inverted against the counts. | Fixed: the bullet now says what each rule alone misses. |
| F10 | glm | NIT | No `user.email` pinned. | Fixed with F4. |
| F11 | codex | UNVERIFIABLE | Rebase and cherry-pick claims untested; "resolved by hand" not shown; 14 of 15 list not given. | Narrowed: only local `git merge`/`git pull` is claimed (case 9 runs it); "differs from both parents: a hand resolution or an edit during the merge"; the 14/15 is credited to the session that ran it, two of the 15 re-run here. |

## Round 2 (plan at d50eacca, 2026-10-26)

reviewers: codex OK, melious FAILED ("Insufficient balance … Required: 123, Available: 0"),
ollama-cloud OK (glm-5.3:cloud stood in again).
timings: codex 1089s (72,933 tokens), ollama-cloud 460s (tokens not reported).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F12 | codex | BUG | "Neither shape was seen" is false: 7ab51d43 and 63b16c41 changed Where and What's opening together. | Fixed: Not in scope names both. A word-overlap third rule was measured and dropped (versions share as little as 32%, different rows up to 62%). |
| F13 | codex | BUG | `git pull` may rebase; calling it a merge is wrong. | Fixed: "a `git pull` that merges (not one set to rebase)". |
| F14 | codex | RISK | `GIT_CONFIG_COUNT` and friends survive the hermetic settings and can inject attributes. | Fixed: those variables are unset; `core.attributesFile=/dev/null`, `init.templateDir=` (checked: `git init` makes no hooks folder) and `GIT_ATTR_NOSYSTEM=1`. |
| F15 | glm | RISK | The zip skip rests on the zip holding no `.git`, not shown. | Fixed: the plan says `package.sh` zips named paths only, none `.git`; `.git` as file or folder counts. |
| F16 | glm | RISK | The user's own attributes file is read whatever the config files are. | Fixed with F14. |
| F17 | glm | NIT | `--cc` also lists clean merges, so 57 overstates the conflicts. | Fixed by measuring: all 57 replayed; 12 merge cleanly, 45 conflict. All 45 replayed with union: 33 same rows, 2 differ only by a merge-time rewording, 10 keep stale versions, every one flagged by the two rules. Why rewritten with these numbers; the earlier 14-of-15 claim is replaced. |
| F18 | glm | NIT | The `SCAN_PRESENT` evidence the trail cites was not in the plan. | Fixed: the plan quotes the Where cell. |
| F19 | glm | RISK (outside scope) | The merge grep misses `git -C`, the Makefile and other folders. | Fixed: re-run over `Makefile`, `scripts/`, `.github/` and all `.sh`/`.mjs`/`.py`; same result. |
| F20 | glm | NIT (outside scope) | Case 7 did not say the What openings differ. | Fixed. |
| F21 | glm | NIT (outside scope) | A ` \| ` inside a cell shifts later cells. | Fixed: the plan states the column mapping and why a shift still matches two versions alike. |

## Round 3 (plan at 80906db2, 2026-10-26)

reviewers: codex OK, melious FAILED (out of credit), ollama-cloud OK (glm-5.3:cloud stood in).
timings: codex 786s (74,693 tokens), ollama-cloud 413s (tokens not reported).
GLM: every earlier fix landed; no BUG or RISK.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F22 | codex | BUG | A ` \| ` added to one version's Where shifts its cells, and both rules miss the pair; "shift alike" is false. | Fixed: a row that does not split into 7 parts is a FAIL naming the line (every row since 2026-09-20 splits into 7, checked); case 8 covers it. |
| F23 | codex | BUG | "The rest need the stale rows deleted" includes the 2 merge-time rewordings, which deletion cannot fix. | Fixed with F25: three buckets. |
| F24 | codex | BUG | The wider grep also finds `git -C "$C" pull -q --ff-only` in the site template's `tests/check_ship_push.sh:976`, not listed. | Fixed: listed; the claim narrowed to merges of this repo's BUGLOG. |
| F25 | glm | NIT | 1641021d sits among the 33 "same rows" yet needs a deletion. | Fixed: 32 need nothing, 11 need a guard-named deletion, 2 a person's rewording (1641021d's replay checked: conflicts, union gives its rows). |
| F26 | glm | NIT | "`.git` beside it" reads as inside `docs/`. | Fixed: "at the repo root". |
| F27 | glm | NIT | No case has two pairs, so "every pair is listed" cannot fail. | Fixed: case 2 holds two pairs and checks four line numbers. |
| F28 | glm | NIT | Rule (b)'s 20-word window is not pinned from both sides. | Fixed: case 5 agrees exactly 20 words (fails) and 19 (passes); case 6 agrees 8. |
| F29 | glm | NIT (outside scope) | The Review section says melious; GLM ran on ollama. | Fixed: the section names the stand-in. |

## Round 4 (plan at 30f33fb2, 2026-10-26; earned by cell-parse, replay-buckets, merge-grep)

reviewers: codex OK (no findings), melious FAILED (out of credit), ollama-cloud OK (glm-5.3:cloud).
timings: codex 475s (60,754 tokens), ollama-cloud 627s (tokens not reported).
GLM: all of F22–F29 landed. No BUG. Each fix below narrows a claim and changes nothing that runs,
so none earns a round 5.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F30 | glm | RISK | A separator moved between cells keeps 7 parts; "keeps a shifted cell from hiding a pair" overclaims. | Fixed: narrowed to added or removed separators; a moved one is named as inside the miss set. |
| F31 | glm | NIT | The grep claim covers only the searched files and same-line matches. | Fixed: narrowed, and says the guard still reports what a missed merge leaves. |
| F32 | glm | NIT | Under union nothing prompts the 2 merge-time rewordings; "as today" is wrong. | Fixed: named as an accepted cost. |
| F33 | glm | RISK (outside scope) | A same-row edit on both sides also keeps both versions; "needs an append" understates the miss. | Fixed: "the other branch changes the same row or a row next to it". |
| F34 | glm | NIT (outside scope) | The replay's argument order was written as (base, first, second). | Fixed: the exact command is shown; the replay ran `git merge-file -p <first> <base> <second>` (this session's script). |
| F35 | glm | NIT (outside scope) | A row with a mistyped date is never read. | Fixed: named in Not in scope. |

## Final full read (plan at 53bf5bd7, 2026-10-26)

Kimi K3 on ollama could not run: ollama's session limit was reached (HTTP 429), and melious had
no credit. The skill's other option ran instead: a fresh Claude (Opus) reviewer that had not seen
the plan, with repo access, read-only. 434s, 157,846 tokens. It reproduced the replay (57, 12,
45, 33, 12), the 7-cell split over 301 versions, the current-file match, and case 10's merge.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F36 | fresh-eyes | RISK | "Keep the newer version": union keeps the two versions in either order and the message shows the same first 100 characters, so the person may delete the edited one. | Fixed: the message says to delete the merge base's version and gives the command that shows it. |
| F37 | fresh-eyes | RISK | Wiring misses the house convention: its own `clean.yml` job and required check, and `check_cdpath_safe.sh`'s lists (else `make check` fails). | Fixed: Wiring names the `buglog-rows` job, the CDPATH lists, and the owner's ruleset step (a status row). |
| F38 | fresh-eyes | NIT | 4 merges lose a merge-time rewording, not 2 (d0e3b21e and 11b00231 too). | Fixed (both checked in this session's replay: a hand-only row in neither parent). |
| F39 | fresh-eyes | NIT | A What with fewer than 20 words is unspecified. | Fixed: all its words; a case added. |
| F40 | fresh-eyes | NIT | A deleted row coming back, and a twice-edited intro, are unnamed. | Fixed: named in Not in scope. |
| F41 | fresh-eyes | NIT | The `directory` branch keeps `.gitattributes`; `plugin.test.mjs` refuses "filter" in it. | Fixed: both stated. |

## Round 5 (plan at 44488375, 2026-10-26; earned by stale-pick, ci-wiring)

reviewers: codex OK, melious FAILED (out of credit), ollama-cloud FAILED (session limit, HTTP 429).
Only Codex counted: the second seat is owed. timings: codex 442s (64,553 tokens).
Codex: F36–F41 landed except as below.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F42 | codex | BUG | "Delete the one the merge base holds" is wrong when both branches edited the row: union keeps both edits and neither base row (reproduced). | Fixed by a cut: the message no longer names a version to delete; it says to make one row of what each side changed, and shows the original. Case 11 replays a both-sides edit. |

## Round 6 (plan at 82616b20, 2026-10-26; earned by stale-pick, cut: message names no version)

reviewers: codex OK, melious FAILED (out of credit), ollama-cloud FAILED (session limit).
Only Codex counted. timings: codex 539s (62,598 tokens). Codex: F42 landed except as below.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F43 | codex | BUG | The message's `grep -F '<start of Where>'` finds nothing when both branches renamed Where (reproduced, git 2.33.0). | Fixed by a cut: the grep is dropped; the message shows the merge base's whole file. |

## Round 7 (plan at 51878955, 2026-10-26; earned by stale-pick, cut: no search in the message)

reviewers: codex OK, melious FAILED (out of credit), ollama-cloud FAILED (session limit).
timings: codex 416s (73,032 tokens). Codex: No BUG/RISK/NIT findings.

## Gate state

No BUG open. Codex clean at round 7. GLM 5.3 (on ollama, standing in for melious) reviewed rounds
1–4 and found no BUG in round 4; the second seat is owed for rounds 5–7, whose changes were the
guard's message, test cases 2, 5 and 11, and the CI wiring. Cost: 7 rounds and a final full read,
43 findings (F1–F43); Codex 487,877 tokens over 4,195 s; GLM 1,864 s (tokens not reported);
fresh-eyes 157,846 tokens over 434 s.
