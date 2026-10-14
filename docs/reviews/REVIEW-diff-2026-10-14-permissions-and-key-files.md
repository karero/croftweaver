# DIFF review — permissions wording, force-push rules, Google key files, the deploy token

Base `3519d2d` (origin/main when the branch was made) · depth: Normal (starter settings, a runtime script and its tests, a skill instruction file; not High: no deploy, guard script or release change) · verdict: open

Owner's decision behind the change (2026-10-14, in chat): "Fix the 5 follow-ups", after the recommendation table for the five mismatches found while writing `docs/WHAT-THE-SKILLS-RUN.md` (#292).

Data check: the diff holds no key, token or password. Destinations: Codex and GLM 5.3 on melious, the standing pair for this repo.

## Test records

`make check` on `c046005`: exit 0, seven "all checks passed" lines, one step skipped as on `main` (SKIP: perl/*.pl, `Perl::MinimumVersion` not installed; CI runs it). First run stopped on a leftover `skills/website-brand-kit` folder that held only ignored `__pycache__` files from the recycled worktree; removed, then green.

`make test` on `c046005`, with `requests` in a scratch virtual environment (the stock python3 here lacks it, which made 13 tests fail to import or run): "Ran 206 tests ... OK", exit 0.

Mutation, `gsc_query.py`: with the old default (`"client_secret.json"`) put back, `test_a_client_file_in_the_current_folder_is_not_used` fails; with the fix, all 7 tests in `test_gsc_no_browser.py` pass.

Live push test, 2026-10-14, Claude Code 2.1.287, `claude -p ... --settings .claude/settings.json --setting-sources project --permission-mode default --model haiku`, in a throwaway repository with a local bare remote; each force push from a branch that had diverged from the remote. BLOCKED = in `permission_denials`; RAN = the remote changed. Without `--settings`, the project file was not applied in headless mode (a plain `git push origin main` was refused), so that first run proves nothing and is not counted.

```
== main's allowlist
git push origin main --force               RAN
git push origin +main                      RAN
git push --force-with-lease origin main    RAN
git push origin main -f                    RAN
git push -f origin main                    BLOCKED
git push --force origin main               BLOCKED
git push origin main --force-with-lease    RAN
git push origin --delete feature           RAN
git push origin main                       RAN
git push --follow-tags origin main         RAN
== branch allowlist
git push origin main --force               BLOCKED
git push origin +main                      BLOCKED
git push --force-with-lease origin main    BLOCKED
git push origin main -f                    BLOCKED
git push -f origin main                    BLOCKED
git push --force origin main               BLOCKED
git push origin main --force-with-lease    BLOCKED
git push origin --delete feature           RAN
git push origin main                       RAN
git push --follow-tags origin main         RAN
```

The test script and its full output are kept in the session's scratchpad; the script is not part of the change.

| Round | Head | Artifact | Reviewers | BUG/RISK/NIT |
|---|---|---|---|---|
