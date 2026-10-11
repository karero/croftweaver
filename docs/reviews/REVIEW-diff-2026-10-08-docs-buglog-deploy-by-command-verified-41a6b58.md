# DIFF review — docs/buglog-deploy-by-command-verified — closing the deploy-by-command row with a live run

Base `origin/main` (`6f4a7e1`) · depth: **Light** (one tracker row) with a cross-model seat · verdict: **CLEAN**, no findings. Authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session, at the owner's "go, run the deploy test on a throwaway project"); GATED

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `41a6b58` | `origin/main...41a6b58`, with the host's evidence of the live run | Codex (medium), `--seat codex` | codex 56 s/23,407 | 0 / 0 / 0 |

## Evidence (the live run, 2026-10-08)

Run 2026-10-08 from a scratch copy of origin/main's starter (PROD_BRANCH = production), git repo on main with a local bare origin, wrangler 4.149.0 logged in by OAuth, project created with `npx wrangler pages project create wb-deploy-test-1008 --production-branch production`.
- The PUBLISHING.md block (git switch main && git pull && CF_PAGES_BRANCH=production npm run build && npx wrangler pages deploy dist --project-name wb-deploy-test-1008 --branch production) exited 0. `wrangler pages deployment list`: Environment Production, Branch production. https://wb-deploy-test-1008.pages.dev/ answered 200 with x-robots-tag noindex (no CANONICAL_URL set) and `<script defer data-domain="example.com" src="https://analytics.example.com/js/script.js">`; /build.txt matched dist/build.txt.
- `CF_PAGES_BRANCH= npm run build && npx wrangler pages deploy dist --project-name wb-deploy-test-1008 --branch preview-test` exited 0; listed as Preview, branch preview-test; https://preview-test.wb-deploy-test-1008.pages.dev/ answered 200, x-robots-tag noindex, 0 data-domain tags (local dist/index.html: 0).
- With HOME set to an empty temp dir and stdin from /dev/null, `npx wrangler pages deploy …` exited 1 before uploading: "In a non-interactive environment, it's necessary to set a CLOUDFLARE_API_TOKEN environment variable …". The real login was untouched (whoami afterwards: logged in).
- Project deleted with `wrangler pages project delete --yes`; project list no longer shows it; the address answers 530.

Waivers: none. Deferrals: none. Follow-ups: none. The row itself names what the run could not show: the `npx` prompt, the message a terminal shows when not logged in, and a failed upload.
