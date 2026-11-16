# DIFF review — branch fix/icons-spec-svg-and-logo — the icons test decodes favicon.svg and reads the logo from the page

Base `07211892` · depth: Normal (one starter test; no user data, auth or deploy path) · verdict:
CLEAN after round 3 and a wording pass · authority used: WORKTREE-WRITE and BRANCH-COMMIT. This session (the small
BUGLOG sweep) created the worktree and the branch.

Artifact: round 1 `git diff 07211892...433a8b6f -- . ':(exclude)docs/reviews/'`; round 2 `git diff
433a8b6f..625d9a5c` (same exclusion), with `--base 433a8b6f`; round 3 `git diff 625d9a5c..c366b927`, with
`--base 625d9a5c`. Evidence: round 1
`npx playwright test tests/icons.spec.ts` in a scratch copy of the starter: the new spec on the
starter as it is, the new spec and origin/main's spec on a site with a cut-off `favicon.svg` and no
logo in its structured data. Gate id 20261116T145246Z-81896. Round 1 started before its
`make check`.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `433a8b6f` | full, merge base with origin's HEAD | Codex (gpt-6.1-sol, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 101 s, 31,751; melious 97 s, 7,902; fresh-eyes 58 s, 119,908 | 0 / 3 / 6 after dedup |
| 2 | `625d9a5c` | delta from `433a8b6f`, verify of F1-F9 | Codex (medium); melious | codex 135 s, 56,421; melious 166 s, 17,007 | 1 / 0 / 2 |
| 3 | `c366b927` | delta from `625d9a5c`, verify of F1-F12 | Codex (medium); melious | codex 113 s, 27,731; melious 123 s, 9,422 | 0 / 0 / 3 |
| wording | `78df2270` | `git diff c366b927..78df2270` (same exclusion), with `--base c366b927` | Codex (medium), `--wording-pass` | codex 123 s, 44,039 | 0 / 1 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | RISK | Codex, fresh-eyes (NIT) | 1 | The logo check kept only the URL's path, so a logo on another host, such as `https://wrong.invalid/images/logo.png`, passed and the test fetched the local file. | fixed in `625d9a5c` | A logo off the site's own origin (`SITE.url`) stays a whole address and fails. Case "wrong-origin" fails on the new spec and passes on 433a8b6f's. |
| F2 | RISK | melious, fresh-eyes | 1 | Only a node whose `@type` is exactly `Organization` counted, at the top level or in `@graph`; an array of types, a subtype or a nested node failed a correct site. | fixed in `625d9a5c` | Every `logo` in the JSON-LD counts, at any depth, on a node of any type. Cases "type-array" and "nested" pass on the new spec and fail on 433a8b6f's. `placeholders.spec.ts` line 323 already uses an array `@type`. |
| F3 | RISK | melious | 1 | An SVG with a viewBox and no width or height would decode to 0 x 0 and fail. | refuted | A probe in the starter's Chromium (159.0.8154.6) gives a viewBox-only SVG 150 x 150; the starter's own `favicon.svg` is viewBox-only and passes. |
| F4 | NIT | melious, fresh-eyes | 1 | A structured-data block that is not valid JSON ended the test in a bare SyntaxError. | fixed in `625d9a5c` | The error names the block and says it is not valid JSON. Case "bad-json". |
| F5 | NIT | melious | 1 | An ImageObject logo with no `url` became the site root, `/`, in the failure message. | fixed in `625d9a5c` | Only a URL string, or an ImageObject's string `url`, counts as a logo. |
| F6 | NIT | melious | 1 | The comment on `svgSize` named two outcomes, a size or null, and left out 0 x 0. | fixed in `625d9a5c` | The probe found no 0 x 0 case (F3); the comment now gives the sizes Chromium returns for a sizeless SVG. |
| F7 | NIT | fresh-eyes | 1 | An empty `<svg>` decodes to 300 x 150 and passes. | no change | The spec checks files, not pictures (its header comment). The `svgSize` comment now says an empty SVG passes. |
| F8 | NIT | fresh-eyes | 1 | The ICONS entry's comment still said `COMPANY.logo`. | fixed in `625d9a5c` | It says the logo the page's structured data names. |
| F9 | NIT | fresh-eyes | 1 | BUGLOG row 334 still says open. | deferred to the record step | The Status cells are written after the last round. |
| F10 | BUG | Codex | 2 | F2 half done: an ImageObject's `url` ended the walk, so a logo nested inside it, such as `logo.creator.logo`, was missed. | fixed in `c366b927` | The reader takes the url and walks on. A new test of the reader fails on 625d9a5c's at "a logo inside a logo's ImageObject". |
| F11 | NIT | melious | 2 | An empty logo string became `/` in the message again, as F5 was for. | fixed in `c366b927` | An empty URL is skipped; the reader's test covers it. |
| F12 | NIT | melious | 2 | A logo array inside an array was dropped. | fixed in `c366b927` | Arrays are read at any depth; the reader's test covers it. |
| F13 | NIT | melious | 3 | The reader can return one logo twice. | no change | The check asks that the list contain the logo (`toContain`), so a repeat changes nothing. |
| F14 | NIT | melious | 3 | The comment said "an ImageObject's url"; the reader takes the url of any object under `logo`. | fixed in `207bb5b0` | The comment says so. |
| F15 | NIT | melious | 3 | "Every logo the JSON-LD names" is wider than the reader, which skips a logo given only as an `@id`. | fixed in `207bb5b0` | The comment says it reads logos given as a URL and skips an `@id` alone; the starter writes a URL. |
| F16 | RISK | Codex | wording | BUGLOG rows 334 and 336 said the logo "must be on the site's own origin"; a site with a local logo and an external one still passes, since the check asks only that the list contain `/images/logo.png`. | fixed in `abaf9e1e` | Both rows now say one of the logos must be `/images/logo.png` on the site's own origin, which is what `icons.spec.ts` line 109 checks. The pass's other notes are UNVERIFIABLE items: the cut-off SVG case is the round 1 scratch run ("a cut-off `favicon.svg`" fails the new spec), and the deferral is the maintainer's answer relayed by this sweep's manager session. |

Mutation check on `abaf9e1e` (playwright, `tests/icons.spec.ts`, after setting `SITE.name` and running
`node scripts/make-icons.mjs --setup` as CI's template job does): 5 mutations of the logo reader
(`icons.spec.ts` lines 55-63), all 5 killed, and both baselines passed. The SVG half of the change has
no mutation here; round 1's scratch run is its evidence (origin/main's spec passes a cut-off
`favicon.svg`, the new spec fails it).
