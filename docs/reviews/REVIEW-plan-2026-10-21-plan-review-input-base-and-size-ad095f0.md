# PLAN review — plan/review-input-base-and-size — check a review diff's base, and lift the 117 KB limit

Base `6681e7be` · depth: Normal (a plan for a guard script's logic; the owner's rule keeps tooling plans at Normal) · verdict: OPEN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY and GATED-THIS-DIFF do not apply to a PLAN gate

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `ad095f01` | full plan | codex-cli 0.163.0, gpt-6.1-sol, effort high (config), read-only · Melious glm-5.3, HTTP API, text only · fresh-eyes: Claude Code sub-agent, Sonnet, read-only by instruction | codex 379 s, 102,724 · melious 238 s, 29,217 · fresh-eyes 650 s, 244,798 | 8/17/11 raw (codex 6/5/0, melious 1/4/4, fresh-eyes 1/8/7); 28 after dedup: 7/12/9 |

UNVERIFIABLE entries, round 1: 17 asked (codex 3, melious 6, fresh-eyes 8); 3 confirmed and made findings (the fetch refspec, ollama's missing `num_ctx`, `hash-object --path`); the rest are the plan's own "not checked" list or probes P1 and P2.

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

Waivers and deferrals: none.
Follow-ups: a BUGLOG row for local ollama cutting a prompt silently under `--local-only` (named in the plan, outside its scope).
Notes: the fresh-eyes seat wrote and removed one empty scratch file in `/tmp` (its report says so); nothing in the repo changed. R1-13 merges melious's NIT into fresh-eyes's RISK. The claims sweep ran before round 1 (`sweep_claims.sh --file`); one claim fixed before the round (`ad095f01`).

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
