# DIFF review — whats-new `--refresh` copies the committed skills

Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`: `scripts/whats-new.sh`
(the refresh copy), `scripts/test_whats_new_removed_skill.sh` (cases 8b, 8c, 8d), one README
sentence on symlinked installs, and two BUGLOG status cells. Depth: Normal (Codex + GLM 5.3 on
melious, fresh-eyes Sonnet in round 1). Gate id 20261112T080819Z-29060. Later rounds sent the delta
from the previous head with `--verify` and the earlier findings with their answers.
Checks: both whats-new test scripts passed at every head; each round's evidence file holds the
mutation runs (every mutation killed). `make check` runs before the push, in a slot the manager
hands out.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | b4ced81c | full diff | codex, melious, fresh-eyes | codex 133 s, 41,580; melious 247 s, 19,715; fresh-eyes 104,006 | 2/2/2 |
| 2 | c2f90cff | delta, `--verify` | codex, melious | codex 150 s, 64,237; melious 151 s, 16,718 | 2/1/2 |
| 3 | 728c2bd5 | delta, `--verify` | codex, melious | codex 115 s, 60,133; melious 281 s, 18,495 | 0/2/1 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| C1 | BUG | codex | 1 | `git archive` honours export-ignore, so the refresh could stamp HEAD over a thinned copy | fixed | the copy no longer uses `git archive`; test 8b puts `SKILL.md export-ignore` in the clone's `.git/info/attributes` and checks SKILL.md arrives |
| C2 | BUG | melious, fresh-eyes (F1, RISK) | 1 | the old copy was deleted before the new one existed, so a failed copy left the site without the skill | fixed | built in `.<skill>.refresh` beside the old copy and swapped in only when complete; test 8c |
| C3 | RISK | melious | 1 | the failure guard depends on pipefail, set outside the diff | refuted | `set -euo pipefail` at the top of the script; the mutation that drops pipefail fails seven cases |
| C4 | NIT | melious, fresh-eyes | 1 | the second new case had no 8c label | fixed | `# --- 8c.` header |
| F2 | NIT | fresh-eyes | 1 | BUGLOG wording beside an unchanged guard | no action | nothing wrong in it |
| D1 | BUG | codex | 2 | a partial `rm -rf` of the old copy was ignored, so `mv` nested the new copy inside the survivor and the stamp advanced | fixed | the swap refuses when the old path (or a symlink) survives; test 8d, a folder `rm` cannot empty |
| D2 | BUG | codex | 2 | assume-unchanged or skip-worktree hides an edit from `git status`, so copying the clone's files could differ from HEAD | fixed | the copy writes HEAD's blobs through a throwaway index (`read-tree` + `checkout-index`); test 8b marks SKILL.md assume-unchanged with other text and checks the site gets HEAD's |
| D3 | RISK | melious | 2 | same as D2, raised on its own | fixed | as D2 |
| D4 | NIT | melious | 2 | a failing `mv` after the rm leaves no copy | no action | the message names the new copy's folder and the stamp stays; it needs the rm to succeed and a same-folder rename to fail |
| D5 | NIT | melious | 2 | the row's Fix column still says `git archive` | answered | the status cell says why not `git archive`; the Fix column stays as the finding's record |
| E1 | RISK | codex | 3 | `checkout-index` applies checkout conversion, so the copy might not be HEAD's bytes | refuted | run on the real repo for `new-website` (246 files) and `independent-review` (41) with `core.autocrlf` false and true: every file's `git hash-object --no-filters` equals its blob id, executable modes kept, the clone's `ls-files -s` unchanged, `git status` empty. The root `.gitattributes` sets `* text=auto eol=lf` |
| E2 | RISK | melious | 3 | a relative site path would put the staging folder and index inside the clone | refuted | the script makes the site path absolute (`PROJECT="$(CDPATH= cd -- "$PROJECT" && pwd -P)"`) before `process_dir`, so `skills_dir` is always absolute |
| E3 | NIT | melious | 3 | after a partial rm the "could not replace" message implies the old copy is whole | fixed in 24c5e2e0 | the message now says the copy may be partly removed and to restore it from the site's git history; test 8d checks the words. A message and one check, not sent to a fourth round |

Outside scope (melious, round 3, unchanged lines): the leftover-folder `rm -rf` ignores its own
failure, as D1 did. Not a finding of this change; filed as a BUGLOG row in this branch. The second note, that
8b leaves lines in the fixture's `.git/info/exclude` and attributes, concerns a throwaway fixture
repo the test builds itself: nothing else reads them.

UNVERIFIABLE (round 3): symlinks in a skill. No skill in the suite has one
(`git ls-files -s skills` shows no mode 120000), so the claim was dropped from the record rather
than tested.

Result: CLEAN, 3 rounds, 13 findings (4 BUG, 4 RISK, 5 NIT; F1 counted with C2), 220,878 tokens logged by the gate
plus 104,006 for fresh-eyes.
