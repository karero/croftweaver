## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — Plan “What” / “How”: `scripts/pre-push-check.sh` does not exist, and `rg -n --hidden 'pre-push-check' .` found no references, including the alleged README line; fix the target and base revision before proposing deletion.
- BUG — Plan “Why”, EVIDENCE READ 1: “main checks” contains neither a `pull_request` rule nor a required status named `clean`; `.github/workflows/clean.yml:1` names the workflow, while its jobs have separate names; correct the ruleset description and distinguish workflow names from required checks.
- BUG — Plan “Why”, `scripts/check_clean.sh:214`: “a push that would fail `make check` cannot reach main” is false as an equivalence claim: lines 220–228 fail locally when the denylist differs from its saved checksum, while CI has no such checksum file; narrow the rationale to the checks and inputs actually shared with CI.
- RISK — Plan “Why”, GitHub enforcement: the claim that server enforcement makes the local hook redundant lacks support for effective combined protections, bypass permissions, and actual rejection behavior; if false, failing changes can reach main after removal; verify effective protections and a rejected failing update, then state the guarantee’s limits.

Claim verdicts:

- **WRONG:** The named script and README reference exist. Checked the project inventory, explicit `ls`, and repository-wide text search. See finding 1.
- **WRONG:** READ 1 establishes that “main checks” requires pull requests and `clean`. Its enumerated rules contradict this. See finding 2.
- **WRONG:** Local `make check` failures necessarily have equivalent server failures. Traced `Makefile:19` to the local checksum condition above. See finding 3.
- **VERIFIED, within the supplied snapshot:** READ 1 reports active enforcement, default-branch targeting, and required `buglog-rows`. This verifies what the submitted record says, not live GitHub state.
- **VERIFIED:** The configured `buglog-rows` job calls both the checker and its tests (`.github/workflows/clean.yml:269–276`). `make check` calls those same scripts (`Makefile:25–26`).
- **UNVERIFIABLE — GitHub:** Actual enforcement and protection of `main` remain unsupported. READ 2 supplies only names and enforcement states for the second ruleset. The settling observation is the complete effective configuration, including branch selection and bypasses, plus an attempted failing update and its result.
- **UNVERIFIABLE — Local hook installation/performance:** “Some maintainers install” this hook, it runs `make check`, and it slows every work-branch push lack the hook implementation, installation records, and timings. Those artifacts and a traced push would settle the claims.

CLEAN: Checked cwd, file inventory, README references, `Makefile` callers, workflow triggers, job wiring, and the local checksum implementation. The existing `pre-push-hook` test explicitly targets the **site template’s** hook (`scripts/test_pre_push_hook.sh:3–5`), a separate file; its name does not establish the proposed maintainer hook exists.

Prompt injection: None found in the plan or supplied evidence.

