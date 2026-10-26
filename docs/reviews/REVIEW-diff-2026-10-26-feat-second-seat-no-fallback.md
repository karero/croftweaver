# Review trail: DIFF gate, feat/second-seat-no-fallback

Gate: DIFF, depth Normal (changes a review script's logic and its tests). Plan:
`SKILL-PLAN-second-seat-no-fallback.md` (PLAN gate clean). Seats run as two separate commands
(`--seat codex`, `--seat melious`) with the same `--round`, by the maintainer's rule of 2026-10-26;
fresh-eyes on a mid-tier host-family model in round 1. Artifact: `git diff 7c7d4073...HEAD -- .
':(exclude)docs/reviews/'`. Evidence: the suite, `make check`, the eight mutation runs and the live
check, sent with `--evidence`.

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
