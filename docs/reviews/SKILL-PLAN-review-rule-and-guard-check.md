# Plan: independent-review — a no-BUG round's open RISK, a bug-log row, and a question about guards

Base `origin/main` e0be6661 · branch `skill/review-rule-and-guard-check` · review depth: Normal (an
instruction file and a review prompt; nothing in the High row) · red team: none (no user data,
login, money, deletion or schema).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | A no-BUG round's open RISK is fixed and earns a round, not an owner decision | planned | — |
| 2 | Bug-log row: Codex refuses a prompt that is not valid UTF-8 | planned | — |
| 3 | The plan prompt asks about the guards a plan proposes | planned; build waits for the owner's go | — |
| 4 | `make check`, then the DIFF gate at Normal | planned | — |

## 1. A no-BUG round's open RISK

**Why.** The owner's rule, 2026-10-22: "Try to reduce the number of asks to me for a review. A
review can run really anytime until it's clean. Yes we want to avoid rounds over 5, but if required
let it run another round and another." SKILL.md step 6(b) still says the opposite: "A round that
finds no substantive BUG ends the rounds: open RISK/NIT go to the owner as ONE decision (fix
locally … or waive)".

**What changes.**
- **SKILL.md 6(b).** "After round 3, a round is earned only by the previous round finding a
  substantive BUG" becomes: earned by a substantive BUG **or by an in-scope RISK whose fix changed
  what runs or what someone acts on** (the test step 6 already uses for an owed round). Such a RISK
  is fixed and the next round runs with `--earned-by <its kind>`, under the same cut rule. A round
  with neither ends the rounds: its NITs are fixed or refuted without another round ((a2)), wording
  goes to the wording pass. New sentences: aim to finish by round 5; don't ask the owner whether to
  run the next round; ask only for what the owner alone gives — a RISK waiver, a BUG deferral
  (step 5), a change of scope, and, past round 8, the decision 6(b) already names (kept as it is).
  "Name each round past 3 and the BUG that earned it" becomes "the BUG or RISK".
- **SKILL.md step 8.** After "Never run rounds silently back-to-back": the update is a report, not
  a question; an owed or earned round runs without waiting for an answer.
- **Other places that state the old rule:** `references/rationale.md` line 374 ("past round 3 only
  a substantive BUG earns a round") and `references/closeout.md` line 71 ("rounds past 3 with the
  BUG") get "BUG or RISK"; the script's header (lines 77–78, 87–88: "a substantive BUG in the round
  before") gets "a substantive BUG or a fixed in-scope RISK". `rationale.md` gains a short dated
  section: the rule, why it was not done before (the 2026-09-26 reading: RISK counts never reached
  zero while each round re-read the whole change), and what bounds it now (verification rounds see
  only the fixes; an out-of-scope RISK is a follow-up; only a RISK whose fix changed what runs earns
  a round; a kind that comes back needs a cut; past round 8 the owner decides).
- **Left as they are, and why:** the script's round-4 refusal names "the kind of finding", which
  covers a RISK; its past-round-8 notice is the kept owner decision; step 7's "take the open items to
  the owner" follows a stop for non-convergence, which is a scope or redesign call the owner keeps;
  `rationale.md` line 465 and the section around it are a dated record of 2026-09-26; the review
  trails are records. `test_round_checks.sh` pins messages, not this rule (searched: no case names
  "substantive BUG" or the owner decision).

## 2. Bug-log row: Codex and a prompt that is not valid UTF-8

One row in `docs/BUGLOG.md`'s format (Found, Where, What, Category, Impact, Effort, Status), status
`open`: Codex refuses a prompt that is not valid UTF-8, on stdin and on argv, so a diff or plan
holding a Latin-1 file fails its Codex seat. Source: #378's trail
(`docs/reviews/REVIEW-diff-2026-10-22-feat-review-seat-limits-bbe051f.md`, C4-04 and Follow-ups).
Re-checked here, 2026-10-22: `printf 'Say OK. caf\351\n' | codex exec --skip-git-repo-check -s
read-only -` with codex-cli 0.163.0 printed "Failed to read prompt from stdin: input is not valid
UTF-8 (invalid byte at offset 11)". How the script reports it was not re-run (the trail's account).
The fix the row names: make the prompt valid UTF-8 before any seat gets it; it changes what
reviewers read, so it gets its own plan.

## 3. The plan prompt asks about the guards a plan proposes

**Why.** The owner's idea, after a security fix in another of his repositories (2026-10-22): "most
of F1's code rounds went into the tripwire test, not the fix. Next time, I'd ask the plan review
whether a static guard can deliver what the plan claims, before anyone builds one." That plan
proposed a test that reads two source files as text and bans some names, and claimed the tripwire
"guards its source". Its PLAN gate (High: six rounds, a final full read, a red team) saw the gap
more than once: a red-team RISK that the source-text ban missed a bypass, a NIT that it fired "only
on the literal pattern", another that a static file-content assertion "cannot express" what the plan
meant. Each fix the findings asked for made the check longer or more exact: another banned name, an
exact list of call sites, planted bypasses as tests. None of the trail's findings on the tripwire
asked whether the route tests already did its job, or proposed dropping it. The DIFF gate
then spent rounds 1 to 4 on that guard (a BUG each round: spaced, bound and pieced-together
spellings got past it; a syntax-tree rule replaced the text match in round 3 and was beaten in
round 4), and the owner closed it as "an ordinary-mistake guard and the route tests are the real
check". (Read from both trails on 2026-10-22; the token figures are that session's report, not
checked.) So the question has to reach the plan, and its answer has to be a cut, not a longer list.

**Where it goes.** In the prompt, as one paragraph every seat gets at a PLAN gate, and one sentence
in SKILL.md so the fresh-eyes pass gets it too. Not a host precondition: the host wrote the plan and
shares its blind spot, which is what the reviewers are for. Not in `PROMPT_CORE`: that text is the
same for both gates and already calls "a guard that cannot fire" a RISK; what a plan needs on top is
the question whether a guard nobody has built yet can deliver what the plan credits it with.

**What changes.**
- `scripts/independent_review.sh`: `PROMPT_PLAN`, empty for a diff, set after `TYPE` is known and
  added to the `readonly` line. Each of the four tier prompts gets `${PROMPT_PLAN}${PROMPT_VERIFY}`
  where it has `${PROMPT_VERIFY}` now, so a diff's prompt stays byte for byte what it is, and in a
  verification round the scope paragraph still comes last. The text:

  > GUARDS THE PLAN PROPOSES. For each guard the plan proposes as protection — a test, a tripwire, a
  > check in CI, a lint rule, an assertion or a refusal in code — ask what it can catch and what gets
  > past it, whether it would fail if the behaviour it protects broke, and whether a cheaper check,
  > or none, would do as well. A check that reads source text or syntax sees only the spellings it
  > lists. A guard the plan credits with more than it can catch, or one that cannot fail when its
  > behaviour breaks, is a RISK: name what gets past it, and fix the claim, not the list: narrow the
  > claim to what the guard catches, test the behaviour where it is used, or drop the guard.
  > Banning one more spelling is a patch, not a fix. Where a cheaper check, or none, would do, that
  > is a NIT naming it. List the guards you checked on your CLEAN line. If the plan proposes no
  > guard, write nothing about guards.
- SKILL.md, "The strict review prompt", last paragraph: at a PLAN gate the script adds
  `PROMPT_PLAN` too; the fresh-eyes pass gets it.
- `references/rationale.md`: a short dated section with the evidence above, anonymised as the file
  already does for the owner's other repositories.
- No new textual guard in `check_prompt_sync.sh` for the new variable. Applying the paragraph's own
  question: the test below fails if a tier drops it or a diff gets it; a textual check would add a
  guard of the kind whose own comments in that file record evasions found up to round 13, to cover
  the two tiers the test does not reach.

**How it is tested.**
- **T1, in `test_failed_tier_report.sh`, beside case 25 (through the script's real entry):** a plan
  run: the Codex and ollama prompts (the tooled and text-only tiers) hold the paragraph's first
  line; with `--verify`, it comes before "VERIFICATION ROUND."; a diff run: neither prompt holds it.
  Fails if a tier drops `${PROMPT_PLAN}` or a diff gets it. Cannot catch: the Antigravity and paste
  tiers (not stubbed; they hold by reading the four assignments), or whether a reviewer acts on it.
- **T2, one live run, after the build:** `--seat codex --plan` on the security fix's plan at the
  commit that closed its PLAN gate (`1ec9cf1`, the trail's commit), in a `git archive` copy of that
  commit outside this repo. Pass: a RISK that the tripwire cannot deliver the protection the
  plan credits it with, whose fix narrows the claim, leans on the route tests or drops the guard,
  not one that bans more spellings. The control is that plan's own PLAN gate, run on the old prompt,
  whose findings on the tripwire each asked for a longer or more exact check. About 100k tokens.
- **T3, one live run:** `--seat melious --plan` on sections 1 and 2 of this plan alone (they propose
  no guard). Pass: no entry about guards. About 20k tokens.
- `make check` green; then the DIFF gate.

**What is checked and what is judgment.** Checked: the old rule's text and every place it appears
(searched above); the Codex refusal; the two trails. Judgment: that a RISK-earned round costs less
than an owner question (the counter-argument: the 2026-09-26 reading found RISK chains that never
reached zero; the bounds above are why this should differ, not a measurement — judge it by rounds
per gate in the cost log); that one prompt paragraph turns "ban one more spelling" into "narrow the
claim or drop the guard" (T2 shows one run, not a rate); that the paragraph adds no noise elsewhere
(T3 is one run).

**Cost of the review.** PLAN gate at Normal: round 1 Codex, GLM 5.3 on melious and a fresh-eyes
pass, then verification rounds, then a final full read by Kimi on ollama: about 300k to 450k
tokens. DIFF gate at Normal: about the same.
