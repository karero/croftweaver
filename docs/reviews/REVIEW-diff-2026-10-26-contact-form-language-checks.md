# DIFF review — contact form: a missing word for "dot" fails the spec; privacy page step

Branch `fix/contact-form-language-checks`. Depth: **Normal**. The diff edits a SKILL.md and a
test template copied into users' sites, both never Light; no privacy text itself changes, so not
High. Seats: Codex (gpt-6.1-sol, read-only) and GLM 5.3 on melious, run as two commands with the
same `--round`.

`make check` passed before round 1 (exit 0). Both form specs (English `/`, German `/impressum`)
ran on a site set up as the `contact-form-skill` CI job sets it up: 29 of 30 passed; the one
failure, the tracker test in the German spec, a test this diff does not touch, passed 6 of 6 on
rerun at load 75. Mutant: `de: 'punkt'` removed from `DOT_WORD` turns the German spec's
no-JavaScript test red with the new message; the English spec stays green.

## Round 1, first run — not counted
Run against `d10802cc` (main after #417) while the branch sat on `8a0d6ea3`, so the diff held
#417 reversed (51,922 + 29,980 tokens). Kept from it: Codex's BUG on the BUGLOG row, fixed below.
Its other findings were on #417's files. Melious's BUG that `en-US` or a missing `lang` would
misfire is refuted: `MailForm.astro` keeps the first part of the code (line 38) and always sets
it on `.mail-form-direct` (line 58).

| id | sev | seat | status | why |
|---|---|---|---|---|
| C1 | BUG | codex | fixed | The row said to copy the new spec over a site's own, which loses the site's changes, such as the field order §2 step 5 asks for. It now says to add the new lines by hand |
| M1 | BUG | melious | refuted | See above |

## Round 1 — `aa937dba`, base `ee7cecb7`
`codex OK` 128s (29,124 tokens) · `melious OK` 224s (15,473 tokens). No findings from either seat.
Their unverifiable points are settled above (the browser run and the mutant) and in SKILL.md
(§4 and §2 step 5 exist and say what the step and the row cite).
