# Plan: independent-review — a no-BUG round's open RISK, a bug-log row, and a question about guards

Base `origin/main` e0be6661 · branch `skill/review-rule-and-guard-check` · review depth: Normal (an
instruction file and a review prompt; nothing in the High row) · red team: none (no user data,
login, money, deletion or schema).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | Past round 3, an in-scope RISK whose fix changed what runs or what someone acts on earns a round, instead of going to the owner | built | `1bd03a19` |
| 2 | Bug-log row: Codex refuses a prompt that is not valid UTF-8 | built | `1bd03a19` |
| 3 | The plan prompt asks about the guards a plan proposes | built, after the owner's go (2026-10-22, "Yes, build it"; the round-8 stop kept: "Keep the round-8 stop") | `6ae85997`; test 25b fails 8 of its checks on the code before it, and 7 when the paragraph is sent for a diff too |
| 4 | Live trials T2 and T3 of step 3 | both passed, one run each (2026-10-22) | T2: one finding, a RISK that the tripwire cannot establish the plan's claim, with a concrete bypass and the fix "narrow the claim, credit the route tests"; no other guard finding (Codex, 190 s, 59,261 tokens). T3: no finding about guards; one CLEAN line said there was none (melious, 154 s, 18,151 tokens) |
| 5 | `make check`, then the DIFF gate at Normal | `make check` green at `6ae85997`; DIFF gate in progress | — |

## 1. A no-BUG round's open RISK

**Why.** The owner's rule, 2026-10-22: "Try to reduce the number of asks to me for a review. A
review can run really anytime until it's clean. Yes we want to avoid rounds over 5, but if required
let it run another round and another." SKILL.md step 6(b) still says: "A round that finds no
substantive BUG ends the rounds: open RISK/NIT go to the owner as ONE decision (fix locally … or
waive)".

**What changes in SKILL.md** (every line holding "substantive", plus step 8):
- **258**, "A substantive BUG is what the round budget counts": past round 3 it counts an in-scope
  RISK whose fix changed what runs or what someone acts on (step 6's test for an owed round, lines
  215–217) as well.
- **277–279 and 288 (6(b))**: a round past 3 is earned by a substantive BUG or by such a RISK; the
  host fixes the RISK and runs the round with `--earned-by <its kind>`, under the same cut rule,
  without asking. A RISK whose fix changes no meaning is wording: it is fixed like a NIT under
  (a2), without another round, and the wording pass reads it where one runs. A round with neither
  ends the rounds: its NITs are fixed or refuted without another round ((a2)). New: aim to finish by round 5; don't ask the owner whether to run the next
  round; ask only for what the owner alone gives: a RISK waiver, a BUG deferral (step 5), a change
  of scope, and past round 8 the decision 6(b) already names (kept). **294**: "the BUG that earned
  it" becomes "the BUG or RISK".
- **304** (final full read): "a substantive BUG earns a verification round" adds "or such a RISK".
- **307** (wording pass): "After the last round with a substantive BUG … whatever changed since"
  becomes: in a gate where a round found a substantive BUG, after the rounds end (and the final full
  read), whatever changed since the last round. Otherwise a RISK-earned round after the last BUG
  round would put already-verified fixes into a prose-only pass.
- **320** (step 7): "the round budget already follows substantive BUGs" adds "and the RISKs that earn rounds".
- **Step 8**, after "Never run rounds silently back-to-back": the update is a report, not a
  question; an owed or earned round runs without waiting for an answer.
- **Stay as they are:** 144 (when record prose gets the wording pass) and 317 (only a substantive
  BUG reopens the rounds after a wording pass). The wording pass is not a round: it runs after the
  rounds end, on prose only; a contradiction it finds is fixed and that fix gets one confirmation
  by the same seat (lines 312–318); its other RISKs are follow-ups, which need no owner decision.
  The owner's rule is about a round's open RISK going to the owner, which the wording pass never
  does. 221 points at the test. Step 7's "take the open items to the owner" follows a stop
  for non-convergence, a redesign or scope call.

**Elsewhere.** `references/rationale.md` line 374 and `references/closeout.md` line 71 get "BUG or
RISK"; the script's header (lines 77–78, 87–88) gets "a substantive BUG, or an in-scope RISK whose
fix changed what runs or what someone acts on, in the round before". The script's checks need no
change: they never see a severity. Line 266 refuses round 4 and later when `--earned-by` is empty, lines 224–241 check a
kind's shape, and the cut check compares kind names; none reads a severity. Its past-round-8
notice (pinned by `test_failed_tier_report.sh` case 37) stays. `rationale.md`'s
section of 2026-09-26 (line 465) and the review trails are dated records and stay. `rationale.md`
gains a short dated section: the rule; why it was not done before (on 2026-09-26 RISK counts never
reached zero while each round re-read the whole change); what limits it now, and how firmly. Where
the cost log can answer, the script refuses a kind that earned an earlier round of the gate since
its last cut, unless the round names a cut; where it cannot (`REVIEW_LOG=off`, an unreadable log),
it warns and goes on (lines 305–308), and the rule is the host's to keep. Everything else is the
host's judgment, shown to the owner but not enforced: whether a RISK is in scope, whether its fix
changed what runs or what someone acts on, and how a kind is named. A
verification round sees only the fixes, and an out-of-scope RISK is a follow-up. Past round 8 the
owner decides. `test_round_checks.sh` has no case naming "substantive BUG" or the owner decision,
and already pins what a RISK-earned round meets, since a kind is only a name: round 4 refused
without `--earned-by` and accepted with any well-shaped kind (its sections 3 and 4), a kind that comes back
refused without `--cut` (section 6), and the warning when the log cannot answer (section 9). So
step 1 adds no test.

## 2. Bug-log row: Codex and a prompt that is not valid UTF-8

One row in `docs/BUGLOG.md`'s format, Category `bug`, Status `open`: Codex refuses a prompt that is
not valid UTF-8, on stdin and on argv, so a diff or plan holding a Latin-1 file fails its Codex seat
and the round loses its tooled reviewer. Source: #378's trail
(`docs/reviews/REVIEW-diff-2026-10-22-feat-review-seat-limits-bbe051f.md`, C4-04 and Follow-ups).
Re-checked here, 2026-10-22, codex-cli 0.163.0: `printf 'Say OK. caf\351\n' | codex exec
--skip-git-repo-check -s read-only -` printed "Failed to read prompt from stdin: input is not valid
UTF-8 (invalid byte at offset 11)"; the same text as an argument exited 2 with "invalid UTF-8 was
detected in one or more arguments". Through the script (`--seat codex --base none` on a two-line
Latin-1 diff) the seat FAILED with that line quoted, under a reason line that points elsewhere:
"check the CLI, its sign-in and the model name". (Round 1's fresh-eyes pass also saw `cut: stdin:
Illegal byte sequence` on stderr; the same run here did not, so the row leaves it out.) The fix the
row names: make the prompt valid UTF-8
before any seat gets it, and say so in the reason line; it changes what reviewers read, so it gets
its own plan.

## 3. The plan prompt asks about the guards a plan proposes

**Why.** The owner's idea, after a security fix in another of his repositories (2026-10-22): "most
of F1's code rounds went into the tripwire test, not the fix. Next time, I'd ask the plan review
whether a static guard can deliver what the plan claims, before anyone builds one." That plan
proposed a test that reads two source files and bans some names and call forms, and said the
tripwire "guards its source". Its PLAN gate (High: six rounds, a final full read, a red team) raised
the guard's gaps in several rounds. The red team said nothing pinned every error redirect to the
trust check; Codex said the ban missed a URL built in a variable; one GLM NIT said it fired "only on
the literal pattern"; another NIT said a static file-content assertion "cannot express" what the
plan meant. Each fix they proposed kept the guard and made it more complete or more exact. None of
the trail's findings on it asked whether the route tests already did its job, or proposed dropping
it. The DIFF gate then spent rounds 1 to 4 on that guard (a BUG each round: spaced, bound and
pieced-together spellings got past it; a syntax-tree rule replaced the text match in round 3 and
was beaten in round 4). The owner closed it as "an ordinary-mistake guard and the route tests are
the real check". So the question has to reach the plan, and its answer should be a cut, not a
longer list.

**Where it goes.** In the prompt, as one paragraph every script seat gets at a PLAN gate, and one
sentence in SKILL.md for the fresh-eyes pass, whose prompt the host builds from SKILL.md's block and
the tooled paragraph, not from the script. Not a host precondition: the host wrote the plan and
shares its blind spot. Not in `PROMPT_CORE`: that text is the same for both gates and already calls
"a guard that cannot fire" a RISK. A plan also needs to ask whether a guard nobody has built yet
can deliver what the plan credits it with.

**What changes.**
- `scripts/independent_review.sh`: `PROMPT_PLAN`, assigned after `PROMPT_VERIFY` and before the four
  tier prompts and the `readonly` line (which gains it). For a diff it is empty, zero bytes; for a
  plan it starts and ends with a newline, like `PROMPT_VERIFY`. Each tier prompt's `${PROMPT_VERIFY}` becomes
  `${PROMPT_PLAN}${PROMPT_VERIFY}`, so a diff's prompt stays byte for byte what it is. The text:

  > GUARDS THE PLAN PROPOSES. For each guard the plan adds to catch a future mistake — a test, a
  > tripwire, a CI or lint check, an assertion — ask what it can catch and what gets past it,
  > whether it would fail if the behaviour it protects broke, and whether a cheaper check, or none,
  > would do as well. For a check that reads source text or syntax, name an input it would miss,
  > if there is one. A guard the plan credits with more than it can catch,
  > or one that cannot fail when its behaviour breaks, is a RISK even if it is also redundant: name
  > a concrete input that gets past it, and fix the claim, not the list: narrow the claim to what
  > the guard catches, test the behaviour where it is used, or drop the guard. Banning one more form
  > is a patch, not a fix. Where the plan's claim for a guard is accurate but a cheaper check, or
  > none, would do, that is a NIT naming it. List the guards you looked at on your CLEAN line. If the
  > plan adds no guard, write nothing about guards.

  With `--verify` it adds: "In this verification round, ask these questions only of guards in the sections that
  changed." The scope paragraph then follows it.
- SKILL.md, "The strict review prompt", last paragraph: at a PLAN gate the script adds `PROMPT_PLAN`;
  the fresh-eyes pass gets it too.
- `references/rationale.md`: a short dated section with the evidence above, anonymised as the file
  does for the owner's other repositories, naming no model (`check_model_agnostic.sh`).
- No textual guard for the new variable in `check_prompt_sync.sh`: T1 below fails if any of the
  four tiers drops it or a diff gets it.

**How it is tested.**
- **T1, in `test_failed_tier_report.sh`, beside case 25, through the script's real entry:** a plan
  run: the Codex and ollama prompts (tooled and text-only) hold the paragraph's first line; with
  `WITH_ANTIGRAVITY=1`, so does `agy-prompt`; with both seats failing (`CODEX_STUB=auth
  OLLAMA_STUB=429`), so does the paste prompt in the output. A plan with `--verify`: the paragraph
  and its verification sentence come before "VERIFICATION ROUND.". A diff, in the same four ways:
  no paragraph. Fails if a tier drops `${PROMPT_PLAN}`, a diff gets it, or the order flips. Cannot
  catch: the fresh-eyes prompt (the host builds it), or whether a reviewer acts on the paragraph.
- **T2, one live run, after `make check`:** `--seat codex --plan`, `CODEX_EFFORT=medium`, on the
  security fix's plan in a `git archive` copy of the commit that closed its PLAN gate (`1ec9cf1`),
  outside this repo, with `docs/reviews/` removed so the old findings are not in reach. Before the
  run, the copy is searched for phrases from the old findings ("literal pattern", "cannot express",
  "RT-4") and stripped wherever they occur; on 2026-10-22 the plan itself held only the trail's
  path and a status line naming "PLAN gate round 1". Pass: a RISK saying
  the tripwire cannot deliver the protection the plan credits it with, whose fix narrows the
  claim, leans on the route tests or drops the guard, not one that bans more forms. Also counted:
  guard entries about anything else (the noise). The comparison is that plan's own PLAN gate, a
  record made under other models and settings, not a controlled run. That fix is in a private
  repository and not yet merged: T2's raw output stays outside this repo and out of any PR comment;
  the trail gets one anonymised line, pass or fail and the count. About 100k–200k tokens, 10–20
  minutes.
- **T3, one live run:** `--seat melious --plan` on sections 1 and 2 of this plan alone (they add no
  guard). Pass: no finding that treats either section as adding a guard; any other mention of
  guards is counted and reported as noise, as in T2. About 20k tokens.
- **On a fail:** revise the paragraph once and rerun both trials on the revised text; both must
  pass on the paragraph that ships. A second fail goes to the owner: step 3 is held, and steps 1
  and 2 ship without it.
- `make check` green; then the DIFF gate.

**What is checked and what is judgment.** Checked: the old rule's text and each line above (read
and searched); that the script never sees a severity; the Codex refusal, alone and through the
script; both trails. Judgment: that a RISK-earned round costs the owner less than a question (the
counter-argument: on 2026-09-26 RISK chains never reached zero, and the new limits rest mostly on
the host's judgment; judge it by rounds per gate in the cost log). Keeping the owner's decision
past round 8 is also a judgment: the owner's words, "let it run another round and another", may
mean no stop at all. It is kept here as the brief asked, and named to the owner with the go for
step 3. T2 and T3 are one run each, not a rate.

**Cost of the review.** Round 1 of this PLAN gate cost 370,078 tokens (Codex 98,670, GLM 21,257,
fresh-eyes 250,151). Verification rounds run the pair only, about 120k each; a final full read by
Kimi on ollama, about 30k. The DIFF gate at Normal is likely about the same as this gate.
