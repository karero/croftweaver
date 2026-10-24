#!/usr/bin/env python3
"""List the sentences a change ADDS that assert an absence or a universal.

Run it through sweep_claims.sh. Advisory: it prints candidates and exits 0; it exits 2
only for a usage error (bad arguments, an unknown ref, no common ancestor, not a repository,
an unreadable file). Why and how to use the list, and what it cannot see: references/claims-sweep.md.

Why it reads sentences, not lines: a per-line grep for "not been attempted" cannot see
"has not" at the end of one line and "been attempted" at the start of the next. So each
paragraph, list item, heading or table cell is joined into running text, split into
sentences, and each sentence is mapped back to its source lines. Only sentences that
touch a line the change adds, or a line either side of text it removes, are reported.

When a split is uncertain, it does not split: a sentence that runs long is still
reported, but a false split can leave the claim word in a half the change did not touch.

Past blind spots, each now pinned by test_sweep_claims.sh: a phrase wrapped across a line
break; a sentence ending ".)" or ".*" dropped; a period inside a word ("SKILL.md") cutting
off the start of a sentence; "e.g." or a wrapped "2024." (in a paragraph or a list item)
splitting a sentence; a removed qualifier, alone, beside a new line or in the same hunk as
an edit that keeps its words.
"""
import argparse
import os
import re
import subprocess
import sys

# What counts as a claim worth checking: an absence, a universal, or an order ("first",
# "last"). Each entry is a regex fragment, matched case-insensitively on word boundaries.
# Extend it here. Bare "not" is left out on purpose: on this skill's own docs, the sentences
# it adds are mostly contrasts ("X, not Y"), not absences. "Must", "mustn't" and "should
# not" are left out too: they give instructions, not claims about the record.
WORDS = [
    # absences
    r"has not", r"have not", r"had not", r"is not", r"are not", r"was not", r"were not",
    r"does not", r"do not", r"did not", r"cannot", r"can not", r"could not",
    r"will not", r"would not",
    r"(?:has|have|had|is|are|was|were|does|do|did|ca|could|wo|would)n[\u2019']t",
    r"not been", r"not yet", r"yet to", r"no longer", r"never", r"nobody", r"no one",
    r"nothing", r"nowhere", r"none", r"neither", r"without", r"no [a-z]+", r"zero",
    r"impossible",
    # universals, order and permanence
    r"only", r"first", r"last", r"all", r"every", r"any", r"every(?:thing|one|body|where)",
    r"any(?:thing|one|body|where)", r"always", r"ever", r"whole",
    r"entire", r"exactly", r"solely", r"both", r"unchanged", r"identical", r"since",
    r"until", r"by design", r"on purpose",
]
WORD_RE = re.compile(r"\b(?:" + "|".join(WORDS) + r")\b", re.I)

# A sentence ends at . ! or ? plus any closers, then whitespace or the end of the text,
# unless the next word starts lowercase or the stop closes "e.g." or "i.e.".
END_RE = re.compile(r"[.!?]+[)\]*\"'_\u201d\u2019]*(?=\s|$)")
ABBREV_RE = re.compile(r"(?:^|[^\w.])(?:e\.g|i\.e)\.$", re.I)
NEXT_RE = re.compile(r"\s*(\S)")

# Lines that end a block, so a sentence cannot run across two paragraphs. Blockquote
# markers are removed first, so a quoted paragraph reads as running text too.
QUOTE_RE = re.compile(r"^\s*(?:>\s?)+")
# Markdown only ("~~~" is an rst underline). A backtick fence's info string has no backtick,
# so "```x``` is inline code" is not a fence.
FENCE_RE = re.compile(r"^\s*(?:(`{3,})[^`]*|(~{3,}).*)$")
# Four spaces (or a tab) of indent make a CommonMark indented code line, never a fence, so
# two such lines cannot pair up and swallow the prose between them.
INDENTED_RE = re.compile(r"^(?: {4}| {0,3}\t)")
RULE_RE = re.compile(r"^\s*([-=*_~^])(?:\s*\1){2,}\s*$")  # thematic break, setext or rst underline
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}(?:\s|$)")
TABLE_RE = re.compile(r"^\s*\|")
LIST_RE = re.compile(r"^\s*(?:[-*+]|(\d{1,9})[.)])\s+")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

# The default file set: prose, minus review trails (the skill keeps those out of the
# artifact it sends to reviewers, so their claims are not under review).
DEFAULT_SPECS = [":(top,icase)*.md", ":(top,icase)*.markdown", ":(top,icase)*.txt",
                 ":(top,icase)*.rst", ":(top,exclude)docs/reviews/"]


class UsageError(Exception):
    pass


def is_markdown(path):
    return path.lower().endswith((".md", ".markdown"))


def indent(raw):
    return len(raw.expandtabs(4)) - len(raw.expandtabs(4).lstrip())


def closes(raw, fence):
    """fence is (marker, deepest indent a closer may have): at most three spaces past where
    the fence's content column starts, as CommonMark allows."""
    line = raw.strip()
    return (line and set(line) == {fence[0][0]} and len(line) >= len(fence[0])
            and indent(raw) <= fence[1])


def blocks(lines, markdown):
    """Split a document into blocks a sentence may not cross: lists of (line number, text)."""
    lines = [QUOTE_RE.sub("", raw, count=1) for raw in lines]
    out, cur, item_col, fence = [], [], None, None
    for i, raw in enumerate(lines):
        n, line = i + 1, raw.strip()
        if fence:
            if closes(raw, fence):
                fence = None
            continue
        lm = LIST_RE.match(raw)
        # Inside a paragraph, a number other than 1 starts an item only as a sibling of the
        # item it follows; "2024." there is wrapped text, in a list item or out of one.
        if (lm and lm.group(1) and int(lm.group(1)) != 1 and cur
                and (item_col is None or len(raw) - len(raw.lstrip()) >= item_col)):
            lm = None
        fm = markdown and (FENCE_RE.match(raw[lm.end():]) if lm
                           else not INDENTED_RE.match(raw) and FENCE_RE.match(raw))
        if fm:
            fm = (fm.group(1) or fm.group(2), (lm.end() if lm else indent(raw)) + 3)
            if not any(closes(later, fm) for later in lines[i + 1:]):
                fm = None  # a fence that never closes is read as text, so nothing is lost
        if not (fm or lm or not line or RULE_RE.match(raw) or HEADING_RE.match(raw)
                or TABLE_RE.match(raw)):
            cur.append((n, line))
            continue
        if cur:
            out.append(cur)
        cur, item_col = [], None
        if fm:
            fence = fm
        elif not line or RULE_RE.match(raw):
            pass
        elif HEADING_RE.match(raw):
            out.append([(n, line.strip("#").strip())])
        elif TABLE_RE.match(raw):
            out.extend([(n, cell.strip())] for cell in line.strip("|").split("|"))
        else:
            cur, item_col = [(n, raw[lm.end():].strip())], lm.end()
    if cur:
        out.append(cur)
    return out


def sentences(block):
    """Yield (sentence, first line, last line) for one block, its lines joined by spaces."""
    text, owner = "", []
    for n, piece in block:
        if not piece:
            continue
        if text:
            text += " "
            owner.append(n)
        text += piece
        owner.extend([n] * len(piece))
    ends = []
    for m in END_RE.finditer(text):
        nxt = NEXT_RE.match(text, m.end())
        if nxt and nxt.group(1).islower():
            continue  # "e.g. workers": a new sentence starts with a capital
        if ABBREV_RE.search(text[max(0, m.start() - 4):m.start() + 1]):
            continue
        ends.append(m.end())
    start = 0
    for end in ends + [len(text)]:
        seg = text[start:end]
        a, b = start + len(seg) - len(seg.lstrip()), start + len(seg.rstrip())
        if a < b:
            yield text[a:b], owner[a], owner[b - 1]
        start = end


def sweep(label, text, added):
    """Return report lines for the sentences in text that touch an added line and make a claim.

    added is a set of line numbers, or None for "every line".
    """
    found = []
    for block in blocks(text.split("\n"), is_markdown(label)):
        for sent, first, last in sentences(block):
            if added is not None and not any(n in added for n in range(first, last + 1)):
                continue
            words = []
            for m in WORD_RE.finditer(sent):
                w = m.group(0).lower()
                if w not in words:
                    words.append(w)
            if words:
                where = str(first) if first == last else "%d-%d" % (first, last)
                found.append("%s:%s [%s] %s" % (label, where, ", ".join(words), sent))
    return found


def added_lines(diff):
    """Line numbers the diff adds, plus the lines either side of any hunk that removes a line.

    Counts "+" lines rather than trusting hunk ranges. The lines beside a removal do come
    from the hunk header, which is exact only because git runs with -U0 and without
    GIT_DIFF_OPTS. Removing a line can widen the claim left beside it (deleting "except on a
    timeout."), and an edit cannot be told from that reliably, so every removal marks its
    neighbours: noisier, never a miss next to the removal.
    """
    added, n, around, removes = set(), None, None, False
    for line in diff.split("\n"):
        m = HUNK_RE.match(line)
        if m:
            if removes:
                added.update(around)
            n, count = int(m.group(1)), int(m.group(2) or 1)
            around, removes = ((n - 1, n + count) if count else (n, n + 1)), False
        elif n is None:
            continue
        elif line.startswith("+"):
            added.add(n)
            n += 1
        elif line.startswith("-"):
            removes = True
        elif line.startswith(" ") or not line:
            n += 1
    if removes:
        added.update(around)
    return added


# GIT_DIFF_OPTS=-u3 would override -U0, and "either side" is read from the hunk header.
GIT_ENV = {k: v for k, v in os.environ.items() if k != "GIT_DIFF_OPTS"}


def git(repo, *args):
    # diff.relative would limit a diff run from a subdirectory to that subdirectory.
    r = subprocess.run(["git", "-C", repo, "-c", "diff.relative=false"] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=GIT_ENV)
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", "replace").strip().splitlines()
        raise UsageError("git %s: %s" % (args[0], err[-1] if err else "exit %d" % r.returncode))
    return r.stdout


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


def from_diff(a, head, found, notes):
    """Sweep the lines added between the merge base and head (or the working tree).

    Returns the repository's top directory and the paths it swept.
    """
    top = os.fsdecode(git(a.repo, "rev-parse", "--show-toplevel")).strip()
    other = "HEAD" if a.worktree else head
    for ref in [a.base] + ([] if a.worktree else [head]):
        try:
            git(a.repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
        except UsageError:
            raise UsageError("not a commit: %s" % ref)
    # Three dots, as the skill builds its artifact: what head adds since it left base.
    try:
        mb = git(a.repo, "merge-base", a.base, other).decode().strip()
    except UsageError:
        shallow = git(a.repo, "rev-parse", "--is-shallow-repository").strip() == b"true"
        raise UsageError("%s and %s have no common ancestor%s" % (
            a.base, other, " in this shallow clone (try git fetch --unshallow)" if shallow else ""))
    rev = [mb] if a.worktree else [mb, head]
    specs = a.paths or DEFAULT_SPECS
    # A renamed file counts as wholly added: noisier, never a miss.
    out = git(a.repo, "diff", "--name-only", "-z", "--no-renames", "--diff-filter=d", *rev,
              "--", *specs)
    files = [(os.fsdecode(p), False) for p in out.split(b"\0") if p]
    if a.worktree:
        out = git(a.repo, "ls-files", "-z", "--full-name", "--others", "--exclude-standard",
                  "--", *specs)
        files += [(os.fsdecode(p), True) for p in out.split(b"\0") if p]
    swept = []
    for path, untracked in files:
        try:
            if untracked:
                text, added = read_text(os.path.join(top, path)), None
            else:
                diff = git(a.repo, "diff", "-U0", "--inter-hunk-context=0", "--text",
                           "--no-color", "--no-ext-diff", "--no-textconv", "--no-renames",
                           *rev, "--", ":(top,literal)" + path)
                added = added_lines(diff.decode("utf-8", "replace"))
                if a.worktree:
                    text = read_text(os.path.join(top, path))
                else:
                    text = git(a.repo, "show", "%s:%s" % (head, path)).decode("utf-8", "replace")
        except (OSError, UsageError) as e:
            notes.append("skipped %s (%s)" % (path, e))
            continue
        found.extend(sweep(path, text, added))
        swept.append(path)
    return top, swept


def main(argv):
    p = argparse.ArgumentParser(
        prog="sweep_claims.sh",
        description="List each sentence a change adds that asserts an absence or a universal "
                    "(never, only, first, has not ...). Advisory: exits 0 whatever it finds.",
        epilog="Output: path:line [matched words] sentence (path:first-last when it spans "
               "lines). The count goes to stderr. See references/claims-sweep.md.")
    p.add_argument("--base", metavar="REF",
                   help="sweep the lines added since REF (three-dot, like the review artifact)")
    p.add_argument("--head", metavar="REF",
                   help="the change's last commit (default HEAD), read from git, not from disk")
    p.add_argument("--worktree", action="store_true",
                   help="include uncommitted edits and untracked files")
    p.add_argument("--repo", metavar="DIR", default=".",
                   help="the repository (default: the current directory)")
    p.add_argument("--file", metavar="PATH", action="append", default=[], dest="files",
                   help="sweep this whole file, relative to the current directory (repeatable; "
                        "for a plan or a new document)")
    p.add_argument("paths", nargs="*", metavar="PATH",
                   help="sweep only these git pathspecs (globs work), relative to --repo "
                        "(default: changed *.md *.markdown *.txt *.rst outside docs/reviews/)")
    a = p.parse_args(argv)
    # A Latin-1 locale cannot print a curly quote; a file name that is not UTF-8 comes back
    # from git as it was.
    sys.stdout.reconfigure(encoding="utf-8", errors="surrogateescape")
    if not a.base and not a.files:
        p.error("give --base REF to sweep a change, or --file PATH to sweep a whole file")
    if not a.base and (a.head or a.worktree or a.paths):
        p.error("--head, --worktree and PATH need --base")
    if a.worktree and a.head:
        p.error("--worktree reads the working tree; leave out --head")
    whole, real = [], set()
    for f in a.files:
        if os.path.realpath(f) in real:
            continue  # one file under two spellings is swept once
        real.add(os.path.realpath(f))
        try:
            whole.append((f, read_text(f)))
        except OSError as e:
            p.error("cannot read %s: %s" % (f, e.strerror or e))

    found, notes, labels, top = [], [], set(), None
    if a.base:
        try:
            top, swept = from_diff(a, a.head or "HEAD", found, notes)
            labels.update(swept)
            if not swept:
                notes.append("no changed files to sweep between %s and %s" % (
                    a.base, "the working tree" if a.worktree else (a.head or "HEAD")))
        except FileNotFoundError:
            notes.append("git not found, so the change was not swept (it is advisory)")
        except UsageError as e:
            p.error(str(e))
    for f, text in whole:
        # Label a file inside the repository the way git does, so --base and --file on the
        # same file list each sentence once however the path was spelled; a file outside it
        # by its absolute path, so it cannot share a label with one inside.
        label = os.path.normpath(f)
        if top:
            rel = os.path.relpath(os.path.realpath(f), os.path.realpath(top))
            inside = rel != os.pardir and not rel.startswith(os.pardir + os.sep)
            label = rel if inside else os.path.abspath(f)
        found.extend(sweep(label, text, None))
        labels.add(label)
    found = list(dict.fromkeys(found))

    try:
        for line in found:
            print(line)
        sys.stdout.flush()  # so the count lands after the list when both go to one terminal
    except BrokenPipeError:
        # The reader stopped early (| head). Not an error for an advisory list.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    try:
        for note in notes:
            print("sweep_claims: %s." % note, file=sys.stderr)
        print("sweep_claims: %d sentence%s to check in %d file%s swept." % (
            len(found), "" if len(found) == 1 else "s", len(labels),
            "" if len(labels) == 1 else "s"), file=sys.stderr)
        sys.stderr.flush()
    except BrokenPipeError:
        # 2>&1 | head: stderr is the same closed pipe.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stderr.fileno())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
