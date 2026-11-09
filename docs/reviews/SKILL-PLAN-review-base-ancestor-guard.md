# Plan: refuse a `--base` that is not on the branch

A guard in `skills/independent-review/scripts/independent_review.sh`. Plan only: the build waits
for the maintainer's go and runs in its own session (Sonnet, high). Not risky work (no server,
user data, login, money, deletion or schema), so no red team.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-11-09 | this file |
| 2 | PLAN gate, Normal depth | ⏳ | `REVIEW-plan-2026-11-09-base-ancestor-guard.md` |
| 3 | The maintainer's go | ⏳ | — |
| 4 | Build: guard, two doc sentences, tests (one PR) | ⏳ | — |
| 5 | DIFF gate | ⏳ | — |

## What and why

With `--base <rev>`, the BASE CHECK compares the diff with git's own patch from `<rev>` and
nothing else; only a run with no `--base` fetches origin and takes the merge base. So a two-dot
diff, `git diff origin/main`, sent with `--base origin/main`, matches itself and passes, even
after main has moved past the branch. Every commit main has and the branch lacks then reaches
the reviewers as removed.

That happened on 2026-11-09 in a session closing row 2.1 R5 of a launch plan (transcript
`3ee41cdd`, read for this plan, E2). Its branch left main at `934bcc12`. At 08:53Z it merged
origin/main as it then stood (`a7617e4`); main then moved on to `a4934f29`. Its round 5, at
about 09:05Z, sent `git diff origin/main` with `--base origin/main`, a `--verify` round. The
run printed `base: a4934f29… (--base origin/main)` and passed, and the reviewers read another
session's proposal file as part of the change. SKILL.md step 2
already says to send `<base>...HEAD` with no `--base` for the whole change; the brief counted 12
sessions in 5 days passing `--base origin/main` anyway (not rechecked here).

**The design differs from the brief.** The brief exempted every `--verify` run, so that the
merge link after a rebase keeps working. But the incident's round 5 was itself a `--verify`
round (E2), so that exemption would have let the one confirmed case through. The guard below
exempts a narrower case instead: a `--verify` run whose base is on neither HEAD nor the default
branch, which is what the old reviewed head is after a rebase (E1, case 7).

## How

In the base check, in the branch that handles `--base <rev>` (after `base_id` is resolved,
before `diff_headers.pl` runs), with `git merge-base --is-ancestor`:

1. `base_id` is an ancestor of HEAD (exit 0): go on as today.
2. Exit 1, no `--verify`: refuse (exit 2).
3. Exit 1, `--verify`, and `base_id` is an ancestor of `refs/remotes/origin/HEAD` (the local
   ref, no fetch): refuse. A verification round names the last reviewed head, never the
   default branch.
4. Exit 1, `--verify`, `base_id` not an ancestor of `refs/remotes/origin/HEAD`: go on (the merge
   link after a rebase).
5. Exit 1, `--verify`, and `refs/remotes/origin/HEAD` not set: refuse, saying the script cannot
   tell a merge link from a diff against the default branch, with the command that sets it:
   `git -C <top> remote set-head origin --auto`.
6. Any exit other than 0 or 1, from either call: refuse, quoting git's exit code.

The refusal in 2 and 3 follows the mismatch refusal's style: what is wrong, then the commands.

```
Base check: --base <BASE> (<sha>) is not on this branch: HEAD does not contain it, so a diff
from it shows every commit HEAD lacks as removed.
For the whole change, drop --base and make the diff from the merge base (three dots):
  git -C <top> diff --no-ext-diff --no-color --no-textconv -M --src-prefix=a/ --dst-prefix=b/ <default>...HEAD -- . ':(exclude)docs/reviews/' | <this script> - <your other options>
For a delta, name the last reviewed head, a commit on this branch: --base <last-reviewed-head>.
```

`<default>` is `git symbolic-ref --short refs/remotes/origin/HEAD` (such as `origin/main`), or
the literal `origin/<default-branch>` when that ref is not set. Case 3 adds one line before the
commands: "A verification round names the last reviewed head, not the default branch."

Docs, one sentence each: SKILL.md step 2, after "passes `--base <the commit it starts from>`"
(lines 148 to 151), and the script header's `--base <rev>` bullet (lines 127 and 128), saying
the base must be on the branch, except a merge link after a rebase. No other caller needs a
change: `website-review` says "a diff of only some commits names its start with `--base
<commit>`", which still holds.

What it does not catch: a `--verify` round sent with `--base origin/<a non-default target
branch>` (case 4 lets it through; such PRs are rare here), and a stale base that is still on
the branch (the reviewers then see main's merged commits as added, not removed).
`sweep_claims.sh --base` is a separate script and already takes the merge base itself (E1,
case 9), so it is unchanged.

## How it is tested

New cases in `test_base_check.sh`, which drives the script the way a caller does (a throwaway
repository, a bare origin, a stub codex). In a repository where main moves past the branch:

| Id | Run | Expected |
|----|-----|----------|
| T9a | two-dot `git diff origin/main HEAD`, `--base origin/main` | exit 2, "is not on this branch", the three-dot command naming `origin/main...HEAD`; no reviewer ran |
| T9b | three-dot `git diff origin/main...HEAD`, no `--base` | exit 0, the reviewer ran |
| T9c | the command T9a printed, run as printed, then sent with no `--base` | exit 0: the remedy works |
| T9d | T9a's diff with `--verify prior.md --base origin/main --round 2` (the incident) | exit 2, the verification-round line |
| T9e | after a rebase, `merge_link.sh` sent with `--verify --base <old reviewed head>` | exit 0, the reviewer ran |
| T9f | T9e's diff and base without `--verify` | exit 2 |
| T9g | T9e with `refs/remotes/origin/HEAD` deleted | exit 2, names `remote set-head origin --auto` |

The existing cases must stay green unchanged: they pass `--base` with reviewed heads and
merge bases. The build also runs `mutation-check` on the guard: deleting it must fail T9a, T9d
and T9f; exempting every `--verify` (the brief's design) must fail T9d; dropping the exemption
must fail T9e; a two-dot remedy must fail T9c. `make check` runs before each review round.

## Evidence

E1, run 2026-11-09 on a throwaway repository with the current script (croftweaver `d0f5c89e`)
and a stub codex; the script and its full output go to the reviewers as `--evidence`. "anc"
is `git merge-base --is-ancestor <base> HEAD`; "on main" is the same against
`refs/remotes/origin/HEAD`.

| Case | Run | Script exit today | anc | on main | Under this plan |
|------|-----|-------------------|-----|---------|-----------------|
| 1 | two-dot, `--base origin/main`, main moved | 0 | 1 | 0 | refused (2) |
| 1v | the same with `--verify` | 0 | 1 | 0 | refused (3) |
| 2 | three-dot, no `--base` | 0 | — | — | unchanged |
| 3 | delta, `--verify --base <reviewed head>` | 0 | 0 | | unchanged (1) |
| 4 | wording pass, `--base <reviewed head>` | 0 | 0 | | unchanged (1) |
| 5 | working-tree diff, `--base HEAD` | 0 | 0 | | unchanged (1) |
| 6 | merge link after merging main, `--verify --base <reviewed head>` | 0 | 0 | | unchanged (1) |
| 7 | merge link after a rebase, `--verify --base <old reviewed head>` | 0 | 1 | 1 | passes (4) |
| 8 | PR to a non-default branch, `--base <its merge base>` | 0 | 0 | | unchanged (1) |
| 9 | `sweep_claims.sh --base origin/main`, main moved | 0, "0 sentences … in 1 file" | 1 | | not touched |

E2, the incident, read from the session's transcript, its saved round outputs and the history
of the repository it worked in. Round 5's options: `--diff --base origin/main --depth normal --round 5
--earned-by … --cut "…" --verify $S/r5-r4.md`; its output file holds `base:
a4934f29f2bb1ae1f2e27ffd8b91c9b91a9e7785 (--base origin/main)`; its diff names two
files: another session's proposal and the change's own plan. The branch's merge
commit `d80098f` has parents `ce1baa6` and `a7617e4`; `git merge-base --is-ancestor a4934f29
5dbc8f99` (the branch's next commit) exits 1, and `934bcc12` exits 0. Rounds 1 and 2 of that
gate printed base `934bcc12`, then on the branch: the guard would have let them pass, rightly.

## Judgment, and the strongest case against

Verified: every row of E1 and E2. Judgment: that a rebase merge link is the only legitimate
`--base` off the branch (E1 found no other, and SKILL.md names no other), and that refusing
beats a warning here.

Against: the maintainer prefers warnings to refusals in the review process, and approved the
brief's simpler design, not this one. The answer: SKILL.md already tells sessions not to do
this, and the brief counted 12 that did; a line people read past is what failed. A wrong
refusal costs one rerun and prints its fix, while the misfire cost a round on another
session's file. Data that would change this: a legitimate run, found in transcripts, that
sends a base off the branch without `--verify`, or a rebase merge link whose old head is on
the default branch.

Cost: the PLAN gate at Normal depth, Codex and GLM 5.3; a recent plan round logged about
200,000 tokens, so 2 to 4 rounds is roughly 0.4 to 0.8 million tokens (an estimate). The build
is about 20 lines of script, two sentences and seven test cases.
