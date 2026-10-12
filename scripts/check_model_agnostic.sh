#!/usr/bin/env bash
# Guard: independent-review is model-AGNOSTIC — the pipeline prescribes no specific LLM.
# The ollama tier auto-detects the owner's signed-in ':cloud' model, Codex and Antigravity
# use their own CLI-configured defaults, and the docs speak in families and generic tags.
# A hardcoded default is exactly how the ollama tier once drifted out of sync with the
# owner's real setup (this script's pre-2026-08-29 ancestor, check_model_defaults.sh,
# managed that drift; this version prevents the class).
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."

SKILL_DIR="skills/independent-review"

# Scan every regular file in the skill EXCEPT two, each matched by exact path, not basename.
# scripts/melious_models.txt is the list of models the Melious seat may run (the owner's
# rule of 2026-10-12): a limit on one seat, kept as data in one file so that no other file
# needs a model's name, and no default for anyone. references/setup-guide.md is the
# drift-prone helper that cites dated, concrete
# local-model examples for the RAM table, and says so inline. The one known
# tag-classification defect that exclusion hides is tracked as row B-TAGCLASS in
# docs/reviews/OPEN-FINDINGS-independent-review.md. Files are discovered, not
# listed, and not filtered by extension, so a new reference, script, or helper of
# any type is scanned by default instead of silently skipped (grep -I skips any
# genuinely binary file).
FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(
  find "$SKILL_DIR" -type f ! -path "$SKILL_DIR/references/setup-guide.md" \
    ! -path "$SKILL_DIR/scripts/melious_models.txt" | sort
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

# grep is tri-state: 0 = matches (violation), 1 = clean, >1 = error. An I/O error
# must not fall through to the OK line.
mismatches=$(grep -nIiE "$PATTERN" "${FILES[@]}")
rc=$?
if [ "$rc" -gt 1 ]; then
  echo "FAIL — grep errored (exit $rc) while scanning; the guard result is unreliable."
  exit 1
fi

if [ -n "$mismatches" ]; then
  echo "FAIL — a concrete model name/tag appears in independent-review's pipeline files."
  echo "The skill is model-agnostic: name model FAMILIES or generic tag shapes only, and"
  echo "let the owner's own CLI config/signin choose the actual model:"
  printf '%s\n' "$mismatches" | sed 's/^/    /'
  exit 1
fi

echo "OK — independent-review stays model-agnostic (no concrete model names/tags in its ${#FILES[@]} pipeline files)"
