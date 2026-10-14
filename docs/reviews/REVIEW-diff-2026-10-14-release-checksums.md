# DIFF review — release checksums: a SHA256SUMS file beside the zip

Base `f4eb2ab` (origin/main when the branch was made; main merged in at `c5e8e44`) · depth: Normal (a release script and its test; not High: it changes no install or deploy path, and the zip itself is built as before) · verdict: open

Owner's decision behind the change (2026-10-14, in chat): "yes to: Release checksums: the smallest honest step is a SHA-256 file with each release, plus marking releases immutable on GitHub", then "start the checksums PR". Marking releases immutable is a repository setting, not part of this diff.

Data check: the diff holds no key, token or password. Destinations: Codex and GLM 5.3 on melious, the standing pair for this repo.

## Test records

`bash scripts/test_package_leak.sh` on `5b88044`: "all checks passed", exit 0, including "clean listing: SHA256SUMS names the zip and matches it" and "a failed build leaves no SHA256SUMS, not even an earlier one".

Mutations, each on a copy restored afterwards: without the line that removes a stale `SHA256SUMS`, "FAIL a failed build leaves no SHA256SUMS, not even an earlier one" (1 check failed); with the checksum taken of another file and relabelled `croftweaver.zip`, "FAIL clean listing: SHA256SUMS names the zip and matches it" (1 check failed).

Tools on this Mac (macOS 26.7.1): `/sbin/sha256sum` and `/usr/bin/shasum`; `sha256sum -c --status` and `shasum -a 256 -c -s` both exit 0 on a matching file, and `sha256sum -c --status` exits 1 after the file changes.

`make smoke` on `6055775`: exit 0; one step skipped as on main (SKIP: perl/*.pl, `Perl::MinimumVersion` not installed; CI runs it); "zip integrity OK"; "wrote …/dist/SHA256SUMS: 3248aa86b7318ee0…"; the file reads `3248aa86b7318ee031ac971958e648e01a9881f9f4dd2ad575ebbab9c87814f3  croftweaver.zip`; `(cd dist && shasum -a 256 -c SHA256SUMS)` printed `croftweaver.zip: OK`.

| Round | Head | Artifact | Reviewers | BUG/RISK/NIT |
|---|---|---|---|---|
