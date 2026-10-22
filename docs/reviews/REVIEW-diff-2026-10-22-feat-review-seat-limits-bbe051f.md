# DIFF review — feat/review-seat-limits — per-seat size limits, prompts on stdin (change 2)

Base `9acc3b97` · depth: Normal (the logic of a guard script, which the owner's rule never puts at Light; no login, money, user data or deletion, so not High) · verdict: OPEN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY: none yet (no PR)

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `bbe051f3` | full since `9acc3b97` (29 KB); the branch's own base check: "every changed tracked file present" | codex-cli 0.163.0, gpt-6.1-sol, effort high (config), read-only · Melious glm-5.3, HTTP API, text only · fresh-eyes: Claude Code sub-agent, Sonnet, read-only by instruction | codex 369 s, 98,681 · melious 470 s, 38,391 · fresh-eyes 2,221 s, 275,008 | raw 2/12/14 (codex 1/4/0, melious 0/2/4, fresh-eyes 1/5/10); 20 after dedup: 2/8/10 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| C1-01 | BUG | codex, melious, fresh-eyes | 1 | `codex_model` misread valid `config.toml`: a trailing comment, single quotes or indentation garbled the model, and a top-level `profile` key could make Codex run another model than the one the limit was looked up for | fixed, locally_verified | a strict top-level read (awk): `model = "<name>"` or `'<name>'`, a trailing comment allowed; no such line, an unreadable value or a top-level `profile` key gives no model, so the seat keeps 120,000; the cost log and the section header use it too. Seven shapes checked by hand; the real config still reads `gpt-6.1-sol`; T11h (commented, single-quoted: its limit applies), T11i (profile: 120,000) |
| C1-02 | BUG | fresh-eyes | 1 | `melious_models.txt` and the README said the model-name guard skips two files; it now skips three | fixed, locally_verified | both name `seat_limits.txt` too |
| C1-03 | RISK | codex | 1 | Codex's stdin delivery, whole take and cap rest on probes the reviewers cannot reproduce; text denser than the probe is untested | waived by the owner (decision 3, 2026-10-22: "Up to its own 1 MB cap"), evidence recorded | the probe output is quoted below (P1 equality, P2 token count and refusal); the density gap is named in `seat_limits.txt` and the plan |
| C1-04 | RISK | codex | 1 | The ollama CLI's stdin delivery and cloud refusal rest on unreproduced probes | refuted for P1 (output quoted below: 400,040 bytes recorded, equal); "refuses rather than cuts" is R4-02, waived by the owner on 2026-10-21 | below |
| C1-05 | RISK | codex | 1 | Melious's one refusal does not prove it never cuts | waived by the owner (R4-02, 2026-10-21) | plan, "Decided by the maintainer" 1 |
| C1-06 | RISK | codex, melious, fresh-eyes | 1 | Melious's limit counted the prompt without the output-format line appended after the check | fixed, locally_verified | the whole payload is written to `melious.prompt`, counted, then sent from that file; T11g: one byte under it FAILS, exactly it runs, and the request carries the file's bytes |
| C1-07 | RISK | fresh-eyes | 1 | No test failed if the Melious or ollama-API size check was removed | fixed, locally_verified | T11e (ollama API, no line: FAILED, curl never ran), T11f (Melious, no line: FAILED, no request, ollama stood in) |
| C1-08 | RISK | fresh-eyes | 1 | T8 in `test_base_check.sh` asserted the absence of "117 KB", which the script no longer prints | fixed, locally_verified | T8 asserts the base check refused and no seat FAILED or met a 120,000 limit |
| C1-09 | RISK | fresh-eyes | 1 | With the global cap gone, a round whose seats all FAIL on size printed the whole prompt as its paste fallback | fixed, locally_verified | over 120,000 bytes the paste prompt is left out with one line saying why; T13 asserts it |
| C1-10 | RISK | fresh-eyes | 1 | `seat_limits.txt` called the probe "denser than code or prose" without the plan's caveat, and the plan's table said "past the window" where it was inside Codex's 872,000-token maximum | fixed, locally_verified | the file names the untested denser text and the 1.2-bytes-a-token point; the table says "past its 500,000-token default window, inside its 872,000-token maximum" |
| C1-11 | NIT | fresh-eyes | 1 | A size FAILED pointed at the CLI and its sign-in, and said "No stderr captured" | fixed, locally_verified | it names the remedy (split, or measure and add a line) and says the seat never started; T11 asserts both |
| C1-12 | NIT | fresh-eyes | 1 | T9 checked a substring, not the bytes | fixed, locally_verified | `cmp` of the prompt file against what the stub received, for Codex (T9) and the ollama CLI (T10) |
| C1-13 | NIT | fresh-eyes | 1 | Nothing tied the real list's keys to the ids production uses | fixed, locally_verified | T13 asserts `melious <the id melious_models.txt allows> refuses` is a line of the real list |
| C1-14 | NIT | melious | 1 | `seat_fits`'s comment implied its byte count is always what is checked | fixed, locally_verified | it says the count is held against a `takes:` line only |
| C1-15 | NIT | melious | 1 | "The first line decides" sat after validation, so a later malformed duplicate voids the list | fixed, locally_verified | the comment says a malformed line anywhere voids the list, by design |
| C1-16 | NIT | melious | 1 | A line for agy voids the whole list | fixed, locally_verified | by design (strict); the header and `seat_limits.txt` now say agy has no line |
| C1-17 | NIT | melious, fresh-eyes | 1 | An unreadable list was reported as missing | fixed, locally_verified | missing and unreadable are told apart; only "missing" is silent |
| C1-18 | NIT | fresh-eyes | 1 | "Read like melious_models.txt", though that list fails the other way | fixed, locally_verified | "Strict like melious_models.txt, failing safe the other way" |
| C1-19 | NIT | fresh-eyes | 1 | No absolute ceiling for a seat that refuses: a 50 MB diff is uploaded before the provider says no | refuted | not a defect: such a seat fails loud by the plan's rule; an extra number would be unmeasured. The cost is one upload |
| C1-20 | NIT | fresh-eyes | 1 | The Melious stub claimed Melious's exact words | fixed, locally_verified | the comment says "in the shape of Melious's reply … wording shortened"; the real reply is quoted below |

Waivers and deferrals: C1-03 by the owner's decision 3 (2026-10-22), C1-04's second half and C1-05 by R4-02 (2026-10-21); both in the plan's "Decided by the maintainer". No deferrals.
Follow-ups: none yet.
Notes: substantive BUG in round 1: C1-01. The machine ran at a load average of 170 to 480 during the round (Spotlight, a VM, an iOS build); `make check` still passed.

Probe evidence (2026-10-22, from this session's probe run; quoted, not re-run):
- P1, ollama 0.40.7 CLI, a 400,040-byte prompt on stdin to a recording stub: `sent bytes 400040 recorded bytes 400040 equal: True`; the request went to `/api/generate` with keys `model, options, prompt, suffix, system, template`, `options: {}`.
- P1, codex-cli 0.163.0 with a model provider pointed at the stub in a throwaway `CODEX_HOME`: the request to `/v1/responses` held an input text that is `exact: True … len 400040 vs 400040`.
- P2, Codex, 1,300,130 bytes: `Error: turn/start: turn/start failed: Input exceeds the maximum length of 1048576 characters. (code -32602), data: {"input_error_code":"input_too_large","max_chars":1048576,"actual_chars":1300130}`.
- P2, Codex, 1,040,130 bytes: answered with the prompt's first line; `tokens used 522,639`. Calibration on the same filler: 5,607 tokens at 8,130 bytes and 41,679 at 80,130 (2.0 bytes a token).
- P2, Melious glm-5.3, 2,300,130 bytes: HTTP 400 `{"error":{"message":"This conversation (1,152,340 tokens) exceeds the model's context window (1,000,000 tokens). Please reduce the conversation length or switch to a model with a larger context window.","type":"invalid_request_error","param":null,"code":"context_length_exceeded"}}`. Calibration: 4,060 and 40,132 prompt tokens.
- P2, ollama CLI, GLM 5.3 on ollama cloud, the same prompt: `Error: 400 Bad Request: The prompt is too long: 1152362, model maximum context length: 1048576`. Calibration: 4,060 and 40,132 (`prompt eval count`).

<details><summary>Round 1 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, read-only)

- BUG — [independent_review.sh:1019](skills/independent-review/scripts/independent_review.sh:1019) — **WRONG:** `codex_model` misparses valid TOML: comments, tabs, and single quotes change the lookup key; reproduced a 200 KB artifact passing with plain formatting and failing with equivalent commented formatting. Fix: parse TOML correctly and bind the selected limit to the model explicitly requested.
- RISK — [seat_limits.txt:10](skills/independent-review/scripts/seat_limits.txt:10) — **UNVERIFIABLE, Codex:** stdin fidelity, whole-input consumption, and the 1,040,000-byte cap depend on unreproduced P1/P2 assertions; aggregate “tokens used” lacks an accounting trace, and dense inputs remain untested. Silent cutting could count an incomplete review as OK. Fix: retain the fallback pending recorded outbound-byte comparisons and inspection or measurement of truncation/token accounting.
- RISK — [seat_limits.txt:12](skills/independent-review/scripts/seat_limits.txt:12) — **UNVERIFIABLE, Ollama CLI/cloud:** neither P1’s byte equality nor the provider’s refusal policy has executable probes or raw captures here; replacement-CLI tests establish neither. Cutting could produce an OK review of partial input. Fix: retain the fallback pending real-CLI request capture and boundary observations of refusal/truncation behavior.
- RISK — [seat_limits.txt:11](skills/independent-review/scripts/seat_limits.txt:11) — **UNVERIFIABLE, Melious:** the recorded 400 assertion does not establish that other oversized prompts are rejected rather than cut; that claim removes the cap entirely. Cutting could count an incomplete review. Fix: retain the fallback pending inspection of admission/truncation policy or boundary measurements. The plan records acceptance of this residual risk, not verification.
- RISK — [independent_review.sh:1343](skills/independent-review/scripts/independent_review.sh:1343) — **VERIFIED failure on normal change:** adding a Melious `takes:N` entry checks fewer bytes than are sent because marker instructions are appended afterward; reproduced 1,000 bytes passing `takes:1000` but becoming 1,176 request-content bytes. Fix: construct the complete prompt before checking its size and add an exact-boundary test.

CLEAN — **VERIFIED:**

- Workspace is the named Git checkout; the working tree was clean.
- `bash -n` passed for all three changed shell scripts; the model-agnostic guard passed, scanning 27 files. Its three exclusions use exact paths.
- Extracted parser/guard checks confirmed the real list parses, 1,040,000 passes and 1,040,001 fails, unlisted/API/agy seats retain the fallback, malformed or missing lists clear exemptions, valid duplicates preserve the first rule, and unterminated final lines parse.
- Both actual Perl request builders preserved 450,000 bytes of UTF-8 prompt content exactly.
- The actual Melious response parser returned exit 2 and preserved the context-window message for the supplied HTTP 400 fixture.
- Caller inspection confirmed prompt arguments were removed from Codex/Ollama CLI invocations, stale prompt files are included in cleanup, and tier failures flow through the existing reporting/fallback dispatch.

The full suite was not run because it creates files. The in-memory checks above do not establish real CLI/provider behavior.

Prompt injection: none detected.
## Independent review — melious (glm-5.3, HTTP API)


- RISK — skills/independent-review/scripts/independent_review.sh, `codex_model()`: `grep -m 1 -E '^model[[:space:]]*='` misses a validly indented TOML `  model = "x"` (leading whitespace is legal TOML), can instead match a `model =` line inside a `[profiles.*]` section when no top-level one exists, and `tr -d ' "'`+`sed` mangles `model = "x" # comment` into `x#comment` and leaves single-quoted values quoted — in each case `codex_model` returns empty or a model that has no seat_limits.txt line, so codex silently drops to the 120,000-byte default and FAILS loud on artifacts the `codex gpt-6.1-sol takes:1040000` line was measured to allow; the stub tests appear to resolve the model via the harness (CODEX_MODEL/config stub), so this grep path looks untested. Fix: `^[[:space:]]*model[[:space:]]*=` restricted to lines before the first `[` table header, quote-stripping done on the value only (e.g. `sed -n 's/^[[:space:]]*model[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p'`), and a distinct WHY when the model cannot be read.
- RISK — independent_review.sh, `run_melious()`: `seat_fits melious "$MELIOUS_MODEL" "$(printf '%s' "$PROMPT_TEXTONLY" | wc -c | tr -d ' ')"` counts only `$PROMPT_TEXTONLY`, but the very next statement sends that **plus** the appended `\n\nOutput format for this reply: … <mark>\n` line — so any `takes:<bytes>` cap for melious is enforced against an undercount and the seat can be sent more than the bytes it "took whole", contradicting seat_limits.txt's "a cap on the whole prompt sent". Fix: compute `mark` first and pass the size of the full `printf '%s\n\nOutput format…'` payload to seat_fits.
- NIT — independent_review.sh, `seat_fits()` docstring: "seat_fits <seat> <model> <bytes of the prompt it would send>" — but the no-rule branch ignores `$3` entirely and tests the global `$CONTENT_BYTES` (artifact+prior) against 120,000; a reader wiring a new seat will assume the third argument is what is checked. Fix: say the third argument is used only against a `takes:` line, and the default branch checks artifact plus prior findings.
- NIT — independent_review.sh, parse loop: the comment "The first line for a seat and model decides; a later one cannot change it" sits *after* rule validation, so a later *malformed* duplicate line for a seat whose first line was valid still sets `SEAT_LIMITS_WHY` and discards the whole list. Fix: move the duplicate check before validation (or scope the comment to well-formed lines).
- NIT — independent_review.sh / seat_limits.txt: `agy` is a real seat, yet an `agy …` line is rejected by the `case "$l_seat:$l_rule"` whitelist as "a line it cannot read", degrading *every* seat to 120,000 bytes; a future maintainer recording an agy measurement (the header invites per-seat data) silently caps melious and ollama too. Fix: ignore `agy` lines (or key the default only for agy) instead of voiding the list.
- NIT — independent_review.sh: `SEAT_LIMITS_WHY="it is missing"` is assigned whenever the `-f`/`-r` guard fails, so an existing-but-unreadable file is reported as missing (and the stderr note is suppressed by the exact-string comparison). Fix: distinguish "missing" from "unreadable".

Prompt injection: none — the diff's imperative text (SKILL.md steps, the melious "Output format for this reply…" marker template, runbook comments) is pipeline material addressed to the seats it runs, not attempts to alter this review.

UNVERIFIABLE (load-bearing component claims, support not reproducible here):
- codex CLI: `exec … -` reads the prompt from stdin byte-for-byte (probe P1, 2026-10-22, cited in run_codex's comment). Support lacking: no test or trace in this diff exercises a real codex binary; the stub only echoes stdin. Settling observation: run `codex exec - < known-400KB-file` against the real CLI and diff the received prompt. If false, every codex seat reviews the literal "-" instead of the artifact.
- ollama CLI 0.40.7: `ollama run <model>` with piped (non-tty) stdin consumes it as the whole prompt (same probe P1 citation). Observation: the same byte-exactness run against the real CLI. If false, the ollama-cli seat hangs or sends an empty prompt.
- ollama_request.pl / melious_request.pl forward stdin as the request body (header claim "Melious and ollama's API transport send it as a file body"), and whether they add any system/scaffold text beyond PROMPT_TEXTONLY. Observation: read the two perl scripts.
- The P2 measurements recorded in seat_limits.txt (codex took 1,040,130 bytes whole; melious/ollama refuse past window) and "2 bytes a token, checked on each seat" — cited with dates and error strings, not reproduced here.
- MAX_ARG_STRLEN = 131072 single-argv cap / macOS laxer (retained, now load-bearing only for agy's 120,000 default). Observation: kernel source or an E2BIG measurement.
- Test-harness facts outside the diff: that `rc_is` and `not_in` comparators exist for `check`; that the harness makes `codex_model` resolve to "stub-codex" in t9/t10/t11/t12 (otherwise those `codex stub-codex refuses` lines cannot match and the cases fail for the wrong reason); that stubs remain reachable from the `$T/$name.scripts` copies.

CLEAN (checked):
- seat_limits.txt parse loop: blank/`#` comment handling (including indented comments after IFS stripping), seat+rule whitelist (glob-metacharacter seats rejected as subjects, not patterns), `takes:` validation — empty, non-digit, leading-zero, and >15-char rules all rejected; date/evidence (`l_rest`) presence required; the checked-in three-line file parses cleanly under these rules, including `glm-5.3:cloud` as a model field.
- `seat_fits` matching: patterns fully quoted so model names match literally (no glob surprises); the trailing space in `"$1 $2 "` prevents `gpt-6.1-sol` matching `gpt-6.1-solx`; here-string iteration over the newline-prefixed `SEAT_LIMITS` reads every entry including the leading empty line harmlessly; `refuses` returns 0 with no cap, per header and file docs.
- run_codex / ollama_via_cli: prompt written to a file before `seat_fits`, stdin redirect forms (`-` for codex, no prompt argument for ollama) match the stub capture and the updated argv expectations (`[-]`, no `<prompt>` anywhere in argv); stale-file `rm -f` extended to `codex.prompt` and `ollama.prompt`, so a seat-failed prompt file cannot leak into the next run.
- run_agy: `seat_fits agy "" 0` sits before mktemp/sbox, so it genuinely fails before sending, and bytes=0 makes a `takes:` branch unreachable by construction; the WHY interpolation `${2:+$1 $2, }` degrades gracefully with an empty model.
- run_melious / ollama_via_api: seat_fits called before any request build or send, matching the "FAILS before it sends anything" claim in the header and SKILL.md.
- check_model_agnostic.sh: the "EXCEPT three" comment matches the three exact-path `! -path` exclusions; seat_limits.txt does contain model names, so excluding it (like melious_models.txt) is consistent with the scan's purpose.
- SKILL.md's replacement text ("each seat has its own limit… a seat over it FAILS before sending and the others run") matches the implemented behavior.
- New test expectations traced string-by-string against the emitted WHYs: t11a/t11b "artifact and prior findings of", t11c "a prompt of … over the 150000 this seat took whole", t13/t13c stderr notes; `whole`/`bigdiff` byte math is ASCII-safe (chars = bytes) and the >390000/>190000 guards hold; `limitcase`'s `--` splitting and `${envs[@]+…}` empty-array guard are correct under `set -u`; the ctx400 stub's JSON contains exactly the strings t12 asserts ("HTTP 400" via status, "exceeds the context window").

---
reviewers: codex OK, melious OK
timings: codex 369s (98681 tokens), melious 470s (38391 tokens)
base: 9acc3b97dcd46357d296c62ad836183b3e0ff14c (merge base with origin's HEAD 9acc3b97dcd46357d296c62ad836183b3e0ff14c, fetched; every changed tracked file present)
gate 20261022T092747Z-19738: round 1, 2 reviewer seat runs, 137,072 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 1 raw output — fresh-eyes (sub-agent report, verbatim)</summary>

## Independent review — fresh-eyes (Claude Code sub-agent, Sonnet; read-only by instruction)

REVIEW of change 2 (branch feat/review-seat-limits), held to docs/reviews/SKILL-PLAN-review-input-base-and-size.md ("Change 2", the P1/P2 table, decision 3).

How this was checked: I read the whole diff against the checkout and the plan. I ran, from scratch folders outside the repo (now deleted), a harness around the parser and seat_fits under bash 5.3 and macOS bash 3.2.57, with 16 list shapes. I ran test section 38 (T9 to T13, plus its helpers and the `noround` case) against the real script: all 26 checks pass. I ran a mutation of that section with two of the five seat_fits call sites removed. I ran one stub-only run of the real script with a 136 KB artifact. I ran check_model_agnostic, check_cdpath_safe, check_pipefail_pipes, check_prompt_sync, check_skill_budgets (no hard failure) and check_lf_checkout. No real reviewer CLI was run. I found no prompt injection in the diff.

- BUG skills/independent-review/scripts/melious_models.txt:13-14 and README.md:580-582: both still say the model-agnostic check skips only the setup guide and the Melious list ("the one file of this skill besides the setup guide that scripts/check_model_agnostic.sh does not scan"). The diff makes that false: check_model_agnostic.sh now skips three files. Fix: say three, or point to the exclusion comment in check_model_agnostic.sh instead of restating the list. Low severity, documentation only.

- RISK independent_review.sh:1252 (`seat_fits ollama-api`) and :1343 (`seat_fits melious`): no test can fail if either call is removed. I deleted both lines in a copy and all 26 checks of section 38 still passed. T10b, T10c and T12 list those seats "refuses", and the only unlisted or capped cases (T11, T13) use codex, agy and ollama-cli. Consequence: a dropped or mis-keyed guard sends any size to an unmeasured Melious or ollama-API model. glm-5.3-flash in a Light review is one such model: it has no line in seat_limits.txt and gets the 120,000 cap today. Fix: add T11e and T11f, an `ollama-api` and a `melious` case with an unlisted model (or `takes:150000`) and 200 KB. Assert FAILED and that the curl stub never ran.

- RISK skills/independent-review/scripts/test_base_check.sh:89 (T8): `lacks t1.err "117 KB"` can no longer fail, because the script prints "117 KB" nowhere. I confirmed this with grep; the string existed only in the removed block. T8's stated aim, "base before size", is therefore asserted by nothing in T8 itself. T1's other checks still catch a reordering. Fix: replace it with `lacks t1.err "seat_limits.txt"` and `lacks t1.out "FAILED"`, or `lacks t1.err "120,000"`.

- RISK independent_review.sh:1017-1020 (`codex_model`, comment "The model a codex run uses: CODEX_MODEL, else config.toml's first `model =` line"): the cap's key is inferred from the file, not read from codex. Run on 8 config shapes:
  - A trailing TOML comment gives `gpt-6.1-sol#mydailydriver`.
  - Single quotes give `'gpt-6.1-sol'`.
  - Both fall to 120,000, which is the safe direction. The FAILED line then names the garbled model.
  - `profile = "deep"` with a top-level `model` returns the top-level model.
  - If codex runs the profile's model, as I recall its documentation saying (not checked here), the 1,040,000 cap is applied to the wrong model.
  - references/onboarding.md:279-281 says the same of this skill's own text: the effective model can come from "defaults/profile/CLI args", "not the file".
  Fix: when CODEX_MODEL is unset, return an empty model (so 120,000 applies) if config.toml has a `profile` key, or if the `model =` line has anything after the closing quote. Better, pass the resolved model to codex with `-c model=` so the key and the run model are the same string.

- RISK independent_review.sh:~1717-1719 (final `printf '%s\n' "$PROMPT_PORTABLE"` on exit 4): with the global size gate gone, a round whose seats all FAIL on size now echoes the whole prompt to stdout. Reproduced with `--seat codex`, an unlisted model and a 136 KB artifact: exit 4, then the full prompt after the summary. A `--seat ollama` Kimi final full read of a 2 MB change would print 2 MB into the caller's context. Before, an oversize run was one stderr line and exit 2. Fix: print the paste prompt only when CONTENT_BYTES is at most 120000, else one line saying why it is omitted.

- RISK seat_limits.txt:8-9 (and the same words in the plan's decision 3): "denser than code or prose" is stated as a bound. The plan itself says "not tested: text denser than the probe ... such as a diff full of base64 hashes". The file drops that caveat. Local `~/.codex/models_cache.json` for gpt-6.1-sol lists context_window 500000, max_context_window 872000 and effective_context_window_percent 95. So the P2 answer at 522,639 tokens was inside the model's maximum window, not past it as the plan's table says. The 1,040,000-byte cap is safe only down to about 1.19 bytes per token (872,000 ÷ 1,040,000). That is also the point where a lockfile or base64 diff goes past Codex's default 500K window, where its auto-compaction applies. Fix: put the plan's caveat into seat_limits.txt, and say "denser than typical code or prose".

- NIT independent_review.sh:1486 (report_tier's generic `reason`): a size FAILED reads "...nothing was sent; no quota or rate-limit error recognised below. Read the quoted lines, then check the CLI, its sign-in and the model name." followed by "No stderr captured". There are no quoted lines, and the remedy points the wrong way. SKILL.md promises "the error and remedy"; the old message said "Split it". Fix: let WHY end with the remedy ("split the artifact, or measure this model (probe P2) and add a line to seat_limits.txt"), and skip the generic sentence for that case.

- NIT test_failed_tier_report.sh:1551 (T9) against plan T9 "same bytes, same hash": `whole` only checks that the artifact is a substring of what the stub received, so a cut tail of the instructions would pass. Fix: `cmp "$T/t9.raw/codex.prompt" "$T/t9.marks/codex-prompt"` (REVIEW_RAW_DIR is `$T/t9.raw`), and the same for ollama.prompt in T10a.

- NIT test_failed_tier_report.sh (T13, last check): "the real list reads cleanly" only asserts that no "holds" note appears. Nothing ties the real keys (`melious glm-5.3`, `ollama-cli glm-5.3:cloud`) to the ids production uses. If melious_models.txt renames glm-5.3, the line goes stale without notice. Fix: assert that `melious $MELIOUS_OK` is a line of the real seat_limits.txt.

- NIT independent_review.sh:1343: Melious's byte count is `$PROMPT_TEXTONLY`, but the request appends an output-format line of about 190 bytes. This only matters if a `melious takes:N` line is ever added. Fix: count what is sent.

- NIT independent_review.sh:~638 ("Read like melious_models.txt"): that list refuses every model when it is missing or malformed. This one falls back to 120,000 and only prints a note. Say "same format".

- NIT independent_review.sh (seat_limits parse): an existing but unreadable file is reported as "it is missing".

- NIT independent_review.sh:1072 and log_seat (`cfg=` and the `model=` in log_seat): these repeat the config.toml grep that codex_model now holds. Use codex_model in all three so a fix to the parse reaches the header and the cost log too.

- NIT (no cap on "refuses" seats): no absolute ceiling on the artifact for a "refuses" seat. A 50 MB accidental diff is JSON-encoded in Perl and uploaded before the provider says no. It does fail loud, and the plan accepted it. A sanity ceiling would be cheap.

CLEAN (checked, no finding):
- check_model_agnostic.sh exclusion by exact path: VERIFIED, ran "OK, 27 files". The `find` and `!` clauses are correct.
- seat_limits parser: VERIFIED on 16 shapes under bash 5.3 and 3.2.57. The first line for a seat and model wins; a later bad line voids the file; CRLF, tabs, a glob model, uppercase, a leading zero, `takes:0` and 16 digits are all handled; agy and unknown seats are refused; the last line without a newline is read.
- seat_fits: VERIFIED against the plan's three rules. 1,040,000 fits and 1,040,001 does not; an unlisted model gets 120,000 on artifact plus prior; agy always gets 120,000.
- Codex and ollama-CLI prompts go on stdin through a file; the stale-file `rm -f` list includes both prompt files; every seat_fits call passes three arguments.
- Section 38 (T9 to T13): all 26 checks pass against the real script. T9 to T13 are present, with the two deviations noted above.
- agy argv margin: VERIFIED. A 119,944-byte diff gave a 122,523-byte argument, an overhead of 2.6 KB, under the 131,072 Linux limit. The 120,000 cap still protects it.
- Keys in seat_limits.txt: `gpt-6.1-sol` matches ~/.codex/config.toml line 1. The bytes-per-token figures (about 2) agree across the three evidence lines.
- check_prompt_sync, check_cdpath_safe, check_pipefail_pipes, check_skill_budgets (no hard failure), check_lf_checkout: pass.
- SKILL.md "Size:" paragraph matches the code and the script header. No other doc still says "117 KB". No second copy of the script exists to drift.
- Plan fidelity: changes match the plan's design (per-seat check, stdin, list, order after the base check). Differences: T9 weaker than "same hash"; T11's agy case runs `--seat agy` alone, not "beside" a refuses seat.

UNVERIFIABLE (grouped by component; claim, support missing, observation that would settle it):
- Codex CLI 0.163.0:
  - Claims: `exec ... -` sends a 400,040-byte stdin prompt through whole (P1); it took a 1,040,130-byte prompt whole, "tokens used 522,639" being the sign (P2); its CLI rejects over 1,048,576 characters (`input_too_large`); the model it runs is config.toml's first `model =` (the codex_model comment).
  - Missing: no probe transcript is in the repo, only the plan's prose and seat_limits.txt; the P1 recording only reached 400 KB while the cap allows 1,040,000; no nonce quote is recorded for P2; Codex's profile handling was not read.
  - Settle: a stub server recording the request body and its sha256 against the sent prompt at 1,040,000 bytes; a P2 reply quoting the first and last nonce; the model name codex prints for a config with `profile = ...` and a differing profile model.
- ollama CLI 0.40.7: claims are that `ollama run MODEL` with no prompt argument and non-tty stdin sends all of stdin as the prompt, and that cloud prompts below 1,048,576 tokens reach the model uncut (the code sends no `num_ctx`). The over-window refusal quoted for glm-5.3:cloud is the only server behaviour recorded. Settle: a recording stub at 400 KB and 2 MB with hashes, and an in-window nonce prompt to the cloud model whose reply is checked for both nonces and a plausible prompt-token count. This is the plan's accepted R4-02, so it is not a finding against the code.
- Melious API: claims are the HTTP 400 `context_length_exceeded` at 1,152,340 tokens against a 1,000,000-token window, and that the test stub's JSON body (test_failed_tier_report.sh, `ctx400`, "in Melious's words (probe P2)") is Melious's real error shape. No recorded response body exists. Settle: the saved P2 response body, compared field by field with the stub.

</details>
