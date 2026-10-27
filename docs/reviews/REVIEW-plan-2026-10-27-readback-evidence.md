# Review trail: PLAN gate, SKILL-PLAN-review-readback-evidence.md

Gate: PLAN, depth Normal (a plan for a review prompt's wording and its tests). Seats: Codex and
GLM 5.3 on melious as one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`); fresh-eyes on
Sonnet (host family, one size down) in round 1. No red team (no box, data, money or deletion).

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
| 1 | plan at b6324240, evidence = script/test/SKILL.md/trail excerpts | codex OK (147 s, 51,833 tokens); melious FAILED (balance: "Available: 0"); fresh-eyes OK (~98k tokens) | 2 BUG, 4 RISK, 4 NIT (F1-F10; F3 and F4 from both) | all fixed in the next revision; F5 led to a probe (below) |
| 2 | plan at 1c015575, `--verify` F1-F10 | codex OK (157 s, 52,705 tokens); melious FAILED (balance, "Available: 0") | 1 BUG, 3 RISK (G1-G4) | G1 fixed; G3 accepted, which cut the scope: the lead change became a follow-up, so G2 and the lead half of G4 lapse; the rest of G4 fixed |
| 3 | plan at 9f52eb15, `--verify` G1-G4 | codex OK (97 s, 54,889 tokens); melious FAILED (balance, "Available: 0") | 1 BUG, 1 RISK (H1-H2) | both fixed; both are claim wording, not design, so no round 4 is owed; wording pass next |
| probe (not a round) | `docs/reviews/probe-readback-evidence/artifact.md` + `evidence.txt` (a real `gh api` read of the "main checks" ruleset) under today's lead | codex OK (60 s, 31,043 tokens) | see the plan's Why | baseline for the build's rerun |

Round 1 counts as codex alone. melious FAILED (balance, "Insufficient balance … Available: 0");
fresh-eyes ran beside it.

UNVERIFIABLE entries, round 1: codex 3 (seat behaviour under the new lead; the intake session's
28; pr285's round-2 input and pr227's read timing), fresh-eyes 1 (seat behaviour). None confirmed
as a finding; the first is what the probe and the build's rerun measure.

Round 1 findings, one line each:

- F1 BUG (codex): "SKILL.md never says where a read belongs" is wrong; step 2 already sends command output to `--evidence`. Fixed: Why now says it names no remote read and no resend.
- F2 BUG (codex): "no seat has network" is wrong; pr285's fresh-eyes had web access. Fixed: external seats have none, a host fresh-eyes pass may.
- F3 RISK (codex, fresh-eyes): a source, a time and "verbatim" do not make a read authentic, and "settles" shuts off challenge. Fixed: the lead calls a READ what the system held, keeps asking for a claim beyond it, a stale one, or one that conflicts with other evidence, and says an entry missing source, time or output is not a READ.
- F4 RISK (codex, fresh-eyes): the stop-loss cannot see over-acceptance, since seats do not say what they settled on a READ. Codex also asked for a baseline for "as often as before". Fixed: the lead asks seats to list each claim settled on a READ; the step-4 sentence puts that count, and any the host found wrong, in the trail row; the old-lead probe answer is the baseline.
- F5 RISK (fresh-eyes): no case shows a seat ignoring a read it was sent; every case predates `--evidence`. Probed: one Codex run under today's lead with a real ruleset read (the plan's Why). It used the read but still asked for live state. The plan now says so, and the build reruns the probe under the new lead.
- F6 RISK (fresh-eyes): the `SKILL.md` sentences have no test, and "as many lines as there are" could be read from the script. Fixed: a hand-written `grep -F` per sentence, the count taken from the hand-written list, and a mutation check.
- F7 NIT (fresh-eyes): the 28 is not supported. Fixed: marked as resting nothing.
- F8 NIT (fresh-eyes): pr227 F23 "rounds 1 to 9" was inferred. Fixed: "every round (the review ran nine rounds)", checked in the trail's round table.
- F9 NIT (fresh-eyes): no rule for secrets in a read. Fixed: "secrets replaced with made-up values".
- F10 NIT (fresh-eyes): the step-4 sentence clashed with step 5's "stays OPEN". Fixed: "one the host cannot read stays open, as step 5 says".

Round 2 findings, one line each (F1, F2, F7-F10 verified by codex; F3-F6 partly, see below):

- G1 BUG (codex): the probe's READ 1 shows its jq filter shortened (`rules:[...]`), so its source cannot be rerun as written. Fixed: `read-command.txt` holds the full command; rerun on 2026-10-27 gave the same output byte for byte. `evidence.txt` stays as sent.
- G2 RISK (codex, re-raise of F3): source, time and "verbatim" still promote the host's word to fact. Lapsed: the plan no longer changes the lead; the candidate text in its follow-up adds "doubtful provenance".
- G3 RISK (codex): the probe shows no redundant question; Codex asked only for what the read lacked. Accepted: the plan now says so, drops the lead change to a follow-up with a trigger, and keeps the `SKILL.md` placement sentences.
- G4 RISK (codex): the two grep anchors survive deleting other clauses. Fixed: three anchors, one per instruction kept, and the plan states the guarantee as "each phrase present, not the whole wording".

Round 3 findings (G1, G3, G4 verified; G2 lapsed as recorded):

- H1 BUG (codex): "its one UNVERIFIABLE entry" is wrong; the probe answer has two (lines 15, 16). Fixed: the GitHub entry described, the hook entry named.
- H2 RISK (codex): "failed because the read never reached a seat" is a cause the trails do not show. Fixed: called a hypothesis, with what tests it.

UNVERIFIABLE, round 3: codex 1 (the rerun's time and byte match have no kept capture). The
rerun is in this session's record; not a finding.

Melious ran in no round (balance "Available: 0" each time): rounds 1 to 3 count as codex alone.
