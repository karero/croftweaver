# Plan: drop the local pre-push hook that runs `make check`

## What
Remove `scripts/pre-push-check.sh` (a local hook some maintainers install). It runs `make check`
before each push.

## Why
It duplicates a server-side guard: on GitHub, karero/croftweaver's ruleset "main checks" is active,
targets the default branch, requires a pull request, and requires the `buglog-rows` and `clean`
status checks to pass before a merge to main. So a push that would fail `make check` cannot reach
main anyway; the local hook only adds a slow step to every push of a work branch.

## How
Delete the script and its README line. No other change.

## Tests
None: a deleted local hook has nothing left to test.
