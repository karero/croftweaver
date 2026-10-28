# Review trail: plan, greeting and sign-off in the contact form's mail

Artifact: `docs/reviews/SKILL-PLAN-contact-form-greeting.md`. PLAN gate, Normal depth (a
SKILL.md, a shipped component, script and spec, a CI job; no High-row item). Seats: Codex and
GLM 5.3 on melious, one command. No red team: nothing stored, no login, money or deletion.

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex alone. melious FAILED: "Insufficient balance for request. Required: 77, Available: 0" | 3 RISK; 4 UNVERIFIABLE groups, all looked at | Codex 139 s, 56,031 |
| 2 | Codex alone (`--seat codex --verify`) | none; G1 to G3 and V4 confirmed | Codex 79 s, 44,968 |

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| G1 | RISK | Codex | SKILL.md edits omit `GREETING` in step 4, the prop in both examples, and the page spec's bodies | fixed: the plan lists each | plan, "SKILL.md" |
| G2 | RISK | Codex | "takes the new spec" would lose a site's `PAGE`, `TO`, `SUBJECT`, `LANG`, `ADDED` and edits | fixed: the spec is merged by hand, settings kept | plan, "BUGLOG" |
| G3 | RISK | Codex | "the mail program shows the whole mail" is unmeasured; a cut long link loses the sign-off first | fixed: qualified, pointed at the existing length row, said in §5 | plan, "The visitor sees it" |
| V1 | — | Codex | `npm run check` failing on a missing `signoff` needs `Texts` extended | answered: the build adds `signoff` to `Texts`; shown by removing it once before DIFF round 1 | plan, "How it is tested" |
| V2 | — | Codex | build rejection, encoding, mutations are future results | pending until the build | — |
| V3 | — | Codex | mail-program signature and editing behaviour | narrowed: the plan claims only that the draft opens, and says the rest was not measured | plan |
| V4 | — | Codex | DIN 5008 and British usage unsourced | fixed: the claim dropped; the punctuation is the maintainer's choice | plan |
