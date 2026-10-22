# DIFF review — feat/review-seat-limits — per-seat size limits, prompts on stdin (change 2)

Base `9acc3b97` · depth: Normal (the logic of a guard script, which the owner's rule never puts at Light; no login, money, user data or deletion, so not High) · verdict: OPEN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY: none yet (no PR)

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `bbe051f3` | full since `9acc3b97` (29 KB); the branch's own base check: "every changed tracked file present" | codex-cli 0.163.0, gpt-6.1-sol, effort high (config), read-only · Melious glm-5.3, HTTP API, text only · fresh-eyes: Claude Code sub-agent, Sonnet, read-only by instruction | codex 369 s, 98,681 · melious 470 s, 38,391 · fresh-eyes 2,221 s, 275,008 | raw 2/12/14 (codex 1/4/0, melious 0/2/4, fresh-eyes 1/5/10); 20 after dedup: 2/8/10 |
| 2 | `8185bef4` | delta since `bbe051f3` (23 KB), `--verify` with round 1's rows; base check `--base bbe051f3` | codex-cli 0.163.0, gpt-6.1-sol, effort medium (`--verify`), read-only · Melious glm-5.3, HTTP API, text only | codex 177 s, 41,110 · melious 611 s, 56,528 | raw 2/2/3 (codex 2/0/0, melious 0/2/3); no duplicates: 2/2/3 |
| 3 | `8df772b0` | delta since `8185bef4` (11 KB), `--verify` with round 2's rows; `--base 8185bef4` | as round 2 | codex 134 s, 48,413 · melious 269 s, 26,107 | raw 2/0/3 (codex 1/0/0, melious 1/0/3); no duplicates: 2/0/3 |
| 4 | `56b6331b` | delta since `8df772b0` (12 KB), `--verify` with round 3's rows; `--base 8df772b0`; earned by C3-01 and C3-02 (`--earned-by utf8-byte-count`, `--cut "dropped iconv and the fall-through to 120,000; a prompt not valid UTF-8 counts 3 bytes per byte"`) | as round 2 | codex 214 s, 38,804 · melious 246 s, 21,992 | raw 2/1/3 (codex 1/0/1, melious 1/1/2); no duplicates: 2/1/3 |

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
| C2-01 | BUG | codex | 2 | C1-01 incomplete: a quoted top-level key, `"profile" = "deep"`, is the same TOML key, and slipped past the profile check | fixed, locally_verified | any quoted top-level key leaves the model unknown (120,000 bytes); checked by hand on three shapes; T11j |
| C2-02 | BUG | codex | 2 | C1-06 incomplete: the request builders decode the prompt as UTF-8 and replace an invalid byte with a longer character, so a Latin-1 diff could pass a `takes:` limit and then grow past it | fixed, locally_verified | a `takes:` line holds only for a prompt `iconv -f UTF-8 -t UTF-8` accepts; any other prompt falls back to 120,000 bytes on the artifact, and the FAILED line says why. `seat_fits` now counts the prompt file itself; the ollama API transport writes one too. T11k (Codex) and T11l (Melious): a Latin-1 byte FAILS before sending; T11m: valid UTF-8 under the same limit runs |
| C2-03 | RISK | melious | 2 | The record says the plan's table changed, but the diff holds no plan edit | refuted | the plan is under `docs/reviews/`, which the review's diff command leaves out; the edit is in `8185bef4` (`git show 8185bef4 -- docs/reviews/SKILL-PLAN-review-input-base-and-size.md`) |
| C2-04 | RISK | melious | 2 | The paste prompt is left out by artifact size alone, so a large round whose seats failed for other reasons (sign-in, no CLI) loses it, and the line told it to "run a seat whose limit takes it" | wording fixed, locally_verified; the gate itself refuted | the line now reads "too long to paste. Fix the failed seats above, or split the artifact." The gate stays: a paste prompt over 120,000 bytes floods the caller's context whatever failed the seats (C1-09), and before this change such a run was refused outright |
| C2-05 | NIT | melious | 2 | The gate counts the artifact and prior findings, but prints the prompt with its wrapper, a little longer | refuted | 120,000 bytes is the line at which pasting stops being sensible, not a provider limit; the wrapper's fixed text does not change that |
| C2-06 | NIT | melious | 2 | The exact-boundary test assumes Melious's prompt is the same size in three runs | fixed, locally_verified | T11 asserts that the two boundary runs wrote the same S bytes as the first |
| C2-07 | NIT | melious | 2 | The note would read "holds it is missing" | refuted | a missing list prints no note (`independent_review.sh`, the `= "it is missing"` test before the echo); an unreadable one reads "holds nothing this script can read (not a readable file)" |
| C3-01 | BUG | codex | 3 | C2-02's check was not the builders' decoder: macOS `iconv` accepts bytes above U+10FFFF and five- or six-byte sequences, which the builders replace | fixed (a cut), locally_verified | `iconv` is gone: `perl/utf8_valid.pl` decides with Encode's strict "UTF-8", the decoder the builders use. It rejects Latin-1, above U+10FFFF, five bytes, a surrogate, overlong and a noncharacter, and accepts UTF-8, ASCII and an empty file (nine shapes by hand; six checked in the suite) |
| C3-02 | BUG | melious | 3 | A prompt that failed the UTF-8 check fell through to the 120,000 rule, so a `takes:` line under 120,000 let a larger prompt through | fixed (a cut), locally_verified | no fall-through: a `takes:` line always holds. A prompt that is not valid UTF-8, or any prompt when perl is missing, counts three bytes for each of its own, since a decoder makes at most one 3-byte U+FFFD of a bad byte. T11o: 100 KB of Latin-1 over `takes:90000` FAILS, though under 120,000 |
| C3-03 | NIT | melious | 3 | A Latin-1 prompt just over 120,000 bytes was refused even where its measured limit would take the grown prompt | fixed, locally_verified | the same cut: T11n, 200 KB of Latin-1 under `takes:700000`, runs; T11k and T11l, under `takes:500000`, FAIL before sending |
| C3-04 | NIT | melious | 3 | T11l's check that Melious's request never left may be empty | refuted | the curl stub copies every request it gets to `melious-body` in the marks folder (`cp "$body" "$STUB_MARKS/melious-body"`), and T10b reads that same path after a run that sent |
| C3-05 | NIT | melious | 3 | `codex_model`'s quoted-key test also fires on a line inside a multi-line top-level string that starts with a quote | refuted | it fails safe: the model reads as unknown, so the seat keeps the 120,000 limit it had before this change and names the remedy; `CODEX_MODEL` overrides. Telling such lines apart needs a TOML parser, which this reader avoids |
| C4-01 | BUG | codex | 4 | `utf8_valid.pl` promised exit 1 for a file it cannot read, but read a folder as an empty, valid file | fixed, locally_verified | a read error now exits 1 (an empty file still reads as `''`); run on the `perl` folder: exit 1; suite: "a file it cannot read (a folder) is not". Not reachable from the script, which passes only the prompt file it has just written; counted as earning round 5 all the same |
| C4-02 | NIT | codex | 4 | Count the decoded length with Perl instead of three times the bytes | refuted | that length holds for the two Perl builders only. The CLIs decode for themselves: Codex refuses such a prompt outright and the ollama CLI makes one U+FFFD of each bad byte (C4-04's probe). Three times is the bound that holds for every seat; the cost is that a prompt with a bad byte FAILS, saying why, past a third of its limit |
| C4-03 | BUG | melious | 4 | With an empty file argument, `wc` printed a stray error and the seat FAILED with "could not count" | fixed, locally_verified | the check is back: no readable file, no `wc`, no stray output. The comment says only agy passes an empty argument, and agy can have no line, so a `takes:` rule never meets it. Falling through to 120,000 instead is refuted: that was C3-02's hole. Counted as earning round 5 |
| C4-04 | RISK | melious | 4 | That the builders decode as `perl/utf8_valid.pl` does, and make at most one 3-byte U+FFFD of a bad byte, rests on code outside the diff | refuted, by observation | both Perl builders call `decode("UTF-8", …)` (`perl/melious_request.pl:7`, `perl/ollama_request.pl:7`); round 4's Codex ran both against 85,793 inputs and found none over three times. Probe, 2026-10-22, against probe P1's recording stub, a 51-byte prompt holding 15 bad bytes: codex-cli 0.163.0 refuses it on stdin ("Failed to read prompt from stdin: input is not valid UTF-8 (invalid byte at offset 11)") and on argv alike ("invalid UTF-8 was detected in one or more arguments"), so moving it to stdin changed nothing; ollama 0.40.7 sent it as 81 bytes, 15 U+FFFD |
| C4-05 | NIT | melious | 4 | The docs left out that with no perl every prompt counts three times | fixed, locally_verified | `seat_limits.txt` and the script header say so |
| C4-06 | NIT | melious | 4 | No test ran `seat_fits` with no perl | fixed, locally_verified | T11p: section 36's PATH without perl; valid UTF-8 that T11m runs FAILS at three times its bytes |

Waivers and deferrals: C1-03 by the owner's decision 3 (2026-10-22), C1-04's second half and C1-05 by R4-02 (2026-10-21); both in the plan's "Decided by the maintainer". No deferrals.
Follow-ups: none yet.
Notes: substantive BUGs: C1-01 in round 1; C2-01 and C2-02 in round 2, each an incomplete fix of a round 1 item; C3-01 and C3-02 in round 3, both in C2-02's fix, which round 3's fix replaced with a cut; C4-01 and C4-03 in round 4, counted as substantive though neither is reachable from the script (each was a comment's promise the code did not keep), so they earn round 5. The machine ran at a load average of 170 to 480 during the round (Spotlight, a VM, an iOS build); `make check` still passed.

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

<details><summary>Round 2 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- BUG — `skills/independent-review/scripts/independent_review.sh:1030` (C1-01, incomplete fix): valid TOML `"profile" = "deep"` bypasses profile detection, so `codex_model` returns the top-level model and permits its measured limit despite the unresolved profile override; recognize quoted keys or conservatively return unknown for unsupported key syntax, and add this regression case.
- BUG — `skills/independent-review/scripts/independent_review.sh:1366` (C1-06, incomplete fix): the cap counts raw bytes before `melious_request.pl:7` replaces invalid UTF-8; reproduced `+caf\xe9\n` expanding from 6 to 8 content bytes, so a Latin-1 diff can exceed `takes:` after passing the check; reject invalid UTF-8 before sending, or count the converted content, and test that boundary.

**Claim verdicts and CLEAN coverage**

VERIFIED means the implementation and assertions were checked; it does not mean the filesystem-writing suites passed.

| Prior claim | Verdict | Evidence |
|---|---|---|
| C1-01: strict model read handles comments, single quotes and profiles | **WRONG in part** | Extracted production awk correctly handled indentation, comments, single quotes and bare `profile`; it returned `stub-codex` for quoted `"profile"`. Python `tomllib` parsed both profile spellings identically. See first BUG. |
| C1-06: checked Melious file contains all content subsequently sent | **WRONG in part** | The appended format line is now included, but a direct invocation of `perl/melious_request.pl` reproduced byte expansion during decoding. See second BUG. |
| C1-02: guard excludes three named files | **VERIFIED — CLEAN** | README, `melious_models.txt`, and exact-path exclusions in `scripts/check_model_agnostic.sh` agree. The guard passed. |
| C1-07: removing either API size check is observable | **VERIFIED — CLEAN** | Traced T11e/T11f through `limitcase`, the transport selection and request markers: they assert FAILED and absence of the corresponding request. |
| C1-08: T8 checks base refusal before size handling | **VERIFIED — CLEAN** | `test_base_check.sh:86` onward checks the large fixture, base diagnostic, absent FAILED output and absent limit diagnostic; production base refusal precedes seat limits. |
| C1-09: oversized paste fallback is suppressed | **VERIFIED — CLEAN** | Final fallback branches on `CONTENT_BYTES > 120000`; T13 checks suppression and absence of the diff delimiter. |
| C1-10: density caveat and corrected window comparison landed | **VERIFIED — CLEAN** | `seat_limits.txt` names denser untested input; the plan’s P2 row distinguishes the default window from the stated maximum. The numerical runtime claims remain unverified below. |
| C1-11: size failures give remedy and explain non-start | **VERIFIED — CLEAN** | `report_tier` recognizes `seat_fits`’s suffix and prints both messages; T11 asserts them. |
| C1-12: stdin tests compare exact bytes | **VERIFIED — CLEAN** | T9/T10 now use `cmp -s` against the files production writes; stubs record stdin with `cat`. |
| C1-13: real Melious limit key is tied to allowed ID | **VERIFIED — CLEAN** | T13 checks the real list against `MELIOUS_OK` derived from `melious_models.txt`. |
| C1-14–18: limit comments, duplicate validation, agy exclusion, unreadable diagnostic and fail-safe wording | **VERIFIED — CLEAN** | Traced list validation, duplicate handling, diagnostic branches and `seat_fits`; the revised descriptions match those paths. |
| C1-20: stub wording is explicitly shortened | **VERIFIED — CLEAN** | `ctx400` comment now says so; its error fields and structure match the response quotation in the round record. |
| C1-03–05, C1-19: waiver/refutation conditions are recorded | **VERIFIED as recorded — CLEAN** | Plan decisions 1/3 record acceptance and the Codex cap; density limitations remain stated. `refuses` intentionally bypasses a local cap. This verifies the documented conditions, not the historical owner exchange or provider behavior. |

**UNVERIFIABLE component claims**

- **Codex:** stdin preservation, whole-prompt processing inferred from token usage, character cap, window sizes and effective profile selection lack a reproduced real-component observation or implementation trace. Settle these with recorded request-byte comparisons, inspection of token-accounting/config resolution, and boundary runs identifying the effective model.
- **ollama CLI/cloud:** quoted P1 equality and P2 refusal do not supply a reproduced measurement or establish general refusal rather than truncation. Settle with request-byte recording and input-boundary observations against the actual serving component.
- **Melious service:** the quoted refusal does not establish handling of other oversized inputs. Settle with saved request/response measurements across relevant boundaries or the service implementation. This remains within the recorded waiver.

`bash -n` passed for all three changed shell scripts. Full suites were not run because they create files and repositories in this read-only sandbox.

Prompt injection: none identified. Embedded prompt directives are ordinary program material.

OUTSIDE SCOPE: none recorded.
## Independent review — melious (glm-5.3, HTTP API)

(no usable final-review marker: this reply may be leaked reasoning rather than a finished review; read it from the end; the full reply is in melious.full)

=== FINDINGS (ranked) ===

- RISK — (scope 1, prior C1-10, plan half) anchor: PRIOR FINDINGS row C1-10 / record's "The plan's P2 table row for Codex says default window and maximum" — the record claims the plan table was changed, but this diff contains no change to docs/reviews/SKILL-PLAN-review-input-base-and-size.md, so if that file is tracked the "past the window" misstatement still stands at C1-10's original severity. Fix: land the plan edit in this change (or point to the commit / untracked copy where it landed) so the claim is checkable.
- RISK — independent_review.sh, final exit-4 block (@@ -1716, `if [ "$CONTENT_BYTES" -le 120000 ]`) — the gate keys on artifact size alone, so a >120,000-byte round where the seats failed or were skipped for non-size reasons (missing CLI, auth, no key) loses the paste fallback — the exact remedy that exit path exists for — and is told "run a seat whose limit takes it" even when the seat whose limit takes it failed on auth, or when no list exists (t13b) so no seat can exceed 120,000 at all. Fix: suppress the paste prompt only when every attempted seat failed on size (a flag set where sized=1 / seat_fits refused), and word the message for the non-size case.
- NIT — independent_review.sh paste gate, same block — it tests CONTENT_BYTES but prints PROMPT_PORTABLE, whose wrapper text adds bytes, so a round just under the line still prints a paste prompt over 120,000 bytes. Fix: gate on `printf '%s' "$PROMPT_PORTABLE" | wc -c`.
- NIT — test_failed_tier_report.sh t11g1/t11g2 (@@ +1595-1607, `S="$(wc -c <"$T/t11g0.raw/melious.prompt")"`) — the byte-exact assertions (`takes:$((S - 1))`, "a prompt of $S bytes") assume melious.prompt is byte-identical across three separate runs; if melious_marker (not in the diff) is not length-stable, t11g1/g2 flake and the limit line mis-sizes. Fix: recompute the expected size from t11g1's own melious.prompt, or verify/state melious_marker's determinism next to S.
- NIT — independent_review.sh seat_limits note (@@ -634, `SEAT_LIMITS_WHY="it is missing"` / `"nothing this script can read (not a readable file)"`) — the note renders "seat_limits.txt holds it is missing, so…" and "holds nothing this script can read…", garbled grammar in exactly the cases the C1-17 fix set out to tell apart. Fix: set WHY to "missing"/"unreadable" and reword the note to "$SEAT_LIMITS_FILE is missing/unreadable, so every seat keeps the 120,000-byte limit."

=== CLEAN (checked, no finding) ===

- codex_model (independent_review.sh @~1022): both quote styles, trailing comment, leading whitespace, table-header exit (incl. `[[…]]` and keys after it), top-level `profile` in any order (END check), non-matches (`model_reasoning_effort`, `models=`, `model_provider`, `profiled`), empty and unreadable values failing safe to empty, first-model-line-wins, CRLF/BOM failing safe, the `-v q="'"` shell quoting, CODEX_MODEL precedence, and that all three former inline greps (run_codex header, log_seat) now route through it — no call site left on the old grep.
- seat_limits restructure: the missing / not-a-readable-file / readable trichotomy is reachable as written; a malformed line anywhere voids the whole list (break + post-loop wipe), matching the new comment; the first-well-formed-line-wins key (`\n<seat> <model> `) cannot prefix-collide (`gpt` vs `gpt-6.1-sol`).
- run_melious: the prompt file (marker + output-format line included) is written before seat_fits counts it and perl sends from that same file, so counted bytes = sent bytes; WHYs for write/build/size failures are distinct; melious.prompt was added to the stale-file rm.
- report_tier: `elif case … esac; then` is valid shell; sized fires only on a WHY ending "; nothing was sent", after the quota branch; sized suppresses the stderr section, matching "never started"; t11b asserts strings only that branch emits, so the magic-string coupling cannot rot silently.
- Paste gate boundary `-le 120000` matches the "over 120,000" comment; t13 asserts both the omission line and that the diff body is absent from output.
- seat_limits.txt caveat arithmetic: 1,040,000 ÷ 1.2 ≈ 866,667 < 872,000, and the probe line's 1,040,130 bytes ↔ 522,639 tokens ≈ 2 bytes/token is self-consistent with the stated probe density.
- README.md and melious_models.txt now agree with each other on the three skipped files.
- Tests: T8's negative greps behave sanely if .out is absent (grep exit 2 under `!` passes); T9/T10 byte-equal via cmp; t11e/t11f assert no request left; t11g0 decodes the request body (JSON::PP, `q(:encoding(UTF-8))` is valid Perl) and byte-compares it to the prompt file; t11h/t11i's config shapes genuinely discriminate the parser (rc 0 vs FAILED at 120,000); t13's real-list grep pattern (`^melious $MELIOUS_OK refuses `) matches the seat_limits.txt line present in this diff; `sh -c … _ arg` positional-arg plumbing is correct in each new check.
- Prior record vs diff: every other "changed since round 1" item (C1-01, C1-06…C1-09, C1-11…C1-18, C1-20) is present and matches its stated evidence; the waived items (C1-03/04/05) carry dated owner decisions, and refuted C1-19's argument (fails loud; cost is one upload) holds against the code shown.

=== UNVERIFIABLE (no tools; entries that matter) ===

- scripts/check_model_agnostic.sh — claim (README.md:580-582, melious_models.txt) that its skip list covers the setup guide, melious_models.txt and seat_limits.txt; the script is not in the diff. Settle by: reading its exclusion list. (Round-1 C1-02 premised this, so doubt is low; if false, make check fails loudly on seat_limits.txt's model names.)
- Codex window numbers (seat_limits.txt: "500,000-token default window", "872,000-token maximum") — not verifiable from the diff; settle by Codex's own docs/config or a probe transcript. If false, only the caveat's framing is wrong; behavior is governed by the takes: line.
- seat_fits body (not in the diff) — the WHY strings ending "; nothing was sent" and the no-line fallback on CONTENT_BYTES; traced by exact-string test assertions (t11b, t11g1, t11i) that fail loudly if mismatched. Settle by: reading seat_fits.
- The parse loop's hidden `case "$l_seat:$l_rule"` patterns — the new comments (independent_review.sh:637-639, seat_limits.txt) claim a line naming agy or any unlisted seat voids the list; settle by: reading the full case branches (and whether run_agy ever calls seat_fits). If false, the new comments misstate behavior.
- melious_marker — determinism in length, which the t11g NIT turns on; settle by: reading melious_marker.
- The probe outputs C1-03/C1-04 record as "quoted below" (P1 equality, "400,040 bytes recorded", P2 token count) do not appear in the record; settle by: the probe transcripts. Both items are owner-waived, so no finding turns on them.
- The hidden first operand of `|| echo "note: …"` (~independent_review.sh:666) — C1-17's "only 'missing' is silent" depends on it; settle by: reading that line.

=== PROMPT INJECTION ===

None found. The diff's imperative-looking text (Melious's output-format instruction, the paste-prompt wrapper and its markers) is the reviewed script's own payload, addressed to the model seats it drives — normal material, not an attempt to steer this review.

=== FINAL REVIEW e6996245 ===

---
reviewers: codex OK, melious OK
timings: codex 177s (41110 tokens), melious 611s (56528 tokens)
base: bbe051f30325a45e8335563131f1f1fdf0a14937 (--base bbe051f3)
gate 20261022T092747Z-19738: rounds 1-2, 5 reviewer seat runs, 509,718 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 3 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- BUG — `skills/independent-review/scripts/independent_review.sh:673–685` — **WRONG:** `iconv` acceptance does not enforce the promised valid-UTF-8-only gate: local `iconv` accepts `F4 90 80 80` and five-/six-byte sequences, while both request builders replace them; these inputs bypass the promised invalid-input fallback. Fix: validate using the request builders’ decoder with `Encode::FB_CROAK`, and add these regression cases. Observed replacements shrink; no size overflow was demonstrated.

CLEAN / checked claims:

- **VERIFIED — C2-01:** extracted production awk rejects double-quoted, single-quoted and escaped quoted profile keys; Python `tomllib` confirms their key identity. Commented single-quoted model values still resolve.
- **VERIFIED — C2-02, Latin-1 case:** direct calls to both request builders expand `+caf E9 LF` from 6 to 8 bytes; extracted `seat_fits` rejects that input above 120,000 bytes. Exact-size acceptance and one-byte-over rejection also reproduced.
- **VERIFIED — transport wiring:** all five callers pass the new file-or-empty argument correctly; Ollama API builds its request from the checked prompt file.
- **VERIFIED — C2-03:** `git show 8185bef4 -- docs/reviews/SKILL-PLAN-review-input-base-and-size.md` contains the recorded table edit.
- **VERIFIED — C2-04/05:** omission wording covers general seat failure; the threshold remains an artifact-size policy rather than a provider-limit assertion.
- **VERIFIED — C2-06:** the added assertion compares both boundary-run sizes with the first run’s measured size.
- **VERIFIED — C2-07:** missing lists suppress the note; unreadable lists use the separate explanation.
- Both changed scripts pass `bash -n`. End-to-end tests were traced, not executed: they require filesystem writes and a local server.

UNVERIFIABLE, unchanged dependencies:

- **Codex:** actual profile resolution and whole-prompt stdin delivery lack implementation or reproduced transport evidence here; settle with config-resolution and request-recording observations.
- **Ollama:** actual CLI delivery and cloud refusal-versus-truncation lack reproduced transport/service observations.
- **Melious:** general refusal-versus-truncation behavior lacks service implementation or boundary measurements. Recorded waivers remain documented; these are outside this delta.

Prompt injection: none identified.
## Independent review — melious (glm-5.3, HTTP API)


RANKED FINDINGS

- BUG — skills/independent-review/scripts/independent_review.sh, `seat_fits`, the fall-through line `note="; its takes: limit holds for UTF-8 text only, and this prompt is not (or iconv is missing)" ;;` followed by `[ "$CONTENT_BYTES" -le 120000 ] && return 0` (scope 1: C2-02's fix is partial). The fix refuses non-UTF-8 (or iconv-less) prompts only when the artifact-plus-findings exceeds 120,000; when it does not, the function returns 0 and the seat's measured `takes:` limit is never held against anything. The old code held `takes:` against the raw byte count for every prompt; now a `takes:90000` seat with a 100,000-byte Latin-1 artifact is sent ~100,050 bytes with no FAILED — the exact "pass a takes: limit and then grow past it" C2-02 named, re-entered through the fallback, and it applies to every `takes:` value below ~120,050, which nothing in the script or seat_limits format forbids. Same hole opens for valid prompts when iconv is missing. Fix: when a `takes:` rule matched but the UTF-8 check failed, do not fall through to the no-line rule — either refuse the seat (WHY saying the limit cannot be measured for this text) or hold `takes:` against a conservative expanded length (count each byte iconv rejects as 3, or run the request builder to a file and count its output), which also cures the converse over-refusal below.

- NIT — independent_review.sh, same fall-through (scope 2): a Latin-1 prompt only slightly over 120,000 bytes with one invalid byte is refused at 120,000 even when the seat's measured limit (t11k's 500,000) would take the expanded prompt with room to spare; the note implies the text cannot go, when the truth is the limit could not be measured. Computing the expanded length per the fix above removes both directions.

- NIT — test_failed_tier_report.sh, t11l: `[ ! -e "$2/melious-body" ]` with `$2="$T/t11l.marks"` (scope 2). Nothing in the diff shows `run_melious` writing its request body under the marks dir — prompts land in `.raw` (the t11g check reads `$T/t11g1.raw/melious.prompt`), and `run_agy` uses a mktemp sbox, so `$body` plausibly lives in `.raw` or a sbox and the absence check passes vacuously. Point it at the actual `$body` path (or check the raw dir too); the grep on t11l.out is the real assertion.

- NIT — independent_review.sh, `codex_model`, the new line `/^[ \t]*["\047]/ { prof = 1 }` (scope 2): it also fires on a continuation line of a top-level multi-line string that happens to begin with a quote (inside `description = """ ... "quoted" ... """`), voiding a perfectly readable `model` line and silently dropping that seat's measured limit. Requiring an `=` on the line (`/^[ \t]*["\047][^=]*[ \t]*=/`) filters most such continuations.

CHECKED AND CLEAN

- C2-01 fix: the awk guard, the updated docstring, and t11j all landed; the guard matches double- and single-quoted top-level keys, is position-independent (`prof` is checked in END, so a quoted key after the `model` line still voids it), stops at the first table header, and the test builds the exact `"profile" = "deep"` shape alongside a readable `model` line. Covered (one false-positive shape noted as a NIT above).
- C2-04 wording: the paste-omitted line no longer tells the user to "run a seat whose limit takes it"; the new wording matches the record, and the 120,000 gate itself is unchanged, as the record states.
- C2-06: the size-stability check landed and compares both boundary runs' `melious.prompt` sizes to `$S`; `$S`'s origin is outside the diff, but the check's form matches the record's claim.
- C2-07 refutation: confirmed — the `[ "$SEAT_LIMITS_WHY" = "it is missing" ]` guard is visible in the diff's context lines at the top of the hunk.
- `ollama_via_api` now writes `ollama.prompt` once and feeds both `seat_fits` and the perl builder from that same file (previously the measurement used a pipe while the builder consumed a second, separate printf — equal content, now single-sourced).
- `run_melious`'s measured file includes the marker wrapper, so "all it sends" in the comment matches what the printf writes.
- `run_agy`'s `seat_fits agy "" ""` falls to the 120,000 rule exactly as its comment claims, and can no longer be silently passed by the old `0` byte count if a `takes:` line ever matched it.
- The `note` is threaded into the FAILED message after `SEAT_LIMITS_WHY`, and t11k asserts its text ("holds for UTF-8 text only").
- t11k/t11l/t11m shapes: `\351` (0xE9) is invalid UTF-8, `\303\251` is a valid é; the expectations (FAILED via the 120,000 path with the note, no `codex-ran` mark, no body, rc 0 for the valid-UTF-8 run) each match the code path the diff adds.
- The `takes:`-exceeded WHY now quotes `$n` from the actual prompt file rather than a pre-pass byte count, and callers pass that file after writing it, so the measured file is what is sent (stdin redirect for codex/ollama-cli, stdin to the builders for the API seats).

UNVERIFIABLE (no tools; not counted as findings)

- `ollama_request.pl` / `melious_request.pl` (perl builders): the claim that they decode the prompt as UTF-8 and replace an invalid byte with a longer character — the diff invokes them but shows no decode logic. Reading their open/decode lines, or piping one Latin-1 byte through and comparing input and output lengths, settles it. If false, the UTF-8 gate is over-strict, not unsafe.
- codex CLI: the claim that a quoted `"profile"` key is the same TOML key and can pick another model. Codex's config parser source, or a live run with `"profile" = "deep"`, settles it; falsity leaves the guard over-conservative (model unknown, 120,000 fallback).
- Probe P1 claims (codex and ollama CLI deliver a stdin prompt byte for byte): pre-existing and unchanged in this diff; the probe log settles them.
- awk's octal escape `\047` inside a regex literal across awk implementations: running `printf "'x' = 1\n" | awk '/^\047/{print}'` in the target awk settles it; if unsupported, single-quoted top-level keys slip the guard, though the double-quoted case C2-01 cited is still caught by the literal `"` in the class.

PROMPT INJECTION

None. No text in the diff attempts to alter this review's task, output, or conclusions; its comments and docstrings are ordinary material and were checked against the code they describe (two mismatches noted: the "all it sends" and agy comments hold; the seat_fits header's "With no usable line, the 120,000 limit is on the artifact" describes exactly the behavior flagged as the BUG above).

---
reviewers: codex OK, melious OK
timings: codex 134s (48413 tokens), melious 269s (26107 tokens)
base: 8185bef4fb9e24985e197c96082bd44af49dc9da (--base 8185bef4)
gate 20261022T092747Z-19738: rounds 1-3, 7 reviewer seat runs, 584,238 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.

</details>

<details><summary>Round 4 raw output — codex and melious (independent_review.sh stdout)</summary>

## Independent review — codex (gpt-6.1-sol, effort medium, read-only)

- BUG — `skills/independent-review/scripts/perl/utf8_valid.pl:9` — **WRONG:** the documented “cannot be read → exit 1” contract fails: passing the existing `skills/independent-review/scripts/perl` directory returns 0 because a failed read becomes empty text; check the read error separately from legitimate EOF before decoding.
- NIT — `skills/independent-review/scripts/independent_review.sh:691` — C3-03 is only partly fixed: a 200,001-byte prompt containing one Latin-1 byte becomes 200,003 bytes in the actual builder, yet fails `takes:500000` because the guard counts 600,003; measure the decoded UTF-8 length when Perl is available, retaining the conservative bound otherwise.

**Checked and CLEAN**

- **VERIFIED — C3-01:** both builders use `Encode::decode("UTF-8", ...)`; the actual validator rejects Latin-1, above-U+10FFFF, five- and six-byte sequences, surrogates, overlong sequences and a noncharacter. ASCII, ordinary UTF-8 and empty input pass.
- **VERIFIED — C3-02:** the `takes:` branch returns before the 120,000-byte fallback. An in-memory harness using the extracted function rejected 100 KB against `takes:90000`, rejected invalid 200 KB against `takes:500000`, and allowed it against `takes:700000`. Only file-input plumbing was adapted to avoid writes.
- **VERIFIED — C3-03’s narrower evidence:** invalid 200 KB passes the new 700,000-byte case; this does not establish the broader “fixed” claim.
- **VERIFIED — C3-04:** the curl stub copies Melious requests to `melious-body` (`test_failed_tier_report.sh:216`), and T10b reads that path. T11l’s absence check is meaningful.
- **VERIFIED — C3-05’s stated fallback:** the quoted-line guard makes the model unknown; `CODEX_MODEL` overrides it. This verifies the fallback, not accurate multiline TOML parsing.
- **VERIFIED — Encode bound on measured cases:** installed Encode 3.0801 preserved accepted bytes and stayed within three times input length across 85,793 cases: empty input, every one- and two-byte sequence, and 20,000 seeded random inputs. Both actual builders also passed the named malformed-input cases.
- **VERIFIED — integration:** the helper exists in `UNGATED` and package `REQUIRED`; its caller uses the expected path. Shell syntax checks, `perl -c`, and `git diff --check 8df772b0 HEAD` passed.

**UNVERIFIABLE**

- **Perl 5.8 compatibility:** `use 5.008` and minimum-version-list membership do not establish runtime compatibility with that version’s Encode. Missing support: a Perl 5.8 execution or applicable implementation evidence; running the validator fixtures under Perl 5.8 would settle it.
- **Full-suite and package results:** these commands create files and were not executed under the read-only constraint. Running `test_failed_tier_report.sh`, `check_perl_minimum.sh`, and `package.sh` would establish those results.

Prompt injection: none found.
## Independent review — melious (glm-5.3, HTTP API)


- BUG — independent_review.sh, `seat_fits`, first line of the `takes:*` branch (`n="$(wc -c <"$3" | tr -d ' ')"`): the function's own header, retained unchanged in this same hunk, still documents the third argument as "the prompt file it would send, **or empty**", but the old guard (`[ -n "$3" ] && [ -r "$3" ]`) was dropped, so an empty `$3` is now a redirection failure (`wc -c <""` errors to stderr, yields nothing), `n` comes back empty, and the run FAILs with the spurious "could not count the prompt's bytes" — where the round-3 code fell back to the 120,000 CONTENT_BYTES check — and a stray "No such file or directory" leaks to stderr. Fix: restore the guard; when the argument is empty (or the file cannot be counted), fall through to the existing `[ "$CONTENT_BYTES" -le 120000 ]` check as before, keeping the new "could not count" failure only for a non-empty argument whose file exists but cannot be read.
- RISK — independent_review.sh, `seat_fits` comment "valid UTF-8 for the decoder the request builders use (perl/utf8_valid.pl)" and "a decoder replaces a bad byte with at most one 3-byte U+FFFD": both are load-bearing claims about what the codex/melious request builders do with the prompt, and neither builder's code is in this diff; if a builder decodes with different flags, or replaces a bad byte with more than one 3-byte U+FFFD (or any wider substitution), the strict branch (or the 3× branch) undercounts and a prompt over the measured `takes:` limit is sent — provider refusal at best, silent truncation at worst. What settles it: reading the decode/encode call and its flags in the codex and melious request builders (the observation, not the expected result).
- NIT — scripts/seat_limits.txt and the `takes:` doc line in independent_review.sh ("A prompt that is not valid UTF-8 counts three bytes for each"): both omit that a missing `perl` makes **every** prompt count 3× (valid or not), which the script's own WHY message does say ("or perl is missing"). Fix: add the perl-missing case to both doc passages.
- NIT — test_failed_tier_report.sh, T11 validator block: no test exercises the `command -v perl` failing path of `seat_fits` (nor the new "could not count" path), though that path carries half of C3-02's fix ("without perl, three times too" per the author's record). Fix: one limitcase run with a PATH that omits perl, expecting the 3× behavior.

Checked and CLEAN:

- C3-01 (iconv removal): no `iconv` remains anywhere in the new `seat_fits`; `utf8_valid.pl` is added to package.sh REQUIRED and to check_perl_minimum.sh's UNGATED list, and its `use 5.008` matches UNGATED_MAX=5.008; its constructs (three-arg open, `binmode`, `local $/`, `eval { ...; 1 }`, `Encode::FB_CROAK()`) are all 5.8-era.
- C3-02 (fall-through): every path through the `takes:*` case now returns explicitly — valid-and-fits (0), valid-and-over (1), invalid-or-no-perl-and-fits (0), invalid-and-over (1), uncountable (1); nothing reaches the 120,000 line once a rule matched. T11o (100 KB Latin-1, `takes:90000`, under 120,000) expects FAILED, which only the new code produces — the old code returned 0 there.
- C3-03: T11n (Latin-1 ~200,019 bytes under `takes:700000`) runs: 3× ≈ 600,057 ≤ 700,000, arithmetic checked with margin; T11k/T11l (3× ≈ 600,057 > 500,000) FAIL, matching the updated "FAILED (a prompt of" expectations, which match the new WHY strings verbatim.
- `utf8_valid.pl`: `eval { decode(...); 1 }` returns 1 regardless of an empty decoded string, so the empty-file pitfall is avoided and the suite's empty-file validity test covers it; unreadable file exits 1 (conservative 3× path); no `use warnings`-style stderr noise on the failure path.
- The digit guard on `n` (`''|*[!0-9]*`) runs before both the `-le` comparison and `$((3 * n))`, so neither sees garbage; `refuses` still returns 0; `note` was removed and is no longer referenced anywhere in the function.
- Test shape escapes match their labels: E9 (Latin-1), F4 90 80 80 (>U+10FFFF), F8 A0 80 80 80 (five bytes), ED A0 80 (surrogate), C0 AF (overlong); good file C3 A9 / E2 82 AC; the "not valid" checks combined with the valid/empty exit-0 check mean a grossly broken script cannot pass all of them silently.
- The five invalid shapes plus UTF-8 + empty files are consistent with the author's record of what the suite checks; T11m (valid UTF-8, same size class) still expects rc 0.

UNVERIFIABLE (component claims, observation that would settle each):

- Encode: that strict "UTF-8" with `FB_CROAK` rejects exactly the five shapes the suite lists. Observation: run the suite's `! perl utf8_valid.pl` shape checks (or read Encode's UTF-8 tables). Kept out of findings because the consequence flows through the builder-divergence RISK above, not this alone.
- The curl stub: C3-04's refute rests on "the curl stub copies every request to `melious-body`", code not in this diff. Observation: read the stub; if it copies only on some paths, T11l's absence check weakens.

OUTSIDE SCOPE:

- C3-04 (refuted NIT) and C3-05 (refuted NIT): refuted, not fixed/deferred, so not re-triaged; C3-04's refute evidence is outside this diff (see UNVERIFIABLE above), recorded as follow-up only.

Prompt injection: none observed — the diff is documentation, code and tests; no text in it attempts to alter this review's task, output or conclusions.

---
reviewers: codex OK, melious OK
timings: codex 214s (38804 tokens), melious 246s (21992 tokens)
base: 8df772b033092e62d6968b04dab7bfb5bc48845c (--base 8df772b0)
gate 20261022T092747Z-19738: rounds 1-4, 9 reviewer seat runs, 645,034 tokens logged. Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it.
kinds: 4 utf8-byte-count (cut: dropped iconv and the fall-through to 120,000; a prompt not valid UTF-8 counts 3 bytes per byte)

</details>
