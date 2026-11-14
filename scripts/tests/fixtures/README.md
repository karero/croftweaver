# Fixtures for test_antigravity_release_test.py

`agy-1.4.2-excerpt.ndjson` is nine events from a real run, cut down: the maintainer's unattended
run of `docs/ANTIGRAVITY-TEST.md` against release 0.32 on 2026-10-18, with agy CLI 1.4.2 and
`gemini-3.8-flash-high`, started as

```
agy -p= --input-format stream-json --output-format stream-json --model gemini-3.8-flash-high \
  --dangerously-skip-permissions --new-project --print-timeout 45m
```

Kept: the `init` event (its tool list shortened), the three turn results (replies cut to 1,200
characters), the first read of `new-website/SKILL.md`, the first `git commit` refused by a deny
rule, and agy's first and last `npm test` (output cut to its last 400 characters). Changed: the
run's folder is `/W`, and conversation ids are zeros. Nothing else was edited. The full
transcript is kept in the maintainer's private records.

`agy-1.5.9-capacity-503.ndjson` and `agy-1.5.9-capacity-503-stderr.txt` come from a real run too: the
maintainer's unattended full run of the same checklist against release 0.35 on 2026-11-14, with agy
CLI 1.5.9 and `gemini-3.8-flash-high`, started the same way (`--print-timeout 30m`). Google
answered turn 2 with `UNAVAILABLE (code 503): No capacity available for model ...`. Kept: the
`init` event (its tool list shortened to three), both user inputs, the first `read_file` of
`new-website/SKILL.md`, turn 1's result (reply cut to 1,200 characters), turn 2's last `read_file`
and its two error steps, and turn 2's error result; the stderr file whole. Changed: the run's
folder is `/W`, conversation ids and the error id are zeros. Nothing else was edited.
