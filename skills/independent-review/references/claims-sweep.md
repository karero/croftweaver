# Claims sweep (Procedure step 2, prose changes)

Read this before round 1 of a review whose change is mostly prose: a docs PR/MR, a runbook, a
status table, a plan. The sweep is advisory. It never blocks a round and never counts as a
reviewer.

## Why

In a prose review the late, expensive findings are usually the author's own: a claim stated
more broadly than its evidence. "X was first deployed at revision R." "The only caller of Y."
"Never seen in production." "Step 4 has not been attempted." On one status-table change of
about 200 added lines, six rounds raised 83 findings, and rounds 3, 4 and 5 each found one or
two claims of this kind, all the author's own.

A per-line `grep` cannot find them reliably: "has not" at the end of one line and "been
attempted" at the start of the next is invisible to it, and one such phrase reached round 5
after a grep had "cleared" that wording. The sweep reads each paragraph, list item, heading
and table cell as running text, then lists the sentences the change adds that use a word of
absence or universality: "never", "only", "first", "has not" and the like.

## Run it

Run it from the repository under review (or pass `--repo DIR`), with the same `<base>` the
artifact uses. `<skill>` is this skill's directory; after an install that is
`<skills-root>/independent-review`.

```
<skill>/scripts/sweep_claims.sh --base <base>              # what the branch's commits add
<skill>/scripts/sweep_claims.sh --base <base> --worktree   # also uncommitted edits and untracked files
<skill>/scripts/sweep_claims.sh --file <plan.md>           # a whole document: a plan, a new file
<skill>/scripts/sweep_claims.sh --base <sha of last round> # what this round's fixes added
```

By default it sweeps changed `*.md`, `*.markdown`, `*.txt` and `*.rst` files outside
`docs/reviews/`, the same trail exclusion the artifact uses. To sweep other files, list them
after the options: they replace the default set, they are git pathspecs (globs work) relative to
`--repo`, and only what the change touched in them is swept. `--file` paths are
relative to the current directory. A sentence counts as changed when it touches an added
line, or a line either side of any hunk that removes a line: removing "except on a timeout."
widens the claim left behind, and an edit cannot be told apart from that reliably, so an edit
also lists the sentences on the lines beside it.

Each line of output is `path:line [matched words] sentence`, or `path:first-last` when the
sentence spans lines. The count, and anything it could not sweep, go to stderr. Exit 0 whatever
it finds; exit 2 means a usage error (bad option, unknown ref, no common ancestor, not a
repository, unreadable file). It needs Python 3.7 or later; without `python3` it prints one line and exits 0.

## Use the list

1. **Check each sentence against the record, or narrow it.** Most need no change. The list is
   candidates, not errors: the sweep finds the sentence; only the evidence can clear it.
2. **Put what is left in the review brief** as claims to challenge, each with its evidence, so
   the seats test them instead of discovering them one round at a time.
3. **Re-run it on each fix round's new text** (`--base <sha of last round>`). A fix can make
   the next finding.

## The habits it backs

The sweep finds the sentence. These habits decide whether the sentence is true, and they do
more than the tool.

- **Write down the whole list first.** For a claim of the form first, only, last, all or
  never, list everything it ranges over (every deploy job, every caller) before writing the
  sentence, and put the whole list in the evidence block, not just the entries that support
  you. On the change above, the author's evidence held two of the jobs, so only the seat with
  access to every job record could test "first deployed at R".
- **Read a seat's UNVERIFIABLE list as a lead.** An entry there can name your own claim. Test
  the claim; do not file the entry as a limit of that seat's access.
- **Delete an inference that has no stated basis; do not reword it.** A reworded claim is a
  new claim, and the next round reviews it.
- **Have the fresh-eyes agent keep a running findings log** in its scratch space and append
  each confirmed finding as soon as it is confirmed. One such agent was lost with its session
  after 25 minutes and left nothing.

## What it cannot see

- A claim without a listed word: "X was introduced in R" claims "first" without saying it.
  The list is `WORDS` in `scripts/sweep_claims.py`; extend it there, and add a case to
  `scripts/test_sweep_claims.sh`. Bare "not" is left out on purpose: on this skill's own
  docs, the sentences it adds are mostly contrasts ("X, not Y"), not absences. "Must",
  "mustn't" and "should not" are left out too: they give instructions, not claims about the record.
- A false sentence split. The sweep does not split before a lowercase word or after "e.g." or
  "i.e.", but another abbreviation before a capital or a digit ("Mr. Smith", "Fig. 2") still
  ends a sentence there. If the claim word lands in the half the change did not touch, it is
  missed.
- A deletion more than one line away from the claim it widens: in another sentence of the
  paragraph, or another paragraph.
- Indented (four-space) code blocks are read as text. Fenced blocks are skipped in Markdown
  files only, since "~~~" is an underline in rst; a fence that never closes is read as text,
  and so is one indented four spaces (or a tab) or more, unless it follows a list marker on the same line.
  A closer counts only up to three spaces deeper than the fence's text column.
- A renamed file counts as wholly added, so all its claims are listed.
