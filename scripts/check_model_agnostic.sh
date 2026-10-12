#!/usr/bin/env bash
# Guard: independent-review is model-AGNOSTIC — the pipeline prescribes no specific LLM.
# The ollama tier auto-detects the owner's signed-in ':cloud' model, Codex and Antigravity
# use their own CLI-configured defaults, and the docs speak in families and generic tags.
# A hardcoded default is exactly how the ollama tier once drifted out of sync with the
# owner's real setup (this script's pre-2026-08-29 ancestor, check_model_defaults.sh,
# managed that drift; this version prevents the class). One name is let through, the model
# the Melious seat is held to: see allow_melious_model below.
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."

SKILL_DIR="skills/independent-review"

# Scan every regular file in the skill EXCEPT references/setup-guide.md (matched by
# exact path, not basename) — the drift-prone helper that cites dated, concrete
# local-model examples for the RAM table, and says so inline. The one known
# tag-classification defect that exclusion hides is tracked as row B-TAGCLASS in
# docs/reviews/OPEN-FINDINGS-independent-review.md. Files are discovered, not
# listed, and not filtered by extension, so a new reference, script, or helper of
# any type is scanned by default instead of silently skipped (grep -I skips any
# genuinely binary file).
FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(
  find "$SKILL_DIR" -type f ! -path "$SKILL_DIR/references/setup-guide.md" | sort
)
if [ "${#FILES[@]}" -lt 2 ]; then
  echo "FAIL — only ${#FILES[@]} pipeline file(s) found under $SKILL_DIR; find/path breakage or a moved skill."
  echo "If the skill was restructured, update this check."
  exit 1
fi

# Tripwire for the common shapes of concrete model names: named ollama tags
# (word:cloud, word:<size>b) and versioned family names, any case. Family names
# WITHOUT a version (Gemini, GLM, gpt-class, Claude) stay allowed — the
# Independence rule classifies by family. A regex cannot catch every conceivable
# model name; this bounds the common drift, it is not an exhaustive parser.
PATTERN='[a-z0-9][a-z0-9._-]*:(cloud|[0-9]+b)\b|\bglm-[0-9]|\bgpt-[0-9]|\bgemini[- ][0-9]|\bclaude[- ][0-9]|\b(opus|sonnet|haiku|fable)[- ][0-9]'

# ONE concrete name is let through: the model the Melious seat is held to (the owner's rule of
# 2026-10-12; independent_review.sh refuses any other MELIOUS_MODEL). It is the limit on a seat,
# not a default: the skill still picks no model for anyone. Two conditions, both needed:
#   - the line's own text names Melious (the file's name does not count). The same id as
#     another seat's default is the drift this guard exists for, and stays a violation.
#   - the id stands bare. Bare is defined by what MAY stand around it, so a spelling nobody
#     listed fails: before it the start of the text, a space or one of = " ' ` ( and after it
#     the end, a space, one of " ' ` ) , ; or a full stop that ends there. Anything else keeps
#     it a violation: a version, a suffix, ":cloud", and a prose colon too (reword the sentence).
# Reads grep's "file:line:text" lines, or bare text (the self-test).
allow_melious_model() {
  perl -pe 'my ($pre, $text) = /^((?:[^:\s]+:[0-9]+:)?)(.*)$/s;
            $text =~ s/(?:^|(?<=[\s=("\x27`]))glm-5\.3(?=$|[\s)"\x27`,;]|\.(?:$|[\s)"\x27`]))/<the Melious model>/g
              if $text =~ /melious/i;
            $_ = $pre . $text'
}

# Self-test, both directions. A guard that cannot fire is worse than none — and one
# that over-fires on the generic phrasing the header comment explicitly allows is
# its mirror image. Herestrings, not `printf | grep -q`: under pipefail a large enough
# input lets grep -q's early exit fail the printf and flip the result.
for bad in 'glm-9.9-flash:cloud' 'somemodel:120b' 'GPT-5' 'gpt-5.6-sol' \
           'Gemini 3.1 Pro' 'Claude Opus 4.6' 'claude-3' 'a Sonnet 4 pass'; do
  grep -qiE "$PATTERN" <<<"$bad" || {
    echo "FAIL — self-test: PATTERN misses '$bad'. Fix the pattern before trusting the scan."
    exit 1
  }
done
for good in 'Gemini' 'gpt-class' "a ':cloud' mention" 'claude family' 'ollama-cloud'; do
  if grep -qiE "$PATTERN" <<<"$good"; then
    echo "FAIL — self-test: PATTERN over-matches the allowed phrase '$good'."
    exit 1
  fi
done

# The same for the let-through: it must pass the bare id and nothing built on it. (With no perl
# it prints nothing, and the first loop fails.)
for bad in 'MELIOUS_MODEL=glm-5.3:cloud' 'melious glm-5.3-flash' 'melious glm-5.30' \
           'melious glm-5.3.1' 'melious glm-5.4' 'melious GLM-5.3' 'melious xglm-5.3:cloud' \
           'melious glm-5.3._preview' 'melious glm-5.3..preview' 'melious glm-5.3+flash' \
           'melious glm-5.3/latest' 'melious glm-5.3~x' 'melious/glm-5.3' 'Melious glm-5.3: prose' \
           'OLLAMA_MODEL=glm-5.3' 'a default of glm-5.3 for another seat' \
           'skills/x/perl/melious_request.pl:12:model glm-5.3' \
           'MELIOUS_MODEL=glm-5.3 OLLAMA_MODEL=glm-5.3:cloud'; do
  grep -qiE "$PATTERN" <<<"$(allow_melious_model <<<"$bad")" || {
    echo "FAIL — self-test: the Melious let-through hides '$bad'. Fix it before trusting the scan."
    exit 1
  }
done
for good in 'MELIOUS_MODEL=glm-5.3' 'Melious runs glm-5.3.' 'melious ("glm-5.3")' \
            'Melious: glm-5.3 and glm-5.3, only' 'a/b.sh:7:`MELIOUS_MODEL=glm-5.3` set (the' \
            'a/b.sh:7:glm-5.3; Melious' "melious 'glm-5.3'."; do
  if grep -qiE "$PATTERN" <<<"$(allow_melious_model <<<"$good")"; then
    echo "FAIL — self-test: the Melious let-through still flags the allowed '$good'."
    exit 1
  fi
done

# grep is tri-state: 0 = matches (violation), 1 = clean, >1 = error. An I/O error
# must not fall through to the OK line.
mismatches=$(grep -nIiE "$PATTERN" "${FILES[@]}")
rc=$?
if [ "$rc" -gt 1 ]; then
  echo "FAIL — grep errored (exit $rc) while scanning; the guard result is unreliable."
  exit 1
fi

# Second pass over the matched lines alone, with the Melious seat's model taken out: what still
# matches is a violation. (A line that holds both shows the let-through as "<the Melious model>".)
# Two steps, not a pipe: a filter that died would leave grep an empty input, grep's "no match"
# would be the pipe's status, and the scan would read as clean.
if [ -n "$mismatches" ]; then
  if ! filtered=$(allow_melious_model <<<"$mismatches"); then
    echo "FAIL — the Melious let-through's filter (perl) failed; the guard result is unreliable."
    exit 1
  fi
  mismatches=$(grep -iE "$PATTERN" <<<"$filtered")
  rc=$?
  if [ "$rc" -gt 1 ]; then
    echo "FAIL — the second pass errored (exit $rc) while scanning; the guard result is unreliable."
    exit 1
  fi
fi

if [ -n "$mismatches" ]; then
  echo "FAIL — a concrete model name/tag appears in independent-review's pipeline files."
  echo "The skill is model-agnostic: name model FAMILIES or generic tag shapes only, and"
  echo "let the owner's own CLI config/signin choose the actual model:"
  printf '%s\n' "$mismatches" | sed 's/^/    /'
  exit 1
fi

echo "OK — independent-review stays model-agnostic (no concrete model names/tags in its ${#FILES[@]} pipeline files, bar the one model the Melious seat is held to)"
