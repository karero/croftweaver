# Close-out and the clerk procedure (Procedure step 9)

Read this when a round is ready to close out — BEFORE writing the trail, posting to the PR/MR, or
stamping the consolidated marker (the round-claim paragraph in (b) is read earlier, before a round
launches, step 2). "Step N" means SKILL.md's Procedure. The permission table below
is the ONLY place that grants or denies a close-out action; the incidents behind it are in
`rationale.md`.

**Both halves, not just the trail file** — doing one is not doing the other, and skipping the PR
comment is the likeliest way this skill's work goes invisible. **Before either half,** for each
property the actions need: establish atom A; if absent, ask the owner for atom B; if neither, apply
the table's fallback. Consult the table BEFORE deciding where to write — in your own primary
checkout WORKTREE-WRITE is usually undeterminable, and deciding first would silently divert every
trail to a fallback nobody chose. **GATED-THIS-DIFF has no atom B:** absent atom A go straight to
its fallback — an owner saying "yes it's reviewed, stamp it" is exactly the forgery it refuses.

## ⚠ The permission table — the one place that GRANTS or DENIES

A grant or a fallback stated anywhere else is stale: delete it, don't reconcile it. Elsewhere,
sentences may only *point* at a property. Reference properties by NAME, never by row number, and
append rows rather than renumbering.

| Action | Property required | Absent → do this instead |
|---|---|---|
| Post review comments on a PR/MR — 9(b), clerk items 1–2 | **POST AUTHORITY** | Hand the consolidated findings to the human owner **in this session, in full**, name the owning session/branch/MR as far as you can establish it, and stop. |
| Create or edit the trail file in a worktree — 9(a) | **WORKTREE-WRITE AUTHORITY** | Write the same content where THIS session's own work durably lives — **not** a temp dir that gets cleaned, since the trail is the permanent record. If nowhere durable exists, hand it to the owner inline and say plainly that no durable trail was written. |
| Commit or push the trail onto a branch — clerk item 3 | **BRANCH-COMMIT AUTHORITY** | Leave it uncommitted in your own durable location and record in the trail that no in-repo copy was committed. **Never in their worktree.** |
| Stamp the consolidated marker — clerk item 2 | **GATED-THIS-DIFF** | Do not stamp. Re-gate per clerk item 2 (which bounds the retries), or block. |
| Add, replace or delete the round-claim line in the gate's PR/MR comment — 9(b) | **POST AUTHORITY** | Skip the line, without asking the owner for atom B: it is advisory (a gate with no PR/MR has no comment for it either). Name the claim in this session's report and go on. |

**Evidence — exactly two kinds.**
- **Atom A — a record of the creating action itself:** this session created that exact PR/MR (POST
  AUTHORITY), that worktree (WORKTREE-WRITE), that branch (BRANCH-COMMIT). For GATED-THIS-DIFF:
  captured reviewer input recorded against a `(base, head)` pair that still matches at post time —
  one full capture of that pair, or a verification chain covering it (clerk item 2). The capture
  may be an earlier session's if its raw outputs and pairs are quoted and still match.
- **Atom B — the owner's instruction naming that action**, given in this session, or made durably
  earlier (an issue comment, a standing instruction) and quoted verbatim and re-confirmed here.
  "Review and comment on !72 for me" is atom B for POST AUTHORITY on !72 and nothing else. If an
  action isn't named, ask. **GATED-THIS-DIFF has no atom B:** an owner can waive a RISK, not waive
  into existence a review that never ran.

Leads are not evidence: a SHA in some transcript, a matching reflog time, a local convention (e.g.
a `ccd.owner` git config) each merit one cheap check for atom A or B and prove nothing alone.

1. **Rows are independent.** Creating a branch grants nothing over its worktree; creating a
   worktree grants no commit to its branch; neither bears on whether reviewers saw the diff.
2. **Every row fails closed.** No atom A and no atom B: no property. Undeterminable is the common
   case — an unattributed worktree, an archived session, a commit in a primary checkout.
3. **Not applicable is not failure.** A PLAN gate has no PR/MR: POST AUTHORITY and GATED-THIS-DIFF
   do not apply; the two write properties still govern where the trail lands.
4. **Audit duty.** For every gated action taken, the trail names the property and the atom relied on.

## The two halves

**(a) The trail — ONE file per gate**, created in round 1 and updated in place each round:
`docs/reviews/REVIEW-<gate>-<date>-pr<N>.md` (`<N>` = the PR/MR number), or
`docs/reviews/REVIEW-<gate>-<date>-<branch-slug>-<sha>.md` with no PR/MR yet (branch lowercased,
non-alphanumerics collapsed to one `-`, `<sha>` = HEAD's 7 hex). `<date>` and `<sha>` are round 1's
and never change; the SHA is mandatory, since slugs are lossy (`feature/x`, `feature_x`). Written
where WORKTREE-WRITE AUTHORITY allows, under `docs/reviews/` (never the repo root). A record, not a
narrative — raw reviewer text lives in the PR comment:

```
# <GATE> review — <PR/MR or branch> — <the change, one line>
Base `<sha>` · depth: Light | Normal | High (why) · verdict: CLEAN | FAIL | OPEN · authority used: <property — atom>
| Round | Head | Artifact (full / delta since <sha>) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
| id | Sev | Source | Round | Finding — one line | Status (+ locally_verified / externally_reverified) | Evidence: commit, command, or quote (a parser or validator fix: the invariant and the variants or comparison, step 5; optionally `caused-by: F<id>`, step 7) |
Waivers and deferrals: the owner's sign-off quoted, dated; each deferral's merge-base reproduction;
the owner's grant for each round past 8, quoted.
Follow-ups: one line each. Notes: at most five lines (degraded seats, rounds past 3 and the BUG
that earned each, final full read, wording pass, stops).
```

**(b) The PR/MR comment — ONE per gate, edited each round, posted before merging** (with POST
AUTHORITY). The trail is the permanent record for someone who knows to look; the comment is what
the owner and teammates actually see. Post it even when the repo's convention is "no human
reviewers" — that governs who approves, not whether the review is visible. Check it off like "did
the tests pass"; a gate that exists only in a file is not satisfied.

**A round claim (advisory).** Before launching a round (step 2), read the comment's current
status; two sessions once ran the same round at once. With POST AUTHORITY, add one line (at the
top while the comment has no marker, below the marker after): session, commit under review,
scope, seats. Delete it when the round's findings are posted. It names no exclusive owner.

## The clerk procedure — who posts what (explain this to the user)

External reviewers **cannot** post: they run read-only or in throwaway dirs with no GitHub/GitLab
credentials, deliberately, because they are untrusted. The host is the clerk.

1. **Raw** (authentic): each reviewer's verbatim notes — the script's stdout sections, not stderr
   or exec logs — as a collapsed (`<details>`) section per round in the gate's one comment,
   labelled with tool, version, model, effort and sandbox. Never committed as `RAW-*.md` files.
   Only past the platform's size limit (GitHub: 65,536 characters) do the oldest rounds move to a
   second comment, linked from the first.
2. **Consolidated** (actionable): the dedup and dispositions across all seats, at the top of the
   same comment, rewritten each round. Its first line is literally
   `<!-- independent-review:consolidated sha=<full commit SHA> -->` — invisible when rendered,
   present in the API body — where the SHA is the **head of the `(base, head)` pair the reviewers
   saw**. A CI gate can then check for a review *of the commit being merged*; don't drop the SHA
   or reword the fixed text, and a later push is *meant* to invalidate the stamp.
   - **Seen pair.** Fetch the target ref first (a stale ref makes both values wrong and the
     re-check matches them anyway), then record `git merge-base <target> HEAD` and
     `git rev-parse HEAD`. **A verification chain counts as seeing the pair:** round 1 saw
     `base...h1` in full, each later round saw exactly the delta from the previous round's head to
     its own. A merge of the base or a rebase is bridged by a **merge link** (SKILL.md step 6,
     `scripts/merge_link.sh`: the change's own files from the last seen head to the new one, merge
     effects included); from it
     on, the new merge-base is the recorded one. **The chain holds per seat**, never for the round as a whole: a seat
     counts toward the stamp only if it produced a counted result in every link since its last full
     round — check the trail's per-round reviewer column, not just the recorded pair; a seat that
     FAILED or was skipped in a link has a gap there. At least one cross-model seat must hold an
     unbroken chain. At Normal depth fresh-eyes' chain ends at round 1 by design: its round-1
     findings stay in the verdict, but it does not count toward the stamp for a later head and is
     not re-run for one. **A prose-only link covers prose only:** if its segment turns out to
     contain code, the chain breaks there and that segment needs a full-scope round.
   - **Before posting,** re-read both values and stamp only if both match. If either moved,
     re-gate the new pair with **every seat the stamp relies on** (the seats with an unbroken
     chain, clean ones included — a seat with no findings still has to have SEEN what you certify;
     at High depth that includes fresh-eyes) — by the chain rule where it still holds for that
     seat, else in full; rebuild the verdict from those runs alone, mark
     superseded raw sections, and re-check. **At most two attempts,** then surface an actively
     moving branch. These re-gates don't count as rounds (step 6(b)). If a re-gate can't run, do
     NOT stamp: the gate stays blocked, like any missing prerequisite. **No seen pair, no stamp.**
   - **After posting,** re-fetch the PR's head and diff-scope once. Only the SHA moved and the
     diff-scope is byte-identical (a bare rebase): re-stamp the new head. The diff-scope changed:
     never re-stamp with the findings you have — re-gate as above. Open gap: the marker names only
     `head`, so a target-branch advance after an unmoved stamp is not encoded; closing it needs
     `base` in the marker, a change shared with a downstream CI job — left open, not claimed solved.
   - **A prose-only re-gate is scoped narrow, never skipped** — and needs only ONE cross-model
     seat (SKILL.md step 6, the wording pass); the stamp then relies on that seat's chain, and the
     other seats' chains end at the head before it. When everything since the last seen head is
     prose, tell the seat so, and to flag ONLY a factual contradiction or misleading claim against
     the code or behaviour described — not style or phrasing; the scope is prepended to the
     unchanged strict prompt and the ranking still applies. Send the delta since that seat's last
     seen head, as any chain link (without an unbroken chain it gets the full pair). A clean
     narrow pass IS the re-gate. A fix the wording pass asked for is re-gated the same way, as
     its confirmation (SKILL.md step 6) — not a second wording pass.
     **Prose-only** is decided from a changed-file/hunk inventory, never by eye: every hunk is
     Markdown body text or comment text. A code hunk, fenced snippet, YAML or config block, shell
     command, generated file or mixed commit is not prose. **Unsure means code** — prose treated as
     code costs one round; code treated as prose stamps a review that never happened. State the
     classification and the carry-over (every code hunk was gated when it entered and hasn't moved
     since) in the scope, and ask the seats to challenge it if they see code.
3. **Trail** (permanent): the gate's one trail file per (a) — committed on the branch when
   WORKTREE-WRITE and BRANCH-COMMIT both permit; the table has the fallback. It carries the
   authority used, dispositions, refuted findings with reasons, pending waivers, deferred BUGs with
   the owner's dated sign-off and this gate's merge-base reproduction (command and output), and
   reviewer versions.
4. **Cleanup.** Reviewer output streams to files in `$RAW_DIR` (never a shell variable, so a
   teardown leaves partials on disk); read it from the TOP, never through `tail`. Delete `$RAW_DIR`
   (printed as `raw output: <dir>`; it holds the artifact and every reviewer's output) only once
   items 1–3 are done AND a durable verbatim copy exists elsewhere: the posted comment is that
   copy. A PLAN gate has no PR/MR, so its raw sections go into its trail, collapsed — the one case
   raw text is committed. An inline hand-off under a fallback is not durable: then `$RAW_DIR` is
   the only copy — say so ("raw output remains only in `$RAW_DIR` until you take custody of it")
   and leave deletion to the owner. Also keep it while a verification round still needs it.
