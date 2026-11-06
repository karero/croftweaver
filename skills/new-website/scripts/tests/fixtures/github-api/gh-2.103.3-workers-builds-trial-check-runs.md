# Where gh-2.103.3-workers-builds-trial-check-runs.json comes from

A real answer from GitHub, read on 2026-11-03 with `gh` 2.103.3.

- Repository: `cf-workers-builds-trial` (public; its owner is left out of the kit).
- Commit: `68569edd6ac8d239f50f7cb77051da58873b829d`.
- Command (the `--jq` filter keeps the fields the script reads and cuts the rest; nothing is edited):

```bash
gh api repos/<owner>/cf-workers-builds-trial/commits/68569edd6ac8d239f50f7cb77051da58873b829d/check-runs --jq '{total_count, check_runs: [.check_runs[] | {id,name,status,conclusion,app:{slug:.app.slug,name:.app.name},started_at,completed_at}]}'
```

The commit has three check runs, all finished: two for Pages and `Workers Builds: croftweaver-trial`.
Their `started_at` equals `completed_at`, so this capture does not show whether Workers Builds posts
its run before it deploys; that is for the throwaway run on a real account (test 5).
