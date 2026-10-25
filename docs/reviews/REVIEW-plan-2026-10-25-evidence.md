# Review trail: plan for `--evidence <file>` (PLAN gate, Normal)

Artifact: `docs/reviews/SKILL-PLAN-review-evidence.md`. Depth Normal: Codex (gpt-6.1-sol) + GLM
5.3 on melious, fresh-eyes (Sonnet) in round 1. No red team: the change touches no box, user
data, login, money, deletion or schema. Gate id 20261024T221701Z-6538.

## Round 1 (uncommitted draft, 2026-10-25)

reviewers: codex OK, melious FAILED ("HTTP 200: Insufficient balance for request. Required: 93,
Available: 0"), ollama-cloud FAILED (quota). Only Codex counted: the second seat is owed.
timings: codex 275s (110,055 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F1 | codex | BUG | "the same diff with the evidence appended is refused, as today" is false: `diff_headers.pl` ignores text after the last hunk. | Confirmed by a probe (same `base:` line, exit 0, with and without a four-line appendix). Fixed: Why now says the case-study session used `--base none` because SKILL.md step 2 says so for a diff not made by `git diff`, and that the check would in fact have passed; the base-check test now gives the evidence a `diff --git` record the check refuses, so a leak would fail the run. The parser's leniency is a BUGLOG row (2026-10-25). |
| F2 | codex | RISK | The size test cannot protect the paste cut-off: Codex succeeds and the script exits before it. | Fixed: a second size run with every seat failing checks exit 4 and the "paste prompt is not printed" line. |
| F3 | codex | RISK | Order checks with wording and evidence together cover only codex and ollama; agy could put evidence before the wording paragraph and pass. | Fixed: the three plain-diff runs (default, agy, all failed) use `--evidence --wording-pass`, so every tier shows the wording paragraph before the evidence; Guards narrows the PLAN/VERIFY placement claim to codex and ollama. |

Fresh-eyes (Sonnet, on the plan with F1–F3 fixed): 248s, 192,223 tokens.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F4 | fresh-eyes | BUG | The size case cannot show "codex runs": the test's stub model `stub-codex` has no `seat_limits.txt` line, so codex keeps the 120,000 limit and FAILS. | Fixed: the case goes through case 38's `limitcase` with a `codex stub-codex takes:1040000` line; its all-failed half needs no stub failure, since seats with no line fail on size. |
| F5 | fresh-eyes | RISK | Order checks look at the lead's first line only, so its data sentences could be cut and every check pass. | Fixed: the lead's six lines are written out in the test and checked as one block, as in 25c. |
| F6 | fresh-eyes | RISK | Evidence lines are unprefixed, so the quota classifier can read an evidence log line as a quota error of a seat that failed for another reason. | Re-sorted: today's behaviour for every plan, and the FAILED section already says to treat a line from the reviewed material as a setup failure. Stated under Guards; not changed. |
| F7 | fresh-eyes | NIT | The END-marker refusal misses a trailing CR or blanks, and the plan overstates what it stops. | Fixed: matched after removing trailing spaces, tabs and CR; plan says it catches accidents, not attackers; a CR case added. |
| F8 | fresh-eyes | NIT | How 3's order sentence put the evidence lead among "scope paragraphs". | Fixed: wording. |
| F9 | fresh-eyes | NIT | Size messages are grepped by T11 and T13; plan did not say they stay unchanged without evidence, nor list every "artifact plus prior findings" comment. | Fixed: How 5 and Docs. |
| F10 | fresh-eyes | NIT | `evidence:` byte count ambiguous (file bytes or as read). | Fixed: counted as read, like CONTENT_BYTES; test uses a file ending in a newline. |
| F11 | fresh-eyes | NIT | SKILL.md's Output sentence and step 8 list the closing lines. | Fixed: Docs adds `evidence:` to both. |
| F12 | fresh-eyes | NIT | No plan + `--evidence` run, so placement against the guards paragraph is unchecked. | Fixed: Tests add it. |

Round 2 is earned by F1 and F4 (substantive BUGs).

## Round 2 (verification, plan at b9464469)

reviewers: codex OK (effort medium), melious FAILED (balance 0), ollama-cloud FAILED (quota).
timings: codex 94s (64,510 tokens). Codex confirmed F1–F12 as fixed in the plan.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F13 | codex | BUG | The new Guards note said diff lines "never count" for the quota classifier; a CR inside a diff line can bring error-shaped text to column 0 after `readable_tail.pl`. | Fixed: wording ("ordinary diff lines … do not count", the CR case named). Prose about today's behaviour, no design change: not substantive, so it earns no round; it goes to the wording pass. |

The rounds end here (no substantive BUG or earning RISK in round 2).

## Final full read (plan at d23b5561)

GLM 5.3 and Kimi had no seat (melious balance 0, ollama quota), so the read was a stronger
host-family pass: a fresh Opus sub-agent that had not seen the plan or the trail. 383s, 223,288
tokens.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F14 | full read | RISK | The host's own seats (fresh-eyes, a host final read) do not go through the script, so they would never see the evidence; before, the hand-made appendix reached them. | Fixed: Docs adds SKILL.md steps 3 and 6: give them the same file under the same lead. Earning: it changes what the host does. |
| F15 | full read | BUG | "a fact the closing lines and the trail already give": closeout's round row has no place for evidence, and closeout deletes the raw folder. | Fixed: Docs adds closeout's round row (Artifact column records the `evidence:` line); How 10 reworded. |
| F16 | full read | BUG | The quota-classifier note still overstated diff immunity: an added or removed line counts when its second word is error or fatal (grep probe). | Fixed: moved to "Known limit, not changed" with the classifier's real reach. Second time this sentence was wrong; this time taken from the agent's probe of the regex. |
| F17 | full read | BUG | "T11 and T13 grep" both size messages: only the `seat_fits` one is grepped. | Fixed: How 5 says which; T13 gains a grep of the paste message's no-evidence wording. |
| F18 | full read | NIT | "Every refusal comes before the base check" is untested. | Fixed: narrowed to "before any seat runs and before anything of the artifact or evidence leaves the machine". |
| F19 | full read | NIT | The FAILED caveat names only "the reviewed artifact". | Fixed: How 11 adds "or evidence". |
| F20 | full read | NIT | `--evidence -` and an empty value unspecified. | Fixed: refused, as `--verify` and `--base` refuse theirs; tests added. |
| F21 | full read | NIT | The closing line says "material to review"; the lead says not under review. | Fixed: the lead says "material to read, not the text under review". |
| F22 | full read | NIT | Size remedies still say only "split the artifact". | Fixed: "or trim the evidence" with evidence. |
| F23 | full read | NIT | The bracketed list of "artifact plus prior findings" comments missed one. | Fixed: list dropped; "every comment" stands. |
| F24 | full read | NIT | The lead's second line holds `${TYPE}` twice; a copied 25c helper replaces once. | Fixed: Tests say replace every place. |
| F25 | full read | NIT | "line references below" but the plan has none. | Fixed: clause dropped. |

Round 3 is earned by F14 (an earning RISK) and F15 (a BUG that changed the Docs list).

## Round 3 (verification, plan at d67657c3)

reviewers: codex OK (effort medium), melious FAILED (balance 0), ollama-cloud FAILED (quota).
timings: codex 119s (57,035 tokens). F14–F25 confirmed fixed except the two below.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F26 | codex | BUG | The known-limit note still says context lines "never count"; a CR inside one brings error text to column 0 after `readable_tail.pl`. | Cut: third finding on this note (F13, F16, F26). It describes today's code and decides nothing in the plan, so it no longer says which lines count; it keeps the limit and points at How 11's caveat. |
| F27 | codex | BUG | "as `--verify` and `--base` refuse theirs": `--verify` accepts a value starting with `-`. | Fixed: compared with `--base` only; `--verify` refuses only an empty value. |

Both are prose about today's behaviour with no design change: not substantive, so the rounds end
here, and they go to the wording pass.

## Wording pass (plan at df331224)

Run with `--wording-pass --seat codex --verify` (F26, F27 and the changed sections), the
build's own flag, from this branch. reviewers: codex OK; timings: codex 51s (25,644 tokens).
No BUG/RISK/NIT findings.

## GLM 5.3 seat (plan at e2e6202b, whole plan, after melious was topped up)

`--seat melious`, MELIOUS_MODEL=glm-5.3, no `--round` (the owed second seat, full scope).
timings: melious 181s (23,675 tokens). No BUG.

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F28 | melious | RISK | The base-check tripwire (evidence opening with a `diff --git` record) is asserted, not probed; the parser ignores text after the last hunk. | Refuted with evidence: the final full read probed exactly that input, appended and prepended: refused, exit 1. The plan now cites the probe. |
| F29 | melious | NIT | The evidence block is checked by one line, so a truncated block would pass. | Fixed: Tests check the file's first line right after BEGIN and its last right before END. |
| F30 | melious | NIT | Trailing spaces and tabs on the END marker are never tested. | Fixed: a refusal case with trailing spaces and a tab. |

No substantive BUG or earning RISK: no further round. The edits are prose, confirmed below.

## Prose-only re-gate of F28–F30 (delta e2e6202b..617fedab, `--wording-pass --seat codex`)

timings: codex 179s (68,371 tokens).

| # | Seat | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| F31 | codex | BUG | "refused with exit 1" mixes the parser's status with the run's: `independent_review.sh` turns `diff_headers.pl`'s 1 into a refusal with exit 2. | Fixed: the plan names both. A wording contradiction, not substantive; confirmed below. |

Confirmation of F31 (delta 617fedab..df31f520, `--wording-pass --verify --seat codex`): codex
44s (28,499 tokens), No BUG/RISK/NIT findings.

## State

Clean at Normal depth on df31f520. Rounds 1–3 (Codex; GLM 5.3 had no credit until after round
3 and then reviewed the whole plan once), fresh-eyes in round 1, a final full read (Opus), a
wording pass, the GLM seat, two prose re-gates: 31 findings, every one fixed, refuted with
evidence or re-sorted (F6). Waiting for the owner's go to build.
