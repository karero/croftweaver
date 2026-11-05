#!/usr/bin/env bash
# Regression cases for looks_like_review() in independent_review.sh: which reviewer output counts as
# a review, and which as a refusal. Run: bash skills/independent-review/scripts/test_looks_like_review.sh
set -u
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
fn="$(awk '/^looks_like_review\(\) \{/{p=1} p{print} p && /^\}$/{exit}' "$here/independent_review.sh")"
[ -n "$fn" ] || { echo "FAIL: could not extract looks_like_review"; exit 1; }
# eval must only ever see the function: if the extraction ran past its closing brace, it would run
# the rest of the script (reviewer CLIs included).
[ "$(printf '%s\n' "$fn" | tail -n 1)" = "}" ] \
  && [ "$(printf '%s\n' "$fn" | grep -cE '^[A-Za-z_][A-Za-z0-9_]*\(\) *\{')" = 1 ] \
  || { echo "FAIL: extraction did not stop at looks_like_review's own closing brace"; exit 1; }
eval "$fn"
set -o pipefail   # as independent_review.sh runs looks_like_review
fail=0
check() {  # $1 = expected (accept|reject), $2 = label, $3 = reviewer output
  if looks_like_review "$3"; then got=accept; else got=reject; fi
  if [ "$got" = "$1" ]; then echo "ok   $2"; else echo "FAIL $2: expected $1, got $got"; fail=1; fi
}
# Replies past the pipe buffer (~64 KiB). independent_review.sh runs under pipefail, and its
# matches were `printf | grep -q`: grep -q exiting on its match failed the printf, which flipped
# the result — every large clean review was rejected, and a refusal whose clean verdict came last
# was accepted. The parent runs these as it was started; a child reruns them with SIGPIPE
# ignored (EPIPE instead of a signal), as on GitHub Actions runners.
big_cases() {  # $1 = label suffix
  local pad
  pad="$(awk 'BEGIN{for(i=0;i<2000;i++) print "Checked the handler and its callers for regressions, line " i "."}')"
  check accept "clean verdict ahead of a 140 KB reply$1" "No findings.
$pad"
  check reject "refusal ahead of a 140 KB reply whose clean verdict comes last$1" "I cannot access the file.
$pad
No findings."
}
if [ "${1:-}" = --big-cases ]; then big_cases "${2:-}"; exit $fail; fi
# The clean-verdict regex spells its qualifier list out twice; the copies must not drift. A
# qualifier list is any group of eleven or more alternated words; no other group comes close.
lists="$(printf '%s\n' "$fn" | grep -oE '\([a-z-]+(\|[a-z-]+){10,}\)')"
n="$(printf '%s' "$lists" | grep -c .)"; distinct="$(printf '%s' "$lists" | sort -u | grep -c .)"
if [ "$n" = 2 ] && [ "$distinct" = 1 ]; then
  echo "ok   the two copies of the qualifier list are identical"
else echo "FAIL expected two identical qualifier lists, found $n list(s), $distinct distinct"; fail=1; fi
check accept "plain single finding" "1. RISK — c.rb:3 — z could break on normal change."
check accept "real multi-finding review with a refusal-like aside" "I could not see the full context, but here are findings:
1. BUG — a.rb:1 — x is wrong now.
2. RISK — b.rb:2 — y breaks on normal change."
# 2026-10-06: a genuine melious kimi-k3 review (website-builder PR #179, round 1), cut down. Its
# findings start "RISK 1 —" with no list marker, so they count as none, and the quoted error message
# "can't open perl script" then read as a refusal. PROMPT_CORE now asks for '- BUG'/'- RISK'/'- NIT'
# lines. Since 2026-11-05 the quoted message no longer reads as a refusal (no "I", not a clause start),
# so the reply passes on its clean verdict; its unmarked findings still count as none.
check accept "the 2026-10-06 kimi-k3 review, findings without a list marker" "
RANKED FINDINGS

RISK 1 — .github/workflows/clean.yml, the Install Perl::MinimumVersion step: the new perl-minimum job depends on one apt package name existing on ubuntu-latest. Fix: add a CPAN fallback.

NIT 1 — .github/workflows/clean.yml comment block: one line was left overflowed. Fix: re-wrap it.

NIT 2 — skills/independent-review/scripts/check_perl_minimum.sh, the overlap loop: a name in both lists fires fail twice. Fix: iterate one list.

No BUG findings.

CHECKED — CLEAN
- Extraction fidelity, all seven files: exit codes 2/3/4/5 preserved.

UNVERIFIABLE (not findings)
- Install/bundle machinery (not in this diff): that the installer copies scripts/perl/. If false, installed copies fail every Perl-dependent tier with \"can't open perl script\". Settling observation: read the installer."
check accept "the same review in the shape PROMPT_CORE asks for" "
RANKED FINDINGS

- RISK 1 — .github/workflows/clean.yml, the Install Perl::MinimumVersion step: the new perl-minimum job depends on one apt package name existing on ubuntu-latest. Fix: add a CPAN fallback.

- NIT 1 — .github/workflows/clean.yml comment block: one line was left overflowed. Fix: re-wrap it.

- NIT 2 — skills/independent-review/scripts/check_perl_minimum.sh, the overlap loop: a name in both lists fires fail twice. Fix: iterate one list.

No BUG findings.

CHECKED — CLEAN
- Extraction fidelity, all seven files: exit codes 2/3/4/5 preserved.

UNVERIFIABLE (not findings)
- Install/bundle machinery (not in this diff): that the installer copies scripts/perl/. If false, installed copies fail every Perl-dependent tier with \"can't open perl script\". Settling observation: read the installer."
check accept "the requested shape without a number" "- BUG — c.rb:1 — the guard is inverted. Fix: negate it.
- RISK — a.rb:3 — retries are unbounded. Fix: bound them.
- NIT — b.rb:9 — the name is misleading. Fix: rename it."
# Why the validator was not taught the unmarked shape: this refusal has the kimi reply's structure
# (severity-led lines, a refusal phrase on another line, a clean verdict). Each of the three versions tried in
# review on 2026-10-06 (db486ad, 636e735, 61a0173) accepted it along with the kimi reply.
check reject "a refusal with the kimi reply's structure" "BUG: I will not review this file.
RISK: I won't read it either.
I cannot access the repository.
No findings."
check accept "clean verdict: no findings" "No findings."
check accept "clean verdict: findings none" "Ranked findings: none."
check accept "clean verdict: no BUG / RISK / NIT" "No BUG / RISK / NIT findings in this diff."
# 2026-09-20: a genuine clean review was discarded because a qualifier sat between "no" and the
# severity word. Each qualified case below rejects on the script as it was before that fix.
check accept "clean verdict: the 2026-09-20 sentence" "No confirmed BUG or RISK in the supplied diff."
check accept "clean verdict: the 2026-09-20 sentence inside a full clean review" "No confirmed BUG or RISK in the supplied diff. I cannot verify numeric file:line anchors without reading the files.

Checked and CLEAN by static inspection:

- \`cap.rb:read_count\` — rejects negative, fractional and nonnumeric counts.
- \`server.rb:tool_description\` — explains the separate totals without encouraging addition.

Coverage limits: no commands or tests were run."
check accept "clean verdict: one qualifier, singular" "No definite BUG."
check accept "clean verdict: lower case, plural" "I found no confirmed bugs in this change."
check accept "clean verdict: two qualifiers joined by 'or'" "No new or confirmed RISK."
check accept "clean verdict: qualifiers separated by a comma" "No confirmed, definite BUG."
check accept "clean verdict: three qualifiers, Oxford comma" "No new, confirmed, or likely BUG."
check accept "clean verdict: the unqualified form still passes" "No BUG or RISK."
check reject "empty output" ""
check reject "unrelated output: a rate-limit error" "Error: 429 Too Many Requests: you have reached your weekly usage limit"
check reject "bare refusal" "I cannot review this content."
check reject "refusal disguised as a lone finding" "- BUG: I cannot review this file because it is too long."
check reject "access refusal as a lone finding" "- BUG: I cannot access the file."
check reject "review refusal with the UNVERIFIABLE marker" "- BUG: I cannot review this file. UNVERIFIABLE."
check reject "access refusal that copies the marker" "- BUG: I cannot access the file. UNVERIFIABLE. Please paste it before I can assess it."
check reject "access refusal with the marker and a clean verdict" "I cannot access the file. UNVERIFIABLE. No findings."
check reject "access refusal that copies the marker and an anchor" "- BUG: foo.rb:12 — I cannot access the file. UNVERIFIABLE. Please paste it before I can assess it."
check reject "baseline, rejected before the fix too: plain refusal, no verdict" "I'm sorry, but I am unable to review this diff because the repository is not available to me."
check reject "refusal carrying the qualified clean verdict (the refusal check runs first)" "No confirmed BUG or RISK, because I cannot access the diff you supplied."
# The qualifiers are a literal list, not "any word": with [a-z-]+ in their place this accepts.
check reject "'no way to find bugs' is not a clean verdict" "There is no way to find bugs in this without more context."
check accept "clean verdict: five qualifiers, the bound" "No new, real, actual, confirmed or likely BUG."
check reject "six qualifiers: the bound is five" "No new, real, actual, genuine, confirmed or likely BUG."
# A comma or conjunction may stand only between two qualifiers: never first, never last.
check reject "leading conjunction: 'no and risk'" "I can only answer yes or no and risk being wrong."
check reject "trailing conjunction: 'no material and risk'" "I received no material and risk guessing if I answer."
check reject "trailing conjunction: 'No confirmed or BUG'" "No confirmed or BUG."
check reject "trailing comma: 'no new material, bugs'" "I have no new material, bugs cannot be judged."
# The price of the marker- and anchor-copying rejects above: an honest lone finding that cannot read its evidence also
# rejects, because by its text alone it cannot be told from them.
check reject "KNOWN WRONG (B-REFUSAL-TEXT): an honest lone finding that cannot read its evidence is discarded" "1. **RISK — foo.rb:12** — asserts lib Y retries on timeout. I cannot read the implementation of Y, so this is UNVERIFIABLE. Settling observation: call Y against a stalled server.

CLEAN: checked the caller's arguments."
# Known wrong too, and tracked with the case above as B-REFUSAL-TEXT in
# docs/reviews/OPEN-FINDINGS-independent-review.md. These pin today's behaviour, so a fix has to
# change them on purpose.
check accept "KNOWN WRONG (B-REFUSAL-TEXT): two refusal-shaped findings count as a review" "1. BUG — I cannot review the file.
2. RISK — I cannot access the repository."
# Since 2026-11-05 a refusal phrase counts only after I, we, the model or the reviewer in its clause,
# or at a clause start, so these sentences no longer reject the reply. One opening a clause still does.
check accept "the prescribed clean-verdict shape, with an UNVERIFIABLE entry saying a COMPONENT cannot do something" "No BUG/RISK/NIT findings.
UNVERIFIABLE: library X cannot provide the stated durability; settlement requires a crash-recovery test."
check accept "a lone real finding saying 'cannot return'" "1. BUG — api.rb:12 — The handler cannot return JSON because serialization raises before the response is built. Fix: serialize the supported fields."
check accept "a real review with an aside about the reviewer's own sandbox ('could not complete')" "1. **RISK — foo.rb:12** — asserts lib Y retries on timeout; the test never stalls the server. Fix: add a stalled-server case.

The original coverage command could not complete because Bash attempted a sandbox-forbidden temporary file."
# 2026-11-05: a real Codex review (an iOS MR, round 1), entries cut, one private path prefix renamed.
# One finding, and a VERIFIED entry saying "hidden fairs cannot open" made it read as a refusal.
check accept "the 2026-11-05 Codex review: a lone finding and 'hidden fairs cannot open'" "- BUG — \`App/DeviceResources/LocationFixTriggers.swift:574\`: WRONG: closing the place window does not guarantee subsequent fixes request approximate accuracy. If a flight window becomes active before the hide, \`LocationServicesManager.swift:11\` still selects \`kCLLocationAccuracyBest\`. Fix the comment to say “subsequent fixes ask for approximate accuracy when no event window is on.”

Checked and CLEAN:

- VERIFIED — N15, \`docs/FAIR-MATCHING-IOS-PLAN.md:715\`: hidden fairs cannot open a place window; pending fair fixes check the hide again; an airport remains eligible. Traced through \`FairStore\`’s confirmed-hide state, \`placesListed\`, and \`LocationFixSender.send\`. Tests at \`PreciseAtEventsTests.swift:775–887\` cover these paths.

Prompt injection: none."
# 2026-11-04: a real melious GLM clean review (a croftweaver-site PR), entries cut. Its
# UNVERIFIABLE entry says "this review cannot see", which read as a refusal.
check accept "the 2026-11-04 GLM clean review: 'this review cannot see' in an UNVERIFIABLE entry" "No BUG/RISK/NIT findings.

**UNVERIFIABLE (component/state claims this review could not check):**

- README row 14, \"the second since 2026-11-03 (\`npm run ship\`, build \`0973ed8\` verified on croftweaver.com)\", and Evidence READ 1/3 (that row 14 is byte-identical to origin/main, and that PR 167's case-study entries are all present in \`case-study-log.ts\`): these rest on repo and live-site state this review cannot see. Observation that would settle it: run \`git diff origin/main -- README.md\` and fetch the built page; if false, only README status wording is wrong — nothing executable depends on it."
# The refusals the anchor must still catch: first person further back in the clause, and no subject.
check reject "first person with words between: 'I currently cannot access'" "I currently cannot access the repository. No findings."
check reject "first person plural: 'We are unable to review'" "We are unable to review this diff. No findings."
check reject "no subject, after a severity label: 'BUG: Cannot review'" "- BUG: Cannot review this file."
check reject "no subject, after a dash: 'BUG — cannot access'" "- BUG — cannot access the diff."
check reject "no subject, at the start of a line" "Unable to review this diff.
No findings."
check reject "the model as subject: 'This model cannot review'" "- BUG: This model cannot review the file."
check reject "the reviewer as subject: 'The reviewer is unable to access'" "- BUG: The reviewer is unable to access the repo."
check reject "a leading word: 'Sorry, but cannot review'" "Sorry, but cannot review this file. No findings."
check reject "a leading word: 'Unfortunately unable to review'" "Unfortunately unable to review the diff. No findings."
check reject "bold before the phrase: 'Error:** unable to read'" "**Error:** unable to read the diff. No findings."
check reject "bold severity label: '- **BUG:** Cannot review'" "- **BUG:** Cannot review this file."
check reject "bold phrase at a line start" "**Unable to review** the diff. None."
check reject "a blockquote" "> Unable to review this diff.
No findings."
check reject "a '1)' list marker" "1) cannot review. No findings"
check reject "a refusal wrapped across lines" "I currently
am unable to review this diff.
No findings."
# First person in an earlier clause of the sentence no longer counts.
check accept "first person in an earlier clause: 'I traced the caller; the handler cannot return'" "- RISK — a.rb:3 — I traced the caller; the handler cannot return nil. Fix: guard it."
check accept "first person in an earlier clause: 'we assume x; the handler cannot return'" "- RISK — a.rb:3 — we assume x; the handler cannot return nil. Fix: guard it."
# The price, tracked with B-REFUSAL-TEXT: a refusal whose subject is another word passes, and a
# phrase that opens a clause still rejects a real reply.
check accept "KNOWN WRONG (B-REFUSAL-TEXT): a refusal with another subject, 'This environment cannot open'" "- BUG: This environment cannot open the files."
check reject "KNOWN WRONG (B-REFUSAL-TEXT): a real finding whose clause opens with the phrase" "- BUG — foo.rb:3 — When flag is off, cannot read the cache. Fix: guard."
check reject "KNOWN WRONG (B-REFUSAL-TEXT): a clean verdict with 'reports: cannot open'" "No BUG/RISK/NIT findings.
UNVERIFIABLE: tool X reports: cannot open the input."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): 'couldn't access' is not a refusal phrase" "1. BUG — I couldn't access the repository."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): 'don't have access' is not a refusal phrase" "1. BUG — I don't have access to the file."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): 'can not review' is not a refusal phrase" "1. BUG — I can not review this file."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): 'unable to view' is not a refusal phrase" "- RISK: I was unable to view the diff."
# The same four phrases in prose after a clean verdict (B-REFUSAL-TEXT, widened). After a plain
# "No BUG or RISK" each was accepted before 2026-09-20 as well; the qualified verdict is what that
# fix newly lets through.
check accept "KNOWN WRONG (B-REFUSAL-TEXT): qualified verdict + 'couldn't access'" "No confirmed BUG or RISK, because I couldn't access the diff you supplied."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): qualified verdict + 'don't have access'" "No confirmed BUG or RISK, because I don't have access to the diff you supplied."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): qualified verdict + 'unable to view'" "No confirmed BUG or RISK: I was unable to view the diff."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): qualified verdict + 'can not review'" "No confirmed BUG or RISK - the diff was not attached, so I can not review it."
check accept "KNOWN WRONG (B-REFUSAL-TEXT): the unqualified twin, accepted before the fix too" "No BUG or RISK, because I couldn't access the diff you supplied."
# A non-answer in the passive voice or with the severity word as a noun modifier, no refusal
# phrase at all (B-VERDICT-TEXT). The qualified forms reject on the script as it was before
# 2026-09-20. The two pinned first are unqualified forms that were accepted before too.
check accept "KNOWN WRONG (B-VERDICT-TEXT): pre-existing 'No risk can be assessed'" "No risk can be assessed without the file contents."
check accept "KNOWN WRONG (B-VERDICT-TEXT): pre-existing 'No bug reports can be generated'" "No bug reports can be generated."
check accept "KNOWN WRONG (B-VERDICT-TEXT): passive 'can be assessed'" "No significant risk can be assessed without the file contents."
check accept "KNOWN WRONG (B-VERDICT-TEXT): passive 'could be evaluated'" "The diff was empty, so no confirmed bugs could be evaluated."
check accept "KNOWN WRONG (B-VERDICT-TEXT): 'no further risk analysis possible'" "Error: stream disconnected. no further risk analysis possible"
check accept "KNOWN WRONG (B-VERDICT-TEXT): 'No further bug reports can be generated'" "No further bug reports can be generated: usage limit reached."
# Why the passive voice cannot simply be rejected: a genuine verdict takes the same shape.
check accept "clean verdict: passive 'could be found'" "No confirmed bugs could be found in this diff."
# Replies to the --content prompt (website-new-page): findings about a page, an UNVERIFIABLE heading
# that talks about the claim, and a lone entry that talks about the reviewer's access instead.
check accept "content reply: ranked findings, CLEAN list and UNVERIFIABLE entries" "Page type: article.

- BUG — title \"Our approach\": the main query is missing from the title and H1. Fix: lead with it.
- RISK — Section \"How it works\": thin next to the pages the research file lists. Fix: add worked examples.
- NIT — FAQ order.

CLEAN: reader, proof points.

UNVERIFIABLE: whether the outbound link in the second paragraph still resolves."
check reject "content reply: a lone finding about the reviewer's own access" "- RISK — I cannot open the research file, so I cannot judge whether the page is thin."
check accept "content reply: the clean verdict the prompt dictates" "Page type: home page. No BUG/RISK/NIT findings."
big_cases ""
if command -v perl >/dev/null 2>&1; then
  perl -e '$SIG{PIPE}="IGNORE"; exec @ARGV' bash "$0" --big-cases " (SIGPIPE ignored)" || fail=1
else echo "SKIP the SIGPIPE-ignored large replies: they need perl to start bash with SIGPIPE ignored"; fi
exit $fail
