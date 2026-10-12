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
# not a default: the skill still picks no model for anyone. It passes in ONE shape only: as the
# whole value given to a variable whose name starts with MELIOUS_ (MELIOUS_MODEL=..., quoted or
# not). Everywhere else it stays a violation: in prose, as any other seat's value, inside a
# longer id or an ollama tag (a version, a suffix, ":cloud"), and with a colon after it. So the
# skill's files write the name as that assignment and nothing else, and what the line or the
# file is called never matters. After the value may stand the end of the line, a space, one of
# ) ` , ; " ' or a full stop that ends there.
allow_melious_model() {
  perl -pe 's/(?<![A-Za-z0-9_])(MELIOUS_[A-Z0-9_]*=)(["\x27]?)glm-5\.3\2(?=$|[\s)`,;"\x27]|\.(?:$|[\s)`"\x27]))/$1<the Melious model>/g'
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

# The same for the let-through: it must pass that one shape and nothing else. (With no perl it
# prints nothing, and the first loop fails.)
for bad in 'Melious runs glm-5.3' 'OLLAMA_MODEL=glm-5.3' 'a default of glm-5.3 for another seat' \
           'MELIOUS_MODEL=glm-5.3 OLLAMA_MODEL=glm-5.3' 'OLLAMA_MODEL=glm-5.3 MELIOUS_MODEL=glm-5.3' \
           'MELIOUS_MODEL=glm-5.3 OLLAMA_MODEL="glm-5.3"' \
           'skills/x/melious notes.md:12:OLLAMA_MODEL=glm-5.3' 'skills/x/MELIOUS_A=b.md:3:glm-5.3' \
           'XMELIOUS_MODEL=glm-5.3' 'melious_model=glm-5.3' 'MELIOUS_MODEL= glm-5.3' \
           'MELIOUS_MODEL="glm-5.3' "MELIOUS_MODEL=\"glm-5.3'" 'MELIOUS_MODEL=${X:-glm-5.3}' \
           'MELIOUS_MODEL=glm-5.3:cloud' 'MELIOUS_MODEL=glm-5.3: prose' 'MELIOUS_MODEL=glm-5.3-flash' \
           'MELIOUS_MODEL=glm-5.30' 'MELIOUS_MODEL=glm-5.3.1' 'MELIOUS_MODEL=glm-5.4' \
           'MELIOUS_MODEL=GLM-5.3' 'MELIOUS_MODEL=xglm-5.3:cloud' 'MELIOUS_MODEL=glm-5.3._preview' \
           'MELIOUS_MODEL=glm-5.3..preview' 'MELIOUS_MODEL=glm-5.3+flash' \
           'MELIOUS_MODEL=glm-5.3/latest' 'MELIOUS_MODEL=glm-5.3~x' 'MELIOUS_MODEL=glm-5.3_x'; do
  grep -qiE "$PATTERN" <<<"$(allow_melious_model <<<"$bad")" || {
    echo "FAIL — self-test: the Melious let-through hides '$bad'. Fix it before trusting the scan."
    exit 1
  }
done
for good in 'MELIOUS_MODEL=glm-5.3' 'MELIOUS_ONLY_MODEL="glm-5.3"' "MELIOUS_OK='glm-5.3'; next" \
            'with `MELIOUS_MODEL=glm-5.3` set (the' 'Set MELIOUS_MODEL=glm-5.3.' \
            'a/b c.sh:7:run x MELIOUS_MODEL=glm-5.3 bash' '"MELIOUS_MODEL=glm-5.3", then' \
            'MELIOUS_MODEL=glm-5.3 MELIOUS_MODEL=glm-5.3'; do
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

# Second pass over the matched lines alone, with the Melious seat's own assignments taken out:
# what still matches is a violation. (Such a line shows them as "<the Melious model>".)
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
