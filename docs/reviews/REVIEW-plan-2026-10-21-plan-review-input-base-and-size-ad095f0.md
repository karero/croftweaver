# PLAN review — plan/review-input-base-and-size — check a review diff's base, and lift the 117 KB limit

Base `6681e7be` · depth: Normal (a plan for a guard script's logic; the owner's rule keeps tooling plans at Normal; no red team: it touches no box, user data, login, money, deletion or schema) · verdict: CLEAN (2026-10-21) — no BUG open; the one open RISK, R4-02, waived by the owner. Five rounds (round 4 earned by R3-01 and R3-02, round 5 by R4-01 and R4-03, with a cut), a final full read, a wording pass and one confirmation · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY and GATED-THIS-DIFF do not apply to a PLAN gate

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `ad095f01` | full plan | codex-cli 0.163.0, gpt-6.1-sol, effort high (config), read-only · Melious glm-5.3, HTTP API, text only · fresh-eyes: Claude Code sub-agent, Sonnet, read-only by instruction | codex 379 s, 102,724 · melious 238 s, 29,217 · fresh-eyes 650 s, 244,798 | 8/17/11 raw (codex 6/5/0, melious 1/4/4, fresh-eyes 1/8/7); 28 after dedup: 7/12/9 |
| 2 | `9a0f5cd3` | full plan, `--verify` with round 1's rows; changed sections named | codex-cli 0.163.0, gpt-6.1-sol, effort medium (the `--verify` default), read-only · Melious glm-5.3, HTTP API, text only | codex 370 s, 86,895 · melious 340 s, 34,257 | 4/3/1 (codex 3/2/0, melious 1/1/1); every round-1 fix confirmed landed, R1-12's refutation confirmed by both |
| 3 | `fa726dd5` | full plan, `--verify` with round 2's rows and R1-12; changed sections named | codex-cli 0.163.0, gpt-6.1-sol, effort medium, read-only · Melious glm-5.3, HTTP API, text only | codex 169 s, 71,055 · melious 232 s, 31,472 | 2/4/3 raw (codex 2/2/0, melious 0/2/3); 7 after dedup: 2/3/2; every round-2 fix confirmed landed |
| 4 | `ea30cd24` | full plan, `--verify` with round 3's rows and R1-12; changed sections named; `--earned-by probe-verdict,merge-base-head` | codex-cli 0.163.0, gpt-6.1-sol, effort medium, read-only · Melious glm-5.3, HTTP API, text only | codex 155 s, 64,429 · melious 249 s, 32,490 | in scope 2/1/0 (codex 1/1/0, melious 1/0/0); outside scope 0/1/2 (melious); every round-3 fix confirmed landed |
| 5 | `caaf7b68` | full plan, `--verify` with round 4's rows and R1-12; changed sections named; `--earned-by header-names,test-spec --cut "mnemonic prefixes no longer accepted: only a/ and b/, stripped only on diff --git, --- and +++ lines"` | codex-cli 0.163.0, gpt-6.1-sol, effort medium, read-only · Melious glm-5.3, HTTP API, text only | codex 112 s, 65,264 · melious 340 s, 39,691 | in scope 0/3/3 (codex 0/1/0, melious 0/2/3); outside scope 1/0/2 (melious); every round-4 fix confirmed landed; no substantive BUG |
| final full read | `c2ff4cc9` | full plan, no `--round` | ollama 0.40.7 CLI, kimi-k3:cloud, text only (a model that had not reviewed this plan) | ollama-cloud 459 s, tokens not reported by the CLI | 0/2/4; no BUG, so no further round |
| wording pass (not a round) | `7582ff37` | delta since `caaf7b68` (round 5's local fixes and the final read's), with a prose-only scope | codex-cli 0.163.0, gpt-6.1-sol, effort medium, read-only | codex 181 s, 54,825 | 3 contradictions and 1 RISK, all fixed |
| confirmation (not a round) | `fbed4442` | that fix's delta | codex, effort medium | codex 78 s, 43,462 | No BUG/RISK/NIT findings |

UNVERIFIABLE entries, round 1: 17 asked (codex 3, melious 6, fresh-eyes 8); 3 confirmed and made findings (the fetch refspec, ollama's missing `num_ctx`, `hash-object --path`); the rest are the plan's own "not checked" list or probes P1 and P2.
UNVERIFIABLE entries, round 2: 10 asked (codex 5, melious 5); 0 new confirmed: they restate the plan's "not checked" list, P1, P2 and the T5 hang test.
UNVERIFIABLE entries, round 3: 9 asked (codex 4, melious 5); 0 new confirmed.
UNVERIFIABLE entries, round 4: 9 asked (codex 3, melious 6); 0 new confirmed.
UNVERIFIABLE entries, round 5: 7 asked (codex 1, melious 6); 0 new confirmed.
UNVERIFIABLE entries, final full read: 6 asked; 0 new confirmed (the script and git claims it could not read are checked in this trail).

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-01 | BUG | codex | 1 | Rule 4 compared ids only: a stale mode change (both trees already at the new mode) passed | fixed, locally_verified | rule 4 now compares modes; T5 "a stale mode change" |
| R1-02 | BUG | codex, fresh-eyes | 1 | `git hash-object --path=<p>` with no file hashes nothing | fixed, locally_verified | git now makes its own patch (rule 2) and hashes the working tree; "Checked" names `git hash-object -- <path>` |
| R1-03 | BUG | codex, fresh-eyes, melious | 1 | From a subdirectory, path lookups and the printed `git diff … -- .` remedy are cwd-relative | fixed, locally_verified | rule 1: every git command runs from the top level; remedy is `git -C <top> diff …`; T4 subdirectory case |
| R1-04 | RISK | codex | 1 | One `ls-tree` with every path on argv hits E2BIG on a large diff | fixed, locally_verified | rule 2: no path on argv |
| R1-05 | RISK | codex, fresh-eyes | 1 | T1's topology need not move the merge base; no "origin moved, branch did not take it" case | fixed, locally_verified | T1 names the update-branch topology; T2 is the moved-not-merged case and must run |
| R1-06 | BUG | codex, fresh-eyes | 1 | The `CONTEXT_RE` label could be tripped by an echoed artifact line; its remedy text clashed with SKILL.md's degraded-round rule; no priority over `QUOTA_RE` | fixed (cut), locally_verified | the label is dropped: with measured caps a length refusal means the provider changed its limit, and the FAILED section quotes it |
| R1-07 | BUG | codex | 1 | "Every seat takes [200 KB] whole" contradicted agy's and the argv CLI's cap | fixed, locally_verified | recommendation now names both default seats at a measured cap |
| R1-08 | BUG | codex | 1 | The existing tests do not run "outside a repo": the runner inherits cwd | fixed, locally_verified | Tests: "from whatever directory the suite runs in (the repo root under `make`)" |
| R1-09 | BUG | melious | 1 | Rule 1 refused outside a repo even with `--base none`, so the existing suite would fail | fixed, locally_verified | `--base none` skips rules 1 to 5 and runs outside a repo; T5 |
| R1-10 | RISK | codex ×3, melious, fresh-eyes | 1 | "A seat never reviews part of the artifact" rested on unchecked windows and an optional P2; a silent cut would count as a review | fixed, locally_verified | change 2 redesigned: one cap per seat, the size it was measured to take whole; unmeasured seats keep 120,000; P2 is a 400 KB probe with three nonces and a token count |
| R1-11 | RISK | melious | 1 | Plain `git diff` and `--cached` take a side from the index; the plan did not say | fixed, locally_verified | table: refused, the old side is the index |
| R1-12 | RISK | melious | 1 | A `diff --git` line inside hunk content becomes a phantom record | refuted | every hunk body line starts with ` `, `+`, `-` or `\`, so a column-0 `diff --git` cannot sit inside a hunk; the real neighbour (a removed `-- x` shown as `--- x`) is R1-16 |
| R1-13 | RISK | fresh-eyes, melious | 1 | Fetching by name may not move `origin/<default>`, so the base stays stale while saying "fetched" | fixed, locally_verified | `git fetch origin HEAD` and `FETCH_HEAD`; checked on git 2.33 in a scratch clone: `FETCH_HEAD` = remote tip, `origin/trunk` unmoved, `FETCH_HEAD` per worktree |
| R1-14 | NIT | melious | 1 | Raising the argv cap to 128,000 cut the margin under 131,072 without a measurement | fixed, locally_verified | 120,000 kept |
| R1-15 | NIT | melious, fresh-eyes | 1 | Header parsing: names only from header lines, prefix stripping, a spaced name on a mode-only record | fixed, locally_verified | rule 3 |
| R1-16 | NIT | fresh-eyes | 1 | A removed line `-- x` reads as a `--- x` header | fixed, locally_verified | rule 3 skips hunks by their line counts; T4 |
| R1-17 | NIT | melious | 1 | "Before anything leaves the machine" while the default path fetches | fixed, locally_verified | "before … any of the artifact leaving the machine (the fetch above goes first)" |
| R1-18 | RISK | fresh-eyes | 1 | The fetch had no bound: a credential prompt or stalled link hangs the round | fixed, locally_verified | bounds from `git-stand.mjs` (read: lines 124-137), a 30 s Perl alarm, `GIT_TERMINAL_PROMPT=0`; T5 hang case |
| R1-19 | RISK | fresh-eyes | 1 | Other callers (`website-review`, `seo-reposition`, vendored site repos) would start being refused, undocumented | fixed, locally_verified | Docs touched lists them and the README |
| R1-20 | RISK | fresh-eyes | 1 | Delta runs without `--verify` (wording pass, confirmation, merge link, re-gates) fall to the merge-base default | fixed, locally_verified | `--base <rev>` covers every diff that is not the whole change; refusal adds the "--base <that head>" line; T3 |
| R1-21 | RISK | fresh-eyes | 1 | The check proves sides, not coverage, while the `base:` line implied a whole diff | fixed, locally_verified | rule 5 names left-out files on the `base:` line; T7 |
| R1-22 | RISK | fresh-eyes | 1 | No refusal when there is no merge base (shallow clone, unrelated histories) | fixed, locally_verified | table row and T5 |
| R1-23 | RISK | fresh-eyes | 1 | Untested stated behaviour: `--local-only` never fetches; prefixes | fixed, locally_verified | T6; T4 and T5 |
| R1-24 | NIT | fresh-eyes | 1 | `--` before paths; validate a `--base` starting with `-` | fixed, locally_verified | no path on argv; `--base` validated as `--cut` is, resolved as `merge_link.sh` does |
| R1-25 | NIT | fresh-eyes | 1 | The new Perl reader must be placed in `check_perl_minimum.sh`; missing perl or git must refuse | fixed, locally_verified | rule 3 (ungated, 5.8); `check_perl_minimum.sh:31-33` read |
| R1-26 | NIT | fresh-eyes | 1 | T3 "base before size" has nothing to order against after change 2 | fixed, locally_verified | T8 orders the base check against the caps |
| R1-27 | NIT | fresh-eyes | 1 | `closeout.md` does not copy closing lines; its template has a `Base` field and Artifact column | fixed, locally_verified | "What the trail records" |
| R1-28 | NIT | fresh-eyes | 1 | The dropped range mode had no size comparison | fixed, locally_verified | "Considered and dropped" gives the estimate and why files stay |
| R2-01 | RISK | codex | 2 | R1-10 partly fixed: a cap measured at 400 KB held only for text as dense as the probe's, for the probed model, and for the artifact rather than the whole prompt | fixed (cut), locally_verified | measured caps dropped; P2 now records per seat and model whether the model refuses or cuts past its window (`seat_limits.txt`); a cutting seat gets a cap of N bytes on the whole prompt (a token is never shorter than a byte); an unlisted model keeps 120,000 |
| R2-02 | RISK | codex | 2 | Rule 4 compared ids for records with no `index` line, but git's own patch has no ids for a mode-only change either | fixed, locally_verified | rule 4 matches such records against git's own records; checked on git 2.33: no `index` line for a mode-only change even with `--full-index`, a rename shown as a deletion and an addition with the same id under `--no-renames` |
| R2-03 | BUG | codex | 2 | "Plain `git diff` or `--cached` refused": headers cannot tell the command; `git diff --cached HEAD^` equals `git diff HEAD^ HEAD` when the index is at HEAD | fixed, locally_verified | table row judges sides, not the command; T4 runs `--cached <base>` with the index at HEAD; T5 refuses plain `git diff` with the index ahead of the base |
| R2-04 | BUG | codex | 2 | The merge-base default cannot refuse every delta without `--base`: a delta over files unchanged since the merge base has the same headers | fixed, locally_verified | "Which base": outside `--verify`, `--base` for deltas is the caller's duty in SKILL.md; rule 5's note names the files a delta leaves out; T3 covers both cases |
| R2-05 | BUG | codex | 2 | P2's total (about 350,000) did not cover the fourth probe if P1 passes | fixed, locally_verified | P2 redesigned (R2-01); its cost is given per seat and per window, nothing totalled |
| R2-06 | BUG | melious | 2 | Rule 3 lost `rename from`/`rename to` as name sources, so a 100% rename had no names | fixed, locally_verified | rule 3 names them, and `copy from`/`copy to` to refuse copies; T4 has a rename at 100% and one below |
| R2-07 | RISK | melious | 2 | The cap sized the artifact, P2 measured the whole prompt: at the boundary the prompt is over | fixed, locally_verified | with R2-01's cut, every cap is on the whole prompt; argv seats keep today's check unchanged |
| R2-08 | NIT | melious | 2 | On the default branch itself the merge base is HEAD and the printed remedy is an empty diff | fixed, locally_verified | "Which base": refused, naming `--base`; T5 |
| R3-01 | BUG | codex | 3 | P2 counted any error as "refuses", so a quota, sign-in, network or request-size error would lift a seat's cap | fixed, locally_verified | "Refuses" now needs an error that names a context or token limit, recorded with its text and date; anything else leaves the seat at 120,000 |
| R3-02 | BUG | codex, melious | 3 | The "merge base is HEAD" refusal also refused uncommitted work on the default branch itself | fixed, locally_verified | that case now compares with the working tree and is refused only when it holds no change; T4 runs uncommitted work on the default branch, T5 refuses it with a clean tree |
| R3-03 | RISK | codex | 3 | "The reported prompt count is the cut point" rested on no traced provider accounting | fixed (cut), locally_verified | the cuts-at-N cap is gone: a reply to P2 is recorded for information, never as a limit |
| R3-04 | RISK | codex, melious | 3 | The cap assumed every seat's tokenizer is byte-level and a 1,000-token template budget | fixed (cut), locally_verified | the same cut: a seat that replies to P2 stays at 120,000 |
| R3-05 | RISK | melious | 3 | Stripping "git's prefixes" could strip twice in a repo with a top-level `c/`, `i/`, `o/` or `w/` | fixed, locally_verified | rule 3: exactly one prefix per name, the pair read from the record's own `diff --git` line; T4 has a top-level folder named `w` |
| R3-06 | NIT | melious | 3 | The 120,000 check was described as the diff alone in one place and artifact plus prior in another | fixed, locally_verified | "What and why" 2: `CONTENT_BYTES` is the artifact plus prior findings (read at `independent_review.sh:480`) |
| R3-07 | NIT | melious | 3 | The printed remedy remade a working-tree diff against HEAD | fixed, locally_verified | the remedy is printed in the form the artifact used |
| R4-01 | BUG | codex | 4 | Stripping "one prefix from each name" also stripped `rename from`/`to` names, which carry none: with mnemonic prefixes a rename inside a top-level `w/` lost its folder | fixed (cut), locally_verified | rule 3: only `a/` and `b/` are accepted, stripped only on the `diff --git`, `---` and `+++` lines; rename and copy names taken as written; mnemonic and other prefixes refused, the remedy sets `a/` and `b/`; T4 has a 100% rename inside `w/`, T5 refuses mnemonic prefixes. Kind header-names also earned round 3 (R2-06), so the fix is a cut: mnemonic prefixes are no longer accepted |
| R4-02 | RISK | codex, codex (R5-01) | 4 | One context-length refusal at one size does not prove the provider refuses, rather than cuts, at every size past its window | waived by the owner, 2026-10-21 | no finite probe can close it; "What this does not see" now names it. A waiver keeps change 2 as planned; no waiver leaves every seat at 120,000 |
| R4-03 | BUG | melious | 4 | T11's malformed-list case could not pass: a malformed list caps every seat, so "the other seats ran" is impossible | fixed, locally_verified | split out as T13: every seat `FAILED` before sending, no stub ran, exit 4 |
| R5-01 | RISK | codex | 5 | R4-02 is still open and no waiver is recorded | waived with R4-02 (merged into it) | Open 1 now asks for that decision by name |
| R5-02 | RISK | melious | 5 | The status row said round 4 had 6 findings; the record held 3 rows | fixed, locally_verified | round 4 had 3 in scope (rows) and 3 outside scope (Follow-ups); the status row now points to the trail |
| R5-03 | RISK | melious | 5 | Codex's move to stdin rested on a help line; nothing showed a large stdin prompt arrives whole | fixed, locally_verified | P1 now covers Codex (a stub through its own model provider, or a 60,000-token real run with nonces); a CLI seat not shown whole stays at 120,000 |
| R5-04 | NIT | melious | 5 | A `--no-index` diff has `diff --git` records, so it is not refused "naming `--base none`" outright | fixed, locally_verified | its own table row: checked like any diff, refused by rule 4 where its sides do not match |
| R5-05 | NIT | melious | 5 | Rule 3 did not say a C-quoted name is unquoted before its prefix is stripped | fixed, locally_verified | rule 3: unquote first, then strip |
| R5-06 | NIT | melious | 5 | `/dev/null` sides would fail the prefix rule | fixed, locally_verified | rule 3: `/dev/null` means "no file on this side" |
| R5-07 | BUG | melious (outside scope) | 5 | T9 names no `seat_limits.txt` setup, so Codex would be capped at 120,000 and the 400 KB case could not pass | fixed, locally_verified | T9 lists Codex "refuses" in a copy's list, as T10 does. Not substantive: test wording, what T9 checks is unchanged |
| R5-08 | NIT | melious (outside scope) | 5 | The `base:` line said "fetched" under `--local-only` too | fixed, locally_verified | a `--local-only` form of the line |
| R5-09 | NIT | melious (outside scope) | 5 | Status row 1 still said "revised after round 1" | fixed, locally_verified | "revised through round 5" |
| F-01 | RISK | kimi (final full read) | — | For a file edited after the last commit, `git diff` writes `0000000` as the new id, so headers cannot pin working-tree content | refuted | on git 2.33 an unstaged edit's patch carried its real id (`index 422c2b7..af19230`, equal to `git hash-object` of the file); all-zero ids appear in `--raw` output, which the plan does not use |
| F-02 | RISK | kimi (final full read) | — | Hunk counts leave out `\ No newline at end of file` lines, so a strict count-based skip goes wrong on any file with no final newline | fixed, locally_verified | rule 3: a line starting with `\` is passed over uncounted; T4 has no-newline cases on each side; checked: `@@ -1,2 +1,2 @@` with two uncounted `\` lines, one inside the hunk |
| F-03 | NIT | kimi (final full read) | — | Open 1 called the probe "free" where P2 says billing of a refusal is not checked | fixed, locally_verified | Open 1 now carries P2's hedge |
| F-04 | NIT | kimi (final full read) | — | "Every changed file present" cannot see untracked files | fixed, locally_verified | the `base:` line says "tracked", and why |
| F-05 | NIT | kimi (final full read) | — | The remedy leaves out rule 2's `--full-index --no-renames` without saying it is deliberate | fixed, locally_verified | the refusal paragraph says why |
| F-06 | NIT | kimi (final full read) | — | T13 sat before T12; "a missing perl or git refuses" read as covering `--base none` too | fixed, locally_verified | tests reordered; rule 3 excepts `--base none` |
| W-01 | RISK | codex (wording pass) | — | P1's paid fallback checked only first- and last-line nonces, which cannot show the middle of the prompt arrived | fixed, externally_reverified (confirmation) | the fallback is removed: P1 is stub-only, the recorded prompt must equal the sent one byte for byte, and a CLI that cannot be pointed at a stub stays at 120,000 |
| W-02 | BUG (contradiction) | codex (wording pass) | — | P1 "free" and "No model runs" beside a fallback costing about 60,000 tokens | fixed, externally_reverified (confirmation) | the same fix |
| W-03 | BUG (contradiction) | codex (wording pass) | — | "Untracked files are in no diff at all" is false for `git diff --no-index` | fixed, externally_reverified (confirmation) | "untracked files appear in neither git's patch nor a diff made with `git diff <base>`" |
| W-04 | BUG (contradiction) | codex (wording pass) | — | Status row 2 said "final full read next" after the read ran | fixed, externally_reverified (confirmation) | status row 2 updated |

Waivers and deferrals: R4-02 (re-raised as R5-01) waived by the owner on 2026-10-21. Asked "Each reviewer gets one test with a prompt bigger than its model can hold. A reviewer that rejects it with a 'too long' error loses the limit. But one test can't prove that reviewer will never silently cut some other long prompt instead. Accept that risk and run the tests?", the owner chose "Yes, accept and test (Recommended)". Also decided then: the split, "Not now (Recommended)". No deferrals.
Cost: about 900,600 tokens logged across 14 seat runs (the Kimi read gave no figure); reviewer time about 3,950 s, about 43 minutes of wall clock with the seats of a round in parallel. Announced before round 1 as about 10-12 minutes and 200-250k tokens over 2-3 rounds: the gate took about 4 times the tokens, mostly round 1's fresh-eyes pass (245k) and two more rounds.
Follow-ups: a BUGLOG row for local ollama cutting a prompt silently under `--local-only` (named in the plan, outside its scope). Round 4, outside scope (melious): measure the Linux per-argument limit on a runner before relying on 120,000 for argv seats (RISK); T7's precondition (NIT, fixed in the plan anyway); git's `1/` and `2/` prefixes (NIT, moot: every prefix but `a/` and `b/` is now refused).
Notes: the fresh-eyes seat wrote and removed one empty scratch file in `/tmp` (its report says so); nothing in the repo changed. R1-13 merges melious's NIT into fresh-eyes's RISK. R2-01 is R1-10's kind (a silent cut counted as a whole review) coming back; its fix is a cut, not a patch: the measured-size caps are gone. R3-03 and R3-04 are the same kind a third time, raised against the cuts-at-N cap that cut left; the fix is a second cut: only a provider that refuses past its window loses the 120,000 check. Round 4 is earned by R3-01 (kind probe-verdict) and R3-02 (kind merge-base-head). Round 5 is earned by R4-01 (kind header-names, which R2-06 earned before: its fix is a cut) and R4-03 (kind test-spec). Round 5 found no substantive BUG (R5-07 is test wording), so the rounds end: round 5's fixes are locally_verified, closing edits not externally re-verified; the final full read (Kimi K3 on ollama) found no BUG; the wording pass found 3 contradictions, fixed and confirmed clean. One reflow of rule 3 after the confirmation changed no words (whitespace-normalized text compared equal). Codex called the wording pass's scope sentence, sent in the prior-findings block, an attempt to restrict its task; it treated it as data. The claims sweep ran before round 1 (`sweep_claims.sh --file`); one claim fixed before the round (`ad095f01`).

<details><summary>Round 1 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, read-only)

`P` = `docs/reviews/SKILL-PLAN-review-input-base-and-size.md`. Ranked findings:

- BUG — P:72 — WRONG: blob equality cannot validate mode changes; a patch claiming `100644→100755` passes rule 4 when both trees already contain the same blob at `100755`. Fix: parse and compare old/new modes alongside IDs; test stale mode changes.
- RISK — P:113 — UNVERIFIABLE, Codex: the 500,000-token/95% window and whole-input overflow behavior lack a captured model record or retention test; omitted input could still produce a counted review. Fix: establish the effective model budget and observe input retention/compaction around its boundary before claiming whole-artifact coverage.
- RISK — P:114 — UNVERIFIABLE, Melious: neither the million-token window nor lossless handling has primary supporting evidence; silent truncation could count an incomplete review. Fix: establish the selected model’s effective limit and trace an oversized request through accepted-input accounting or provider implementation.
- RISK — P:115 — UNVERIFIABLE, ollama: an advertised model window does not establish the serving context or overflow behavior; a truncated request could count as whole. Fix: capture the effective serving configuration and compare known input token counts with evaluated input around its limit; P1 alone checks transport.
- BUG — P:69 — WRONG: `git hash-object --path=<p>` supplies no input file; reproduced exit 0 with empty stdout, whereas adding `-- <p>` produced the blob ID. Fix: supply the file operand and define separate handling for symlinks and gitlinks.
- BUG — P:60 — WRONG: being inside a worktree is insufficient for the proposed path lookup; from `skills/`, the repository-root path returned zero bytes from `ls-tree`, while `--full-tree` returned its entry. Fix: normalize paths and run lookups from the repository root; test invocation from a subdirectory.
- RISK — P:67 — VERIFIED failure mechanism: putting every path into one `ls-tree` argv reintroduces an argument ceiling as diffs grow; a 1,225,023-byte invocation reproduced `E2BIG` here. Fix: batch NUL-delimited paths or stream the trees and select entries in the reader.
- RISK — P:177 — VERIFIED test gap: advancing origin alone need not change the merge base, so T1’s stated topology need not produce a refusal. Existing history reproduced the same merge base before and after a base-side advance. Fix: explicitly merge the advanced base into the feature branch, then construct the stale-base diff.
- BUG — P:125 — WRONG: error-shaped echoed artifact text can trigger the existing classifier; its own comment at `independent_review.sh:1256` acknowledges this, and an unindented `ERROR: maximum context length…` passes its filter. Fix: qualify the guarantee, retain exit/provenance information, and add that counterexample.
- BUG — P:153 — WRONG: “every seat takes [200 KB] whole” contradicts the planned 128,000-byte agy limit and ollama CLI fallback when P1 fails. Fix: qualify the recommendation by transport; use the API when a whole-input second seat is required.
- BUG — P:187 — WRONG: the existing test runner inherits cwd (`test_failed_tier_report.sh:329`); its temporary artifact location does not place execution outside a repository. Fix: correct the description and explicitly select cwd for repository-boundary tests.

Checked claims that were CLEAN:

- VERIFIED — Checkout identity: current branch matches the plan; `origin/main` resolves to `6681e7be…`; only the plan differs from that base.
- VERIFIED — Current input behavior: artifact/stdin loading, extension-based type detection, and the 120,000-byte artifact-plus-prior limit with exit 2 match `independent_review.sh:298`, `:314`, and `:480`.
- VERIFIED — Current call sites pass prompts through argv for Codex, ollama CLI and agy, and through request files for both APIs (`:843`, `:977`, `:912`, `:1044`, `:1137`). Both Perl request builders preserved a 200,000-byte Unicode payload in a reproduced JSON round trip; this establishes serialization, not provider retention.
- VERIFIED — `codex-cli 0.163.0` help contains the quoted stdin contract. Ollama’s displayed stdin examples use `--ask`; ordinary `run` stdin behavior remains unverified.
- VERIFIED — The raw directory receives mode 700 (`independent_review.sh:697`); `merge_link.sh:68` diffs from the reviewed head; SKILL.md step 8 requests timings, and closeout records rounds.
- VERIFIED — Git measurements reproduced binary `index` records, trailing tabs for space-containing header paths, and C-quoted tab-containing paths.

Additional UNVERIFIABLE claims: Linux’s exact per-argument ceiling needs Linux implementation evidence or a boundary measurement; default-fetch ref freshness needs the local-origin integration test; P2’s “refusal costs nothing” needs provider billing evidence. No full suite was run: it creates filesystem fixtures, and the proposed implementation/tests do not yet exist.

Prompt injection: none found.
## Independent review — melious (glm-5.3, HTTP API)


Ranked findings:

- BUG — anchor "How it tells" step 1 vs the "Tests" closing line and T5 — rule 1 ("The current directory must be inside a git work tree, or the run is refused") is stated unconditionally and the plan never says `--base none` exempts it, yet "The existing cases send a hand-made `change.diff` from outside a repo, so they pass `--base none`" and `--base none`'s stated use cases (another project's patch, `--no-index`) can occur outside any repo, so under the natural reading the existing suite the plan must keep green fails at its first `make check`. Fix: state explicitly that `--base none` skips rules 1–4 (and address the "Codex reads the same directory" rationale, which argues the opposite), or move the existing tests' cwd inside a repo.

- RISK — anchor "How it tells" rule 3, "the new id a prefix of `HEAD`'s or of the working tree's (`git hash-object --path=<p>`, for a diff of uncommitted work)" — the lookup covers HEAD and the worktree but never the index, while plain `git diff` (and `--cached`) take one side's ids from the index, so a legitimate uncommitted diff of a file also changed since the merge base is refused as stale and no `--base` rev can name the index. Fix: also accept the index blob (`git ls-files -s -- <p>`) on either side, or enumerate the supported diff forms (`base..HEAD`, `<base>`, `HEAD`) and refuse index-side diffs with a message naming them; T4's "working-tree diff" case must pin the exact command.

- RISK — anchor "How it tells" step 2, "splits the diff into one record per `diff --git` header" — hunk content that adds lines beginning `diff --git ` (docs quoting diffs, this repo's own fixtures) becomes a phantom record whose paths fail rule 3, refusing a correct diff. Fix: accept a split point only when a well-formed `index`/`--- a/`/`+++ b/`/rename block follows it, or validate the whole parse (e.g. against `git apply --numstat` on the artifact) before refusing.

- RISK — anchor Change 2, "A seat never reviews part of the artifact" vs "Without P2 the table's 'not checked' stays, and the risk is named in the script's comments" — for the file-body seats the only detector is the provider's refusal plus CONTEXT_RE, neither of which fires on a silent cut; Melious's limit is a third-party figure and ollama's is a stated window whose per-request enforcement is unknown, and P2 is optional (Open #1), so change 2 can replace a working 120,000-byte guard with documentation. Fix: make the minimal refusal-vs-cut determination of P2 mandatory before removing the script-wide cap, or keep a conservative per-seat byte cap for seats whose window is unverified.

- RISK — anchor Change 1 refusal message, "`git diff <base-id>..HEAD -- . ':(exclude)docs/reviews/'`" — `-- .` is a cwd-relative pathspec, so run from a repo subdirectory (rule 1 permits any point in a work tree) the printed remedy produces a partial diff of that subtree, and the per-path `ls-tree` lookups may be cwd-relative the same way, listing every file. Fix: print the remedy without `-- .` (or anchored at the repo root) and run all lookups with `-C "$(git rev-parse --show-toplevel)"`.

- NIT — anchor "runs `git fetch --quiet origin <default>` … takes `git merge-base origin/<default> HEAD`" — fetch-by-name updates the remote-tracking ref only opportunistically (not at all on older git), so the merge base can still be the stale ref, the very bug this change exists to fix. Fix: fetch with an explicit refspec (`+refs/heads/<default>:refs/remotes/origin/<default>`) or merge-base against FETCH_HEAD.

- NIT — anchor seat table "argv: 128,000 bytes of prompt | the Linux argument limit the script cites today" while "Not checked" admits the limit is "cited by the script today, not re-run" — raising the per-string cap from 120,000 to 128,000 shrinks the margin against the cited 131,072 from ~11 KB to ~3 KB without re-measuring. Fix: re-run the measurement or keep 120,000 until it is.

- NIT — anchor rule 2, "else from the `diff --git` line when both names are equal" — git writes spaced names on the `diff --git` line unquoted and ambiguous, so the one record type that must fall back to it (a mode-only change, which has no `---`/`+++`/`rename` lines) cannot be parsed when the filename contains a space. Fix: mirror `git apply`'s both-sides-equal heuristic, or refuse such records naming the limitation.

- NIT — anchor "before any reviewer starts, and before anything leaves the machine" — the default path itself runs `git fetch` against origin before the check, so network traffic does leave the machine; say "before any prompt content leaves the machine".

What I checked that was CLEAN:

- Arithmetic and cross-references: 120,000-byte cap vs the cited 128 KB (131,072) per-string limit; 200 KB → 50,000–70,000 tokens at 3–4 bytes/token; 95% of 500,000 used consistently.
- Seat table vs test table: T6/T7 assert stdin/file-body seats carry a 200 KB artifact whole; T8's agy refusal matches agy's 128,000-byte argv limit; T9 matches removal of the script-wide check; no test asserts a seat receives input its transport forbids.
- Ordering claims: base check before the size check in both "Order, and how the two checks meet" and T3; change 2 keeps the base check after removal; "`--base none` skips only the base check, never a size limit" is consistent with the per-seat limits remaining.
- Exit codes: every refusal named in the input table and tests is exit 2, uniformly.
- Refusal rationales: the format-patch-series refusal (a later patch's old side is an earlier patch's new side) and the `diff --cc` refusal (no single old side) are sound; the id prefix direction (diff's abbreviated id as a prefix of ls-tree's full id) is stated in the workable direction.
- The split analysis (for/against/recommendation/"strongest case against") is internally coherent and its numbers are self-consistent; the two-PR sequencing, gates, and docs-touched list (SKILL.md steps 2/6, closeout.md) do not contradict each other.
- The stale-ref scenario description (`git pull origin <branch>` fetching that branch alone, so the local default ref lags) is internally consistent with the fetch-first design.
- Prompt injection: none. No text in the plan attempts to alter this review's task, output, or conclusions; the imperative prose in it (commands, remedy text, probe runbooks) is ordinary plan material.

UNVERIFIABLE (load-bearing component claims, grouped; not counted as findings except where a finding above names the breakage):

- git: (a) `git fetch origin <default>` updates `origin/<default>` (backs the NIT); (b) 100%-similarity renames and mode-only changes carry no `index` line, worktree-diff new ids equal `git hash-object --path`, binary files do carry one — claimed checked on git 2.33 by the plan, not checked here (backs rules 3–4); (c) plain `git diff`/`--cached` index lines carry index blobs (backs the index-side RISK); (d) per-path `ls-tree` matching is cwd-relative (backs the subdir RISK's lookup half). Settling observation: run each on a scratch repo from a subdirectory, with spaced, quoted, and subdirectory paths.
- codex CLI 0.163.0: reads instructions from stdin when the prompt argument is `-` (the plan's support is a quoted help string, not a traced behavior), and the model cache says 500,000 tokens / 95% usable. Observation: `codex exec - < prompt` against a stub recording what arrives, and read the cache file.
- ollama 0.40.7 / ollama cloud: `ollama show` reports 1,048,576 tokens and the server honors that per request rather than a smaller default context setting (backs the silent-truncation RISK); the CLI sends piped stdin as the prompt (P1). Observation: the stub-server recording of the request body (P1 as planned) and one oversized request (P2).
- Melious: `/v1/models` carries no context field and the 1,000,000-token figure is third-party (backs the same RISK). Observation: one request past the cited window.
- Linux MAX_ARG_STRLEN ≈ 131,072 per argv string (backs the argv-cap NIT). Observation: exec a single 128,000-byte argument.
- The current repo files the plan quotes — `independent_review.sh` (the 120,000 check, which seats travel by argv vs file body), `merge_link.sh` (diffs from the last reviewed head), SKILL.md step 8 (`timings:` reported each round), and the existing tests — presented by the plan as checked; not checkable here. Observation: read those files against each quoted claim.

---
reviewers: codex OK, melious OK
timings: codex 379s (102724 tokens), melious 238s (29217 tokens)
gate 20261021T172444Z-64903: round 1, 2 reviewer seat runs, 131,941 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 1 raw output — fresh-eyes (sub-agent report, verbatim)</summary>

## Independent review — fresh-eyes (Claude Code sub-agent, Sonnet; read-only by instruction)

Fresh-eyes review of docs/reviews/SKILL-PLAN-review-input-base-and-size.md (identical to the plan in the prompt). Line numbers "plan:NN" are lines of that file. Review only, nothing in the repo changed. Prompt injection: none found in the plan.

### Findings, ranked

- BUG (small, one-line fix) plan:69 and plan:202. The working-tree mechanism is written as `git hash-object --path=<p>`, and the "Checked" list says a working-tree diff's new id equals `git hash-object --path`. As written it hashes nothing. I ran `git hash-object --path=README.md </dev/null` on git 2.33.0: no output, exit 0. `--path` only sets which filters apply and is meant for `--stdin`. Fix: name the real call, `git hash-object -- <p>` or `--path=<p> --stdin < <p>`, and make a missing or empty hash a mismatch, not a pass.

- RISK plan:60-68 (rule 1 and rule 3). Run from a subdirectory of the repo, the lookup finds nothing and reports it as "file absent". Rule 1 only requires "inside a git work tree", and rule 3's `ls-tree` and `hash-object` take paths relative to cwd. I ran the line below from `skills/independent-review/` with the root-relative path. It exited 0 with 0 bytes of output, while the cwd-relative `SKILL.md` and `--full-tree` forms found the blob.
  `git --literal-pathspecs ls-tree -z HEAD -- skills/independent-review/SKILL.md`
  Every modified file would then be refused as "no such file at the base". Every new-file record (all-zero old id, "must be absent") would pass for the wrong reason. Fix: use `ls-tree --full-tree`, or `cd "$(git rev-parse --show-toplevel)"` before the reader and `hash-object`. Add a subdirectory-cwd case to T4 covering a modified file and a new file.

- RISK plan:109, plan:115, plan:133-140 (Change 2: "A seat never reviews part of the artifact"). The plan's own P2 allows that a provider may "cut silently", and without P2 the table stays "not checked". So the headline holds only for providers that refuse. The ollama limit (1,048,576 tokens) comes from `ollama show`, which is model metadata. `perl/ollama_request.pl` sends no `options.num_ctx`, so the window a request is served with is whatever the server defaults to. P2 as written (past each full window, up to 1M tokens per seat) also cannot detect a cut below the nominal window, which is the realistic case. Consequence: a 200-400 KB artifact reviewed from its tail only, with the seat reported "OK". Fix: (a) probe at the sizes this change enables (about 200 KB and 400 KB) with a nonce on the first line, and require the reply to quote it. That costs roughly 60-100k tokens per seat instead of a full window. (b) Ship the same nonce as a runtime truncation check, as `melious_marker` already does for the reply. (c) Reword the headline: "fails loud where the provider refuses; otherwise a nonce check".

- RISK plan:40 (`git fetch --quiet origin <default>`). There is no bound on the fetch. A credential prompt or a stalled connection hangs the whole round, and the plan only handles a fetch that fails. The repo already has the fix: `skills/new-website/templates/claude/hooks/git-stand.mjs:124-137` uses `BatchMode=yes`, `ConnectTimeout`, `http.lowSpeedLimit` and `lowSpeedTime`, a 30 s kill, and only sets `GIT_SSH_COMMAND` when the person has not chosen one. Fix: reuse that pattern (macOS has no `timeout`; use a perl alarm), set `GIT_TERMINAL_PROMPT=0`, and add a hang case to T5.

- RISK plan:187-194 (Docs touched) and plan:41-46 (default base). Other callers are not listed and will start being refused:
  - `skills/website-review/SKILL.md:68` documents `independent_review.sh <file> --plan --first-success   # or --diff`.
  - `skills/seo-reposition/SKILL.md:94` documents `independent_review.sh <diff> --diff --first-success`.
  - This skill is vendored into site repos for site owners (README.md:428-436). Many have no `origin/HEAD`, no remote, or a diff not from `git diff`, so these documented commands exit 2 until `--base` or `--base none` is added.
  - Fix: add both files to "Docs touched", plus a test or a stated decision for a repo with no `origin`.

- RISK SKILL.md:293-303 (wording pass and its confirmation), SKILL.md:213-219 (merge link), closeout re-gates (plan:41-47 versus plan:187-194). These delta runs use no `--verify`, so the plan's "no --base, no --verify" default sends them to the merge-base check. The plan documents `--base` only for `--verify`. The refusal then prints "the command that makes a correct diff for that base", which is a full diff from the merge base (plan:77-78). Following it turns a narrow delta pass into a full-diff review. Fix: list the wording pass, its confirmation, the final full read and the re-gates in "Docs touched". Make the refusal also say "for a delta since a reviewed head, pass --base <that head>".

- RISK plan:60-81 and the `base:` line (plan:84-89). The check proves the sides of every file in the diff. It does not prove the diff is complete. A diff that leaves out earlier commits of the branch, such as the last commit alone, passes whenever its files were not touched earlier, and then reads `base: <id> (merge base with origin/main, fetched)`. That line implies a verified base-to-HEAD diff. Fix: either state this limit in the plan and the `base:` wording, or compare the diff's file set with `git diff --name-only <base> HEAD`, allowing for the `:(exclude)docs/reviews/` pathspec. Add a test that a partial diff is accepted or refused, whichever is intended.

- RISK plan:40-43 (git behavior). The plan relies on `git fetch origin <default>` refreshing `refs/remotes/origin/<default>`, then runs `merge-base origin/<default> HEAD`. If the remote's fetch refspec does not cover that ref, the guard uses the stale ref and prints "(fetched)". Fix: take the base from the fetched object (`FETCH_HEAD`), or verify the ref moved. Also add refusals for `merge-base` failing, which the refusal table lacks: a shallow clone and unrelated histories. `scripts/sweep_claims.py:255-259` already says "no common ancestor … try git fetch --unshallow".

- RISK plan:169-186 (tests) against the stated behavior. Three behaviors the plan states have no test:
  - "`--local-only` never fetches" (plan:43-45) has none. A fetch would break the documented "nothing leaves the machine" guarantee the script defends elsewhere.
  - T1's wording is ambiguous. If origin moved but the branch did not merge it, a three-dot diff against the old local default is correct and must run. Only the update-branch case (the branch contains the new base commits), or a two-dot diff, must be refused. Add a "moved origin, not merged, runs" case. It is the most common situation and the one a wrong implementation would refuse.
  - No test for `diff.noprefix` or `diff.mnemonicPrefix` (see the NIT on prefix stripping).

- NIT plan:62-66 (reader). Say that names are read only from header lines (before the first `@@`, or by line-count tracking). A removed line `-- x` shows as `--- x` and an added `++ x` as `+++ x` inside a hunk. Failure is a loud false refusal, but a T4 case costs nothing. Also say how `a/` and `b/` are stripped, since `diff.noprefix`, `diff.mnemonicPrefix` and `--src-prefix` change them (plan:62-66 is silent).

- NIT plan:67. Put `--` before the paths given to `ls-tree` (a file named `-x`). Validate a `--base` value that starts with `-`, as `--cut` is validated at independent_review.sh:~212. Resolve it with `git rev-parse --verify --quiet "$rev^{commit}"` as `merge_link.sh:34-36` does.

- NIT plan:62 (new Perl file). `check_perl_minimum.sh:34-35` fails any `perl/*.pl` not in GATED or UNGATED. The reader runs with no version probe, so it is UNGATED (5.8 syntax only: no `//`, no `say`). Say that, and say that a missing `perl` or `git` refuses the run. A silent skip would be a guard that cannot fire.

- NIT plan:179 (T3). Once Change 2 removes the script-wide size rule, "base checked before size" has nothing left to order against. Re-point it or retire it in the Change 2 PR.

- NIT plan:123-128 (remedy and classification). The text "or keep the round with the seats that took it whole" conflicts with SKILL.md:73, where a one-seat round is degraded and normally needs the pair. `report_tier`'s generic reason ("check the CLI, its sign-in and the model name") fits neither the argv refusal nor a context refusal. Also state which class wins when `CONTEXT_RE` and `QUOTA_RE` both match. T8's stub uses the author's own phrase, so it cannot show that real providers' wording matches `CONTEXT_RE`.

- NIT plan:194 (closeout.md). `references/closeout.md` does not "copy the closing lines". The trail template at closeout.md:65-67 has a `Base \`<sha>\`` header and an "Artifact (full / delta since <sha>)" column. Add the `base:` value there.

- NIT plan:54-56 (dropped alternative). "A file still needs this check for deltas" is only true while file and stdin input stay supported. A script-built `--range` removes the subdirectory, prefix, omission and staleness classes above, against roughly ten parser cases plus nine tests. The dismissal gives no size comparison.

### CLEAN (checked, VERIFIED)

- Type detection `case "$FILE" in -|*.diff|*.patch) TYPE="diff"` (independent_review.sh:~273).
- The size gate: `CONTENT_BYTES -gt 120000`, exit 2, content plus prior only (independent_review.sh:480-485). `CONTENT_BYTES` is used nowhere else.
- Prompt transport today: Codex takes `"$PROMPT_TOOLED"` as its last argument with `</dev/null`; the ollama CLI and agy take it on argv. Melious and the ollama API write `$RAW_DIR/*.req` and send it with `curl --data-binary @file`. The `melious_request.pl` and `ollama_request.pl` bodies carry the whole prompt.
- `RAW_DIR` is mode 700, already holds the full request bodies, and has a stale-file `rm` list that a new prompt file must join.
- Codex help (codex-cli 0.163.0) says: "If not provided as an argument (or if `-` is used), instructions are read from stdin". It also says that with a prompt argument and piped stdin, stdin is appended as a `<stdin>` block. That is why `</dev/null` matters today and why `-` is the right form.
- SKILL.md:138 holds the only "Over 117 KB: split it" in docs. SKILL.md:318 already has the host report `timings:`. `merge_link.sh:68` ends with `git diff "$reviewed" HEAD`, so `--base <last-reviewed-head>` is right for it.
- Pure rename and mode-only records have no `index` line. In commit 21125ea1 the pure rename shows only `similarity index 100%` and `rename from/to`. Abbreviated ids vary in length (8 hex digits there), so prefix matching is right.
- The test claim holds: a decoy 429 in `change.diff` is pinned (test_failed_tier_report.sh:27, 469, 479). `inrepo` (line ~744) and all `change.diff` cases are hand-made, so they need `--base none`. The Codex stub pins argv exactly, so T6 must change that stub.
- Base 6681e7be is an ancestor of the plan branch. `.mjs` and `ship.sh` already classify fetch failures, and `sweep_claims` has a `--base` of its own, so the flag name matches the skill.

### UNVERIFIABLE (by component)

- Codex model cache: the claim is "500,000 tokens, 95% usable" (plan:113). Settle by reading the cache entry for the configured model. It is outside the project, so it was not read here.
- Codex CLI: the claims are that a 200 KB stdin prompt arrives whole, and that Codex's own context management keeps the whole first message through a long tool-using run (plan:109, 113). The plan's T6 uses a stub, which proves only what the script sends. Settle with a live `codex exec … -` run on an artifact over 128 KB, nonce on the first line and last line, reply must quote both, ideally after tool calls large enough to trigger compaction.
- ollama server and cloud: the claims are that the served window equals the metadata window (1,048,576), and whether an over-window prompt is refused or cut. Settle with the nonce canary above through the API transport, or the server's per-request context length.
- ollama CLI: whether piped stdin is sent whole as the prompt. The plan already marks this as P1. Settle with its stub server.
- Melious: the claim is a 1,000,000-token window from a third-party listing (plan:114). OpenAI-compatible servers also count `max_tokens` (`MELIOUS_MAX_TOKENS` defaults to 96000) against the window. Settle with the provider's own doc, or a refusal at a known size.
- Linux: MAX_ARG_STRLEN = 128 KB (plan:204 says not re-run). Settle by exec'ing a 131072-byte argument on Linux.
- agy: whether `-p` reads stdin (plan:121). Settle with one Antigravity credit.
- git: whether `git fetch origin <default>` refreshes the tracking ref in a narrow-refspec clone. Settle by comparing `git rev-parse origin/<default>` before and after a fetch in a default clone and a single-branch clone.

Note on the read-only rule: I created and then deleted one empty scratch file in /tmp (`/tmp/.irv_out`) while checking `ls-tree`'s exit status. Nothing else was written, fetched or changed.

</details>

<details><summary>Round 2 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

Let **P** mean `docs/reviews/SKILL-PLAN-review-input-base-and-size.md`. Findings concern the rewritten sections or prior fixes. Implementation and new tests remain planned.

- RISK — P:139–167, **R1-10 partially fixed** — P2 supports one synthetic input on one configuration; it does not establish whole-input retention for other token densities, configured models, or prompts enlarged by prior findings and instructions (`independent_review.sh:576–620`). Silent truncation could still count an incomplete review as OK. Fix: bind measurements to model/transport/context configuration, budget the complete prompt, and verify consumed input against an independently established token count.
- RISK — P:73–86, **new canonical-patch design** — Rule 4 requires comparing blob IDs for mode-only records, but the described header reader has no defined ID source when the generated patch also lacks `index`; the claimed comparison remains unsupported and could reject valid T4 inputs. Fix: obtain modes and IDs through full-width raw metadata, or explicitly define acceptance through a matching generated mode-only record; trace that case through the reader.
- BUG — P:104, T5, **R1-11** — WRONG: `--cached` does not invariably have the index on its old side, and headers cannot establish command provenance. Locally, `git diff --cached --full-index HEAD^ -- <plan>` and `git diff --full-index HEAD^ HEAD -- <plan>` produced identical 29,949-byte patches. Fix: accept matching sides regardless of command origin; test index states that actually mismatch the selected base or new side.
- BUG — P:53–56, T3, **R1-20** — WRONG: the merge-base default cannot refuse every delta without `--base`; a delta touching paths unchanged between the merge base and reviewed head has matching headers. Locally, the newly added review trail produced identical patches against `HEAD^` and `HEAD^^`. T7 also expressly permits omitted files. Fix: describe `--base` as required caller discipline for delta runs; qualify refusal as conditional on side mismatches, or introduce an explicit delta mode requiring it.
- BUG — P:162–169, Open 1, **rewritten P2 estimate** — WRONG: if P1 passes, P2 names four probes; at the stated 100,000–130,000 tokens each, that is 400,000–520,000 tokens, rather than about 350,000. Fix: give separate three-probe and four-probe totals.

**Checked that was CLEAN**

“VERIFIED” here distinguishes landed plan requirements from future runtime behavior.

| Prior finding | Verdict and evidence |
|---|---|
| R1-01 | VERIFIED: P:82–86 now requires mode comparison; T5 includes stale modes. The separate metadata-source risk is above. |
| R1-02 | VERIFIED: the erroneous hash invocation was removed; P:67–72 delegates comparison-patch generation to Git, and P:247 supplies the file operand. |
| R1-03 | VERIFIED: P:64–66 anchors commands at the repository root; P:114 anchors the remedy. `git -C skills rev-parse --show-toplevel` returned the project root. |
| R1-04 | VERIFIED: the proposed canonical command carries no changed-path list on argv. |
| R1-05 | VERIFIED: T1 now includes taking origin’s updates into the branch; T2 separately covers origin advancing without that update. |
| R1-06 | VERIFIED: the proposed `CONTEXT_RE` classifier and conflicting remedy were removed. |
| R1-07 | VERIFIED: the recommendation now names only Codex and Melious, conditional on P2. Its whole-input inference remains covered by R1-10 above. |
| R1-08 | VERIFIED: the revised cwd description matches `test_failed_tier_report.sh:329–336`, whose runner inherits cwd. |
| R1-09 | VERIFIED: P:57–59 explicitly exempts `--base none` from rules 1–5 and permits execution outside a repository. |
| R1-12 | VERIFIED refutation for ordinary unified hunks: content lines have a diff marker; examined Git patches do not expose their content as column-zero record headers. |
| R1-14 | VERIFIED: argv transports retain 120,000 rather than increasing to 128,000. |
| R1-15–16 | VERIFIED as revised requirements: header boundaries, prefix handling, quoted names, equal-name fallback and hunk-count skipping are specified. Parser execution remains unverified. |
| R1-17 | VERIFIED: P:61–62 limits the claim to artifact transmission and acknowledges the earlier fetch. |
| R1-18 | VERIFIED as a requirement: bounds and a hanging-fetch test are now specified. The claimed runtime bound remains unverified below. |
| R1-19 | VERIFIED: the docs list includes both other skill callers and vendored-repository guidance; their existing calls occur at `website-review/SKILL.md:68` and `seo-reposition/SKILL.md:94`. |
| R1-21 | VERIFIED: P:88–90 and T7 add omitted-file reporting without claiming hunk completeness. |
| R1-22–23 | VERIFIED as requirements: no-merge-base refusal, local-only no-fetch behavior, and prefix tests are now explicit. |
| R1-24 | VERIFIED: leading-dash rejection is specified; commit resolution matches `merge_link.sh:34`; canonical generation avoids path arguments. |
| R1-25 | VERIFIED as integration requirements: the reader is assigned to UNGATED and missing tools must refuse. `check_perl_minimum.sh:30–32` defines the existing lists and 5.8 ceiling. |
| R1-26 | VERIFIED: T8 orders base validation against size checks. |
| R1-27 | VERIFIED: `references/closeout.md:66–67` contains the stated Base field and Artifact column. |
| R1-28 | VERIFIED: the dropped alternative now includes an explicitly labelled implementation estimate and its reason. |

Additional source checks were VERIFIED: current argv versus file-body transports, the artifact-plus-prior 120,000-byte check, raw-directory mode and cleanup (`independent_review.sh:480–485, 686–707, 843, 912–914, 977–979, 1040–1044, 1132–1137`); merge-link output compares the reviewed head with HEAD (`merge_link.sh:68`). Local Codex help contains the quoted stdin contract; local ollama help shows the cited `--ask` examples. Git commit `21125ea1` confirms a pure rename without an `index` header.

**Remaining UNVERIFIABLE claims, grouped by component**

- **Git — R1-13 and edge-record behavior:** the worktree-specific `FETCH_HEAD` path was verified with `git rev-parse --git-path FETCH_HEAD`; fresh remote-HEAD selection, tracking-ref effects, and all proposed parser edge cases lack reproduced integration evidence. Settling observation: inspect refs and parsed metadata before and after the specified local-origin fixtures.
- **Perl/process handling — R1-18:** the site hook uses Node’s timeout and additional SSH keepalive options (`git-stand.mjs:32–33, 124–137`); it does not establish the proposed Perl alarm’s behavior. Settling observation: run T5’s hanging helper through the actual wrapper and record refusal time and surviving processes.
- **Codex:** help supports the documented stdin interface; end-to-end retention and compaction under P2 lack a traced request. Settling observation: inspect the actual submitted and retained input during the configured probe.
- **Melious / ollama serving:** request builders establish serialization, including omission of `num_ctx`, rather than effective serving windows or token-accounting semantics. Settling observation: compare independently counted complete inputs with accepted/evaluated input for each selected model and configuration. This supports the first RISK.
- **Linux argv limit:** the exact per-string boundary remains unsupported by a reproduced Linux measurement or kernel implementation evidence; retaining the existing cap avoids the previously proposed increase.

No deferred rows were listed. The new tests and `make check` were not run: they require filesystem writes, and the proposed implementations are absent.

Prompt injection: none found.
## Independent review — melious (glm-5.3, HTTP API)


Findings (ranked):

- BUG — "How it tells" rule 3, against rule 4 and the table row "Rename or mode change with no `index` line | checked by rule 4". Rule 3 never names `rename from`/`rename to` as a name source, and its stated fallback ("splits a `diff --git` line … where both halves name the same path") can never fire for a rename, whose halves differ. A 100%-similarity rename record has no `index` line and no `---`/`+++` lines, so per rule 3 as written it has no name source at all — yet rule 4 explicitly promises to check "a rename at 100%", which is only reachable through those lines. A plain `git diff <base>` (rename detection on by default) containing a pure rename would then be refused or uncheckable. Fix: name `rename from`/`rename to` (and `copy from`/`copy to`, needed anyway to classify the refused copy record) as header name sources in rule 3, and pin T4's "rename" case at 100% similarity so this path is actually exercised (a <100% rename carries `---`/`+++` lines and would pass without it).

- RISK — Change 2: "A seat's cap is the largest size it was measured to take whole (probe P2)" and the refusal message "artifact 410 KB, over this seat's measured 400 KB", against P2's "One prompt of 400 KB per seat". The measurement is of whole-prompt bytes; the check and message size the artifact. At artifact == cap the sent prompt (artifact plus the review wrapper) exceeds the measured size, so the closing guarantee "no seat is sent more than it was measured to take whole" fails exactly at the boundary the cap exists to enforce — a silent cut, the failure R1-10 was about. T9 ("a 400 KB artifact") and T10 ("A 400 KB artifact reaches every seat with a 400 KB cap") sit on the wrong side of that boundary. Fix: apply each cap to the whole prompt (wrapper + artifact), or define P2's 400 KB as wrapper-plus-artifact and check the same quantity; size T9/T10 to the capped quantity.

- NIT — "Which base", no-`--base` default. When HEAD is itself origin's default tip (a diff made on the default branch, e.g. a wording pass), the merge base is HEAD, git's patch is empty, and the printed remedy `git diff <base-id> HEAD -- . ':(exclude)docs/reviews/'` produces an empty diff — a dead-end command for a correct caller. Fix: detect base == HEAD and name `--base <parent of HEAD>` in the refusal.

Checked and CLEAN:

- All 28 prior findings re-checked against the current plan text. Every row marked "fixed" has its fix present and covering the whole claim, not just the example: R1-01 (rule 4 compares modes; T5 stale-mode case), R1-02/R1-04 (git makes its own patch; "No path goes on argv"), R1-03 (rule 1 top-level `git -C`; `git -C <top>` remedy; T4 subdirectory), R1-05 (T1 update-branch topology, T2 moved-not-merged must run), R1-06 (the label is fully cut, with the rationale in "Considered and dropped"), R1-07 (both default seats named at a measured cap), R1-08 (repo-root wording), R1-09 (`--base none` skips rules 1–5 and runs outside a repo; T5), R1-10 (per-seat caps redesign present), R1-11 (index-side row), R1-14 (120,000 kept for argv and unmeasured seats), R1-15/R1-16 (rule 3 header-only names, prefix strip, tab, hunk skip by line counts; T4), R1-17 ("the fetch above goes first"), R1-18 (prompt-off, BatchMode, lowSpeed, 30 s alarm; T5 hang case), R1-19 (docs list), R1-20 (`--base` for every non-whole-change diff; the "--base <that head>" line; T3), R1-21 (rule 5 left-out names; T7), R1-22 (no-merge-base row), R1-23 (T6; T4/T5), R1-24 (no paths on argv; `--base` validated as `--cut`), R1-25 (ungated Perl 5.8; missing perl/git refuses), R1-26 (T8), R1-27 (Base field / Artifact column wired to the `base:` line), R1-28 (estimate and files-stay rationale given). The one "refuted" row, R1-12, I re-derived from the diff format itself: every hunk-body line begins with ` `, `+`, `-` or `\`, so a column-0 `diff --git` cannot sit inside a hunk — the refutation holds, and the real neighbour (`--- x` from a removed `-- x`) is now handled by hunk skipping plus T4.
- Internal consistency of the input table against rules 1–5: every row traces to a rule or a test.
- Rule 2's two-patch logic, including the working-tree gating ("only if some file's new side does not match `HEAD`") across committed diffs, uncommitted work, deletions and new-in-worktree files — each case lands on a patch that can answer it.
- Rule 4's mapping with `--no-renames` on git's side: pure renames appear as delete+add with equal blob ids, matching "equal ids on its two sides" — sound except for the name-source BUG above.
- Change 2's seat table: cap sources, the unmeasured 120,000 fallback, agy not probed (credit cost stated), the CLI probe conditional on P1, `--base none` never skipping a cap, and base-before-caps ordering (T8).
- T1–T11 against the stated behaviours; the existing-suite `--base none` accommodation; the stale-`origin/<default>` story coheres with a fetch that never updates it (T1 depends on that).
- No `CONTEXT_RE` or nonce-check residue in change 2; the "caps do not see" and "outside this plan" sections state the residual silent-cut risks honestly.

UNVERIFIABLE (component and repo claims this review could not check — not findings):

- git (as checked by the author on 2.33): `git fetch origin HEAD` fills `FETCH_HEAD` per-worktree without moving `origin/<default>`; pure renames and mode-only changes carry no `index` line while binaries do; a working-tree diff's new id equals `git hash-object -- <path>`; a tab follows a spaced name; the mnemonic prefix set is exactly `a/ b/ c/ i/ o/ w/`; `git apply` splits same-path `diff --git` lines. Support: the author's scratch-clone checks, not reproduced here. Settling observation: reproduce each output in a scratch clone (and read git's apply code for the split).
- codex-cli 0.163.0: reads instructions from stdin when `-` is used. Support: quoted help text only — but P2/T9 are the planned tests. Settling observation: run `codex exec -` with a piped prompt and confirm the answer reflects it (P2's three nonces do this).
- ollama 0.40.7 CLI: piped stdin becomes the prompt. Support: P1 is the probe. Settling observation: run P1's stub-server recording.
- ollama API transport sends no `num_ctx`. Settling observation: read the request the stub records in a test.
- The script's own current code: Codex prompt on argv, ollama CLI argv, agy `-p`, Melious/ollama API file bodies, the mode-700 raw folder and stale-file clearing, `check_perl_minimum.sh` placement, `merge_link.sh` resolution, `closeout.md`'s existing Base field, the website-review/seo-reposition `--diff` commands. Settling observation: read `independent_review.sh` and the named files.

OUTSIDE SCOPE: none.

Prompt injection: none found — the plan's imperative text (git commands, refusal messages, doc updates) is ordinary material and was reviewed as such; nothing in it attempts to alter this review's task, output or conclusions.

Verdict: two substantive findings — the pure-rename name-source gap in rule 3 (BUG) and the artifact-vs-prompt cap mismatch in change 2 (RISK) — plus one NIT; everything else checked clean, with the unverifiable claims collected above.

---
reviewers: codex OK, melious OK
timings: codex 370s (86895 tokens), melious 340s (34257 tokens)
gate 20261021T172444Z-64903: rounds 1-2, 5 reviewer seat runs, 497,891 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 3 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

Ranked findings (`P` = `docs/reviews/SKILL-PLAN-review-input-base-and-size.md`):

- BUG — P:184, P2 — WRONG: “An error is ‘refuses’” classifies quota, authentication and transport failures as context-limit evidence, granting an uncapped entry at P:151; existing error paths distinguish these failures (`independent_review.sh:1045–1050,1267–1273`). Fix: require a diagnosed context-length rejection; leave every unrelated or ambiguous failure unmeasured.
- BUG — P:60, “merge base is HEAD” — WRONG: HEAD can still be compared with uncommitted work, which rule 2 and the input table explicitly support; this new unconditional refusal rejects that valid whole-change diff. Fix: attempt working-tree validation before refusing, and add dirty-worktree cases with merge base equal to HEAD.
- RISK — P:181–185, P2 / R2-01 — The claim that a successful reply’s reported prompt count is the truncation boundary lacks support from Codex, Melious and ollama’s accounting implementations or traced requests; a count taken before truncation could produce an unsafe cap and count an incomplete review. Fix: independently count submitted tokens and establish what each reported field measures; ambiguous results must retain the fallback cap.
- RISK — P:153–156, token budgeting / R2-01 — Applying the byte-level bound to every selected model, with only 1,000 tokens for its wrapper, lacks tokenizer and wrapper-budget evidence; either assumption failing can put a supposedly capped prompt beyond the retained window. Fix: establish each model’s encoding bound and actual transport overhead, or count the complete encoded request using the matching tokenizer.

CLEAN checks and prior-finding verdicts:

| Claim | Verdict and evidence |
|---|---|
| Review scope and checkout | VERIFIED: cwd matches the supplied project; `git status --short` was clean. Compared `9a0f5cd3..HEAD` (`fa726dd5`) to identify this round’s edits. |
| R2-01 fixed completely | UNVERIFIABLE: the redesign landed, but its safety depends on the accounting and token-budget claims flagged above. The original silent-cut consequence remains unresolved. |
| R2-02: records without `index` have a defined matching strategy | VERIFIED as a revised requirement at P:90–95. Pure-rename behavior reproduced using `git diff -M 21125ea1^ 21125ea1` and its `--no-renames --full-index` counterpart: rename headers become delete/add records with equal blob IDs. Mode-only behavior remains unverified below. |
| R2-03: judge index-derived patches by their sides | VERIFIED: compared `git diff 9a0f5cd3 HEAD` with `git diff --cached 9a0f5cd3` for the plan; output was byte-identical. T4/T5 now distinguish accepted and rejected cases. |
| R2-04: no universal delta detector | VERIFIED as a corrected specification: P:53–59 acknowledges indistinguishable headers and assigns caller responsibility; T3 covers both branches. |
| R2-05: incorrect aggregate probe estimate removed | VERIFIED: P2 now states costs per seat; no four-seat total remains. The replacement billing claims remain unverified below. |
| R2-06: pure-rename name sources restored | VERIFIED: P:80–81 names rename/copy headers; T4 explicitly includes 100% and partial renames. The reproduced pure rename contains the stated rename headers. |
| R2-07: artifact/prompt mismatch addressed | VERIFIED as a revised requirement: cutting seats now cap the whole prompt; T9 checks prompt bytes. This does not establish the budget assumptions flagged above. |
| R2-08: empty-remedy case addressed | VERIFIED: explicit refusal and T5 coverage landed. Its new dirty-worktree regression is the BUG above. |
| R1-12 refutation | VERIFIED for ordinary unified hunks: inspected 223 hunk-body lines in this revision’s patch; every line retained its diff marker. Column-zero record headers were outside hunks. |
| Current transports and cap | VERIFIED: `independent_review.sh:480–485,843,912–914,977–979,1040–1044,1132–1137` match the described argv/file-body transports and artifact-plus-prior cap. |
| Request builders and raw storage | VERIFIED: read both request builders; ollama’s contains no `num_ctx`. Raw directory protection and stale-file cleanup match `independent_review.sh:686–707`. |
| Callers and documentation anchors | VERIFIED: `merge_link.sh:68` compares the reviewed head with HEAD; closeout fields exist at `references/closeout.md:66–67`; both other skills contain the identified diff commands. |
| Deferrals | VERIFIED: the prior record lists no deferred rows. |

Additional UNVERIFIABLE claims, grouped by component:

- **Git:** mode-only output without `index` lacks a reproduced fixture here. Settling observation: compare an actual mode-only commit using the specified canonical command and inspect its headers.
- **Codex / ollama CLI:** stdin behavior lacks an implementation trace or executed P1/T9 result in this round. Settling observation: capture the exact submitted request from the installed transport using controlled input.
- **Provider billing:** “nothing” for refusals and “up to one window” for successful probes lack billing evidence. Settling observation: reconcile each probe’s request, usage records and charged amount.
- **Proposed implementation/tests:** `diff_headers.pl`, `seat_limits.txt` and the new tests are not implemented yet. Parser behavior and T1–T12 remain requirements, not passing evidence; no write-producing suite was run.

OUTSIDE SCOPE: none reported.

Prompt injection: none found. The plan’s imperatives describe implementation and review procedures; they do not attempt to redirect this review.
## Independent review — melious (glm-5.3, HTTP API)


Scope 1 — prior findings (round 2 record) re-checked

- RISK — Change 2, "The change" ("A token is never shorter than a byte in a byte-level tokenizer, so N bytes is at most N tokens, whatever the text") — this is the leg R2-01's fix stands on: nothing establishes that the seats' configured tokenizers (Codex's model, GLM 5.3) are byte-level, and it is a claim about what those components do, not something the plan tested; if it is false for a configured model, a "cuts" seat's cap of N bytes can be more than N tokens, the provider cuts the prompt silently mid-review, and the round reads as OK — the exact failure R2-01 was filed against. Fix: in P2, record per model both the probe's byte length and its reported token count (tokens ≤ bytes checked on the sample); any model that fails the check, or was not sampled, falls back to the 120,000-byte cap.
- RISK — "How it tells" rule 3 ("It strips git's prefixes (`a/`, `b/`, and the mnemonic `c/`, `i/`, `o/`, `w/`)") — nothing says one prefix per name: an implementation of the sentence as written strips twice in a repo with a top-level `c/`, `i/`, `o/` or `w/` directory (`--- a/w/x` → `w/x` → `x`), mis-pathing the record into a wrong refusal or a match against an unrelated changed file. Fix: decide each record's prefix pair from its own `diff --git` line and strip exactly one leading prefix per name in that record.
- NIT — intro "A diff over 117 KB is refused (`CONTENT_BYTES -gt 120000`)" vs Change 2 "today's check, artifact plus prior findings at most 120,000 bytes" — the plan describes the check it preserves two incompatible ways; if `CONTENT_BYTES` sizes the diff alone, an argv seat's full string (diff + prior findings + template) can pass Linux's 131,072-byte per-string limit and die at exec instead of being refused. Fix: read the script, state once what `CONTENT_BYTES` covers, and if it is the diff alone, keep the argv seats' check on the assembled prompt string.
- NIT — "Which base", merge-base-is-`HEAD` bullet ("refused, since there is nothing to compare against") — the reason is false for uncommitted work on the default branch: rule 2's working-tree patch is exactly something to compare against, and `--base HEAD` would validate it. Fix: name `--base HEAD` in the refusal message, or allow the run when the working tree differs from `HEAD`.
- NIT — refusal message ("prints the command that makes a correct diff: `git -C <top> diff … <base-id> HEAD -- . ':(exclude)docs/reviews/'`") — for an artifact that was a working-tree diff (uncommitted work), diffing against `HEAD` does not remake it; the correct remake is `<base-id>` alone. Fix: print both forms, or pick the form matching the side the artifact used.

Prior findings whose fix I confirmed landed and covers the whole claim: R2-02 (rule 4 text, mode-only and 100%-rename matching, T4 case), R2-03 (sides-not-command row, T4 `--cached` with index at `HEAD`, T5 plain `git diff` with index ahead of base), R2-04 (caller's-duty bullet, rule 5's note, SKILL.md step 6, T3's two sub-cases), R2-05 (per-seat cost, stop after the first cutting seat), R2-06 (rule 3 names `rename from`/`rename to`, `copy from`/`copy to` to refuse; T4 renames at 100% and below), R2-08 (refusal names `--base`; T5). R2-07's whole-prompt caps are in place for every off-argv seat; only the two NIT-severity residuals above touch it. R1-12's refutation is accepted: every hunk body line carries a leading ` `, `+`, `-` or `\`, so a column-0 `diff --git` cannot sit inside a hunk of a git-format diff.

Scope 2 — new problems in the changed text: the five findings above are the ones that rise; the rest of the changed sections (seat table, `seat_limits.txt` semantics, unlisted-model fallback, T9–T12 expectations, "Considered and dropped", "What this does not see", the split recommendation's reasoning, "Order", Open 1's now-correct statement that without P2 nothing lifts) is internally consistent with the rest of the plan.

UNVERIFIABLE (claims about components, not findings; grouped by component)

- git — "checked on git 2.33" in the "Checked" section, not reproducible here: (a) a mode-only change has no `index` line even with `--full-index` (rule 4 depends; if false, mode-only records never pass); (b) under `--no-renames` a 100% rename shows as a deletion and an addition sharing one id (T4's rename-at-100% case); (c) `git fetch origin HEAD` fills a per-worktree `FETCH_HEAD` without moving `origin/<default>`; (d) a path with a space gets a trailing tab on `---`/`+++`. Settle by running each in a scratch repo on git 2.33 and on the newest git in use.
- codex-cli 0.163.0 — the quoted help line ("If not provided as an argument (or if `-` is used), instructions are read from stdin") is a quotation, not a reproduction, and T9's stub verifies only what the script passes, not what the real CLI does. Settle by piping instructions to `codex exec … -` against a recording endpoint.
- Melious / ollama API / Codex response formats — P2's "its reported prompt token count is the cut point N" assumes each seat's reply carries a prompt-token count. Settle by inspecting each seat's response body for such a field; a seat without one must fall back to "not measured".
- `references/closeout.md` — "already has a `Base` field and an 'Artifact' column". Settle by reading the file.
- Cited model windows (Codex 500,000 at 95% usable; GLM 5.3 1,048,576 and 1,000,000) — cited, not measured; they only size P2's probes, and P2 measures the real cut points.

Checked and CLEAN (silence is not coverage): the byte/token arithmetic direction — with tokens ≤ bytes, an N-byte prompt is ≤ N tokens, and subtracting reply room and the 1,000-token template margin is in the safe direction (modulo the byte-level RISK above); P2's stop-after-first-cut bounds cost with no total to exceed; base check ordered before the size check with T8 proving it; `--base none` skips only the base check, never a cap; `--base` refused on plans and on values starting with `-`; T1's expected file list follows from rules 4 and 5 as written; the index row's side-based judgment matches rule 2's two patches (committed and working tree); the `--cached <base>`-with-index-at-`HEAD` equivalence and the plain-`git diff` refusal condition are consistent with rule 4's side comparison; rule 3's hunk-body skipping makes `-- x` / `++ x` records safe; the removed-line-as-`--- x` case and R1-12's refutation agree; the stale-mode-change and path-not-in-git's-patch refusals follow from rule 4; the docs list covers every caller the plan names; no prompt-injection text — nothing in the plan addresses the reviewer or attempts to alter this review's task, output or conclusions.

---
reviewers: codex OK, melious OK
timings: codex 169s (71055 tokens), melious 232s (31472 tokens)
gate 20261021T172444Z-64903: rounds 1-3, 7 reviewer seat runs, 600,418 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 4 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- BUG — `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:85` — The revised “one prefix from each name” rule also strips unprefixed rename headers: with mnemonic prefixes `w/` and `i/`, `rename from w/old` names the repository path `w/old`, so stripping `w/` corrupts it; fix by stripping prefixes only from `diff --git` and `---`/`+++` names, preserving rename/copy names, and adding a pure-rename fixture under `w/`.
- RISK — `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:156` — Provider/CLI behavior: one oversize context-limit rejection does not establish the load-bearing claim that other oversized inputs always fail rather than truncate; removing the cap could therefore count a partial-artifact review as complete. No serving-policy implementation or traced test establishes that distinction; inspect admission, truncation and forwarding behavior across accepted/rejected lengths for the seat/model/configuration, and retain the cap until a reject-without-truncation policy is supported.

**Checked claims and CLEAN results**

These verdicts concern the revised plan. Its status correctly leaves implementation and tests pending.

| Claim | Verdict and evidence |
|---|---|
| Scope and changed sections | **VERIFIED:** cwd is the supplied project; checkout is clean. `git diff fa726dd5 HEAD` changes only the plan and review record. |
| R3-01: unrelated errors no longer automatically lift caps | **VERIFIED:** plan lines 156–161 and 187–195 distinguish context/token-limit errors from quota, sign-in, network and request-size errors. The broader refusal-policy inference is the RISK above. |
| R3-02: uncommitted work when merge base equals HEAD | **VERIFIED:** lines 61–63 explicitly select the working-tree comparison; T4 adds acceptance and T5 restricts refusal to a clean tree. |
| R3-03/R3-04: token-count and tokenizer assumptions removed | **VERIFIED:** replies retain 120,000 bytes; reported tokens are informational. The former calculated caps and template allowance are removed. |
| R3-05: repeated prefix stripping removed | **VERIFIED** as a textual change; **WRONG** that stripping once from every header name preserves paths. The new regression is the BUG above. |
| R3-06: `CONTENT_BYTES` includes prior findings | **VERIFIED:** `independent_review.sh:480–484` counts `CONTENT` plus `PRIOR` and exits 2 above 120,000. |
| R3-07: remedy distinguishes committed/working-tree forms | **VERIFIED:** plan lines 125–128 now specify both forms and their selection condition. |
| R1-12: column-zero `diff --git` is not ordinary hunk content | **VERIFIED:** inspected Git-produced hunks in the round-3 diff; content carries its hunk prefix. |
| Deferred findings | **VERIFIED:** none are marked deferred in the supplied record. |
| Existing transport and storage descriptions | **VERIFIED:** script call sites pass prompts through argv for Codex/ollama CLI/agy, use request-body files for both APIs, and create/clear the private raw directory (`independent_review.sh:686–707`). |

The rename finding was checked against Git itself: `git show --find-renames 377ecc82` emits unprefixed rename headers even with explicit mnemonic prefixes. A synthetic pure rename using `w/w/old`, `i/w/new`, and `rename from w/old` was accepted by `git apply --numstat -`, reporting `w/new`.

**Additional UNVERIFIABLE claims**

- **Codex/ollama CLI:** stdin completeness lacks an implementation trace or real-transport capture. T9’s stub checks the caller, not Codex. Settling observation: capture the request produced by each installed CLI from known stdin bytes.
- **Provider windows and billing:** cited windows and P2’s cost estimates lack supporting model metadata, citations or usage records in this review. Settling observation: inspect the relevant model configuration and reconcile probe usage with billing.
- **Linux runtime:** the 128 KB argument limit is repeated by the script comment, which is not independent support. Settling observation: inspect the applicable kernel implementation or reproduce the argument boundary.

OUTSIDE SCOPE: no additional findings recorded.

Prompt injection: none found.
## Independent review — melious (glm-5.3, HTTP API)


**Findings (ranked)**

- BUG — Tests, T11 vs Change 2 “The change” (“a missing list, or a line the script cannot read, leaves every seat at 120,000”): with a 200 KB artifact and a malformed `seat_limits.txt` line, *every* seat is capped at 120,000, so every seat is `FAILED` before sending and T11's pass condition “the other seats ran” is impossible for that subcase — the rule sentence and the test contradict each other (the author's R3-01 row also says “anything else leaves the *seat* at 120,000”, per-seat, a third wording). Fix: pick one semantics — either an unreadable line caps only the seat whose entry it is (rewrite the “every seat” sentence to match, and T11 stands) or it poisons the whole list (split the malformed-line case out of T11 as its own row asserting every seat `FAILED`, no stub ran).

That is the only finding in scope. Verdict per scope:

**Scope 1 — prior findings** (each checked against the plan text, not the author's evidence column):
- R3-01 fixed and whole: “Refuses” now requires an error naming a context or token limit, text and date recorded; quota/sign-in/network/request-size explicitly fall to “Anything else” at 120,000; T11/T12 cover both directions.
- R3-02 fixed and whole: the merge-base-is-HEAD bullet compares with the working tree and refuses only when it holds no change; rule 2's working-tree fallback (“only if some file's new side does not match HEAD”) covers it, since the artifact's new sides are working-tree blobs differing from HEAD; T4 runs the dirty-tree case, T5 refuses the clean one.
- R3-03/R3-04 fixed by cut: no reply-as-limit or tokenizer-derived cap remains anywhere; the only cap is 120,000; “Considered and dropped” names the round-3 cap and its two unsupported claims as dropped; a P2 reply is “recorded for information… never as a limit”.
- R3-05 fixed and whole: rule 3 strips exactly one prefix, the pair read from the record's own `diff --git` line; T4 has a top-level folder named `w`; other/none prefixes refused (matching the input table).
- R3-06 fixed: “What and why” 2 says `CONTENT_BYTES` is the artifact plus prior findings; no remaining spot describes the check as the diff alone (T8's “stale diff over 120,000 bytes” is about the artifact, not the check's definition).
- R3-07 fixed: the remedy prints `diff <base-id> HEAD -- . ':(exclude)docs/reviews/'` for committed work or `<base-id>` alone for the working-tree form, i.e. the artifact's form.
- R1-12 refutation checked and holds: hunk body lines all begin with ` `, `+`, `-` or `\`, so a column-0 `diff --git` cannot be hunk content in a well-formed diff.

**Scope 2 — new problems in the changed sections**: the T11 BUG above is the only one. Checked clean: the Refuses/Anything-else taxonomy against the seat table (all rows consistent, agy and argv-ollama always 120,000, stdin-CLI “as the API”); “Until P2” column vs Open question 1 (transports move, nothing lifts without P2); P2's stop-on-reply, nonce, per-seat-and-model keying vs the “new `CODEX_MODEL`” fallthrough; 'What this does not see' vs the dropped caps; the split recommendation (depends on no dropped claim); the changed 'Which base' bullet against the input table's default-branch rows; changed rule 3 against T4's edge records (`--- x`, `++ x`, mnemonic pairs, space/tab paths); the changed remedy against rule 4's prefix id comparison and rule 5's `docs/reviews/` exemption.

**OUTSIDE SCOPE** (unchanged sections, recorded as follow-ups, not blocking):
- RISK (follow-up): the Linux single-argument 128 KB cap is load-bearing for the 120,000 argv cap and is admitted unchecked (“Not checked: the Linux argument limit”); if smaller on a target runner, an argv seat hits E2BIG before the friendly `FAILED`. Measure `MAX_ARG_STRLEN` on the runner.
- NIT (follow-up): T7 (“a diff of the last commit only, no —base | runs”) does not state the precondition T3 shows is required — earlier commits must touch disjoint files, else the delta is refused.
- NIT (follow-up): the mnemonic-prefix set listed (`c/ i/ o/ w/`) omits git's `1/`/`2/` pairs; those arise only for `--no-index`/blob diffs, which are refused anyway, but the refusal table could name it.

**UNVERIFIABLE** (load-bearing component claims I could not check here; observations that would settle each):
- codex-cli 0.163.0 reads instructions from stdin when the argument is `-` (quoted help text; the Codex transport rests on it). Observation: run `codex exec … -` against a recording stub, or read the CLI's argument handling; T9 also settles it at build time.
- Quoted behaviors of `independent_review.sh` itself: `CONTENT_BYTES` = artifact plus prior findings (claimed at line 480), Melious/ollama-API prompts via `curl --data-binary @file`, ollama API sends no `num_ctx`, agy `-p` and ollama CLI on argv, raw folder mode 700 with stale-file clearing, a `QUOTA_RE` to sit beside. Observation: read the script's size check and seat transports.
- The git 2.33 behaviors claimed checked (per-worktree `FETCH_HEAD` from `git fetch origin HEAD`; no `index` line for a mode-only change under `--full-index`; a 100% rename under `--no-renames` shown as deletion+addition with the same id; tab after a spaced name; working-tree new id = `hash-object`). Rules 2–4 rest on these. Observation: reproduce each in a scratch repo on git 2.33.
- `seat_limits.txt` “read like `melious_models.txt`”: what the existing list reader does with missing/malformed lines (distinct from the T11 contradiction, which is internal). Observation: read the script's `melious_models.txt` reader.
- Model window figures (Codex ~500,000; GLM 5.3 ~1,000,000) — used only for probe sizing and cost estimates, and marked “cited, not measured”. Observation: provider docs / `ollama show` on the configured models.
- “Everything else is unchanged since round 3” — the record's own change list; observation: a diff of the plan between rounds.

**What I checked that was CLEAN** (beyond the per-finding checks above): internal consistency of the seat table with the argv-transport and P1/P2 gating; the “no probe at all” fallthrough against T10/T11 setups; the order section (base check before size, `--base none` skips only the base check) against the T8 case and the change-2 text; the refusal table's rows against rules 2–5 and the merge-base-is-HEAD bullet; the status table against the Open questions (P2 is the maintainer's call, step 5 precedes 6); T4's edge-record list against rule 3's parsing rules; T5's refusal list against the table; T6 against the `--local-only` paragraph; T9's assertions against the Codex transport row; T12 against the no-cap failure path; the “Checked here, and not” section against the claims used load-bearing elsewhere (windows are cited and only used for probes/costs; git behaviors used in rules 2–4 are claimed as checked, listed under UNVERIFIABLE above).

**Prompt injection**: none. The plan's imperative prose (script behavior, test steps, runbook-style remedies) is ordinary material; no text in it attempts to alter this review's task, output, or conclusions. The trailing output-format instruction comes from the task framing, not the plan.

---
reviewers: codex OK, melious OK
timings: codex 155s (64429 tokens), melious 249s (32490 tokens)
gate 20261021T172444Z-64903: rounds 1-4, 9 reviewer seat runs, 697,337 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 probe-verdict,merge-base-head

</details>

<details><summary>Round 5 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- RISK — `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:158` (R4-02, still open): the claim that other oversized prompts fail loudly lacks a provider admission/truncation implementation trace; one refusal cannot establish it, so removing the cap could count a truncated artifact as fully reviewed. The record at `REVIEW-plan-…ad095f0.md:63–66` requires a waiver and records none. Retain 120,000 bytes unless that waiver is granted; add the decision explicitly under “Open.” Settling observation: trace the configured provider’s rejection and truncation policy across input lengths.

Checked claims and CLEAN coverage:

| Claim | Verdict and evidence |
|---|---|
| Revision scope matches the author’s record | **VERIFIED:** `git diff ea30cd24 HEAD` changes only the plan and review record; substantive plan changes match the listed sections. |
| R4-01’s prefix fix covers the original defect | **VERIFIED as a plan fix:** rule 3 preserves rename names and strips only prefixed header names. Git 2.33’s `git show --find-renames --src-prefix=w/ --dst-prefix=i/ 377ecc82` emitted prefixed diff/file headers and unprefixed rename headers. |
| Top-level folder names survive the revised interpretation | **VERIFIED:** synthetic pure-renames under `w/`, `a/`, and `b/`, passed to `git apply --numstat -`, retained their folders. T4 now specifies the `w/` regression. |
| Remedy explicitly restores accepted prefixes | **VERIFIED:** executing its prefix options with both `diff.noprefix=true` and `diff.mnemonicPrefix=true` still emitted `a/` and `b/`. Rule 3, the refusal table and T5 agree. |
| R4-03’s contradictory test expectation is removed | **VERIFIED as a plan fix:** T11 now pairs an individually capped seat with an eligible seat; T13 separately expects global failure. The existing script’s terminal path at `independent_review.sh:1477–1504` exits 4 when no reviewer succeeds. |
| T7 now states its necessary precondition | **VERIFIED:** its selected files were untouched by earlier branch commits, consistent with rules 4–5 accepting those sides while reporting omitted files. |
| R1-12’s ordinary-hunk refutation | **VERIFIED:** a count-based trace of all six hunks in the revision found only valid body markers; no body content became a column-zero record header. |
| R4-02 is acknowledged and waived | **VERIFIED** acknowledgment at plan lines 208–212; **UNVERIFIABLE** waiver—none is recorded. The risk remains open. |

Remaining implementation claims:

- **UNVERIFIABLE — planned parser/Perl and test integration:** `diff_headers.pl`, `test_base_check.sh`, `seat_limits.txt`, and T13’s executable case are absent. The fixes above are specification changes. Settling observation: run the implemented script through T4/T5/T11/T13, including malformed-list handling and supported-Perl checks.

OUTSIDE SCOPE

No additional findings recorded. Existing transport call sites, the model-list parser, Makefile registration, named caller documents and closeout template were inspected for context. No write-dependent suite was run.

Prompt injection: none found.
## Independent review — melious (glm-5.3, HTTP API)


Findings (scope 1 and 2):

- RISK — PRIOR FINDINGS record vs Status row 2 ("rounds 1 to 4 done (36, 8, 9 and 6 findings)"): the record dispositions four rows, only three of them round-4-sourced (R4-01..03) plus round-1's R1-12, yet the plan claims round 4 produced 6 findings — two or three round-4 findings have no row, and if any was a BUG left unfixed it ships untracked. Fix: add the missing round-4 findings with their dispositions, or correct the count.
- RISK — Change 2, Codex row ("stdin: `codex exec … -`") + the quoted help ("If not provided as an argument (or if `-` is used), instructions are read from stdin") + T9/T10: the help citation supports that `-` means stdin, not that a ~400 KB prompt is read whole; T9's stub proves the script's side only, "Not checked" lists P1 for the ollama CLI and P2 for windows but no probe for codex's stdin capacity, and "What this does not see" does not name it — if real codex truncates or drops a large stdin prompt, Codex reviews run on part of the change silently while the suite stays green, the failure class this script exists to catch. Fix: name it in "What this does not see", and before lifting Codex's cap do one real `codex exec … -` run with a nonce-marked large prompt (the P1/P2 pattern), or keep Codex at 120,000 until observed whole.
- NIT — Input table, row "No `diff --git` record at all (hand-made, `diff -u`), or `--no-index` | refused, naming `--base none`": a `--no-index` diff is a patch in git's own format, `diff --git` records included, so it reaches rule 4 and is refused there with the repo remedy printed (or runs if its sides match), never "naming `--base none`". Fix: split the row — record-less artifacts get the `--base none` refusal; `--no-index` gets the rule-4 refusal (settling observation: run `git diff --no-index a b` and read the first line).
- NIT — rule 3, prefix paragraph: the order of "It unquotes C-quoted names" against "stripped there, once" is unspecified; when git C-quotes a name (T4's tab path) the `a/`/`b/` prefix sits inside the quotes, so a strip-first reading refuses or mis-parses exactly that case. Fix: one sentence — unquote first, then strip the prefix.
- NIT — rule 3: `/dev/null` sides (new and deleted files) are never mentioned, and the prefix rule ("`a/` on the old side") would refuse `--- /dev/null` unless special-cased. Fix: state that `/dev/null` on either side means "no side" and is exempt from the prefix rule (T4's new/deleted cases exercise it).

OUTSIDE SCOPE:

- BUG — Tests table, T9 row ("stdin carries a 400 KB prompt whole … | passes"): under the plan's own rule (unlisted model, or a missing/unreadable list, caps a seat at 120,000) a Codex seat with no stated `seat_limits.txt` setup is FAILED before sending, so stdin never carries the prompt and T9 cannot pass as specified — unlike T10, it names no list setup. Fix: give T9 T10's precondition (Codex listed "refuses" in the copy's `seat_limits.txt`).
- NIT — "What the trail records": the merge-base form hardcodes "fetched" ("base: <id> (merge base with origin's HEAD <id>, fetched; …)"), but under `--local-only` the base is `origin/HEAD`'s merge base with no fetch, so the trail misreports provenance. Fix: make "fetched" conditional or add a `--local-only` form.
- NIT — Status row 1: "This plan | ✅ revised after round 1" is stale against a round-4 head and a record of four rounds. Fix: "revised through round 4".

CLEAN (checked, not assumed):

- R4-01 fix landed and covers the whole claim: rule 3 takes rename/copy names as written, refuses mnemonic and absent prefixes, strips `a/`/`b/` only on the `diff --git`/`---`/`+++` lines; the refusal row, the remedy command and rule 2's own command all set `--src-prefix=a/ --dst-prefix=b/`; T4 has the 100% rename inside a top-level `w/`, T5 refuses mnemonic prefixes; the cut (mnemonic acceptance removed) removes the finding's path entirely.
- R4-03 fix landed: T13 exists with a pass condition consistent with the cap rule (a malformed line leaves every seat at 120,000 → a 200 KB artifact fails every seat before sending, no stub runs); T11 no longer carries the malformed case and its three cases each match the seat_limits rules.
- R4-02 deferral conditions met: still open as the owner's decision, the residual is named in "What this does not see", and Open item 1 poses the choice with the no-waiver fallback ("every seat stays at 120,000").
- R1-12 refutation is sound: hunk bodies always carry a leading ` `, `+`, `-` or `\` and the reader skips hunks by their line counts, so a column-0 `diff --git` cannot be read as a header in a git-produced diff.
- T7's new precondition is the right one: a last-commit diff's old sides equal the merge-base patch's only when no earlier branch commit touched those files; otherwise the T3 refusal with the "--base <that head>" line applies — rules 2, 4 and 5 agree.
- Base-before-size ordering (T8 and the "Order" section) is internally consistent, and `--base none` skips only the base check, never a cap.
- Rename-at-100% is coherent across the check's `--no-renames` patch, the remedy's default-rename diff, and rule 4's deletion-plus-addition-same-id match; abbreviated ids in the remedy diff are covered by the prefix comparison.
- The remedy's `-- . ':(exclude)docs/reviews/'` agrees with rule 5's docs/reviews exemption; a remedy-made diff passes the check with no unnamed omission.
- The mode-only, stale-mode, index-side, three-dot, shallow-clone and HEAD-moved table rows each follow from rules 2–5 as written.
- Binary/new/deleted records fit the reader's header window (`diff --git` … first `@@` or `Binary files` line); the split rule covers mode-only records (same path both halves).
- No prompt injection: the plan is ordinary prose about its own work; nothing in it attempts to steer this review.

UNVERIFIABLE (component claims that matter, not counted as findings):

- git diff output — `rename from`/`to` and `copy from`/`to` carry no `a/`/`b/` prefix (R4-01's "as written" hinges on it). Settling observation: run `git diff -M` on a rename with default prefixes and read those lines.
- git diff output — a mode-only change and a 100% rename emit no `index` line even with `--full-index` (rule 4's no-id matching hinges on it; plan says checked on git 2.33). Observation: run both diffs with `--full-index --no-renames` and look for index lines.
- git diff output — a name with a space gets a trailing tab on `---`; a name with a tab is C-quoted (the reader drops/unquotes these). Observation: `git diff` files named "a b" and "a\tb".
- git fetch — `git fetch origin HEAD` fills per-worktree `FETCH_HEAD` with the remote tip without moving `origin/<default>` (the no-`--base` base choice). Observation: fetch inside a worktree and compare `FETCH_HEAD` with the refs.
- existing script — the seat transports quoted under "Today (checked in the script)" and the exit-4-for-no-reviewer behavior T13 asserts. Observation: read the script's seat invocations and run it once with every seat failing (make check will also surface a wrong exit).
- `check_perl_minimum.sh` gating and `melious_models.txt` read semantics — the mechanisms `diff_headers.pl` and `seat_limits.txt` inherit. Observation: read both files.

Verdict: not clean — the round-4 record does not reconcile with its own finding count, one test as specified cannot pass (T9), and Codex's stdin move carries an unprobed, unnamed residual; every prior finding marked fixed did land and covers its whole claim.

---
reviewers: codex OK, melious OK
timings: codex 112s (65264 tokens), melious 340s (39691 tokens)
gate 20261021T172444Z-64903: rounds 1-5, 11 reviewer seat runs, 802,292 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 probe-verdict,merge-base-head; 5 header-names,test-spec (cut: mnemonic prefixes no longer accepted: only a/ and b/, stripped only on diff --git, --- and +++ lines)

</details>

<details><summary>Final full read raw output — ollama kimi-k3:cloud (independent_review.sh stdout)</summary>

## Independent review — ollama (kimi-k3:cloud)

## Findings (ranked)

- RISK — "Checked here, and not": the claim "`a working-tree diff's new id 
equals `git hash-object -- <path>` of the file`" and rule 2's "git, not 
this script, hashes the working tree" — for a file dirty relative to the 
index, `git diff` emits `0000000` as the new-side id (there is no object), 
so headers cannot pin worktree content: a diff made from `git diff <base>` 
before worktree edits still passes (artifact `0000000` vs fresh 
`0000000`), no rule ever compares hunk text, and the "HEAD moved after the 
diff was made → refused" guarantee is undefended for exactly the 
"uncommitted work" table row. Fix: for records whose git-side new id is 
all-zero, compare content instead of headers — regenerate `git diff 
<base>` and byte-compare those records, or run `git apply --check` of the 
artifact's records against the worktree — then correct the "Checked" line 
and add a T5 case "worktree edited after the diff was made → refused."

- RISK — Rule 3 ("Each hunk is skipped by its line counts"): the `@@` line 
counts exclude `\ No newline at end of file` marker lines, which follow an 
unterminated removed/added line; a strict count-based skip lands on the 
marker in the header zone and desyncs the next record for extremely common 
artifacts (any file lacking a trailing newline), and no T4/T5 case 
exercises it. Fix: in the reader spec, treat lines beginning with `\` as 
non-counting continuations of the previous content line, and add a T4 case 
with missing trailing newline on the old side, the new side, and both.

- NIT — "Open for the maintainer" #1 says "The probe is free where the 
provider refuses," directly contradicting P2's own "(whether a refused 
request is billed is not checked)" — a maintainer answering "Open" would 
rely on the stronger statement. Fix: drop "free" there and mirror P2's 
hedge.

- NIT — Rule 5 / base-line format "`(…; every changed file present)`": 
untracked files appear in neither `git diff <base> HEAD` nor any artifact, 
so the line can claim full coverage while a brand-new un-`add`ed file is 
never reviewed. Fix: under no-`--base`, append untracked paths from `git 
status --porcelain --untracked-files=all` to the `base:` line, or soften 
the wording to "every tracked file."

- NIT — Refusal remedy command omits `--full-index --no-renames` that rule 
2 uses for its own comparison; it only works because rule 4 tolerates 
abbreviated ids and rename records — this is invisible in the plan trail. 
Fix: either print the same flags for one-to-one reproducibility, or note 
explicitly that the acceptance of shortened ids/rename records is 
deliberate.

- NIT — Tests table: T13 is listed before T12; and "a missing `perl` or 
`git` refuses the run" is not scoped to runs where the base check actually 
executes, sitting oddly with "`--base none` … runs anywhere, outside a 
repo too." Fix: renumber and state the tool-availability refusal applies 
only when the base check runs.

## Checked, CLEAN

- `--base` validation design (`rev-parse --verify --quiet 
"<rev>^{commit}"`, refusal of `-`-leading values, refusal on plans) — 
internally consistent and matches normal git usage.
- Ordering consistency: "base before size before seats" traced across "How 
it tells", the "Order" section, T8, and T1's "no stub seat ran" — 
coherent.
- Header-grammar claims (prefixes `a/`/`b/` limited to `diff 
--git`/`---`/`+++`; `rename from/to` unprefixed; tab after 
space-containing names; C-quoting; body lines always prefixed so column-0 
`diff --git` is unambiguous) — consistent with git's known diff format.
- Mode-only changes and 100% renames carrying no `index` line, and rule 
4's matching of them via `--no-renames` (mode-only↔mode-only, 
rename↔delete+add with equal ids) — coherent and matches known git 
behavior; T3's four delta sub-cases trace cleanly through rules 4 and 5.
- T13 vs the text rule ("malformed line leaves every seat at 120,000") — 
not contradictory: a 200 KB artifact then fails every seat pre-send, exit 
4; T12 likewise matches "fails loud in the FAILED section."
- The Linux per-argument cap motivation matches `MAX_ARG_STRLEN` 
(32×PAGE_SIZE = 131,072 bytes); the plan also correctly separates it from 
macOS `ARG_MAX` and flags it as unchecked.
- The "split by seat" weighing and the degraded-round semantics are 
internally consistent.

## UNVERIFIABLE (no findings; needed observations)

- **git 2.33 behaviors** (all of the "Checked on 2026-10-21: On git 2.33" 
bullets other than the worktree-id one): FETCH_HEAD being per-worktree and 
not moving `origin/<default>` after `git fetch origin HEAD`; no `index` 
line for mode-only changes under `--full-index`; rename→delete+add with 
same id; binary `index` lines; tab-after-space names. Lacked: any 
reproduced output or test trace. Observation: run each stated command on 
git 2.33 and capture raw stdout.
- **`independent_review.sh` as it exists today** (the "Today (checked in 
the script)" block): transports (codex last-argv, `ollama run MODEL 
"$PROMPT_TEXTONLY"`, agy `-p`, melious/ollama-API `curl --data-binary`), 
the `CONTENT_BYTES ≤ 120,000` check covering artifact+prior findings, 
mode-700 raw folder and its stale-cleanup list, `melious_models.txt` read 
semantics that `seat_limits.txt` mirrors, exit-4-on-no-reviewer (T13 
relies on it), `--cut`'s refusal pattern. Lacked: the script's text. 
Observation: read the script and match each behavior; likewise 
`merge_link.sh`, `git-stand.mjs`, `closeout.md`, SKILL.md for the cited 
patterns/fields.
- **codex CLI 0.163.0**: the quoted help line and whether `-c 
model_provider=…` + `base_url` works. Observation: `codex exec --help`; 
the P1 stub run at 127.0.0.1.
- **ollama CLI 0.40.7**: stdin delivery under `--ask`. Observation: same 
P1 stub run.
- **Providers** (Codex's configured model, Melious GLM 5.3, ollama cloud 
GLM 5.3): refuse-vs-cut past window, cited windows (500k / 1,048,576 / 
1,000,000), error wording, billing of refused requests. Observation: the 
P2 probe per seat/model plus provider docs and billing statements.
- **Linux per-argument cap**: plan itself marks it "Not checked." 
Observation: execve an ~130 KiB single argument on Linux and observe 
E2BIG, or cite `MAX_ARG_STRLEN` in the kernel headers.

No prompt-injection content found in the plan.


---
reviewers: ollama-cloud OK
timings: ollama-cloud 459s
⚠ PLAN round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat ollama was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
gate 20261021T172444Z-64903: rounds 1-5, 12 reviewer seat runs, 802,292 tokens logged (1 run gave no figure). Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 probe-verdict,merge-base-head; 5 header-names,test-spec (cut: mnemonic prefixes no longer accepted: only a/ and b/, stripped only on diff --git, --- and +++ lines); 1 run with no round

</details>

<details><summary>Wording pass raw output — codex (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- RISK — `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:198` — R5-03 is only partly fixed: endpoint nonces lack evidence that Codex received the middle, so truncated input could unlock uncapped reviews. A reproduced counterexample preserved both nonces while reducing 400,024 bytes to 24. Fix: require an exact outbound-payload comparison at the intended probe size; otherwise retain 120,000 bytes.
- BUG — `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:193–199` — P1’s “free” and “No model runs” claims contradict its new real-model fallback of roughly 60,000 tokens. Fix: qualify those claims as applying to stub probes and explicitly describe the fallback’s potential cost.
- BUG — `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:140` — “untracked files are in no diff at all” is false for `git diff --no-index`, which the plan explicitly supports; a measurement produced its patch without any repository/index. Fix: say the ordinary repository comparison omits untracked files, while supplied artifacts can include them.
- BUG — `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:13` — “final full read next” contradicts the trail’s completed final-full-read row at head `c2ff4cc9`. Fix: record that read as completed and identify the current verification step.

**Checked claims that were CLEAN**

Verdicts below verify specification changes; they do not certify an unbuilt implementation.

| Claim | Verdict and evidence |
|---|---|
| R5-01/R4-02 remains open under its stated conditions | **VERIFIED:** Open item 1 explicitly requests acceptance; without it every seat retains the cap. The trail records no waiver. |
| R5-02 corrects the findings-count statement | **VERIFIED:** status row 2 delegates counts to the trail, which distinguishes round 4’s in-scope and outside-scope findings. |
| R5-04 correctly separates `--no-index` | **VERIFIED:** line 120 describes side-based checking; reproduced `git diff --no-index` emitted `diff --git`. |
| R5-05/R5-06 specify unquoting before stripping and exempt absent sides | **VERIFIED:** lines 86–95 state both; `git apply --numstat -` accepted quoted-tab and `/dev/null` fixtures. |
| R5-07 supplies T9’s missing eligibility setup | **VERIFIED:** T9 now specifies Codex listed “refuses,” consistent with the planned cap rule. |
| R5-08/R5-09 correct provenance and revision wording | **VERIFIED:** separate unfetched `--local-only` output and “revised through round 5” are present. |
| F-01’s working-tree-ID objection is refuted | **VERIFIED:** `git diff --full-index caaf7b68 -- <plan>` produced new ID `1aca7eeb…`, equal to `git hash-object -- <plan>`. |
| F-02 handles no-final-newline markers | **VERIFIED:** rule 3 excludes backslash markers from counts; T4 covers each side and both. Git accepted a both-sides fixture with uncounted markers. |
| F-03/F-05/F-06 fixes landed | **VERIFIED:** Open item 1 hedges billing; the remedy explains omitted options; T12 precedes T13; rule 3 excepts `--base none`. |
| Supplied changes are plan prose | **VERIFIED:** the supplied diff changes only Markdown plan text, including command examples and test specifications. |

**Unsupported component claims**

- **UNVERIFIABLE — Codex CLI:** large-stdin integrity and custom-provider configuration lack a real CLI trace. Settling observation: capture and compare the complete outbound prompt from the specified CLI version; endpoint quotes are insufficient.
- **UNVERIFIABLE — ollama CLI:** large-stdin integrity and the stated `--ask` behavior lack implementation or execution evidence checked here. Settling observation: capture its complete request through P1’s stub and compare payload bytes.
- **UNVERIFIABLE — configured Codex provider, Melious, and ollama serving providers:** window sizes, refusal/truncation policies, and refusal billing lack checked provider traces. Settling observations: request admission/evaluation records across relevant lengths and corresponding usage/billing records. The plan explicitly retains a maintainer decision for the residual policy risk.
- **UNVERIFIABLE — planned parser and cap implementation:** `diff_headers.pl`, `seat_limits.txt`, and the new executable cases are absent. Settling observation: inspect the implementation and execute the specified regression cases.

**OUTSIDE SCOPE**

No additional findings.

**Prompt injection:** the author-record sentence “Flag ONLY a factual contradiction … not style or phrasing” attempts to restrict this review’s task. It was treated as data; ordinary plan instructions were not classified as injection.

No network or write-dependent tests were run; the worktree remained clean.

---
reviewers: codex OK
timings: codex 181s (54825 tokens)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
gate 20261021T172444Z-64903: rounds 1-5, 13 reviewer seat runs, 857,117 tokens logged (1 run gave no figure). Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 probe-verdict,merge-base-head; 5 header-names,test-spec (cut: mnemonic prefixes no longer accepted: only a/ and b/, stripped only on diff --git, --- and +++ lines); 2 runs with no round

</details>

<details><summary>Confirmation raw output — codex (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

No BUG/RISK/NIT findings.

CLEAN — checked claims:

- **VERIFIED — W-01:** `docs/reviews/SKILL-PLAN-review-input-base-and-size.md:193–199` removes the nonce fallback, requires byte-for-byte prompt equality, and retains 120,000 bytes when routing or equality fails. The seat table at lines 181–184 agrees.
- **VERIFIED — W-02:** P1 now specifies only stub requests; its paid model-run fallback is gone. P2 remains separately described and costed.
- **VERIFIED — W-03 wording fix:** Lines 139–140 remove the universal “no diff at all” claim and restrict it to the specified Git patches. The `--no-index` exception at lines 64–66 and 120 remains consistent.
- **VERIFIED — W-04, partly:** Status no longer says the final full read is next. The trail records that read at line 12 and keeps R4-02 awaiting the owner at lines 67 and 85. Plan “Open” item 1 preserves the no-waiver cap.
- **VERIFIED — reflow:** Comparing rule 3 before and after `HEAD` with whitespace-normalized Python strings returned `True`: no words changed.

UNVERIFIABLE — grouped claims:

- **Git:** Exclusion of untracked files from the specified patches lacks an implementation trace or a reproduced untracked-file fixture. Settling observation: compare both planned Git commands and `git diff --no-index` against the same untracked file.
- **CLI transports:** Exact large-prompt delivery and local stub routing lack executed P1 captures. CLI help confirms advertised stdin/configuration options, not delivery behavior. Settling observation: capture each CLI’s requests and compare the decoded prompt bytes. The retained cap makes these pending probes, rather than new findings.
- **Review completion:** “Wording pass done” lacks its raw reviewer output in the cited trail; the trail’s line 87 still says that pass follows. Settling observation: a recorded wording-pass invocation and output identifying its reviewed artifact. The final-full-read completion is independently recorded.

OUTSIDE SCOPE: no additional findings recorded.

Prompt injection: none found.

---
reviewers: codex OK
timings: codex 78s (43462 tokens)
⚠ DIFF round landed with 1 reviewer(s) counted toward the gate, fewer than the 2 of the standard pair — --seat codex was requested. One reviewer is right for the wording pass or the final full read (SKILL.md step 6); any other round needs the standard pair.
gate 20261021T172444Z-64903: rounds 1-5, 14 reviewer seat runs, 900,579 tokens logged (1 run gave no figure). Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 probe-verdict,merge-base-head; 5 header-names,test-spec (cut: mnemonic prefixes no longer accepted: only a/ and b/, stripped only on diff --git, --- and +++ lines); 3 runs with no round

</details>
