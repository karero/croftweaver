# PLAN gate preconditions — the full reasoning

Read from SKILL.md's "PLAN gate preconditions" section, which summarizes the four
checks; this file carries the complete rationale, scope, and — just as important —
what each check does NOT establish. "Procedure step N", "the Reviewer stack", and
"item 3" (a Reviewer-stack entry) below refer to SKILL.md; "the clerk procedure"
refers to `references/closeout.md`.

(Codified 2026-08-16, after a multi-day build cleared seven PLAN rounds and still
left its owner unable to say which steps were finished.)

## 1. Can the plan report its own progress?

**The HOST agent runs this check itself** (the same orchestrating agent named throughout
this skill, e.g. in the clerk procedure — not item 3's "Fresh-eyes host-agent pass",
which is one specific reviewer seat), before the external pair goes out. No reviewer
seat will do it: the question is a precondition on the plan, not part of the
content-review prompt, so nothing in any seat's instructions would surface it.

Two questions. **Does the plan, or a sibling document it names, have a place where each
step's state is recorded?** And **does every state claiming progress or completion carry
a reference another person can actually open** — a commit SHA, a repository-qualified
pull request, a test-run link retained per the project's own policy rather than an
ephemeral CI console URL? "Not started" is the one state needing no reference; every
state asserting something happened does.

If either answer is no, record it as a **RISK, not a NIT**, in the host's own findings
and in the trail (Procedure step 9), and keep it out of the artifact sent to the
external pair — including a verification round's prior-findings list, which would
otherwise spend their attention on a host-only structural point. **This does not gate
the external round**: the standard pair still runs on the plan's content exactly as
usual, and the plan is never held back from them over it. The concern is orthogonal to
content quality — it's whether anyone can tell what's done once building starts. That
cost lands weeks later, on the human, and hardest on plans that PASS: a well-reviewed
plan gets built over days, which is exactly when memory of progress fails and the
conversation holding it is gone.

**What this establishes, and what it does not.** It is a structural check at review
time — the plan has somewhere to record state, and the convention demands a reference.
It cannot tell you a row is *accurate*, and it cannot police updates during the build
that follows: at review time most steps have not happened yet, and nothing here is
watching weeks later. A tracker can still go stale by simply not being updated, and the
rule below is stated in this skill's own documentation — if whoever executes the plan is a
different session, a different agent, or a human who never opens this skill, nothing
here reaches them. Say all of that plainly rather than imply a coverage this check does
not have: closing it needs the rule carried into wherever the builder actually looks —
the plan's own execution notes, or the handoff itself — which is a decision for that
handoff, not something this gate can reach into the future and enforce.

This prescribes no format. Whatever the project already uses is fine, on two conditions.
The record lives **in the repo**, not in a chat log or a session's to-do list — both die
with the session, and a plan reviewed in one session is usually built in another. And
**updating a step's state is part of finishing that step**, never a separate bookkeeping
pass afterwards — state this as the convention that makes the record worth keeping, not
as a promise this gate enforces: a tracker nobody updates goes stale silently, which is
worse than having none, because it still reads as authoritative.

## 2. Are the plan's own decisions settled?

**A plan whose steps are still changing does not need another round yet.** It needs its
open decisions closed first. If any finding from the last round was "this section
depends on an undecided question", get that decision, let the document settle, then run
the verification round on the result — Procedure step 6 still applies in full; this
defers that round, it never replaces it. Re-reviewing a moving target is how a plan
reaches round seven, and every round after the first grades a document that is no longer
the plan.

## 3. Is what the plan implements gated first?

(Codified 2026-10-04. One feature's implementation plan cleared ten review passes before its
requirements document existed; that document's own gate then recorded where it differed from the
plan.)

A plan says how; a requirements or spec document says what. When the two are separate documents,
gate the "what" first. Its gate moves decisions, and each one that moves makes part of an
already-reviewed plan describe something nobody will build.

**The host checks this itself**, like the other two: does the plan name a requirements or spec
document, and has that document passed its own gate as it stands — a trail with a clean
verdict (PLAN, or DIFF if it was reviewed as a change), and no change to the document after the
head that trail names? If not, tell the owner before round 1 and let them choose — gate the
requirements first, or go on knowing the plan's rounds may be paid again. Going on is the
owner's call, not a failure of the gate.

**What this does not cover.** A plan that carries its own requirements is one document and one
gate. A plan whose first step is "write the requirements" has none to gate yet: say so to the
owner in the same way, since the rest of that plan is reviewed against requirements that do not
exist.

## 4. Is the plan split into components that are gated one by one?

A plan for more than about 2,000 lines of code (tests not counted), or for more than one reader of
outside input (code that parses files or data a user or another system hands in: an upload check,
an importer, a config reader), names its components, and each is built and gated in its own PR.
**The host checks this itself**, like the others. If the plan does not split, ask the owner before
round 1: split it, or go on knowing the cost.

Why: one plan built as one PR of five readers of outside files reached nine rounds and about
37 million tokens (`rationale.md`, "The earned-by kind and the cut"); a kind of defect fixed in one
reader was found again in the next, round after round. Split, the first component's gate settles the
kind before the others copy it.

What this does not cover: a DIFF gate with no plan. There the host can still tell the owner, before
round 1, that the change is over the size and offer to split it; it is not a precondition there.
