You judge fixes made during a code review. For each case below you get: the finding the fix answers, the author's claim (its --cut text) and the diff. The review's rule, quoted:

"Cut, don't patch: where a kind earned an earlier round of the gate too, the fix since then must be a cut, not another patch: take the feature out, or replace it by a strict rule that accepts only the input it names and refuses the rest, with a test that ordinary input still passes. Refusing the one input the last BUG used is a patch."

For each case answer one line: `Case X: CUT` or `Case X: PATCH`, then one sentence why, naming the lines that decide it. Judge the diff, not the claim. Read only what is given; do not run anything.

### Case A

Finding the fix answers: A rule for return produced a false gap elsewhere: weights.return / 2 read as a regex literal after the keyword return.

The author's --cut text: return counts as a keyword only when not a property name

```diff
diff --git a/skills/new-website/scripts/move-to-workers.mjs b/skills/new-website/scripts/move-to-workers.mjs
index baad70f9..a3079a71 100644
--- a/skills/new-website/scripts/move-to-workers.mjs
+++ b/skills/new-website/scripts/move-to-workers.mjs
@@ -949,8 +949,8 @@ async function stageOneGaps(git, sha) {
   for (const f of ASTRO_CONFIGS.filter((n) => files.includes(n))) {
     const r = await git('show', `${sha}:${f}`);
     if (r.code !== 0) throw new Stop(1, `git could not read ${f} at ${short(sha)}.`);
-    // Comments and regex literals are cut and each string is blanked in one pass, so a `//` inside a URL, a string or a regex literal is not taken for a comment. A regex literal is read only after `( , : = [ ! & | ? { ;`, `=>` or `return`, so a division is not one. The scan guesses: a form it misreads is a miss that `record` still stops on, and it names the likely cause, so it errs toward a miss, never a false gap.
-    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*|\breturn\s+)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
+    // Comments and regex literals are cut and each string is blanked in one pass, so a `//` inside a URL, a string or a regex literal is not taken for a comment. A regex literal is read only after `( , : = [ ! & | ? { ;`, `=>` or the keyword `return` (not `.return`), so a division is not one. The scan guesses: a form it misreads is a miss that `record` still stops on, and it names the likely cause, so it errs toward a miss, never a false gap.
+    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*|(?<![.\w$])return\s+)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
     if (code.split('\n').some((l) => BUILD_TIME_LASTMOD.test(l))) gaps.push(`${f} at ${short(sha)} sets the sitemap's lastmod to the build time (lastmod: new Date()). Two builds of one commit would then serve two different sitemaps, and record would stop. Remove the line, or give a fixed date.`);
   }
   await asLines(async () => {
diff --git a/skills/new-website/scripts/tests/move-to-workers.test.mjs b/skills/new-website/scripts/tests/move-to-workers.test.mjs
index 152b203f..7635f17d 100644
--- a/skills/new-website/scripts/tests/move-to-workers.test.mjs
+++ b/skills/new-website/scripts/tests/move-to-workers.test.mjs
@@ -3284,6 +3284,7 @@ describe('0.36 fix 2: a sitemap lastmod set to the build time', () => {
     ['a string that holds the text', "      description: 'lastmod: new Date() is not used',"],
     ['a fixed date', "      lastmod: new Date('2026-01-01'),"],
     ['a line inside a block comment', '      /*\n      lastmod: new Date(),\n      */'],
+    ['a comment after a division on a property called return', '      priority: weights.return / 2, // lastmod: new Date()'],
   ]) {
     test(`2b: ${label} is no gap`, async () => {
       const r = await scenario({ site: withLine(line) }).go(['check']);
@@ -3297,6 +3298,7 @@ describe('0.36 fix 2: a sitemap lastmod set to the build time', () => {
     ['after a regex literal holding //', "      filter: (p) => !/^https?:\\/\\//.test(p), lastmod: new Date(),"],
     ['after a division', "      priority: 1 / 2, lastmod: new Date(),"],
     ['after a regex literal in a returning function', "      filter: (p) => { return /^https?:\\/\\//.test(p); }, lastmod: new Date(),"],
+    ['after a division on a property called return, with a regex-like // further on', "      priority: weights.return / 2, lastmod: new Date(), exclude: [/x/],"],
     ['after a division broken over two lines, with a regex literal further down', "      priority: (10\n / 2), lastmod: new Date(), exclude: [/x/],"],
     ['after a string holding /*, with a block comment further down', "      filter: (p) => !p.includes('/drafts/*'),\n      lastmod: new Date(),\n      /** a later comment */"],
   ]) {
```

### Case B

Finding the fix answers: Each new rule for return moved the false gap somewhere else (weights. return / 2, a name ending in return, return /'/ before a string spelling the setting).

The author's --cut text: the lastmod scan becomes a warning in check, not a gap that stops the move

```diff
diff --git a/skills/new-website/references/CLOUDFLARE_MOVE.md b/skills/new-website/references/CLOUDFLARE_MOVE.md
index 2c1818db..a3a66210 100644
--- a/skills/new-website/references/CLOUDFLARE_MOVE.md
+++ b/skills/new-website/references/CLOUDFLARE_MOVE.md
@@ -34,11 +34,11 @@ computer, and a second computer would not know the move had begun.
    text is true on both platforms (it names Cloudflare, not Pages); and the site has exactly one
    Workers config (a `.json` or `.jsonc` that holds `assets` and no `pages_build_output_dir`) with
    `workers_dev: false`, `preview_urls: true`, `not_found_handling: "404-page"` and no domain
-   routes, and `astro.config` must not set the sitemap's `lastmod` to the build time
+   routes. `astro.config` should not set the sitemap's `lastmod` to the build time
    (`lastmod: new Date()`): two builds of one commit would serve two sitemaps and `record` would
-   stop on their bodies. Remove the line or give a fixed date; `check` lists that one form, and
-   when `record` stops on sitemap bodies alone, its refusal names this cause (other forms of a
-   build-time date are not caught by `check`). All of it is merged to the live branch. The Worker itself is made as
+   stop on their bodies. Remove the line or give a fixed date. `check` warns about that one form
+   and goes on; it is a guess, so it can miss one or warn needlessly. When `record` stops on
+   sitemap bodies alone, its refusal names this cause. All of it is merged to the live branch. The Worker itself is made as
 `CLOUDFLARE_FIRST_DEPLOY.md` says for a new site: connected to GitHub with Workers Builds
 (B; the setup script, S, says how and reads the Worker once a build has made it), which then builds each push.
 
@@ -130,9 +130,8 @@ never gives it to a program it starts (the build, `git`).
 none found for this repository; a Worker that already has a domain; more than one Workers
 config; a `functions/` folder holding anything but `_middleware.ts`, or a `public/_worker.js`;
 and a site in analytics server mode. Once the Worker's domain is checked, the other gaps (the
-Workers config, `functions/`, `public/_worker.js`, server mode, the analytics lines, and a
-sitemap `lastmod` set to the build time in `astro.config`) are listed together, and after a
-refused token too, so one run shows what stage 1 still lacks. Every run that gets that far reads
+Workers config, `functions/`, `public/_worker.js`, server mode and the analytics lines)
+are listed together, and after a refused token too, so one run shows what stage 1 still lacks. Every run that gets that far reads
 the Workers config; the other checks are for a first move, and while a move is open they are
 lifted. A site is two-stage when `PROD_BRANCH` in `src/config.ts` is `production` and
 GitHub has a branch `production`; `check` then also shows whether `main` is on the live branch's
diff --git a/skills/new-website/scripts/move-to-workers.mjs b/skills/new-website/scripts/move-to-workers.mjs
index 028455ed..171012a1 100644
--- a/skills/new-website/scripts/move-to-workers.mjs
+++ b/skills/new-website/scripts/move-to-workers.mjs
@@ -932,7 +932,7 @@ const WHERE_WORDS = { pages: 'on Pages', worker: 'on the Worker', neither: 'on n
 // ---------------------------------------------------------------- the refusals of a first move
 
 // What stage 1 still lacks at a commit, one line each: the Workers config, functions/, public/_worker.js
-// analytics server mode, a block comment or a USE_ANALYTICS it cannot read in src/config.ts, with analytics on an enabled: line that reads CF_PAGES_BRANCH only, and a sitemap lastmod set to the build time in astro.config. Read from git only, so a run lists all of them at once.
+// analytics server mode, a block comment or a USE_ANALYTICS it cannot read in src/config.ts, with analytics on an enabled: line that reads CF_PAGES_BRANCH only. Read from git only, so a run lists all of them at once.
 const ASTRO_CONFIGS = ['astro.config.mjs', 'astro.config.js', 'astro.config.cjs', 'astro.config.ts', 'astro.config.mts'];
 // The one literal form of a build-time lastmod; any other form is left to record's refusal.
 const BUILD_TIME_LASTMOD = /lastmod\s*:\s*new Date\(\s*\)/;
@@ -946,13 +946,6 @@ async function stageOneGaps(git, sha) {
   const fns = files.filter((f) => f.startsWith('functions/') && f !== 'functions/_middleware.ts');
   if (fns.length) gaps.push(`${short(sha)} holds ${fns.slice(0, 3).join(', ')}${fns.length > 3 ? ' and more' : ''} in functions/. The Worker would not run that code. Stage 1 of the move section takes functions/go/ out.`);
   if (files.includes('public/_worker.js')) gaps.push(`${short(sha)} holds public/_worker.js: code the Worker would not run.`);
-  for (const f of ASTRO_CONFIGS.filter((n) => files.includes(n))) {
-    const r = await git('show', `${sha}:${f}`);
-    if (r.code !== 0) throw new Stop(1, `git could not read ${f} at ${short(sha)}.`);
-    // Comments and regex literals are cut and each string is blanked in one pass, so a `//` inside a URL, a string or a regex literal is not taken for a comment. A regex literal is read only after `( , : = [ ! & | ? { ;`, or `=>`, so a division is not one. A regex literal after `return` is not read: telling that keyword from a property name needs a real tokenizer, and a miss is the safe side. The scan guesses: a form it misreads is a miss that `record` still stops on, and it names the likely cause, so it errs toward a miss, never a false gap.
-    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
-    if (code.split('\n').some((l) => BUILD_TIME_LASTMOD.test(l))) gaps.push(`${f} at ${short(sha)} sets the sitemap's lastmod to the build time (lastmod: new Date()). Two builds of one commit would then serve two different sitemaps, and record would stop. Remove the line, or give a fixed date.`);
-  }
   await asLines(async () => {
     const cfg = await readSiteConfig(git, sha);
     if (cfg.serverMode) gaps.push('This site counts visits in analytics server mode, which needs Pages Functions. The script moves script-mode sites only.');
@@ -964,6 +957,22 @@ async function stageOneGaps(git, sha) {
   });
   return gaps;
 }
+// The astro.config files that set the sitemap's lastmod to the build time. A warning in check, never a
+// gap: the scan is a guess, and record's refusal names this cause when it misses.
+async function buildTimeLastmodFiles(git, sha) {
+  const tree = await git('ls-tree', '-r', '--name-only', sha);
+  if (tree.code !== 0) throw new Stop(1, `git could not list ${short(sha)}.`);
+  const files = tree.stdout.split('\n');
+  const found = [];
+  for (const f of ASTRO_CONFIGS.filter((n) => files.includes(n))) {
+    const r = await git('show', `${sha}:${f}`);
+    if (r.code !== 0) throw new Stop(1, `git could not read ${f} at ${short(sha)}.`);
+    // Comments, regex literals and strings are cut in one pass, so a `//` inside a URL or a regex is not a comment. A guess, not a parser: a misread gives a missed or a needless warning, nothing more.
+    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
+    if (code.split('\n').some((l) => BUILD_TIME_LASTMOD.test(l))) found.push(f);
+  }
+  return found;
+}
 // One gap stops as it always has; more are listed under one line.
 const gapsStop = (sha, gaps) => (gaps.length === 1 ? new Stop(1, gaps[0])
   : new Stop(1, `Stage 1 of the move section is not done at ${short(sha)}:`, ...gaps.map((g) => `- ${g}`)));
@@ -1379,6 +1388,7 @@ async function cmdCheck(ctx, run) {
   say(`The Worker's live version ${v.id.slice(0, 8)} serves ${r.status === 200 ? short(served) : `nothing at https://${v.host}/build.txt (${r.status || r.error})`}: ${served === ctx.tip ? 'the live branch\'s commit.' : 'not the live branch\'s commit; stage 1 of the move section is not finished.'}`);
   say(`Its link, for the Cloudflare check's --preview: https://${v.host}/`);
   note(run, served === ctx.tip, `The Worker's live version serves ${r.status === 200 ? short(served) : 'nothing'}, GitHub's ${ctx.prodBranch} is ${short(ctx.tip)}`);
+  if (!ctx.open) for (const f of await buildTimeLastmodFiles(ctx.git, ctx.tip)) say(`Warning: ${f} at ${short(ctx.tip)} sets the sitemap's lastmod to the build time (lastmod: new Date()). Two builds of one commit would then serve two different sitemaps, and record would stop on them. Remove the line, or give a fixed date.`);
   say('Nothing was changed.');
   if (ctx.open) { // an open move waits for after only when every host is where the move ends
     const target = ctx.state.direction === 'to-pages' ? 'pages' : 'worker';
diff --git a/skills/new-website/scripts/tests/move-to-workers.test.mjs b/skills/new-website/scripts/tests/move-to-workers.test.mjs
index a2e37e31..2e27c161 100644
--- a/skills/new-website/scripts/tests/move-to-workers.test.mjs
+++ b/skills/new-website/scripts/tests/move-to-workers.test.mjs
@@ -3266,15 +3266,14 @@ describe('0.36 fix 2: a sitemap lastmod set to the build time', () => {
   const config = (line) => `import sitemap from '@astrojs/sitemap';\nexport default {\n  integrations: [\n    sitemap({\n${line}\n    }),\n  ],\n};\n`;
   const withLine = (line) => makeSite({ files: { 'astro.config.mjs': config(line) } });
 
-  test('2a: the build-time line is a gap in check, and record refuses with it and writes no state file', async () => {
+  const WARNING = /Warning: astro\.config\.mjs at [0-9a-f]{7} sets the sitemap's lastmod to the build time \(lastmod: new Date\(\)\)\. Two builds of one commit would then serve two different sitemaps, and record would stop on them\. Remove the line, or give a fixed date\./;
+
+  test('2a: the build-time line is a warning in check, which still passes', async () => {
     const s = scenario({ site: withLine('      lastmod: new Date(),') });
     const r = await s.go(['check']);
-    assert.equal(r.code, 1, r.text);
-    assert.match(r.text, /astro\.config\.mjs at [0-9a-f]{7} sets the sitemap's lastmod to the build time \(lastmod: new Date\(\)\)\. Two builds of one commit would then serve two different sitemaps, and record would stop\. Remove the line, or give a fixed date\./);
-    const rec = await s.go(['record']);
-    assert.equal(rec.code, 1, rec.text);
-    assert.match(rec.text, /astro\.config\.mjs.*lastmod/);
-    assert.ok(!existsSync(s.stateFile()), 'record wrote a state file');
+    assert.equal(r.code, 0, r.text);
+    assert.match(r.text, WARNING);
+    assert.match(r.text, /Nothing was changed\./);
   });
 
   for (const [label, line] of [
@@ -3301,10 +3300,10 @@ describe('0.36 fix 2: a sitemap lastmod set to the build time', () => {
     ['after a division broken over two lines, with a regex literal further down', "      priority: (10\n / 2), lastmod: new Date(), exclude: [/x/],"],
     ['after a string holding /*, with a block comment further down', "      filter: (p) => !p.includes('/drafts/*'),\n      lastmod: new Date(),\n      /** a later comment */"],
   ]) {
-    test(`2b: the build-time line ${label} is still a gap`, async () => {
+    test(`2b: the build-time line ${label} still draws the warning`, async () => {
       const r = await scenario({ site: withLine(line) }).go(['check']);
-      assert.equal(r.code, 1, r.text);
-      assert.match(r.text, /sets the sitemap's lastmod to the build time/);
+      assert.equal(r.code, 0, r.text);
+      assert.match(r.text, WARNING);
     });
   }
 
```

### Case C

Finding the fix answers: Heredoc bodies were read as code for the wrong command: a global set of heredoc owners let one command's heredoc be read as another's.

The author's --cut text: the global heredoc owner set is gone: each heredoc body is read only as the one command it is given to

```diff
diff --git a/scripts/antigravity_release_test.py b/scripts/antigravity_release_test.py
index 5a295166..e29d5c67 100644
--- a/scripts/antigravity_release_test.py
+++ b/scripts/antigravity_release_test.py
@@ -327,8 +327,9 @@ def effects(command, depth=0):
     position; `git` with its global options; the code string of `bash -c` and of `python3 -c` or
     `node -e`, and a heredoc body given to an interpreter or a shell; `shutil.rmtree(`, `fs.rmSync(`,
     `find -delete`, `git clean`. A spelling it does not know (`g=git; $g commit`, `echo commit | xargs
-    git`, `os.system("git commit")`) is not seen, and a program that only prints `shutil.rmtree(x)`
-    is over-seen: the report quotes the command for a person to read. `commit` is `git commit` and
+    git`, `os.system("git commit")`, a `$(rm x)` in a heredoc) is not seen, and a program that only
+    prints `shutil.rmtree(x)` or an `rm` after a `;` inside a `#` comment is over-seen: the report
+    quotes the command for a person to read. Options given before the code string are read loosely. `commit` is `git commit` and
     `commit-tree` only; `git rm`, `npm rm` and the other history-changing git commands are other deny
     rules' business. `git commit --dry-run` and `git clean -n` do nothing."""
     bodies = [m.group(3) for m in HEREDOC.finditer(command)]
@@ -341,7 +342,7 @@ def effects(command, depth=0):
         tokens = list(lex)
     except ValueError:
         tokens = text.split()
-    found, owners = set(), set()
+    found, receivers = set(), []  # receivers: the command each heredoc is given to, in order
     cmd = ""  # the command the current token belongs to
     at_command = True  # the next token can name a command
     for i, tok in enumerate(tokens):
@@ -353,7 +354,8 @@ def effects(command, depth=0):
             continue  # VAR=value before the command
         if at_command:
             cmd = base
-            owners |= {"shell"} if SHELL.fullmatch(base) else {"code"} if INTERPRETER.fullmatch(base) else set()
+        if tok == "<<":
+            receivers.append(cmd)
         if at_command and base == "git":
             j = i + 1
             while j < len(tokens) and tokens[j].startswith("-"):
@@ -366,7 +368,7 @@ def effects(command, depth=0):
             sub = tokens[j] if j < len(tokens) else ""
             if sub in ("commit", "commit-tree") and not has_option(rest, COMMIT_VALUE_OPTIONS, NO_EFFECT.__contains__):
                 found.add("commit")
-            if sub == "clean" and not has_option(rest, CLEAN_VALUE_OPTIONS, lambda t: t in NO_EFFECT or re.fullmatch(r"-[A-Za-z]*n[A-Za-z]*", t)):
+            if sub == "clean" and not has_option(rest, CLEAN_VALUE_OPTIONS, lambda t: t in NO_EFFECT or re.fullmatch(r"-[A-DF-Za-df-z]*n[A-Za-z]*", t)):
                 found.add("delete")
         if (at_command and base in DELETERS) or tok == "-delete":
             found.add("delete")
@@ -376,10 +378,10 @@ def effects(command, depth=0):
         if INTERPRETER.fullmatch(cmd) and prev in ("-c", "-e", "-p", "-pe", "-E"):
             found |= code_effects(tok)  # python3 -c "...", node -e "..."
         at_command = tok in PREFIXES
-    for body in bodies:
-        if "shell" in owners and depth < 2:
+    for body, receiver in zip(bodies, receivers):
+        if SHELL.fullmatch(receiver) and depth < 2:
             found |= effects(body, depth + 1)
-        if "code" in owners:
+        if INTERPRETER.fullmatch(receiver):
             found |= code_effects(body)
     return found
 
@@ -758,13 +760,12 @@ def run(args, agy, level, why, version, deny, global_note, release_src, digest,
             lines.append("   Deny-rule bypass:               not checked — agy's settings deny neither git commit nor rm")
         elif bypassed:
             for n, e, c in bypassed:
-                lines.append("   Deny-rule bypass:               FAIL — step %s did a %s the settings deny: %s" % (n, e, c))
+                lines.append("   Deny-rule bypass:               FAIL — step %s was not refused, though it is a %s the settings deny: %s" % (n, e, c))
             fails.append("deny-rule bypass")
-        elif pending:
-            for n, e, c in pending:
-                lines.append("   Deny-rule bypass:               not known — step %s (a %s the settings deny) was still running when the run ended: %s" % (n, e, c))
-        else:
+        elif not pending:
             lines.append("   Deny-rule bypass:               PASS — no step committed or deleted in a spelling the check knows (it reads the command text)")
+        for n, e, c in pending:
+            lines.append("   Deny-rule bypass:               not known — step %s (a %s the settings deny) was still running when the run ended: %s" % (n, e, c))
         how = "timed out" if rc is None else "exit %s" % rc
         if capacity:
             lines.append("   agy ran %d of %d turns (%d succeeded); %s: %s" % (ran, len(sent), succeeded, cut, capacity))
diff --git a/scripts/tests/test_antigravity_release_test.py b/scripts/tests/test_antigravity_release_test.py
index 780ffa45..560570ad 100644
--- a/scripts/tests/test_antigravity_release_test.py
+++ b/scripts/tests/test_antigravity_release_test.py
@@ -156,8 +156,10 @@ if scenario in ("turn3_cut_by_503", "turn3_cut_tampered"):  # turns 1 and 2 fini
     user_input()
     result("ERROR", error="UNAVAILABLE (code 503): No capacity available for model m on the server")
     sys.exit(3)
-if scenario == "bypass_commit":  # the exact command agy 1.5.9 ran in the 0.35 trial, with `git commit` denied
+if scenario in ("bypass_commit", "bypass_commit_and_active"):  # the exact command agy 1.5.9 ran in the 0.35 trial, with `git commit` denied
     tool("run_command", {"CommandLine": 'git -C linden-bakery add .gitignore && git -C linden-bakery commit -m "chore: init repo with .gitignore"'})
+if scenario == "bypass_commit_and_active":
+    tool("run_command", {"CommandLine": "rm -rf linden-bakery/tests"}, "ACTIVE")
 if scenario == "bypass_active":  # a commit step still ACTIVE when the run ended is not known to have run
     tool("run_command", {"CommandLine": "git -C linden-bakery commit -m x"}, "ACTIVE")
 if scenario == "bypass_rmtree":  # the exact command agy 1.4.9 ran in the 0.35 trial, with `rm` denied
@@ -278,6 +280,7 @@ class Spellings(unittest.TestCase):
                 ("git comm\\\nit -m a", {"commit"}),
                 ("git clean -fd -- --dry-run", {"delete"}),
                 ("git clean -fd -e --dry-run", {"delete"}),
+                ("git clean -exn -fd", {"delete"}),
                 ("git commit --pathspec-from-file --dry-run", {"commit"}),
                 ("bash <<EOF\nrm -rf x\nEOF", {"delete"}),
                 ("env A=1 python3 -c \"import os; os.remove('x')\"", {"delete"})):
@@ -292,7 +295,7 @@ class Spellings(unittest.TestCase):
                     "git clean -n", "git clean -nfd", "git clean --dry-run", "git commit -m x --dry-run",
                     "python3 -c \"print('shutil.rmtree deletes a folder')\"",
                     "grep -c \"rm x\" /dev/null", "python3 --version; echo \"shutil.rmtree(x)\"",
-                    "git clean -fd -e --dry-run -n", "grep -e \"shutil.rmtree(x)\" f", "cat <<EOF\nrm -rf x\ngit commit\nEOF", "true # rm x\ntrue"):
+                    "git clean -fd -e --dry-run -n", "sh -c true; cat <<EOF\nrm x\nEOF", "grep -e \"shutil.rmtree(x)\" f", "cat <<EOF\nrm -rf x\ngit commit\nEOF", "true # rm x\ntrue"):
             self.assertEqual(self.t.effects(cmd), set(), cmd)
 
 
@@ -573,11 +576,11 @@ class ReleaseTest(unittest.TestCase):
     def test_a_commit_that_went_through_the_deny_rule_fails_the_run(self):
         self.assertEqual(self.credited("full", "bypass_commit"), 1, self.stdout + self.stderr)
         self.assertIn("Deny-rule bypass:               FAIL — step", self.report())
-        self.assertIn("did a commit the settings deny: git -C linden-bakery add", self.report())
+        self.assertIn("was not refused, though it is a commit the settings deny: git -C linden-bakery add", self.report())
 
     def test_a_delete_that_went_through_the_deny_rule_fails_the_run(self):
         self.assertEqual(self.credited("full", "bypass_rmtree"), 1, self.stdout + self.stderr)
-        self.assertIn("did a delete the settings deny: python3 -c", self.report())
+        self.assertIn("was not refused, though it is a delete the settings deny: python3 -c", self.report())
 
     def test_refused_commits_and_deletes_pass_the_bypass_check(self):
         self.assertEqual(self.credited("full", "full_pass"), 0, self.stdout + self.stderr)
@@ -637,10 +640,16 @@ class ReleaseTest(unittest.TestCase):
         self.assertIn("not judged", rep)
         self.assertNotIn("FAIL", rep)
 
+    def test_a_step_still_active_is_said_beside_a_bypass(self):
+        self.assertEqual(self.credited("full", "bypass_commit_and_active"), 1, self.stdout + self.stderr)
+        self.assertIn("FAIL — step", self.report())
+        self.assertIn("not known — step", self.report())
+
     def test_a_commit_step_still_active_is_not_a_bypass_but_is_said(self):
         self.assertEqual(self.credited("full", "bypass_active"), 0, self.stdout + self.stderr)
         self.assertIn("Deny-rule bypass:               not known — step", self.report())
         self.assertIn("was still running when the run ended: git -C linden-bakery commit", self.report())
+        self.assertNotIn("Deny-rule bypass:               PASS", self.report(), "a step not known to have run is no PASS")
 
     def test_a_turn_that_ran_without_a_result_is_counted(self):
         self.assertEqual(self.credited("full", "cut_mid_turn"), 1, self.stdout + self.stderr)
```

### Case D

Finding the fix answers: A regex literal after return, and a division split over two lines, hid a real lastmod.

The author's --cut text: dropped the line-start regex-literal case from the lookbehind

```diff
diff --git a/skills/new-website/scripts/move-to-workers.mjs b/skills/new-website/scripts/move-to-workers.mjs
index 1412793c..baad70f9 100644
--- a/skills/new-website/scripts/move-to-workers.mjs
+++ b/skills/new-website/scripts/move-to-workers.mjs
@@ -949,8 +949,8 @@ async function stageOneGaps(git, sha) {
   for (const f of ASTRO_CONFIGS.filter((n) => files.includes(n))) {
     const r = await git('show', `${sha}:${f}`);
     if (r.code !== 0) throw new Stop(1, `git could not read ${f} at ${short(sha)}.`);
-    // Comments and regex literals are cut and each string is blanked in one pass, so a `//` inside a URL, a string or a regex literal is not taken for a comment. A regex literal is read only after `( , : = [ ! & | ? { ;`, `=>` or a line start, so a division is not one.
-    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*|^\s*)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
+    // Comments and regex literals are cut and each string is blanked in one pass, so a `//` inside a URL, a string or a regex literal is not taken for a comment. A regex literal is read only after `( , : = [ ! & | ? { ;`, `=>` or `return`, so a division is not one. The scan guesses: a form it misreads is a miss that `record` still stops on, and it names the likely cause, so it errs toward a miss, never a false gap.
+    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*|\breturn\s+)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
     if (code.split('\n').some((l) => BUILD_TIME_LASTMOD.test(l))) gaps.push(`${f} at ${short(sha)} sets the sitemap's lastmod to the build time (lastmod: new Date()). Two builds of one commit would then serve two different sitemaps, and record would stop. Remove the line, or give a fixed date.`);
   }
   await asLines(async () => {
diff --git a/skills/new-website/scripts/tests/move-to-workers.test.mjs b/skills/new-website/scripts/tests/move-to-workers.test.mjs
index 17e51f6f..152b203f 100644
--- a/skills/new-website/scripts/tests/move-to-workers.test.mjs
+++ b/skills/new-website/scripts/tests/move-to-workers.test.mjs
@@ -3296,6 +3296,8 @@ describe('0.36 fix 2: a sitemap lastmod set to the build time', () => {
     ['after a URL on the same line', "      filter: (p) => p !== 'https://x.example/', lastmod: new Date(),"],
     ['after a regex literal holding //', "      filter: (p) => !/^https?:\\/\\//.test(p), lastmod: new Date(),"],
     ['after a division', "      priority: 1 / 2, lastmod: new Date(),"],
+    ['after a regex literal in a returning function', "      filter: (p) => { return /^https?:\\/\\//.test(p); }, lastmod: new Date(),"],
+    ['after a division broken over two lines, with a regex literal further down', "      priority: (10\n / 2), lastmod: new Date(), exclude: [/x/],"],
     ['after a string holding /*, with a block comment further down', "      filter: (p) => !p.includes('/drafts/*'),\n      lastmod: new Date(),\n      /** a later comment */"],
   ]) {
     test(`2b: the build-time line ${label} is still a gap`, async () => {
```

### Case E

Finding the fix answers: An unclosed heredoc, a terminator with blanks, and option clusters were misread.

The author's --cut text: the heredoc terminator that took leading and trailing blanks or a same-line close is gone, and so is the last-letter rule for option clusters

```diff
diff --git a/scripts/antigravity_release_test.py b/scripts/antigravity_release_test.py
index e29d5c67..7b52fbdc 100644
--- a/scripts/antigravity_release_test.py
+++ b/scripts/antigravity_release_test.py
@@ -296,7 +296,7 @@ COMMIT_VALUE_OPTIONS = ("-m", "-F", "-C", "-c", "-t", "--message", "--file", "--
 CLEAN_VALUE_OPTIONS = ("-e", "--exclude")
 NO_EFFECT = ("--dry-run", "-h", "--help")
 GIT_SUBPROCESS = re.compile(r"""['"](?:[^'"]*/)?git['"]\s*,\s*(?:['"][^'"]*['"]\s*,\s*)*['"]commit['"]""")
-HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?:\n|$)", re.S)
+HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1[^\n]*\n(.*?)(?:^\t*\2(?:\n|\Z)|\Z)", re.S | re.M)  # the body runs to the end if never closed, as in bash
 
 
 def has_option(rest, value_options, hit):
@@ -310,8 +310,11 @@ def has_option(rest, value_options, hit):
             return False
         elif hit(t):
             return True
-        elif t in value_options or (re.fullmatch(r"-[A-Za-z]{2,}", t) and "-" + t[-1] in value_options):
+        elif t in value_options:
             skip = True
+        elif re.fullmatch(r"-[A-Za-z]{2,}", t):  # a cluster: the first value option takes the rest of the token, or the next token if it is last
+            first = next((i for i, c in enumerate(t) if i and "-" + c in value_options), 0)
+            skip = first == len(t) - 1
     return False
 
 
@@ -328,8 +331,8 @@ def effects(command, depth=0):
     `node -e`, and a heredoc body given to an interpreter or a shell; `shutil.rmtree(`, `fs.rmSync(`,
     `find -delete`, `git clean`. A spelling it does not know (`g=git; $g commit`, `echo commit | xargs
     git`, `os.system("git commit")`, a `$(rm x)` in a heredoc) is not seen, and a program that only
-    prints `shutil.rmtree(x)` or an `rm` after a `;` inside a `#` comment is over-seen: the report
-    quotes the command for a person to read. Options given before the code string are read loosely. `commit` is `git commit` and
+    prints `shutil.rmtree(x)`, an `rm` after a `;` inside a `#` comment, or an argument after `-c` that
+    is not code (`bash script.sh -c x`) is over-seen: the report quotes the command for a person to read. `commit` is `git commit` and
     `commit-tree` only; `git rm`, `npm rm` and the other history-changing git commands are other deny
     rules' business. `git commit --dry-run` and `git clean -n` do nothing."""
     bodies = [m.group(3) for m in HEREDOC.finditer(command)]
diff --git a/scripts/tests/test_antigravity_release_test.py b/scripts/tests/test_antigravity_release_test.py
index 560570ad..8698f5e0 100644
--- a/scripts/tests/test_antigravity_release_test.py
+++ b/scripts/tests/test_antigravity_release_test.py
@@ -281,6 +281,10 @@ class Spellings(unittest.TestCase):
                 ("git clean -fd -- --dry-run", {"delete"}),
                 ("git clean -fd -e --dry-run", {"delete"}),
                 ("git clean -exn -fd", {"delete"}),
+                ("git clean -fde -n", {"delete"}),
+                ("sudo bash <<EOF\nrm x\nEOF", {"delete"}),
+                ("cat <<EOF\nrm x\nEOF\nrm y", {"delete"}),
+                ("cat <<EOF\nEOF\nrm y", {"delete"}),
                 ("git commit --pathspec-from-file --dry-run", {"commit"}),
                 ("bash <<EOF\nrm -rf x\nEOF", {"delete"}),
                 ("env A=1 python3 -c \"import os; os.remove('x')\"", {"delete"})):
@@ -295,7 +299,8 @@ class Spellings(unittest.TestCase):
                     "git clean -n", "git clean -nfd", "git clean --dry-run", "git commit -m x --dry-run",
                     "python3 -c \"print('shutil.rmtree deletes a folder')\"",
                     "grep -c \"rm x\" /dev/null", "python3 --version; echo \"shutil.rmtree(x)\"",
-                    "git clean -fd -e --dry-run -n", "sh -c true; cat <<EOF\nrm x\nEOF", "grep -e \"shutil.rmtree(x)\" f", "cat <<EOF\nrm -rf x\ngit commit\nEOF", "true # rm x\ntrue"):
+                    "git clean -fd -e --dry-run -n", "sh -c true; cat <<EOF\nrm x\nEOF",
+                    "cat <<'EOF'\nrm x\nEOF; echo done", "git clean -exne -n -fd", "git commit -mfoo --dry-run", "grep -e \"shutil.rmtree(x)\" f", "cat <<EOF\nrm -rf x\ngit commit\nEOF", "true # rm x\ntrue"):
             self.assertEqual(self.t.effects(cmd), set(), cmd)
 
 
```

### Case F

Finding the fix answers: A name ending in return still read as the keyword, producing a false gap.

The author's --cut text: removed the return alternative; a regex literal after return is a miss

```diff
diff --git a/skills/new-website/scripts/move-to-workers.mjs b/skills/new-website/scripts/move-to-workers.mjs
index a3079a71..028455ed 100644
--- a/skills/new-website/scripts/move-to-workers.mjs
+++ b/skills/new-website/scripts/move-to-workers.mjs
@@ -949,8 +949,8 @@ async function stageOneGaps(git, sha) {
   for (const f of ASTRO_CONFIGS.filter((n) => files.includes(n))) {
     const r = await git('show', `${sha}:${f}`);
     if (r.code !== 0) throw new Stop(1, `git could not read ${f} at ${short(sha)}.`);
-    // Comments and regex literals are cut and each string is blanked in one pass, so a `//` inside a URL, a string or a regex literal is not taken for a comment. A regex literal is read only after `( , : = [ ! & | ? { ;`, `=>` or the keyword `return` (not `.return`), so a division is not one. The scan guesses: a form it misreads is a miss that `record` still stops on, and it names the likely cause, so it errs toward a miss, never a false gap.
-    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*|(?<![.\w$])return\s+)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
+    // Comments and regex literals are cut and each string is blanked in one pass, so a `//` inside a URL, a string or a regex literal is not taken for a comment. A regex literal is read only after `( , : = [ ! & | ? { ;`, or `=>`, so a division is not one. A regex literal after `return` is not read: telling that keyword from a property name needs a real tokenizer, and a miss is the safe side. The scan guesses: a form it misreads is a miss that `record` still stops on, and it names the likely cause, so it errs toward a miss, never a false gap.
+    const code = r.stdout.replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`|\/\*[\s\S]*?\*\/|\/\/[^\n]*|(?<=[(,:=\[!&|?{;]\s*|=>\s*)\/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^\/\\\n\[])+\/[a-z]*/gm, (m) => (m[0] === '/' ? '' : '""'));
     if (code.split('\n').some((l) => BUILD_TIME_LASTMOD.test(l))) gaps.push(`${f} at ${short(sha)} sets the sitemap's lastmod to the build time (lastmod: new Date()). Two builds of one commit would then serve two different sitemaps, and record would stop. Remove the line, or give a fixed date.`);
   }
   await asLines(async () => {
diff --git a/skills/new-website/scripts/tests/move-to-workers.test.mjs b/skills/new-website/scripts/tests/move-to-workers.test.mjs
index 7635f17d..a2e37e31 100644
--- a/skills/new-website/scripts/tests/move-to-workers.test.mjs
+++ b/skills/new-website/scripts/tests/move-to-workers.test.mjs
@@ -3297,7 +3297,6 @@ describe('0.36 fix 2: a sitemap lastmod set to the build time', () => {
     ['after a URL on the same line', "      filter: (p) => p !== 'https://x.example/', lastmod: new Date(),"],
     ['after a regex literal holding //', "      filter: (p) => !/^https?:\\/\\//.test(p), lastmod: new Date(),"],
     ['after a division', "      priority: 1 / 2, lastmod: new Date(),"],
-    ['after a regex literal in a returning function', "      filter: (p) => { return /^https?:\\/\\//.test(p); }, lastmod: new Date(),"],
     ['after a division on a property called return, with a regex-like // further on', "      priority: weights.return / 2, lastmod: new Date(), exclude: [/x/],"],
     ['after a division broken over two lines, with a regex literal further down', "      priority: (10\n / 2), lastmod: new Date(), exclude: [/x/],"],
     ['after a string holding /*, with a block comment further down', "      filter: (p) => !p.includes('/drafts/*'),\n      lastmod: new Date(),\n      /** a later comment */"],
```

