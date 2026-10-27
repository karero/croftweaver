# Plan: send read-backs of remote systems as `--evidence`

Status: plan, under the PLAN gate. Nothing built. Builds on `--evidence`
(`SKILL-PLAN-review-evidence.md`, built 2026-10-25).

## What

Give the "the seat cannot see GitHub (or Cloudflare, or a docs page)" question a standard
answer: the host reads the system and sends the read in the `--evidence` file, every round.
Two sentences in `skills/independent-review/SKILL.md` and a test that pins them. The script's
EVIDENCE lead stays as it is, for the reason in the probe below; changing it is a follow-up with
a named trigger.

## Why

Seats keep asking about systems they cannot reach: GitHub rulesets and settings, a Cloudflare
dashboard, a vendor's docs page. The external seats have no network (the tooled prompt says "no
credentials, no network"; melious is text only); a host fresh-eyes pass may have it (pr285 round
1 had web access). `SKILL.md` step 2 sends "command output, logs, measurements" to
`--evidence`, but does not name a read of a remote system or say to resend it each round, and in
the trails below such reads landed in the PR text, which no seat sees.

Checked in this repo's trails on 2026-10-27:

- `REVIEW-diff-2026-10-14-pr285.md`: 9 UNVERIFIABLE questions in round 1 and 9 in round 2,
  none confirmed, "nearly all" asking for Cloudflare pages the author had read (quotes in the PR
  description). Round 2 was sent "the author's record of round 1", and Codex re-raised F10 and
  F11, "no new evidence". The trail's F10/F11 rows quote the pages; whether the record sent in
  round 2 did is not checked (it is not kept). Either way a quote reached Codex only as the
  author's word, or not at all. (`--evidence` did not exist yet.)
- `REVIEW-diff-2026-10-09-pr227.md` F23: asked by both seats "every round" (the review ran nine rounds), and
  settled only by the host reading two OpenRouter docs pages. F21 and F22 (rounds 5 to 9, owner
  waivers) are a different kind: they ask what a field *means*, which no read settles. This change
  would not have saved them.
- `REVIEW-diff-2026-10-09-pr228.md`: the ruleset question was settled by measurement in round 1,
  and the result "went to the PR text".
- 222 `REVIEW-*` trails are dated 2026-09-27 to 2026-10-27 (counted, not including this plan's own trail). The intake session counted
  28 of them recording UNVERIFIABLE questions about such systems (not re-counted here; nothing
  below rests on it).

All three cases predate `--evidence`: they show reads not reaching seats, not a seat ignoring a
read it was sent. A probe on 2026-10-27 tested the second. It sent Codex a real read of this
repo's "main checks" ruleset (`gh api`, timed, verbatim, some fields cut) under today's lead,
with a small plan making two claims the read shows and two it does not. The files are in
`docs/reviews/probe-readback-evidence/`: `artifact.md`, `evidence.txt` (as sent), Codex's answer
`codex-old-lead-2026-10-27.md`, and `read-command.txt`, the full command, since `evidence.txt`
shortens its filter (rerun 2026-10-27: same output). Codex caught both unsupported claims from
the read and marked the shown ones "VERIFIED, within the supplied snapshot". Of its two
UNVERIFIABLE entries, the GitHub one asked for what the read did not hold: the second ruleset's
rules, bypasses, and "an attempted failing update"; the other was about the local hook, not a
remote system. So it did not ask again for anything the read showed. One run, one seat: a sign,
not a measurement. It points at placement, not wording. That the cases above failed because the
read never reached a seat is a hypothesis (pr285's round-2 input was not kept); the step-4
sentence and the ten-round check below test it.

## How

1. **`SKILL.md` step 2**, after the `--evidence` sentence (~line 145): "A read of a system no
   seat can reach (a GitHub setting, a dashboard, a docs page) goes in that file as a READ: the
   exact command or URL, the time it ran, and its output verbatim, with entries cut but none
   edited, never a field a claim rests on, and secrets replaced with made-up values. Send the
   same file every round its claims are under review; a quote in the PR text reaches no seat."
2. **`SKILL.md` step 4**, after "UNVERIFIABLE entries are questions…" (~line 199): "One about a
   system the host can read is answered by reading it and adding the READ to the next round's
   `--evidence` file, not by an argument in the trail; one the host cannot read stays open, as
   step 5 says. Where a seat asks for what a READ it was sent already shows, the round's row says
   so."
3. **No script change.** Today's lead already tells seats to "use it to check the claims it
   supports", and the probe's seat did. The fresh-eyes pass (step 3) builds its lead from the
   script, so it needs nothing either.

## Tests

- New, in `test_failed_tier_report.sh` beside 25d: `grep -F` on `SKILL.md` for three phrases,
  written out by hand: "goes in that file as a READ", "Send the same file every round", and
  "adding the READ to the next round's". The guarantee is that each phrase is present, not the
  whole wording; a reworded clause between them passes.
- Mutation check before review: delete each of the three phrases' sentences in turn; each must
  fail its check.
- `make check` runs the file; nothing else changes.

## Net benefit

Saves: a re-raised question per affected round (pr285: two RISKs re-raised in round 2, 9
UNVERIFIABLE per round; pr227 F23: asked every round of nine), the host's triage of those lines,
and owner waivers when they become RISKs. Adds: two sentences and three greps.

Not worth keeping if, in the first ten rounds after the build that send a READ, seats ask for
remote state about as often as in the cited trails. That would mean placement was not the cause.

## Follow-up, not built: the lead

If a trail row records a seat asking for what a READ it was sent already shows, add a BUGLOG row
and plan a lead change. The candidate, reviewed in rounds 1 and 2 of this gate: "A READ … Take a
READ as what that system held at that time, and do not ask again for the read or for the live
state it records", keeping challenges for a claim beyond the READ, a stale READ, a conflict, or
doubtful provenance, and asking seats to list claims settled on a READ. It costs about eight
prompt lines a run and invites over-trust, so it waits for a case.

## Strongest counter-argument

Daniel's idea was that reviewers should *accept* a read, which is a wording change, and this plan
makes none. Answer: the probe's seat already accepted the read and asked only for what it did not
hold, so the wording change would buy nothing seen yet, and it adds a way for a stale read to
close a question. The trigger above brings it back the first time a case appears. Judgment, not
measured: that one Codex run speaks for melious and for other evidence shapes.

## Review

PLAN gate, Normal depth (instructions an agent loads, so never Light; not High: no auth, data,
secrets or deploy). No red team (no box, user data, logins, money, deletion or schema). Trail:
`REVIEW-plan-2026-10-27-readback-evidence.md`.
