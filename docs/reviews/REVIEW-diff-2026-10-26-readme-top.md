# DIFF review — README top: screenshot, finished site, quick install

Branch `claude/readme-top-3335af`. Depth: **Normal** (README text ships to users in the zip and
the plugin-directory branch; no code, guard or script changes). Seats: Codex (gpt-6.1-sol,
read-only) and GLM 5.3 on melious, run as two commands with the same `--round`; fresh-eyes
(Sonnet sub-agent) in round 1. Evidence file sent with `--evidence` (installer output line, the
unchanged npm-create section, live page titles, screenshot source, the author's decisions).

`make check` passed before round 1 (exit 0); `make test-plugin` 30 pass, 0 fail, 1 skipped (the
release-tag-only test).

Not in the diff, by decision: a direct link to the site's repository. `scripts/check_clean.sh`
allows the owner's GitHub name only in this project's own repo reference, and the first `make
check` failed on that link. The case-study page links that repository's pull requests instead.

## Round 1 — `8ab12d98`, base `4b5b927c`
`codex OK` 1358s (41,247 tokens; machine load near 240) · `melious OK` 100s (8,989 tokens) ·
fresh-eyes 67s (104,856 tokens)

| id | sev | seat | status | why |
|---|---|---|---|---|
| C1 | BUG | codex | fixed | The image was a relative path; `scripts/build_directory_tree.sh` keeps README.md but not `docs/images/`, so the plugin-directory copy showed a broken image. Now an absolute raw.githubusercontent.com URL on `main`, which the zip, GitHub and the directory copy all load; the release script is untouched |
| F2, M1 | RISK | fresh-eyes, melious | fixed | Same as C1 |
| F1, M3 | RISK, NIT | fresh-eyes, melious | fixed | The top block said only "Node 22.12 or newer" and dropped the existing caveat that building needs a newer Node; the caveat is back, linking the setup guide (SETUP.md:84 names the floor) |
| F3 | NIT | fresh-eyes | fixed | Image and the next line both linked to /case-study; the image (of the home page) now links to the home page |
| M2 | NIT | melious | refuted | `npm create croftweaver` appears twice. The brief asked for the quick install near the top and allowed repeating it; the top block sends readers to the full section |
| F4 | NIT | fresh-eyes | no change | The reviewer's own note: the anchor and claim hold |
