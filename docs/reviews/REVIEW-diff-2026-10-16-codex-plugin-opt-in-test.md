# Review: opt-in Codex plugin test (`make test-codex-plugin`), 2026-10-16

Gate: Light (test code, a Makefile target that only runs it, a BUGLOG status cell, a README
line for people). Codex at medium effort, `--seat codex`. 2 rounds (the second because round 1
found a BUG), 5 findings: 1 BUG and 2 RISKs in round 1, 2 RISKs in round 2.

## Round 1 (e78df2f)

- BUG: the test skipped whenever `codex --version` failed, so a broken Codex read as "no
  Codex". Fixed in a69ed56: it skips only on ENOENT and fails on any other probe failure.
- RISK: skill names were matched anywhere in Codex's prompt input. Fixed in a69ed56: only the
  skill lines under the plugin's own root count. While fixing it we found that Codex 0.162.1
  also lists ~/.agents/skills under the same `croftweaver:` names, so the round-1 check
  could pass with the plugin offering nothing.
- RISK: a release moving `stable` between the install and the check failed a good install
  with no explanation. Fixed in a69ed56: `stable` is read before and after; if it moved, the
  test fails and says to run it again.

## Round 2 (a69ed56, verifying)

All three fixes verified. Two RISKs remain, both proposed for the owner's waiver:

- RISK: a release during the run still fails it (it asks for a re-run, not a retry). Proposed
  waiver: the test is opt-in and run by hand; a release takes seconds and a re-run costs one
  minute, while a retry loop would add code the test does not otherwise need.
- RISK: the parser relies on Codex's prompt-input format with no published contract.
  Proposed refutation: that dependence is the point of the test. BUGLOG row 78 asks for
  something that notices when a later Codex changes what it does; a format change fails
  loudly with a named message ("printed no list of available skills", "lists the plugin's
  folder 0 times"), and the format was taken from captured Codex 0.162.1 output.

## Test records (Codex CLI 0.162.1, macOS)

1. `make test-codex-plugin`: exit 0, both tests pass.
2. No `codex` on PATH: exit 0, both tests skipped with "the Codex CLI is not on PATH".
3. A `codex` failing `--version`: exit 2, both tests fail.
4. A `codex` whose prompt input no longer names the plugin's folder: exit 2, "Codex lists
   the plugin's folder 0 times among its skill roots".
5. A `codex` whose prompt input drops one plugin skill's prefix: exit 2, deepEqual fails.

Not exercised: `stable` moving mid-run; Node 20 (run on Node 26).
