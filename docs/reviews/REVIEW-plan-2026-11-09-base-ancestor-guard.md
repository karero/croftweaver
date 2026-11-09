# PLAN review — branch `claude/plan-base-ancestor-guard-4c9cae` — refuse a `--base` not on the branch

Plan: `docs/reviews/SKILL-PLAN-review-base-ancestor-guard.md`. Evidence sent every round with
`--evidence`: `docs/reviews/EVIDENCE-review-base-ancestor-guard.md`. Depth: Normal (a plan for
a guard script's logic; no High-row item, so no red team). Seats: Codex and GLM 5.3 on melious.

Checks before round 1: `make check` on the round-1 tree failed one check only, `T5 ... in under
6 seconds (took 7s)`, a timing check, with the load average near 700. `test_base_check.sh`
alone then passed (99 ok, 0 FAIL, exit 0). The only file added since, the evidence file, passed
`check_clean.sh`. No full rerun before round 1.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `e70e090a` | the whole plan | Codex alone; melious out of balance (no rerun owed, owner's rule 2026-10-27) | codex 126 s, 37,007 | 1 / 2 / 0 |
| 2 | `b440e17b` | the whole plan, `--verify` round 1's findings | Codex alone (`--seat codex`), melious still out of balance | codex 109 s, 67,146 | 0 / 0 / 0 |
| final read | `b440e17b` | the whole plan, every cited line read against the repo | a host subagent (fresh context) | 243 s, 146,957 | 0 / 1 / 2 |
| 3 | `af42364e` | the whole plan, `--verify` the final read's findings | Codex alone (`--seat codex`), melious still out of balance | codex 120 s, 51,318 | 1 / 0 / 0 (outside the changed sections) |

Fresh-eyes, owed in round 1 at Normal depth, was not run; the final full read is the only
host read in fresh context, and it came after round 2.

## Round 1 findings

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| A1 | BUG | Case 3's remedy says to drop `--base`, but a `--verify` run with no `--base` is refused (script lines 610 to 614), so the fix it prints fails | fixed: case 3 prints its own refusal, reusing the delta command and merge-link lines of the existing `--verify`-without-`--base` refusal through one helper |
| A2 | RISK | "On neither HEAD nor main" does not prove a merge link: a `--verify` run with another branch's head also passes; the docs sentence overstated the exception | fixed: the plan, case 4 and the docs sentence now describe the rule of thumb; "What it does not catch" names another branch's head |
| A3 | RISK | No test runs case 3's printed remedy | fixed: T9d now checks the refusal text, and the new T9d2 runs its delta command and expects the reviewer to run; a mutation printing case 2's remedy in case 3 must fail T9d and T9d2 |

Also reworded: "Verified: every row of E1 and E2" now reads "Run or read by me", after Codex
marked the claim UNVERIFIABLE (it saw outputs, not reruns).

## Final read findings

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| F1 | RISK | Case 2 refused every base off the branch without `--verify`, but the wording pass after a rebase sends the delta since the old reviewed head with `--base <that head>` and no `--verify` (closeout.md, the prose-only re-gate; an empty `--verify` file is refused, script line 399), so the guard would refuse a use SKILL.md names | fixed: the default-branch test now applies to every run; a base on neither HEAD nor the default branch goes on with or without `--verify`, and the two remedies are told apart by `--verify`; T9f now runs the wording pass after a rebase and expects exit 0; a new mutation (exemption only for `--verify`) must fail T9f; E1 gains row 7w |
| F2 | NIT | The whole-change refusal gives no remedy for a PR to a non-default branch (E1 case 8) | fixed: one line naming `--base <its merge base with that branch>` |
| F3 | NIT | "What it does not catch" omits that cases 2 to 4 test the local `refs/remotes/origin/HEAD`, so a newer main base (a local `main` ahead, `FETCH_HEAD`, a pasted SHA) passes as case 4 | fixed: named there |

F1 changes what the guard does, so round 3 verifies it.

## Round 3 findings

Round 3 confirmed F1 to F3 fixed, and found one BUG outside the changed sections.

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| C1 | BUG | Judgment still said a rebase merge link is the only legitimate `--base` off the branch, which the wording pass after a rebase (closeout.md, E1 case 7w) contradicts | fixed: Judgment names both, the old reviewed head sent as a merge link or as a wording pass |

C1 is a prose fix to a claim, so the wording pass checks it.

## Wording pass

| Pass | Head | Artifact | Reviewer | seconds, tokens | BUG/RISK/NIT |
|------|------|----------|----------|-----------------|--------------|
| 1 | `06ebae15` | the plan's delta since `af42364e`, `--diff --wording-pass --base af42364e` | Codex alone | codex 105 s, 44,211 | 1 / 0 / 0 |
| 2 | `2defa605` | the plan's delta since `06ebae15`, `--diff --wording-pass --base 06ebae15` | Codex alone | codex 1,880 s (machine load), 43,975 | 0 / 1 / 0 |

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| W1 | BUG | C1's fix still claimed an exhaustive list ("the only legitimate"), which an ordinary verification delta after an amend contradicts: SKILL.md asks for the last reviewed head without limiting it to rebases | cut: Judgment no longer lists the uses; it says only that a legitimate base off the branch is never on the default branch, being a reviewed head the branch has since rewritten. The guard was right already: an amended head is on neither, so case 4 lets it through |

The same claim came back twice (C1, W1), so the second fix is a cut, not a patch.

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| W2 | RISK | "Never on the default branch" is unsupported: E1 shows one rebase shape, the amend was not run, and a reviewed head that later lands on the default branch would be refused | fixed as wording: Judgment now calls it a rule of thumb; E5 runs the amend (on neither, passes) and the wrong-refusal shape (on main, refused); "What it does not catch" names that shape and its way out. The guard's design is unchanged, so no further pass (SKILL.md 6(b): a RISK whose fix leaves the meaning unchanged is wording) |

## Close

CLEAN 2026-11-09 at the commit that adds this section: no BUG or RISK open. Every round stood
on Codex alone (melious out of balance; owner's rule 2026-10-27); fresh-eyes was skipped in
round 1 and the final full read stood in for a fresh-context read after round 2. The gate
script logged 243,657 tokens over six seat runs; the final read (146,957) is not in that
figure, so the total is about 390,000. The last wording fix (W2) was not shown to a reviewer.
make check: round 1's run failed only the T5 timing check under a load near 700; round 2's run,
on `b440e17b`, passed (exit 0, no failing line). Every commit since touches only `docs/reviews/`,
and `check_clean.sh` passed on each.
