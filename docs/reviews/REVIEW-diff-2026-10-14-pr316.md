# DIFF review — karero/croftweaver#316 — brand-kit: the small follow-ups of #301, in one sweep

Base `ebc3f39` (origin/main after the merge at `b6fddb4`) · depth: Normal (Codex and GLM 5.3; not the High of the skill's first gate: nothing here changes what the SVG allowlist accepts; a palette row now read can change the colour of a `currentColor` mark, as any palette edit can; the owner may ask for High) · verdict: open · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY — atom A each (this session opened the PR, made the worktree and made the branch)

| Round | Head | Artifact (full / delta since) | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `eb3a086` | full (78,169 bytes: a context note with the test record, then the diff) | Codex: gpt-6.1-sol, config effort, read-only; GLM 5.3 on melious.ai (text only) | codex 457 s, 111,876 tokens; glm 792 s, 70,358 tokens | 4 / 2 / 4 |
| 2 | `37a246c` | delta since `eb3a086` on this PR's own files (31,344 bytes), round 1's findings and the author's record as `--verify` | the same, Codex at medium | codex 259 s, 167,628 tokens; glm 532 s, 42,420 tokens | 1 / 2 (one finding, both seats) / 2 (one finding, both seats) |
| 3 | `62279f4` | delta since `37a246c` on this PR's own files (11,164 bytes; `docs/reviews/` left out), round 2's findings and the author's record | the same | codex 182 s, 48,451 tokens; glm 202 s, 19,409 tokens | 2 / 2 (one finding, both seats) / 2 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| S1 | BUG | Codex | 1 | the `--!>` comment scan was still quadratic: each `-->` search ran past a comment that ended at `--!>` (440 KB took about 17.6 s) | fixed; locally_verified | one regex search finds whichever end comes first; a new timing case, a megabyte of `--!>` comments with no `-->`, took 41 s on the round-1 code and passes now |
| S2 | BUG | Codex | 1 | the held Ctrl-C was handed on with `None` for the frame | fixed; locally_verified | the frame the press came in is kept and handed on; the test's handler checks it; the test fails on the round-1 code |
| S3 | BUG | Codex | 1 | the import note quoted a hidden character as `<U+200B>` without the note that explains it | fixed; locally_verified | the note goes through `_noted` too; a test with `@import url("a​b.css")`; fails on the round-1 code |
| S4 | BUG | Codex | 1 | the author's depth rationale said no change reaches the installed SVG; a palette row newly read after `--!>` can colour a `currentColor` mark | fixed (the rationale, in the PR text and this trail) | the allowlist is unchanged; the PR now names this effect and leaves High to the owner |
| S5 | RISK | GLM | 1 | the `namespaces` refutation rests on a quotation the diff does not verify | refuted | the sentence was read from https://www.w3.org/TR/selectors-4/ on 2026-10-14 (fetched and searched for "default namespace"), section 5.3; the BUGLOG row now names the URL and the date |
| S6 | RISK | GLM | 1 | the new Ctrl-C test uses `os.kill(pid, SIGINT)`, which on Windows ends the process | fixed | the test is skipped where `os.name` is not `posix` |
| S7 | NIT | GLM | 1 | the guard's message named a cause ("one came back empty") the count does not show | fixed | it prints the count and the results as they came |
| S8 | NIT | GLM | 1 | in the backslash message a tab after the backslash still shows as `<U+0009>`, without the note | refuted | after a backslash the character is the escaped one and is shown exactly, as the line end there is; the note says "take it out", which is the wrong advice for a tab or a line end, so it stays off |
| S9 | NIT | GLM | 1 | "put the character itself … (but & as &amp; …)" contradicts itself for those two | fixed | "(but write & as &amp; and < as &lt; …)" |
| S10 | NIT | GLM | 1 | SKILL.md grows further past the 500-line soft budget | open, for the owner | the 30-line trim is its own BUGLOG row (round 6's follow-up), not this sweep |
| S11 | BUG | Codex | 2 | the trail's merge note said main's bug log had 141 lines; it has 140 (the author's script counted the empty piece after the last line break) | fixed | the note says 140; the preservation itself was confirmed |
| S5 again | RISK | Codex, GLM | 2 | the namespaces refutation still rested on a quotation, with no browser evidence | refuted, now with a measurement | Chromium 153 and Firefox 155 (Playwright, a page with `:root { --bg: red }` and `html { ... }`): with no `@namespace`, with the page's own XHTML namespace as default, and with only a prefixed namespace, both rules apply; with another default namespace (`http://example.com/foo`) neither applies. So `:root` alone is bound by a default namespace, as the sentence says; the BUGLOG row now gives the measurement |
| S8 again | NIT | Codex, GLM | 2 | after a backslash a tab or form feed still shows as `<U+0009>` or `<U+000C>` with nothing saying what it is | fixed | the quote still shows the character exactly; the message now adds which blank each such mark is ("In the quote, <U+0009> is a tab: the character after the backslash, as the file has it."), without the "take it out" note; a test for a tab, a form feed and a line end |
| S12 | BUG | Codex (GLM as NIT) | 3 | `_blanks_named` read the shown quote, so the six letters `<U+0009>` written in a file were named a tab | fixed; locally_verified | it reads the raw characters; a regression with the letters written out names no blank |
| S13 | BUG | GLM | 3 | the trail's count still said 141 | refuted | the trail says 140 since `62279f4`; round 3's artifact left `docs/reviews/` out, so the seat could not see it |
| S5 a third time | RISK | Codex, GLM | 3 | the browser measurement was narrated, not shown | answered | the probe script and its whole output are now in this trail ("The namespace probe" below) |
| S14 | NIT | GLM | 3 | the carriage return was named in the row and not tested | fixed | the test drives a carriage return too |

Waivers and deferrals: none yet.

Test record (outputs kept by the author): the brand-kit suite on a copy of the tree, `sharp` from a scratch install of the starter (Node 26.11.1), a python3 with Pillow first on PATH. Before round 1, at `eb3a086`: Python 3.9.6 with `REQUIRE_SHARP=1`, 1,080 tests OK (4 skipped by design); Python 3.13.16, 1,080 OK (4 skipped); the two real-site tests (`BRAND_KIT_E2E_SITE` on the throwaway starter) OK. Before the change, origin/main on Python 3.9.6 without `sharp`: 1,074 OK (156 skipped).

Merge of main at `007faae`: main added one row (the pages.dev reading guide) among the rows this PR closes. Resolved by keeping this PR's six closed rows and putting main's row after the `want_logo` row, where main has it. Checked by script: the file has main's 140 lines, no row of main is missing, and the 19 lines that differ differ only in their Status cell.

After round 2's BUG (S11), and again after round 3's (S12), auto-merge was turned off, as said; the fixes above came first, then it was set again. The owner wrote "Merge 316" before round 2. Auto-merge was set on CI (the brand-kit tests run there with `sharp` and Pillow required); round 2 runs beside it on round 1's fixes, and a BUG from it before the merge stops auto-merge.

## The namespace probe (S5), as run on 2026-10-14

Run with Node 26.11.1 from a scratch install of the starter (Playwright as the starter pins it), `node nsprobe.mjs`:

```js
import { chromium, firefox } from "playwright";
const css = (ns) => `${ns}
:root { --bg: rgb(255, 0, 0); }
html { --type-sel: yes; }`;
const cases = {
  "no @namespace": "",
  "default namespace = XHTML (the page's own)": '@namespace url("http://www.w3.org/1999/xhtml");',
  "default namespace = another": '@namespace url("http://example.com/foo");',
  "prefixed namespace only": '@namespace svg url("http://www.w3.org/2000/svg");',
};
for (const [label, launcher] of [["chromium", chromium], ["firefox", firefox]]) {
  const b = await launcher.launch();
  const p = await b.newPage();
  for (const [name, ns] of Object.entries(cases)) {
    await p.setContent(`<!doctype html><html><head><style>${css(ns)}</style></head><body></body></html>`);
    const r = await p.evaluate(() => { const s = getComputedStyle(document.documentElement); return [s.getPropertyValue("--bg").trim() || "(unset)", s.getPropertyValue("--type-sel").trim() || "(unset)"]; });
    console.log(`${label} | ${name} | :root sets --bg: ${r[0]} | html sets --type-sel: ${r[1]}`);
  }
  console.log(`${label} version ${b.version()}`);
  await b.close();
}
```

Its whole output:

```
chromium | no @namespace | :root sets --bg: rgb(255, 0, 0) | html sets --type-sel: yes
chromium | default namespace = XHTML (the page's own) | :root sets --bg: rgb(255, 0, 0) | html sets --type-sel: yes
chromium | default namespace = another | :root sets --bg: (unset) | html sets --type-sel: (unset)
chromium | prefixed namespace only | :root sets --bg: rgb(255, 0, 0) | html sets --type-sel: yes
chromium version 153.0.8010.12
firefox | no @namespace | :root sets --bg: rgb(255, 0, 0) | html sets --type-sel: yes
firefox | default namespace = XHTML (the page's own) | :root sets --bg: rgb(255, 0, 0) | html sets --type-sel: yes
firefox | default namespace = another | :root sets --bg: (unset) | html sets --type-sel: (unset)
firefox | prefixed namespace only | :root sets --bg: rgb(255, 0, 0) | html sets --type-sel: yes
firefox version 155.0
```
