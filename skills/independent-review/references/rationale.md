# Independent review — rationale, history and detailed tests

`SKILL.md` holds the operative rules; this file holds WHY they exist, the incidents that produced
them, and the detailed form of the tests SKILL.md summarises. Read the matching section when a
rule's application is contested or unclear. **SKILL.md is authoritative:** where this file reads
differently, SKILL.md wins and this file is stale — fix it here, don't reconcile the rule to it.
Step and point numbers below are SKILL.md's Procedure steps.

Moved here verbatim from SKILL.md and closeout.md on 2026-09-26, when SKILL.md was cut to its
working rules to stop every review paying ~15k tokens to read them.

## Gate on consequence — the incident

(Codified 2026-08-03 after a single session sent five MRs through this gate and
**every one came back with something real**, including two where the defect was
in the artifact's *proposed fix* rather than its description.)

The instinct that a BUGLOG row, a ledger row, or a runbook is "too small to
review" is about the artifact's SIZE. The thing that matters is whether someone
will later ACT on it without re-deriving it. A deferred-bug row's "suggested
fix" field is a **delegated instruction**: months later, an implementer reads it,
trusts it, and builds it. It is simultaneously the field the author reasons
about least (the bug is already understood; the fix is an afterthought) and the
one the reader trusts most. That asymmetry is where the defects were:

- A row said "add the missing build steps to the CI job." The job was *manual*,
  so the fix would not have closed the gap. Round 1 caught it.
- The rewrite said "…and add a cross-project trigger." A triggered pipeline ran
  the *automatic* job, still never the manual one. **Round 2 caught the same
  class of error one level down** — which is the case for a verification round
  after any BUG, not just a code one.

Practical rule: **gate on consequence, not on diff size or file extension.** A
row whose fix someone will implement, a runbook headed for a production session,
a plan a stage agent will execute — all carry more downstream weight than a
small code change that CI will catch anyway. Where a lighter gate is genuinely
right, name the gate it got and why (Procedure step 9's trail does this), rather
than skipping silently.

**Corollary — send the code that CONSUMES the config, not just the config.**
A compose/env/infra diff reviewed in isolation reliably draws "silent no-op?"
and "fails indistinguishably?" findings the consuming source already answers —
one round spent a full standard pair producing exactly those two speculations,
both refuted from twenty lines of the code that reads the variable. Include
the reading code in the artifact, or expect to spend the round refuting.

## Reviewer stack and independence — full notes

1. **Codex CLI** (`codex exec -s read-only --skip-git-repo-check -c project_doc_max_bytes=0
   -c skills.include_instructions=false`) — may start outside a git repo or trusted
   project; a project's AGENTS.md stays out of its instructions and skills are no longer
   listed there (one live probe each). The user's global AGENTS.md still applies, and an
   explicit `$name` mention in the reviewed text still loads a skill — R-PROJCTX. Asks the
   CLI for a read-only sandbox
   (enforcement untested: R-SANDBOX in the open-findings tracker); model +
   effort from `~/.codex/config.toml` (daily-driver default). Override per-run with
   `CODEX_MODEL=<model-tag>` for a harder case or a long plan — config.toml's
   reasoning-effort setting still applies on top, since the override only touches
   the model key.
2. **ollama cloud** (`OLLAMA_MODEL`) — the standard second reviewer, runs
   automatically alongside Codex with no env var needed: the script
   auto-detects your signed-in `:cloud` model from `ollama list`. The skill
   prescribes no specific model — set `OLLAMA_MODEL` to pick a different
   cloud or local tag if a specific case warrants it. **Melious fallback**
   (`MELIOUS_MODEL`, opt-in by naming a model): when the ollama seat does not
   count — no model or CLI, a failure such as a quota refusal, or a local
   sanity pass — the script sends the same text-only prompt to Melious's
   OpenAI-compatible API instead, so the pair keeps its second reviewer. It
   stands in for the seat and is never a third counted reviewer; `--seat
   melious` runs it alone, and `--seat ollama` never falls back to it.
   `SECOND_SEAT=melious` swaps the two: Melious runs with Codex, and ollama
   is its fallback.
3. **Fresh-eyes host-agent pass** — a read-only sub-agent (or the vendored
   `double-knuth` skill) with NO shared context: give it only the artifact and
   the strict prompt below. Never reuse the authoring conversation. If the host
   has no sub-agent primitive (some Codex installs), use a separate fresh
   session with only the artifact — or record the pass as *degraded* in the
   trail, not as no-shared-context. On a Claude Code host, an extra pass with
   a stronger host-family model (the Agent tool's model option) is a good
   candidate for this seat when the owner wants a second same-family opinion
   on top of the host's own — it's free (no external credits, no CLI), just
   not cross-model (see the Independence rule below). Offer it after
   presenting results, don't run it unasked.
4. **Antigravity — OPT-IN ONLY, never automatic.** Google Gemini via the
   Antigravity CLI (`agy --sandbox --mode plan -p`, a prompt telling it not to use tools;
   `AGY_MODEL` overrides the CLI's default model — `run_agy` in
   `scripts/independent_review.sh` has the full call), free Antigravity login. The
   owner's Antigravity free-tier credits are scarce and get spent only when
   explicitly worth it: pass `--with-antigravity` to the script, or the owner
   directly asks ("antigravity review", "agy review", "worth burning a
   credit on this one"). The default run (no flags) never touches it — this
   is a deliberate change from earlier drafts of this skill, which ran it
   unconditionally on every default pass and burned credits silently.
5. **ollama local** — sanity pass only; the script never lets it satisfy the
   gate alone.
6. **Any model, copy & paste** — the script emits the prompt; a human pastes it
   into whatever is available and feeds findings back.

**The standard pair (Codex + ollama-cloud) is the un-flagged default for both gates** —
DIFF included, not only PLAN; `--first-success` reduces either to a single reviewer.
**PLAN additionally treats fewer than 2 as worth flagging**: a plan is often high-stakes
enough that "whichever one answered first" isn't enough independence, so the script
notes it explicitly (see Procedure below) whenever a plan lands with fewer than 2
reviewers. The same note fires for a DIFF round too: a tier that fails quietly is
how a one-reviewer round once passed for a pair. This is a default expectation, not a hard
floor: passing `--first-success` on a plan is a caller's conscious choice to accept one
reviewer instead (the script honors this, it does not override it — see the
credit-cost tradeoff this represents). If a
plan lands with only one reviewer's output for any reason — an explicit
`--first-success` or a tier failing — treat the round as degraded *only if
that wasn't the deliberate choice*, and say so either way.

**Independence rule:** *classify* every tier that actually ran — which tiers
those are is decided by the reviewer stack above (the standard pair by default;
Antigravity only on explicit opt-in; paste always manual; local ollama runs
whenever `OLLAMA_MODEL` names a local tag, but never *closes the gate* on its
own), and this rule governs how the ones that ran are scored, not how many to
launch. The tier matching the HOST agent's model family counts as the
fresh-eyes seat, never as cross-model independence. **The gate is satisfied only when at least one
successful reviewer is cross-model (a different family than the host)**; if
only same-family reviewers ran, the gate is degraded and needs an explicit
owner waiver — codex reviewing codex-authored work shares the blind spots this
gate exists to catch. Per host: **Claude Code** — fresh-eyes = the Claude pass
(optionally a stronger same-family pass, see the reviewer stack above —
doesn't count as cross-model either), cross-model = Codex + ollama-cloud
(classified by the family of the tag actually used — the standard default
pair) + Gemini/Antigravity (opt-in extra,
not needed to satisfy the gate since Codex or ollama-cloud already does).
**Codex** — fresh-eyes = Codex, cross-model = ollama-cloud + Gemini + Claude.
**Antigravity/Gemini** — fresh-eyes = Gemini, cross-model = Codex +
ollama-cloud + Claude. On any non-Claude host, an Anthropic seat may be
reachable via the Antigravity CLI — see `references/setup-guide.md` for the
current model tag, verification status, and free-tier caveat; it shares the
same scarce-quota, opt-in-only rule as every other `agy` use in this skill,
not a standing free lane.

## Step 1 — data consent, in full

1. **Data check before anything leaves the machine.** External reviewers are
   third-party services: grep the artifact for secrets (keys, tokens, passwords,
   customer data) and get the owner's OK the first time a given repo's content
   is sent out **to each destination service, not just each named tool** —
   Codex, ollama-cloud, and Antigravity are separate services with separate
   consent, not one blanket "external reviewers are OK," and naming the tool
   isn't always naming the destination: Antigravity with `AGY_MODEL` set to
   a Claude tag routes content on to Anthropic too, a distinct destination
   from Antigravity's own Gemini path, needing its own consent — and the
   paste tier (tier 6) sends the same artifact to whatever service a human
   pastes it into, chosen ad hoc, which needs the same per-destination
   consent as any named provider, not a free pass for being manual. Record
   the OK the way the permission table (`references/closeout.md`) records
   an owner instruction (atom B: quoted verbatim). **Only a standing
   instruction durably written in the repo persists across sessions** — a
   later session can check for that and tell "owner consented for this
   provider" from "nobody has asked yet." This session's own in-conversation
   record is real consent for the current session, but per this file's own
   durability standard (an in-session hand-off doesn't count as durable
   anywhere else here either) it is invisible to a later one — that session
   re-asks rather than assuming consent it cannot see. Adding a new provider
   later needs its own consent, not an inherited one. If the content must stay local, run the script with
   `--local-only` (skips codex/agy/paste entirely; local ollama only — the
   script requires the EFFECTIVE ollama tag to be local: under `--local-only` the
   cloud auto-detect default is never applied, and an explicitly-set cloud tag is refused outright,
   rather than silently sending content out) plus the tier-3 host fresh-eyes
   pass — tier 6 (paste into any model) is just as
   external as the CLIs and is excluded. A local-only verdict is inherently
   DEGRADED; record that in the trail.

## Step 2 — why the trail is excluded from the artifact

   **Build that artifact from the CHANGE, not from the whole diff — exclude `docs/reviews/`.** A
   DIFF gate on a branch that already carries a trail file will otherwise send the trail to the
   reviewers, and they will review it: its arithmetic, its finding counts, whether it describes the
   round currently reading it. Those findings are real — an arithmetic error in a trail IS an error
   — but they are about the review RECORD, not the change under review, and they arrive in rounds
   that would not otherwise have happened. Generate the artifact with the trail excluded:

   ```
   git diff <base>...HEAD -- . ':(exclude)docs/reviews/'
   ```

   Audit the trail's own numbers yourself instead. Two MRs on the same internal backend repo
   (8 and 7 rounds) each paid a late round that found nothing but the trail auditing itself —
   excluding the file PREVENTS that loop; the "scope it by RULE, not round number" guidance
   only BOUNDS it. **The trail must still be in the MR diff** — a repo CI gate may require it
   and clerk item 3 (`references/closeout.md`) commits it — this is only about what reaches the reviewers.

## Step 4 — pre-existing annotations, in full

   **A pre-existing artifact annotation never auto-closes a finding that re-raises it — its own
   reasoning must actually cover what THIS reviewer raised, confirm that first.** Only once
   confirmed: if the artifact itself already explains a deliberate choice a finding re-raises (a
   code comment, a plan annotation — e.g. from a prior planning-stage review whose reasoning was
   carried forward, see `phased-plan-runner`'s equivalent convention for artifacts produced by
   that skill), triage can cite that existing reasoning instead of a from-scratch re-derivation —
   but citing it does not by itself pick a status: the finding still resolves to REFUTED only if
   the annotation's reasoning actually disproves it, or to WAIVED only if the annotation traces to
   a real prior owner decision (citing an old waiver does not manufacture a NEW one's required
   sign-off out of nothing — get a fresh one if the annotation doesn't already clearly carry it).
   An annotation that merely explains a tradeoff the team accepted, without disproving the finding,
   is waiver-shaped, not refutation-shaped — treat it as such, not as an automatic close.
   Whenever the annotation's reasoning does NOT cover what the new finding raises, that finding is
   new signal — not repetition — regardless of whether the reviewer saw the annotation; it gets
   triaged like any other finding, never dismissed because *something* was already written nearby.

## Step 5 — the deferral exception, in full

   **The one exception: a BUG the change did not introduce.** DIFF gate only; a plan has no base
   to compare against, so a BUG in a plan is fixed before anyone builds from it. The owner may
   defer the BUG out of the change when all three hold:
   - every wrong input the row quotes goes wrong at the merge-base with the target branch,
     through an entry point the target branch already used at the merge-base, before this change
     — so the change did not create it;
   - a row describes it in the repo's open-findings tracker — a file in the repo with a BUG
     section, whose row gives the id, the location, the finding and the owner's dated sign-off;
   - tests that the repo's CI runs assert today's wrong result for each quoted input, are
     labelled KNOWN WRONG and name the row, so whoever fixes the BUG changes them on purpose. A
     BUG no test can pin, such as wrong wording, does not qualify: fix it.

   **A widening is a BUG the change introduced.** If the change lets more inputs reach an old
   defect, or adds a caller that reaches it, the new wrong results did not exist at the
   merge-base, so condition 1 fails for them: fix them, or hold the change. The row may be new,
   written by the change itself; what counts is that its inputs go wrong at the merge-base.

   **DEFERRED is a status of its own** (point 4). For this gate a deferred BUG is closed: it does
   not keep a round from being clean (6(a2)), does not count as an open BUG in the round budget (6(b)),
   and a reviewer who raises it again without new evidence is making a re-raise (point 7). In the
   tracker it stays open, in the BUG table, until someone fixes it. The owner's sign-off carries
   over to later gates, but each gate's trail records DEFERRED, never fixed or refuted, together
   with its own merge-base reproduction — the command and its output — so condition 1 is at least
   `locally_verified`. A deferral made after the last round is marked "deferral not externally
   re-verified", as (c) does for fixes. (Codified 2026-09-26: the owner had deferred BUGs, and
   once a widening of one, under a rule that said "no exceptions", so the rule and the practice
   had drifted apart. Widenings were left out after four review rounds failed to define one that
   two readers would apply the same way.)

## Step 5 — verifying claims: the two failure shapes

   **Verify checkable claims — empirically where the claim is about runtime/checkable behavior, by
   direct textual/logical demonstration where it's about structure, logic, or wording — before
   calling them fixed OR refuted; a reviewer's named example is illustrative, not exhaustive.** Two
   recurring failure shapes:
   (a) a fix that resolves only the ONE example a reviewer happened to cite (a specific
   string, a specific input) can still leave the reviewer's actual, broader claim true — test
   against their full stated reasoning, not just the named case, before marking it fixed
   (caught in practice: a regex fix was accepted after disproving only one cited false-positive
   string, but the reviewer's broader point still reproduced on a harder test). (b) a finding that an
   API/data surface is reachable, or behaves a certain way, is NOT settled by confirming a
   type/field/shape matches — trace the real access path (auth mechanism, routing,
   permissions) it actually goes through; a correctly-shaped type sitting behind different
   auth than assumed is still wrong, and "the shape looks right" is exactly the plausible
   half-check that misses it. Both apply symmetrically to REFUTING a finding, not just
   fixing one: don't dismiss a reviewer's claim as wrong just because its own cited example
   fails to reproduce — check whether the underlying point still holds under a harder case
   before writing it off. **A claim that's checkable in principle but can't actually be tested
   right now** (missing environment, credentials, or permissions) **stays OPEN**, with the
   missing prerequisite recorded — don't force it into fixed or refuted without the check that
   would justify either. (A RISK/NIT in this state may still be WAIVED with a reason and the
   owner's sign-off, same as any other open RISK/NIT — waiving needs no check, just the owner's
   call; only fixed/refuted are blocked pending the missing prerequisite.)

## Step 6 — why verification rounds are scoped and capped

   **Rounds are counted per artifact, not per finding (6(b)).** (Until
   2026-09-26 it counted per finding id, so each new RISK in round 3 earned its own round and the
   cap never fired — the 5–13-round gates.)

Codified 2026-09-26 from the trails: RISK counts per round ran 6 → 5 → 5 → 2 on a one-line flag
change and never reached zero on most multi-round gates, because each round re-read the whole
change and "an unsupported load-bearing claim" can always be found somewhere in it. Gates ran 5,
6, 7, 8, 9 and 13 rounds. Scoping a verification round to the fixes and the change since, making
out-of-scope RISK/NIT a follow-up, and counting the cap in rounds removes that loop. (The cap
first adopted here — 3 rounds, extended to 5 only while the BUG count fell — was replaced the same
day by the round budget; see the next section for why.)

   **Two verification statuses, not one — "verified" alone is what makes 6(c) ambiguous.**
   `locally_verified` = the author reproduced, demonstrated, or ruled out the claim themselves,
   to point 5's standard. `externally_reverified` = an independent reviewer confirmed the fix in
   a later round. A checkable claim with neither status stays OPEN and blocking. The one exception
   is a BUG DEFERRED under point 5: it has no fix to verify, and its merge-base reproduction must
   itself be `locally_verified`. Record both per
   finding; a trail that says only "fixed" does not say which.

Codified 2026-10-09 from a 13-round DIFF gate on a new tool that reads other sites (PR #230; its
trail, `docs/reviews/REVIEW-diff-2026-10-09-pr230.md` on that PR's branch, counts 77 findings and
29 confirmed BUGs as of round 13). By the trail's own notes 8 BUGs came from the first Codex read
of the whole change, 13 or 14 from an earlier round's fix (caused or left half done) and 7 or 8
from older code of the same change, found late. Rounds 4 to 13 each cite the finding that earned
them under 6(b) — all BUGs but one, a NIT that proved to be a real bug — and 6(b) calls a chain of
fixes that each expose the next real defect the gate working; the trail records neither a
convergence assessment nor the owner's decision past round 8. Three components made most of the
chains (split numbers, address checks, robots.txt), each guessing at or copying another
component's behaviour. At round 13 the robots.txt code was replaced by one written from the RFC,
tests first, instead of another patch; whether that ends the chain was not yet known. What came
of that: a notice past round 8, an optional `caused-by` note and a mention to the owner at a
chain of three, a fix standard for parsers and validators, refuted rows carried into `--verify`,
and a round claim. All are non-blocking, the owner's preference: nothing here stops a run or a merge. A
refusal at round 9 was considered and left out for that reason. Also left out: a realism filter
that demotes BUGs found only with constructed inputs (a byte-order mark, filed as a NIT, was a real
bug, and the author who wants rounds to stop is the wrong judge of "realistic"); a second full
read up front (about 8 of the 29 were older code found late — a retrospective candidate set, not a
measured yield); and older-code BUGs as follow-ups (step 5 allows deferral only with a merge-base
reproduction, and a new tool has none). None of it is measured: judge it by rounds per gate
(`scripts/review_log.sh summary`) on the next gate that runs past round 3.

## Step 7 — the convergence detector, in full

7. **Convergence check — the rabbit-hole detector.** Iteration is only healthy
   while quality demonstrably rises each round. After every round, check three signals:

   **(a) Finding count.** Is it falling? Don't read this alone as the verdict — a rising count
   from genuinely new scrutiny is healthy: a later round that finally verifies claims no earlier
   round checked SHOULD find more, not fewer, real issues.

   **(b) Are findings landing on genuinely new ground?** A finding PASSES (b) when it targets
   code *added by the previous round's fixes*, or when checking it names a concrete new thing —
   a specific check, input class, execution path, invariant, or evidence source the earlier pass
   didn't use (e.g. round 3 starts empirically tracing auth/data-access paths where rounds 1-2
   only reasoned from reviewer prose) — regardless of whether the overall method is nominally the
   same or different; simply asserting a pass was "more careful," "deeper," or used a "different"
   method, without naming that concrete delta, does not pass (b) on its own. A genuinely new
   method that comes back CLEAN isn't a (b) failure either — there's no finding for it to
   classify; it's valid convergence evidence, not wasted effort. (b) FAILS when a finding
   re-covers ground a PRIOR PASS explicitly checked and reported CLEAN, without naming that
   concrete new thing — this is about ground nothing was ever raised against, a different
   population from the re-raises (c) below covers, where something WAS raised and dispositioned.

   **(c) No oscillation.** A fix that, once verified per point 5's own standard (reproduced or
   demonstrated, not just asserted), DEMONSTRABLY re-breaks something an earlier round FIXED means
   STOP regardless of how many other findings that round are genuinely new — a regression isn't
   offset by unrelated progress elsewhere. This is the only EVEN-ONE-finding trigger in this
   section; every other case below pools into the STOP threshold's MOST-of-the-round test instead.

   A reviewer re-raising a finding THIS REVIEW's own round-to-round trail already dispositioned
   (matched by the stable id from point 4, not just similar wording) is common and NOT
   automatically oscillation — an independent reviewer, especially the no-shared-context
   fresh-eyes seat, is expected to sometimes re-notice something a prior round already
   handled, precisely because that seat doesn't know the prior rounds happened. What matters,
   checked with the same verification standard as any other claim (not just asserted): does the
   re-raise bring new reasoning or evidence beyond what the prior disposition already considered —
   the same coverage test point 4 uses for pre-existing artifact annotations (does the prior
   disposition's reasoning actually cover what the new evidence raises?), adapted here to
   round-to-round dispositions *within this review*. If it does, it's a fresh finding, full stop,
   regardless of what the prior disposition was. If it doesn't (checked, and the original
   disposition still holds), where it counts depends on that prior disposition:
   - a re-raise of something FIXED or REFUTED with no new reasoning pools into the MOST threshold
     below, alongside (b)-failures — NOT this signal's strict even-one bucket above. It's reviewer
     overhead (re-checking a claim that turned out to still be nothing new), not the artifact
     regressing; the strict bucket is for a DEMONSTRATED regression specifically, and holding a
     routine no-shared-context re-raise to that same bar would effectively punish running a
     genuinely independent reviewer every round — the whole point of that seat.
   - a re-raise of a BUG DEFERRED under point 5, with no new reasoning, pools into the MOST
     threshold too: the owner accepted it as real and it stays open in the tracker, so re-noticing
     it is neither a regression nor new signal.
   - a re-raise of something WAIVED with no new reasoning also pools into the MOST threshold, for
     a related but distinct reason: waiving concedes the issue may be real, so it was never "ruled
     clean" (that's (b)'s own test above) and re-noticing it isn't a regression of something
     dispositioned-as-resolved (that's this signal's own test above) — it's an independent
     reviewer correctly re-noticing something the owner already knew about and accepted.
   - a re-raise of something still OPEN under point 5's untestable-claim rule (blocked on a
     missing prerequisite) pools into the MOST threshold the same way: it was never "ruled clean"
     either, and there's no fixed/refuted disposition for it to contradict — restating a known,
     already-tracked open item is not new signal, but it isn't instability either.

   **STOP patching when:** the regression case above fires for even one finding; OR (b)-failures
   and any of the four no-new-evidence re-raise cases above, TOGETHER, characterize MOST (more
   than half) or all of the round's findings — not just one stray finding amid otherwise-new ones;
   OR the count plateaus for two consecutive rounds AND those plateauing findings are not
   predominantly (b)-passing (a plateau of genuinely distinct, newly-surfaced findings each round
   is not itself non-convergence — see (a) above — it's a slower signal the artifact's surface
   area is bigger than first estimated, worth naming explicitly rather than silently forcing
   STOP). (This is an early-exit heuristic layered on top of, not instead of, point 6(b)'s round
   budget — past round 3 only a substantive BUG earns a round, past round 8 the owner decides —
   which bounds iteration regardless of how these signals read.) When triggered: step back and redesign the
   component (patch-churn on a wrong design converges never), or take the open items to the owner
   as a decision — escalation can postpone, re-scope, or reject the release, but it cannot waive a
   BUG that's still open. It can defer a BUG out of the change only under point 5's one
   exception. A BUG blocked on a missing prerequisite (point 5's untestable-claim rule) is held
   open, not deferred: holding it keeps the release blocked, and the BUG can close only after the
   prerequisite becomes available and verification supports either a refutation or a verified
   fix. Point 5's rule holds regardless of who's deciding. Say so plainly in the trail — "stopped: not
   converging" is a legitimate, documented outcome; silent round 7 is not.

## Close-out — why the permission table exists

**Why these rules exist** — non-normative; incidents, not instructions. 2026-08-02: a session
gated its own abandoned branch, found real issues that also applied to a parallel session's MR,
and posted them onto that MR — the behaviour POST AUTHORITY now prohibits. 2026-08-03: a
session's uncommitted edit to a tracked file was swept into another session's `git commit -a`
under an unrelated message, and a new untracked file is swept the same way by `git add -A` or
`git add .` — hence the two write properties. Round 1 of this skill's own review:
A downstream repo's CI gate, as originally implemented in its MR branch,
matched a bare marker that any note containing the token would satisfy — caught by round-1
review (Codex) before merge, so it never reached the shared branch in that state — hence
GATED-THIS-DIFF, and the advice to describe the marker rather than spell it out. See the `loose-ends` skill, "Open ends belong to a session".

## Close-out — prose-only re-gates: the incidents

Two incidents on the same
review track show why: an *un-scoped* re-review once re-litigated committed trail prose through
rounds 6–9 of one PR — ~40 findings, zero contract defects — before a narrow scope ended it in
one more pass. A second PR hit the same failure from a different trigger (fix commits repeatedly
moving the head) and the same fix converged it: 5 passes, 22 findings, ending on one
explicitly-scoped pass that came back clean. And prose diffs are where real findings live, not
just noise: on a third PR, a re-gate round caught its own prior round's fix overstating a claim
("ran in production" for something that had only run in a test environment) — proof a fix round
can introduce a new problem, not just resolve the old one — and the very next round then skipped
that same check on its own fixes, reasoning the diff was "just wording." Don't make that call
from the diff's size; run the narrow pass and let it tell you.

## Close-out — never read reviewer output through `tail`

**Read the whole file, never a tail of it.** The prompt asks for a RANKED list, so the severe end is
at the TOP: piping a reviewer's output through `tail -n` hides exactly the findings the round was
run for. Caught live on a 7-round MR (the trail-exclusion incident, Step 2 above) — a round read through `tail -40` showed only its NITs; re-running
it in full surfaced a BUG. The re-run also cost a second round AND produced a DIFFERENT list from
the same model on the same input, so three findings acted on from the first sample went unlogged and
a later round had to reconcile the trail's arithmetic. If output is too long to read at once, page
through it from the top or write it to disk and read the file — never sample the end.

## Review depth — why three depths, and why Light may be same-family

Codified 2026-09-26 by the owner. Every change used to get the same gate: the Codex + ollama pair
and a fresh-eyes pass on the host's own model, every round — so a copy fix cost as much as an auth
change. Depth now follows consequence, which "gate on consequence, not size" already asked for.
Light accepts one same-family seat (the host's diff review) for changes whose mistakes are cheap to
find and undo; that is a standing owner decision, recorded here and in SKILL.md, not something a
session may extend to other changes. Normal runs fresh-eyes once, on a mid-tier model, because the
cross-model pair carries the gate; High keeps every seat at full strength every round. Verification
rounds drop Codex to medium effort because they check fixes and a small delta. Whether these
trades pay off is to be judged from the trails' `timings:` lines and fresh-eyes token counts.

## Verification chains and the stamp; the cost log

Before delta verification rounds (2026-09-26), a re-gate had to send every seat the full
`(base, head)` pair, because the stamp certifies that reviewers saw that pair. With delta rounds,
closeout's chain rule carries that guarantee instead: round 1 saw `base...h1` in full and each
later round saw exactly the delta from the previous head, with the merge-base unchanged. A moved
base breaks the chain, which is why SKILL.md step 6 bridges it with a merge link.

The cost log (`scripts/review_log.sh`) exists because the depths and effort levels were set from
a handful of trails, not from measurements. It records seconds and tokens per seat per round —
codex's own token count where it prints one, the host's sub-agent report for its seats — locally,
outside any repo, so measuring adds no paperwork. Ollama tokens are not captured: getting them
needs a change to the ollama call that could not be tested when this was written.

## Round budget, wording pass, final full read, merge links — the backend evidence

Codified 2026-09-26 after reading the review trails of ten of the largest tasks in the owner's
backend repo (261 gated tasks, 782 rounds; 30% of all rounds after round 3, 15% after round 5).
Long gates came in two kinds, and a count-based cap cannot tell them apart:

- **Productive chains.** Each round found a real defect, often in the previous round's own fix:
  an itinerary fix (six real regressions in rounds 2–7), an authentication change (concurrency
  bugs through round 15), an admin error-handling change (rounds 5 and 7), a data-deletion change
  (round 6: an account left half-erased), an authentication design plan (rounds B4–B5). BUGs per round ran
  flat or noisy — 3,3,2,3,1,2,0 and 1,0,8,5,3 — so "extend only while the BUG count falls" would
  have stopped five of the ten tasks around round 3–4 and missed those bugs.
- **Waste.** After its round 7 the itinerary fix ran 20 more rounds without a new product
  bug: wording drift, test-assertion tightening, two known issues re-raised every round, and three
  full re-reviews after merges of the base. The design plan's late rounds spent most findings on the review
  file's own arithmetic; one waived race was re-raised six times.

Hence: rounds past 3 are earned by what the last round found (a substantive BUG), not by a
count's direction; after the last such round, wording gets one narrow pass by one seat; a merge
of the base is reviewed where it touches the change, not in full. And because delta rounds never
reread untouched text, while two specs' most important late bugs sat in exactly such text (one
found at round 14 by a fresh model reading the whole document, one wrong since round 1), plans,
specs and High-depth changes end with one full read by a reviewer new to the artifact. None of
the trails recorded time or tokens; the cost log exists so the next such review can.

## Confirmed findings, unseen text, record prose — the second backend reading

Codified 2026-10-04 from the 51 trails the owner's backend repo wrote in the first eight days
under the round budget, 221 passes. On 42 DIFF gates (one ten-stage trail left out), 94 passes
ran after the first, and 75 of them found no BUG.

- **Raised is not confirmed.** Of the 327 RISKs ruled fixed or refuted, 187 were refuted. In the
  26 gates whose first pass found no BUG, the 44 passes that followed found two code BUGs, both
  in one gate and both in fixes that had changed code, and one test BUG, in the first round of a
  redesign. Under this rule each of those rounds still runs. Stop condition (a2) read "zero BUG
  and zero in-scope RISK" and did not say whether a refuted RISK counts. Hence the count after
  triage, and a round owed only by a fix that changed something. What this gives up: a wrongly
  refuted finding gets no reviewer's second look — which is why a refuted BUG goes to the owner
  with its evidence.
- **A seat that cannot open the files.** Share refuted, of the findings ruled
  fixed or refuted: 4% each for Codex and for fresh-eyes (of 76 and of 118), and 45%, 66% and
  73% for the three text-only cloud seats (of 93, 303 and 11). 49 of the 94 later passes were
  one text-only seat alone (the tooled cross-model seat was out of quota on three of the eight
  days); they raised 85 RISKs and confirmed no code BUG. One three-round gate: 22 findings, 19
  refuted, and of its first round the trail says most were "this name may not exist" about code
  outside the diff. Hence the text-only prompt's rule that a concern about unseen text is a
  question. What this evidence does not show: "refuted" is the author's own ruling;
  Antigravity, which also reviews from the text alone, was upheld on 18 of 19 findings, so the
  model matters as well as the tools; and whether the rule loses real findings is not measured,
  at any depth or for plans. Antigravity's prompt is left as it is: its last fix has not yet
  been seen working live (R-AGY-PROMPT in the open-findings tracker).
  Not done here: sending a DIFF's verification rounds to the tooled seat alone. A draft of this
  change did, and its final full read found that rule at odds, in three places, with the
  per-seat chain the stamp relies on (closeout, clerk item 2). It needs the chain rule reworked
  first, as a change of its own.
- **Record prose draws findings.** Of the 26 later BUGs the trails describe, 16 were about
  sentences — changelog entries, comments, test-case wording, the review record — and 10 about
  code or tests. In one gate all four BUGs raised after the first pass were sentences in its
  changelog entry. Hence the entry is written after the last round and read once, by the wording
  pass.
- **A plan gated before its requirements.** `plan-preconditions.md` §3 has the incident.

Where the numbers come from: the trails, read partly by a model whose extraction was checked by
hand on two trails and against a parser on 17. Timings were recorded for part of the passes only.
The cost log held nothing: on the owner's machine its directory was not writable.
