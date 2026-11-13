# DIFF review — og-cards: stop when no font is installed (#556)

Base `a5fc9f25` · depth: Normal (the starter's generator ships to every site, plus a CI step) ·
verdict: CLEAN after 3 rounds, 10 distinct findings (later rounds repeated F2 and F4); one BUG overruled by the maintainer ("Merge as is") ·
gate id 20261113T223737Z-28176.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `761e7a9b` | full | Codex (medium); melious (glm-5.3); fresh-eyes (Claude Sonnet sub-agent) | codex 163 s, 64,930; melious 240 s, 24,709; fresh-eyes 36 s, about 96,000 | 3 / 2 / 4 |
| 2 | `19c68244` | change, `--verify`, `--base 761e7a9b` | Codex (medium); melious (glm-5.3) | codex 185 s, 55,352; melious 150 s, 12,112 | 1 / 1 / 1 (new) |
| 3 | `fc4d9e44` | change, `--verify`, `--base 19c68244` | Codex (medium); melious (glm-5.3) | codex 144 s, 34,009; melious 46 s, 4,650 | 1 / 1 / 1 (repeats and new) |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 1 | The new CI step ran from the workflow's default folder (`skills/new-website/templates/astro`), where the test path does not exist. | fixed | `working-directory: .`. CI's first run failed at exactly this step. |
| F2 | BUG | Codex | 1–3 | The brand-kit installer reports only the last line of a generator failure, so the stop's message lost its cause and the font paths. | fixed in part; rest overruled | Round 1: the last line stands alone (119 characters, under the installer's 200; a test asserts it). The paths still do not reach the installer's report. Host: the report ends "When that is put right, run: npm run og" (`_install.py:1293`), and that run prints the full list. Codex held it as a BUG in rounds 2 and 3. The maintainer, asked: "Merge as is"; BUGLOG row added. |
| F3 | BUG | Codex | 1 | The CI comment said nothing else runs the generator; the brand-kit e2e test does. | fixed | Comment reworded. |
| F4 | RISK | melious, Codex | 1–3 | CI assumed the runner image has a listed font. | fixed | The step installs `fonts-dejavu-core` first; `OG_FONTS_REQUIRE_FONT=1` fails the step if no pair resolves. |
| F5 | RISK | melious | 1 | Other callers might now fail on a machine with no font. | refuted | Fresh-eyes traced every caller: the installer (reports the failure), `_reads_generator` (loads the module, `main()` not run), `run_og.mjs` (passes the exit code through). |
| F6 | NIT | melious | 1 | `--check` might write nothing, so "no card written" could not fail. | refuted | Codex: `main()` builds every card before it looks at `--check`. |
| F7 | NIT | melious | 1–2 | The missing-font stub covers only `.ttf`/`.ttc`. | not taken | Codex: every candidate is `.ttf` or `.ttc`. |
| F8 | NIT | melious | 1–2 | `font:` prints only the regular file. | not taken | It names the pair by its regular file. |
| F9 | NIT | melious | 1 | The L3f BUGLOG row is outside this fix's scope. | not taken | Called out in the PR body. |
| F10 | NIT | melious | 3 | `apt-get install` without `apt-get update`. | refuted | The step before it runs `npx playwright install --with-deps`, which updates the apt index. |

Notes:
- `make check` on the tree of `ac53540c`: exit 0, "all checks passed"; brand-kit `test_install.py` 239 OK
  (98 skipped), `test_site_edits.py` 130 OK (1 skipped). Not rerun after the later commits (the stop's last line, the CI step, docs); CI covers them.
