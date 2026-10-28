# Review trail: plan, contact form takes a page's own fields and a hint

Artifact: `docs/reviews/SKILL-PLAN-contact-form-fields.md`. PLAN gate, Normal depth (a SKILL.md,
a shipped component and spec, a CI job; no High-row item). Seats: Codex and GLM 5.3 on melious,
run as one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`). No red team: the change stores
nothing, touches no login, money or deletion, and leaves the script that builds the mail as it is.

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex alone. melious FAILED (error mid-stream (HTTP 200); quota/rate limit) | 1 BUG, 3 RISK; 4 UNVERIFIABLE groups, all looked at | Codex 312 s, 44,867 |
| 2 | Codex alone (`--verify`). melious FAILED: "Insufficient balance for request. Required: 110, Available: 0" | 1 BUG, 2 RISK; F1, F3, F4 and U4 confirmed | Codex 236 s, 45,902 |
| 3 | Codex alone (`--seat codex --verify`; melious still at balance 0) | none; every round-1 and round-2 disposition confirmed | Codex 112 s, 42,242 |

Total, rounds 1–3: 2 BUG, 5 RISK, no BUG open. Every round ran on Codex alone: the second seat was out of balance all morning. U1 and U2 stay pending until the build's starter run, before DIFF round 1.

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| F1 | BUG | Codex | "every filled field" overstates: a `select` with an empty-valued "Please choose" option sends its text as an answer | fixed: the plan claims the script fits the recommended fields only; SKILL.md asks a choice with radios and gives a list no empty entry | Codex's VM run of `mail-form.js`: `Town: Choose a town` |
| F2 | RISK | Codex | A paired `<MailForm>…</MailForm>` on the home page breaks the job's self-closing greps and its three break-the-build edits | fixed: the filled form goes on the German `/impressum` page; the home page's form stays self-closing | `template-tests.yml` last step edits `src/pages/index.astro` only |
| F3 | RISK | Codex | No CI test ticks a radio, so dropping the radio branch of the script would pass | fixed: CI installs the SKILL.md page spec, which checks the exact body with a radio ticked | plan, CI paragraph |
| F4 | RISK | Codex | The Tab test starts with `order[0].focus()`, so a field missing from the front of `ADDED` passes | fixed: the test starts from a `tabindex="-1"` point inserted before the form | plan, spec paragraph |
| U1 | — | Codex | Astro scoping and `:global` claims unverified | pending until the build: the client build's attributes are quoted in the plan; the starter run before DIFF round 1 records the compiled selectors and a slotted input's computed width and border (R2-2) | plan, "How" and "How it is tested" |
| U2 | — | Codex | Browser behaviour (radio Tab stop, accessible description, CSS hint) unverified | pending until the build: the starter run and its mutations before DIFF round 1 show each (R2-3) | plan, "How it is tested" |
| U3 | — | Codex | Research quotes lack citations | fixed: URLs and quoted lines, read 2026-10-27; the nine-site survey marked not re-checked and kept out of SKILL.md | plan, "What and why" |
| U4 | — | Codex | Client branch evidence missing | narrowed: the plan no longer leans on the client site as a test | plan, "How it is tested" |

## Round 2

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| R2-1 | BUG | Codex | F2's fix keeps the home page's greps, but the German page's install grep also wants a self-closing tag | fixed: the plan changes the German install line and its grep to the paired form | `template-tests.yml:526` and `:537`; Codex reproduced exit 1 |
| R2-2 | RISK | Codex | U1 recorded as answered on author evidence; the `:global` reach is not shown | accepted: U1 is pending until the build, which records the compiled selectors and computed styles before DIFF round 1 | U1 row |
| R2-3 | RISK | Codex | U2 and F4's runtime behaviour (focus point, radio stop, description, CSS hint) not shown | accepted: pending until the build's starter run and mutations | U2 row |
