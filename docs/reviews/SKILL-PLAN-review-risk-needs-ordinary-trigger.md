> **Parked after an inconclusive trial (2026-11-22).** The live Codex trial missed its bar, but both test cases had an ordinary reading; see `docs/reviews/risk-trigger-trial/RESULT.md`. Do not build this plan as written.

# Plan: independent-review — a RISK must name an ordinary input or change

Base `origin/main` c0477040 · review depth: PLAN gate, Codex and GLM 5.3 (it changes the prompt
every reviewer of every user gets) · red team: none (no user data, login, money, deletion or
schema).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | This plan, reviewed until no BUG is open | PLAN gate: round 4 had no BUG; its RISKs and NITs are fixed here by hand (no round 5) | — |
| 2 | The maintainer's go to build | not given | — |
| 3 | Build: the prompt, its copy in `SKILL.md`, the tests, the live trial | not started | — |

## What

`PROMPT_CORE` in `skills/independent-review/scripts/independent_review.sh` (copied word for word
into `SKILL.md`, under "The strict review prompt (both gates)", which `check_prompt_sync.sh` holds
equal) defines a RISK as "breaks on normal change, a guard that cannot fire, or an unsupported
load-bearing claim whose consequence is named". Reviewers also raise very rare cases as RISKs (two
unlikely things at once, an input no caller sends). `SKILL.md` step 6 counts an in-scope RISK
whose fix changes what runs as a reason for another round, so a rare case can cost a round.

The change, in four parts:
1. A RISK of the "breaks on normal change" kind names the ordinary use or ordinary change that
   produces it. Three kinds stay RISKs however rare: a silent wrong result (wrong output with no error and no warning), a security
   hole or data loss, and a guard or test that cannot fire. An unsupported load-bearing claim
   already needs its consequence named and is unchanged. A result that is wrong now stays a BUG;
   the change touches RISK only.
2. Any other rare case is still reported, on a line that starts `- NIT (rare):` and says what it
   would cost. Silence is not coverage, so leaving it out is a failure of the prompt, not a
   saving. The guard findings that `PROMPT_PLAN` asks for keep their own rule and are not made
   `(rare)`.
3. `SKILL.md` step 4 (consolidate) changes in two places. Its *follow-up* bullet today covers only
   a RISK or NIT a verification round raised outside its scope; it is widened by one clause to
   take a `(rare)` NIT from any round. Such a NIT is listed for the owner, blocks nothing and
   needs no sign-off (the bullet's own behaviour), so the user's cost does not move from a round
   to a waiver. Step 5's "fixed, refuted, waived or follow-up" already allows the status. And a `(rare)` NIT that two different seats of the same round raise is treated as a
   RISK: a priority override, because two seats naming the same case is a reason to look again,
   not proof it is ordinary. The seats are the script's seats and the fresh-eyes pass; the same
   seat repeating itself in a later round does not count. With one seat (a round the maintainer
   chose to run Codex alone, or one where a seat failed) there is no such net; the caveat goes
   into part 4's "what limits it", so it ships with the rule. Where a `(rare)` NIT could also be read as in scope for a fix, the widened
   bullet wins: it is a follow-up unless two seats raised it.
4. `references/rationale.md` gets a short dated section: the rule, why, and what limits it.

## Why

The maintainer's own sessions re-sort such RISKs when sorting findings (a working rule outside this
repo, 2026-10-23); the repo shows the cost: `git grep -ic 're-sorted: rare' -- docs/reviews`
counts 17 files with 31 such lines, and `docs/BUGLOG.md` holds 6 `re-sorted` lines. A user of the
kit has no such rule: their host fixes the rare case and runs the round. This moves the sorting to
the reviewer's prompt, where every user gets it. The cost is the opposite error: a real rare
problem demoted to a NIT and lost. Parts 1 and 3 are the guard against that, and the trial below
is the check that the classification works; the step 4 override for a case two seats raise is
not tried (see the trial section). The counts show how often rare RISKs were raised, not how many
rounds they cost.

## How

Edit the `PROMPT_CORE` severity lines and the same lines in `SKILL.md`; add the two step 4
sentences and the rationale section; release notes get one line. `PROMPT_TOOLED`,
`PROMPT_TEXTONLY`, `PROMPT_AGY` and `PROMPT_PORTABLE` begin with `${PROMPT_CORE}` and need no edit;
`PROMPT_PLAN` is a paragraph added to them, not a copy, and is not edited either.
`--content` mode has its own prompt (`skills/website-new-page/references/content-review.md`,
"The content review prompt"), which defines BUG, RISK and NIT in page terms and has none of the
words above; it is out of scope, and `check_prompt_sync.sh` holds only its finding format.
The validator needs no code change: a probe of the script's `looks_like_review` on 2026-11-22
accepted `- NIT (rare): …` with and without the word "cannot" in its cost sentence (both carry a
cost sentence), and rejected the
same text with no leading dash (outputs quoted in the evidence file, READ 15).

## How it is tested

- `check_prompt_sync.sh` fails if only one copy is changed (it self-tests on mutated copies, in
  that script's own self-test: it mutates a copy of `SKILL.md` and requires the check to fail
  (`fires`, lines 117 to 127). The build step runs it and records the output. It cannot catch
  the same wrong wording in both. The trial catches a wrong new wording; it does not test the
  unchanged clause on the same line (the load-bearing-claim kind), so a typo there, the same in
  both copies, passes every check. The build diff is reviewed for that, and its commit changes
  only the words this plan names.
- `test_failed_tier_report.sh`: its stub Codex saves the prompt a run really sends (lines 58 and
  63), and cases such as the `noverify` ones read it with `grep` (lines 694 to 697). The build adds
  an assertion of that kind: the saved prompt holds the new severity words. It fails on the code
  before the change. It shows delivery, not that a model obeys.
- `test_looks_like_review.sh`: three cases, accepted: a review whose only finding is a
  `- NIT (rare):` line with a cost sentence containing "cannot", the same line without it, and a
  review where that line sits among a BUG and a RISK. They pass before the change too (the probe
  above covers the first two); they guard the validator against a later tightening.
- Live trial, Codex, three runs per cell; fixtures are committed with the run outputs. Cases:
  - T1: an ordinary-use bug plus a case that needs two unlikely things at once. Pass: in at least 2
    of 3 runs after the change, the ordinary bug is found as BUG or RISK naming its input and the
    rare case is a `- NIT (rare):` line (the cell checks that the ordinary bug is not demoted below
    RISK; it does not check BUG against RISK); a run that leaves the rare case out fails that run. Before
    the change, the rare case should be a RISK in most runs; if it is not, the trial shows
    nothing and the plan is dropped.
  - T2, T3, T4: one rare case each of a silent wrong result, a security hole or data loss, and a
    guard that cannot fire. Pass: all 3 runs report it as BUG or RISK. Any demotion fails the
    trial.
  - T5: a rare case that fails loudly (an exception with a clear message). Pass: `- NIT (rare):`
    in at least 2 of 3 runs, which shows that the line is drawn and "silent wrong result" is not a
    wide gate. A failed T5 follows the T2 to T4 rule: reword once, run again, a second fail drops
    the plan.
  - One of T1 to T5 is built from a real diff in a trail that holds a `re-sorted: rare` line, not
    written by hand.
  A failed T1 (the ordinary bug missed, or the rare case left out in 2 of 3 runs) means the new
  wording makes the reviewer lazier, and the plan is dropped. A failed T2 to T4 means the wording is too weak: reword once and run again; a second fail drops
  the plan. The trial covers one seat (Codex). It does not test the two-seat part of step 4 (the
  override for a case two seats raise), which is a rule for the host and rests on the argument in
  part 3; the other seats get the same words and are not tried, and the release note says so. Cost: 5 cases × 3 runs after, and T1 × 3 before, all on
  small inputs, about 18 Codex runs.

## Rollback

One revert of the build commit: the wording in both copies, the step 4 sentences and the test
changes go together, so no test is left failing. No stored data depends on the wording; reviews
already recorded keep their labels.
