#!/usr/bin/env bash
# Guard: per-skill size budgets. Two budgets per skills/*/SKILL.md:
#   - frontmatter `description` ≤ 1024 CHARACTERS — the skill-spec HARD limit
#     (tooling that indexes skills truncates or rejects longer ones). FAIL when
#     over; warn from 900 so a skill nearing the ceiling is visible before it
#     turns the gate red. Pre-existing overages are allowlisted below,
#     shrink-only, so the gate can land without blocking unrelated work while
#     still refusing NEW violations and any growth of the old ones.
#   - SKILL.md ≤ 500 lines — the skill-authoring guideline. SOFT budget: warn
#     only, never fail — an over-long body degrades quality, not loading, and
#     two shipped skills already sit over it while being slimmed down.
# Added 2026-08-29 after the skill-debloat review (finding D15): one description
# had silently grown ~60% past the hard limit with nothing in place to catch it.
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.." || { echo "FAIL — cannot cd to the repo root from $0."; exit 1; }

DESC_HARD=1024
DESC_WARN=900
LINES_SOFT=500
# Breakage tripwire, not an inventory ledger: it catches a broken glob/path
# (0 files) or catastrophic loss, while tolerating routine removals. The suite
# holds 35 skills as of 2026-10-12.
MIN_SKILLS=20

# Descriptions over DESC_HARD that are tolerated for now, pinned so they can
# only shrink. This started as four entries, all predating the check; the
# skill-debloat work (#85) then trimmed three of them back under the limit and
# those entries came out in this same change — the stale-entry FAIL is what
# forced the cleanup, exactly as intended.
#
# The one left is NOT leftover debt: the careful-interpretation hardening (#86)
# GREW this description from 1603 to 1716 while the check was in review. It is
# now the only skill over the spec limit, and by a wide margin. Trimming it is
# a content decision for that skill's owner, so it is re-pinned at its current
# length rather than edited here.
#
# Caps are the YAML-parsed value lengths (see desc_of) and each pin must EQUAL
# the current value: a trim lowers the pin in the same change, so regrowth
# under a stale cap has nowhere to hide. For clip-chomped (`>`) blocks the
# parsed value includes a trailing newline, so a pin reads one higher than the
# visible text — that is correct, do not "fix" it. One entry per skill;
# duplicates FAIL.
ALLOW_OVER=(
)

# The limit counts characters, not bytes — the descriptions are full of
# multi-byte punctuation (em-dashes), so `wc -m` needs a UTF-8 locale. No UTF-8
# locale would mean silently counting bytes; fail instead. The list is captured
# once and matched via herestrings so pipefail can never eat a genuine match.
LOCALES=$(locale -a 2>/dev/null || true)
UTF8_LOCALE=""
for loc in C.UTF-8 C.utf8 en_US.UTF-8 en_US.utf8; do
  if grep -qixF "$loc" <<<"$LOCALES"; then UTF8_LOCALE="$loc"; break; fi
done
if [ -z "$UTF8_LOCALE" ]; then
  UTF8_LOCALE=$(grep -m1 -iE '\.utf-?8$' <<<"$LOCALES" || true)
fi
if [ -z "$UTF8_LOCALE" ]; then
  echo "FAIL — no UTF-8 locale on this system; wc -m would count bytes, not characters,"
  echo "and the ${DESC_HARD}-char limit check would over-count. Install/enable one."
  exit 1
fi

chars() { printf '%s' "$1" | LC_ALL="$UTF8_LOCALE" wc -m | tr -d '[:space:]'; }

# Print the YAML-parsed frontmatter description of a SKILL.md, exactly as a
# real YAML parser would return it, for the shapes this suite uses:
#   - single-line plain/quoted scalars, verbatim (outer quotes stripped);
#   - block scalars `>` `>-` `|` `|-` with a uniform indent: folded joins
#     lines with spaces and turns each blank line into a newline, literal
#     joins every line with a newline (plus one per blank line), and clip
#     chomping (`>`/`|`) contributes its trailing newline.
# Every other shape is REFUSED — output is empty and the caller fails loud
# instead of measuring a truncated or under-counted string: multi-line
# plain/quoted scalars (an indented continuation after the value line, blank
# lines included), keep chomping (`>+`/`|+`), block headers beyond the four
# bare forms (indentation indicators like `>2`, trailing comments), blank
# lines before a block's first content line, any block line whose indent
# differs from the first content line's, tabs in or immediately after a
# block's indentation (YAML indent is spaces-only; a tab there is content a
# real parser keeps), whitespace-only block lines wider than the indent (a
# real parser keeps the excess as content), alias values (`*ref` expands to
# the anchored content — unmeasurable here), duplicate description keys (a
# real parser returns the LAST value, not the first), and plain values a
# real parser rejects or resolves to non-strings (anchors, tags, flow
# collections, sequence/mapping indicators, colon-space, unterminated
# quotes, value-position comments, and whole-token non-strings: null/boolean
# forms, numbers, hex/octal/binary, inf/nan, bare dates). Residual over-counts
# (quoted-scalar escapes, trailing `#` comments after a plain value, kept
# trailing spaces on block lines) err conservative: they can false-FAIL near
# the boundary, never false-pass. Frank residual gap, loud-or-conservative
# for valid YAML: a frontmatter never closed by `---` scans on into the body.
#
# The output can END IN A NEWLINE (clip chomping), which $(...) strips — every
# caller must capture with the x-sentinel idiom:
#   d=$(desc_of "$f"; printf x); d=${d%x}
desc_of() {
  # LC_ALL=C: the parser is ASCII-structural (indent/quote/token matching) and
  # tolower()/regex behavior must not vary with the ambient locale; multibyte
  # description content passes through untouched and is counted by chars().
  LC_ALL=C awk '
    BEGIN {
      sq=sprintf("%c",39); dq=sprintf("%c",34)
      # Duplicate-key SCAN pattern: also catches the valid alternate spellings
      # `description :` and quoted keys, which a real parser still resolves
      # last-wins. The CAPTURE rule below stays strict on purpose.
      dupre = "^[" dq sq "]?description[" dq sq "]?[ \t]*:"
    }
    NR==1 { if ($0 ~ /^---[ \t\r]*$/) infm=1; next }
    infm==0 { exit }
    /^---[ \t\r]*$/ { exit }
    # After a single-line value: skip blanks, refuse an indented continuation
    # (multi-line plain/quoted), then keep scanning the frontmatter so a
    # DUPLICATE description key — which a real parser resolves to the LAST
    # value — is refused rather than first-copy-measured.
    captured==1 {
      if ($0 ~ /^[ \t\r]*$/) next
      if ($0 ~ /^[ \t]/) { desc=""; exit }
      captured=0; done=1
    }
    done==1 {
      if ($0 ~ dupre) { desc=""; exit }
      next
    }
    mode=="block" {
      if ($0 ~ /^[ \t\r]*$/) {
        ws=$0; sub(/\r$/,"",ws)
        if (desc!="" && (ws ~ /\t/ || length(ws) > indent)) { desc=""; exit }
        blanks++; next
      }
      if ($0 !~ /^[ \t]/) {
        if ($0 ~ dupre) { desc=""; exit }
        mode=""; done=1; next
      }
      if ($0 ~ /^ *\t/) { desc=""; exit }
      match($0, /^ +/)
      if (desc=="") {
        if (blanks>0) { desc=""; exit }
        indent=RLENGTH
      } else if (RLENGTH!=indent) { desc=""; exit }
      line=substr($0, RLENGTH+1); sub(/\r$/,"",line)
      if (desc!="") {
        if (lit) { n=blanks+1; while (n-- > 0) desc=desc "\n" }
        else if (blanks>0) { while (blanks-- > 0) desc=desc "\n" }
        else desc=desc " "
      }
      desc=desc line; blanks=0
      next
    }
    /^description:([ \t]|$)/ {
      val=$0; sub(/^description:[ \t]*/,"",val); sub(/[ \t\r]+$/,"",val)
      if (val==">")  { mode="block"; wasblock=1; lit=0; clip=1; next }
      if (val==">-") { mode="block"; wasblock=1; lit=0; clip=0; next }
      if (val=="|")  { mode="block"; wasblock=1; lit=1; clip=1; next }
      if (val=="|-") { mode="block"; wasblock=1; lit=1; clip=0; next }
      a=substr(val,1,1)
      if (a==">" || a=="|") { exit }
      if (length(val)>=2) {
        z=substr(val,length(val),1)
        if ((a==sq && z==sq) || (a==dq && z==dq)) {
          desc=substr(val,2,length(val)-2); captured=1; next
        }
      }
      # Plain scalar: refuse shapes a real parser rejects or resolves to a
      # non-string — aliases/anchors/tags/flow/reserved indicators, sequence
      # or mapping indicators, and a colon-space (invalid inside a plain
      # scalar). Quoted values, handled above, may contain any of these.
      if (a==sq || a==dq) { exit }
      if (a=="*" || a=="&" || a=="!" || a=="[" || a=="{" || a=="%" || a=="@" || a=="`") { exit }
      if (a=="#" || a=="," || a=="]" || a=="}") { exit }
      lv=tolower(val)
      if (val=="~" || lv=="null" || lv=="true" || lv=="false" || lv=="yes" || lv=="no" || lv=="on" || lv=="off") { exit }
      if (val ~ /^[-+]?([0-9][0-9_]*(\.[0-9_]*)?|\.[0-9_]+)([eE][-+]?[0-9]+)?$/) { exit }
      if (val ~ /^[-+]?0[xXoObB][0-9a-fA-F_]+$/) { exit }
      if (lv ~ /^[-+]?\.(inf|nan)$/) { exit }
      # YAML 1.1 sexagesimals (5:30 resolves to 330) and timestamps. Both are
      # anchored whole-token so ordinary prose that merely opens with a date
      # or a clock time still measures. Intervals are spelled out, not {n},
      # for mawk (the ubuntu-latest default awk).
      if (val ~ /^[-+]?[0-9][0-9_]*(:[0-5]?[0-9])+([.][0-9]*)?$/) { exit }
      if (val ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?$/) { exit }
      if (val ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?[Tt ][0-9][0-9]?:[0-9][0-9]:[0-9][0-9]([.][0-9]*)?( ?([Zz]|[-+][0-9][0-9]?(:[0-9][0-9])?))?$/) { exit }
      if (val ~ /^[-?:]([ \t]|$)/) { exit }
      if (val ~ /:[ \t]/) { exit }
      desc=val; captured=1; next
    }
    # A description-shaped key the capture rule above declined (`description:x`
    # with no separating space, the `description :` / quoted-key spellings).
    # Skipping it would let a LATER valid key be measured in a document a real
    # loader rejects outright, so refuse loudly instead.
    $0 ~ dupre { desc=""; exit }
    END {
      if (desc !~ /[^ \t\n\r]/) desc=""
      else if (wasblock && clip==1) desc=desc "\n"
      printf "%s", desc
    }
  ' "$1"
}

# Verdict for one skill description against the budgets and its optional
# allowlist entry. Prints findings; bumps the fails/warns/allowed_over globals.
# Kept as a function so the self-test below can drive the enforcement logic
# directly. Both numbers are validated first: without `set -e`, a garbled len
# or cap would otherwise make every [ -gt ] test silently false and pass the
# gate.
judge_desc() { # <skill> <len> <allowed:yes|no> <cap>
  local skill=$1 len=$2 allowed=$3 cap=$4
  case "$len" in
    ''|*[!0-9]*)
      echo "FAIL — $skill: measured description length '$len' is not a number — chars()/locale breakage; fix the script."
      fails=1; return ;;
  esac
  if [ "$allowed" = yes ]; then
    case "$cap" in
      ''|*[!0-9]*)
        echo "FAIL — $skill: malformed ALLOW_OVER cap '$cap' — the entry must be \"skill-name=<number>\"; fix it."
        fails=1; return ;;
    esac
    if [ "$cap" -le "$DESC_HARD" ]; then
      echo "FAIL — $skill: ALLOW_OVER cap ${cap} is not above the ${DESC_HARD} hard limit — a pin at or under the limit is meaningless; remove the entry."
      fails=1
    elif [ "$len" -le "$DESC_HARD" ]; then
      echo "FAIL — $skill: description is ${len} chars, back under the ${DESC_HARD} hard limit — remove its now-stale ALLOW_OVER entry from this script."
      fails=1
    elif [ "$len" -gt "$cap" ]; then
      echo "FAIL — $skill: description grew to ${len} chars, past its pinned ALLOW_OVER cap of ${cap} — allowlisted descriptions may only shrink."
      fails=1
    elif [ "$len" -lt "$cap" ]; then
      echo "FAIL — $skill: description shrank to ${len} chars — lower its ALLOW_OVER pin to ${len} in this same change (a stale higher cap would let it regrow unnoticed)."
      fails=1
    else
      echo "warn — $skill: description ${len} chars, over the ${DESC_HARD} hard limit but allowlisted (pinned at ${cap}; see the tracking note in this script)."
      warns=1; allowed_over=$((allowed_over+1))
    fi
  elif [ "$len" -gt "$DESC_HARD" ]; then
    echo "FAIL — $skill: description is ${len} chars — over the ${DESC_HARD}-char skill-spec hard limit. Shorten it (aim under ${DESC_WARN})."
    fails=1
  elif [ "$len" -ge "$DESC_WARN" ]; then
    echo "warn — $skill: description ${len} chars — nearing the ${DESC_HARD}-char hard limit (warning starts at ${DESC_WARN})."
    warns=1
  fi
}

# Self-test on known fixtures before trusting the scan — a guard that miscounts
# is worse than none. Exact-equality assertions catch both under- and
# over-extraction; the em-dash fixture catches byte-instead-of-char counting;
# the judge_desc calls catch enforcement regressions (dead pins, inverted
# comparisons, boundary drift). Not driven here (hand-verified plain logic):
# the MIN_SKILLS floor, the missing-SKILL.md sweep, the SKILL.md line count,
# and the stale/unknown/duplicate-entry loop.
TMP=$(mktemp -d "${TMPDIR:-/tmp}/skill-budgets-selftest.XXXXXX") || {
  echo "FAIL — self-test: could not create a temp dir."; exit 1; }
trap 'rm -rf "$TMP"' EXIT
st_fail() { echo "FAIL — self-test: $1. Fix the script before trusting the scan."; exit 1; }
# Both helpers preserve a trailing newline in the description: st_len counts
# inside one function, st_read hands the exact string back in the ST global —
# a bare $(desc_of …) in an assertion would strip the very newline (or reduce
# a lone-newline regression to empty) that the assertion exists to catch.
st_len()  { local out; out=$(desc_of "$1"; printf x); out=${out%x}; chars "$out"; }
st_read() { ST=$(desc_of "$1"; printf x); ST=${ST%x}; }

cat > "$TMP/plain.md" <<'EOF'
---
name: t
description: abcde
---
body
EOF
cat > "$TMP/quoted.md" <<'EOF'
---
name: t
description: "abc def"
---
EOF
cat > "$TMP/folded-clip.md" <<'EOF'
---
name: t
description: >
  one two
  three
metadata: x
---
description: not this one
EOF
cat > "$TMP/folded-strip.md" <<'EOF'
---
name: t
description: >-
  one two
  three
---
EOF
cat > "$TMP/literal-clip.md" <<'EOF'
---
name: t
description: |
  one two
  three
---
EOF
cat > "$TMP/literal-blank.md" <<'EOF'
---
name: t
description: |
  a

  c
---
EOF
cat > "$TMP/folded-utf8.md" <<'EOF'
---
name: t
description: >
  a — b

  c
---
EOF
cat > "$TMP/nodesc.md" <<'EOF'
---
name: t
---
EOF
cat > "$TMP/multiline-plain.md" <<'EOF'
---
name: t
description: first line
  silently-truncated continuation
---
EOF
cat > "$TMP/multiline-plain-blank.md" <<'EOF'
---
name: t
description: first line

  continuation after a blank line
---
EOF
cat > "$TMP/block-indicator.md" <<'EOF'
---
name: t
description: >2
  never measured
---
EOF
cat > "$TMP/keep-chomp.md" <<'EOF'
---
name: t
description: >+
  never measured
---
EOF
cat > "$TMP/block-lead-blank.md" <<'EOF'
---
name: t
description: >

  text
---
EOF
cat > "$TMP/block-indent-jump.md" <<'EOF'
---
name: t
description: >
  text
    deeper-indented line
---
EOF
printf -- '---\r\nname: t\r\ndescription: abc\r\n---\r\n' > "$TMP/crlf.md"
printf -- '---\nname: t\ndescription: >\n  \tnever\n  \tmeasured\n---\n' > "$TMP/block-tab-indent.md"
printf -- '---\nname: t\ndescription: >\n  a\n    \n  c\n---\n' > "$TMP/block-wide-blank.md"
cat > "$TMP/alias.md" <<'EOF'
---
name: t
description: *bigdesc
---
EOF
cat > "$TMP/duplicate-key.md" <<'EOF'
---
name: t
description: short
description: a much longer duplicate that a real parser would return instead
---
EOF
cat > "$TMP/plain-colon.md" <<'EOF'
---
name: t
description: a: b
---
EOF
cat > "$TMP/plain-seq.md" <<'EOF'
---
name: t
description: - item
---
EOF
cat > "$TMP/unterminated-quote.md" <<'EOF'
---
name: t
description: "abc
---
EOF
cat > "$TMP/quoted-colon.md" <<'EOF'
---
name: t
description: "a: b"
---
EOF
cat > "$TMP/comment-value.md" <<'EOF'
---
name: t
description: # TODO write this
---
EOF
cat > "$TMP/null-value.md" <<'EOF'
---
name: t
description: null
---
EOF
cat > "$TMP/numeric-value.md" <<'EOF'
---
name: t
description: 1600
---
EOF
cat > "$TMP/flow-starter.md" <<'EOF'
---
name: t
description: , x
---
EOF
cat > "$TMP/colon-no-space.md" <<'EOF'
---
name: t
description:x
---
EOF
cat > "$TMP/date-only.md" <<'EOF'
---
name: t
description: 2026-08-29
---
EOF
cat > "$TMP/sexagesimal.md" <<'EOF'
---
name: t
description: 5:30
---
EOF
cat > "$TMP/timestamp-value.md" <<'EOF'
---
name: t
description: 2026-08-29T10:00:00Z
---
EOF
cat > "$TMP/malformed-then-valid.md" <<'EOF'
---
name: t
description:x
description: a later valid key a real loader would never reach
---
EOF
cat > "$TMP/time-starts-string.md" <<'EOF'
---
name: t
description: 5:30 is when the build runs
---
EOF
cat > "$TMP/date-starts-string.md" <<'EOF'
---
name: t
description: 2026-08-29 was the day this suite got budgets
---
EOF
cat > "$TMP/dup-alt-spelling.md" <<'EOF'
---
name: t
description: short
description : a longer duplicate under an alternate valid key spelling
---
EOF

n=$(st_len "$TMP/plain.md")
[ "$n" -eq 5 ] || st_fail "plain description counted $n chars, expected 5"
n=$(st_len "$TMP/quoted.md")
[ "$n" -eq 7 ] || st_fail "quoted description counted $n chars, expected 7 (quotes stripped)"
st_read "$TMP/folded-strip.md"
[ "$ST" = "one two three" ] || \
  st_fail "strip-chomped folded description parsed wrong, expected exactly 'one two three'"
n=$(st_len "$TMP/folded-clip.md")
[ "$n" -eq 14 ] || st_fail "clip-chomped folded description counted $n chars, expected 14 (13 + trailing newline)"
n=$(st_len "$TMP/literal-clip.md")
[ "$n" -eq 14 ] || st_fail "literal block counted $n chars, expected 14 — newline joins broke"
n=$(st_len "$TMP/literal-blank.md")
[ "$n" -eq 5 ] || st_fail "literal block with a blank line counted $n chars, expected 5 (a+2 newlines+c+newline)"
n=$(st_len "$TMP/folded-utf8.md")
[ "$n" -eq 8 ] || st_fail "em-dash description counted $n chars, expected 8 — counting bytes, not characters?"
n=$(st_len "$TMP/crlf.md")
[ "$n" -eq 3 ] || st_fail "CRLF file counted $n chars, expected 3 — CR handling broke"
n=$(st_len "$TMP/quoted-colon.md")
[ "$n" -eq 4 ] || st_fail "quoted value containing colon-space counted $n chars, expected 4 — quote path must bypass the plain-scalar refusals"
n=$(st_len "$TMP/date-starts-string.md")
[ "$n" -eq 45 ] || st_fail "plain string starting with a date counted $n chars, expected 45 — whole-token refusals must not fire on real descriptions"
n=$(st_len "$TMP/time-starts-string.md")
[ "$n" -eq 27 ] || st_fail "plain string starting with a clock time counted $n chars, expected 27 — the sexagesimal refusal must stay whole-token"
for fx in nodesc multiline-plain multiline-plain-blank block-indicator keep-chomp \
          block-lead-blank block-indent-jump block-tab-indent block-wide-blank alias \
          duplicate-key dup-alt-spelling plain-colon plain-seq unterminated-quote \
          comment-value null-value numeric-value flow-starter colon-no-space date-only \
          sexagesimal timestamp-value malformed-then-valid; do
  st_read "$TMP/$fx.md"
  [ -z "$ST" ] || st_fail "$fx.md was measured instead of refused (got '$ST')"
done

fails=0 warns=0 allowed_over=0
judge_desc t 899  no  ""     >/dev/null
[ "$fails" -eq 0 ] && [ "$warns" -eq 0 ] || st_fail "in-budget description tripped judge_desc"
judge_desc t 900  no  ""     >/dev/null
[ "$warns" -eq 1 ] || st_fail "description at DESC_WARN did not warn"
fails=0 warns=0
judge_desc t 1024 no  ""     >/dev/null
[ "$fails" -eq 0 ] && [ "$warns" -eq 1 ] || st_fail "description at exactly DESC_HARD must warn, not fail"
fails=0 warns=0
judge_desc t 1025 no  ""     >/dev/null
[ "$fails" -eq 1 ] || st_fail "over-limit description did not fail"
fails=0 warns=0
judge_desc t "" no ""        >/dev/null
[ "$fails" -eq 1 ] || st_fail "non-numeric measured length did not fail (gate would silently pass)"
fails=0 warns=0 allowed_over=0
judge_desc t 1600 yes 1600   >/dev/null
[ "$fails" -eq 0 ] && [ "$warns" -eq 1 ] && [ "$allowed_over" -eq 1 ] || \
  st_fail "allowlisted at-pin description did not warn cleanly"
fails=0 warns=0
judge_desc t 1500 yes 1600   >/dev/null
[ "$fails" -eq 1 ] || st_fail "description shrunk below its pin did not fail (stale cap would allow regrowth)"
fails=0 warns=0
judge_desc t 1700 yes 1600   >/dev/null
[ "$fails" -eq 1 ] || st_fail "description grown past its pin did not fail"
fails=0 warns=0
judge_desc t 1000 yes 1600   >/dev/null
[ "$fails" -eq 1 ] || st_fail "stale (back-under-limit) allowlist entry did not fail"
fails=0 warns=0
judge_desc t 1500 yes "13l2" >/dev/null
[ "$fails" -eq 1 ] || st_fail "malformed allowlist cap did not fail (pin would be silently dead)"
fails=0 warns=0
judge_desc t 1500 yes 1000   >/dev/null
[ "$fails" -eq 1 ] || st_fail "allowlist cap at/under DESC_HARD did not fail"

# Scan every skill. Glob, not a maintained list, so a new skill is covered by
# default; the floor catches path breakage masquerading as a clean run, and the
# directory sweep catches a skill directory whose SKILL.md is missing (which
# the glob alone would silently skip).
shopt -s nullglob
FILES=(skills/*/SKILL.md)
if [ "${#FILES[@]}" -lt "$MIN_SKILLS" ]; then
  echo "FAIL — only ${#FILES[@]} skills/*/SKILL.md found (floor ${MIN_SKILLS}); path breakage or a moved suite."
  echo "If the suite was deliberately reduced below ${MIN_SKILLS} skills, lower MIN_SKILLS in the same PR."
  exit 1
fi

fails=0 warns=0 allowed_over=0 allow_seen=" "
for d in skills/*/; do
  if [ ! -f "${d}SKILL.md" ]; then
    echo "FAIL — ${d%/}: no SKILL.md — the budget scan cannot see this skill at all."
    fails=1
  fi
done

for f in "${FILES[@]}"; do
  skill=${f#skills/}; skill=${skill%/SKILL.md}

  allowed=no cap=""
  for entry in ${ALLOW_OVER[@]+"${ALLOW_OVER[@]}"}; do
    if [ "${entry%%=*}" = "$skill" ]; then
      if [ "$allowed" = yes ]; then
        echo "FAIL — $skill: duplicate ALLOW_OVER entries — keep exactly one."
        fails=1
      fi
      allowed=yes; cap=${entry#*=}
      [ "$cap" = "$entry" ] && cap=""   # entry has no '=' at all
      allow_seen="$allow_seen$skill "
    fi
  done

  # Line budget first, so a skill whose description is refused below still
  # gets its line warning. The numeric guard mirrors judge_desc's: without
  # set -e a garbled count would silently skip the warn.
  lines=$(awk 'END{print NR}' "$f")
  case "$lines" in
    ''|*[!0-9]*)
      echo "FAIL — $skill: measured line count '$lines' is not a number — awk breakage; fix the script."
      fails=1 ;;
    *)
      if [ "$lines" -gt "$LINES_SOFT" ]; then
        echo "warn — $skill: SKILL.md is ${lines} lines — over the ${LINES_SOFT}-line soft budget; move detail to references/."
        warns=1
      fi ;;
  esac

  desc=$(desc_of "$f"; printf x); desc=${desc%x}
  if [ -z "$desc" ]; then
    echo "FAIL — $skill: no measurable frontmatter description (missing, a leading BOM, or a YAML style this parser refuses — see desc_of)."
    fails=1; continue
  fi
  judge_desc "$skill" "$(chars "$desc")" "$allowed" "$cap"
done

for entry in ${ALLOW_OVER[@]+"${ALLOW_OVER[@]}"}; do
  name=${entry%%=*}
  case "$allow_seen" in *" $name "*) ;; *)
    echo "FAIL — ALLOW_OVER entry '$name' matches no skill — remove or fix the entry."
    fails=1 ;;
  esac
done

if [ "$fails" -ne 0 ]; then
  exit 1
fi
if [ "$allowed_over" -ne 0 ]; then
  echo "OK (gate passes) — no new violations; ${allowed_over} pre-existing over-limit description(s) remain allowlisted, shrink-only (${#FILES[@]} skills checked, see warn lines above)."
elif [ "$warns" -ne 0 ]; then
  echo "OK (with warnings) — no skill over a hard budget; see the warn lines above (${#FILES[@]} skills checked)."
else
  echo "OK — all ${#FILES[@]} skills within budget (description ≤ ${DESC_HARD} chars, SKILL.md ≤ ${LINES_SOFT} lines)."
fi
