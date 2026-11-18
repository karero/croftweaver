You judge fixes made during a code review. For each case below you get: the finding the fix answers, the author's claim (its --cut text) and the diff. The review's rule, quoted:

"Cut, don't patch: where a kind earned an earlier round of the gate too, the fix since then must be a cut, not another patch: take the feature out, or replace it by a strict rule that accepts only the input it names and refuses the rest, with a test that ordinary input still passes. Refusing the one input the last BUG used is a patch."

For each case answer one line: `Case X: CUT` or `Case X: PATCH`, then one sentence why, naming the lines that decide it. Judge the diff, not the claim. Read only what is given; do not run anything.

### Case G

Finding the fix answers: three review rounds each found a new case the comment scanner (which decides whether a site: line in the config is commented out) got wrong.

The author's --cut text: cut the comment scanner; any second site: match means no address is checked

```diff
diff --git a/skills/new-website/templates/astro/scripts/ship.sh b/skills/new-website/templates/astro/scripts/ship.sh
index a3929dde..7083dbe4 100755
--- a/skills/new-website/templates/astro/scripts/ship.sh
+++ b/skills/new-website/templates/astro/scripts/ship.sh
@@ -68,40 +68,15 @@ config_text() { # <folder>
 # follows such redirects, but keep the normalization.
 site_of() { # <astro.config.mjs text>
   local s
-  s="$(site_addrs "$1" | head -1 || true)"
+  s="$(grep -oE "site:[[:space:]]*['\"]https?://[^'\"]+" <<<"$1" 2>/dev/null | sed -E "s/site:[[:space:]]*['\"]//" | head -1 || true)"
   printf '%s\n' "${s%/}"
 }
 
-# The `site:` addresses in the astro.config.mjs text given, one per line, outside comments: an old
-# address kept in a comment is not the address the build uses. Quotes are tracked, across lines too,
-# so a `//` or `/*` inside a string stays; a regular-expression literal is not understood.
-site_addrs() { # <astro.config.mjs text>
-  awk -v sq="'" '
-    { out = ""; n = length($0); i = 1
-      while (i <= n) {
-        c = substr($0, i, 1); d = substr($0, i, 2)
-        if (blk) { if (d == "*/") { blk = 0; i += 2 } else i++; continue }
-        if (q != "") {
-          out = out c
-          if (c == "\\") { out = out substr($0, i + 1, 1); i += 2; continue }
-          if (c == q) q = ""
-          i++; continue
-        }
-        if (d == "//") break
-        if (d == "/*") { blk = 1; i += 2; continue }
-        if (c == "\"" || c == sq || c == "`") q = c
-        out = out c; i++
-      }
-      print out
-    }' <<<"$1" 2>/dev/null |
-    grep -oE "site:[[:space:]]*['\"]https?://[^'\"]+" | sed -E "s/site:[[:space:]]*['\"]//" || true
-}
-
-# none, one or many `site:` addresses outside comments. Many means no one address can be named or
-# checked.
+# none, one or many `site:` addresses in the astro.config.mjs text given, counting every match, so
+# an old address kept in a comment counts. Many means no one address can be named or checked.
 site_count() { # <astro.config.mjs text>
   local h
-  h="$(site_addrs "$1")"
+  h="$(grep -oE "site:[[:space:]]*['\"]https?://[^'\"]+" <<<"$1" 2>/dev/null || true)"
   case "$h" in '') echo none ;; *$'\n'*) echo many ;; *) echo one ;; esac
 }
 
@@ -984,7 +959,7 @@ fi
 # the published copy.
 if [ -z "$site" ]; then
   if [ "$site_n" = many ]; then
-    echo "⚠ astro.config.mjs has more than one site: address, so there is no one address to check — can't verify the deploy."
+    echo "⚠ astro.config.mjs has more than one site: address (an old one in a comment counts), so there is no one address to check — can't verify the deploy."
   else
     echo "⚠ Couldn't read the site URL from astro.config.mjs — can't verify the deploy."
   fi
diff --git a/skills/new-website/templates/astro/tests/check_ship_push.sh b/skills/new-website/templates/astro/tests/check_ship_push.sh
index f248a683..d98d8faa 100755
--- a/skills/new-website/templates/astro/tests/check_ship_push.sh
+++ b/skills/new-website/templates/astro/tests/check_ship_push.sh
@@ -914,38 +914,14 @@ url_case oddurl "$repo_fallback" "https://example.invalid"
 url_case hostonly "$repo_fallback" "https://github.com/site.git"
 url_case scpnoowner "$repo_fallback" "git@github.com:site.git"
 url_case oddchars "$repo_fallback" "git@github.com:owner/s%te.git"
-# An old address kept in a comment beside the live one, on its own line, on the same line, in a
-# comment spanning lines, or with no space before the comment: the first line names the live one.
-# A `//` or `/*` inside the address, in a string with an escaped quote, or in a string spanning
-# lines, stays in it. Two `site:` keys outside comments: the line says
-# many. Each stops at the fetch (noorigin); P6 and P7 check the live check with configs like these.
-new_site="→ Site: https://new.example · GitHub repo: $repo_fallback"
+# An old address kept in a comment beside the live one: more than one match, on two lines and on
+# one. Each stops at the fetch (noorigin); P6 and P7 check that the live check then checks none.
 two_sites="→ Site: (more than one site: address in astro.config.mjs — check which one is live) · GitHub repo: $repo_fallback"
-mark twosite1 noorigin; mark twosite2 noorigin; mark twosite3 noorigin; mark twosite4 noorigin
-mark twosite5 noorigin; mark twosite6 noorigin; mark starsite noorigin; mark semisite noorigin
-mark escsite noorigin; mark tplsite noorigin; mark contsite noorigin
+mark twosite1 noorigin; mark twosite2 noorigin
 printf "// site: 'https://old.example'\nexport default { site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect twosite1 1 0 "not for a network reason"
+want_line1="$two_sites"; expect twosite1 1 0 "not for a network reason"
 printf "/* site: 'https://old.example' */ export default { site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect twosite2 1 0 "not for a network reason"
-printf "/*\n  site: 'https://old.example'\n*/\nexport default { site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect twosite3 1 0 "not for a network reason"
-printf "export default {site: 'https://new.example'};// site: 'https://old.example'\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect twosite4 1 0 "not for a network reason"
-printf "export default { site: 'https://new.example/*archive*/' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="→ Site: https://new.example/*archive* · GitHub repo: $repo_fallback"; expect starsite 1 0 "not for a network reason"
-printf "export default { site: 'https://new.example/a;/*b*/c;//d' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="→ Site: https://new.example/a;/*b*/c;//d · GitHub repo: $repo_fallback"; expect semisite 1 0 "not for a network reason"
-printf "const old = []// site: 'https://old.example'\nexport default { site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect twosite5 1 0 "not for a network reason"
-printf "const old = { site: 'https://old.example' };\nexport default { site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$two_sites"; expect twosite6 1 0 "not for a network reason"
-printf "export default { title: 'a \\\\'// b', site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect escsite 1 0 "not for a network reason"
-printf "const t = \`Title\n/* deco\n\`;\nexport default { site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect tplsite 1 0 "not for a network reason"
-printf "const t = 'a \\\\\n/* b';\nexport default { site: 'https://new.example' };\n" > "$work/cwd/astro.config.mjs"
-want_line1="$new_site"; expect contsite 1 0 "not for a network reason"
+want_line1="$two_sites"; expect twosite2 1 0 "not for a network reason"
 rm -f "$work/cwd/astro.config.mjs"
 
 # --- no line in ship.sh may replace its shell --------------------------------------
@@ -1860,16 +1836,18 @@ GATE
   site_case p5 github https://Ship-Test.PAGES.DEV.
   want "a host in capitals with a final dot is a pages.dev address too" last_starts "✓ Published — verified on the pages.dev address: https://Ship-Test.PAGES.DEV. is serving"
   want "never says LIVE" lacks "✓ LIVE"
-  # P6: an old address kept in a comment; the live check reads the address the build uses, never
-  # the commented one. P7: two `site:` keys outside comments; it checks none, and says so.
+  # P6: an old address kept in a comment; P7: two `site:` keys. Either way the live check checks
+  # neither address, since it cannot tell which one the build uses, and says so.
+  many="⚠ astro.config.mjs has more than one site: address (an old one in a comment counts), so there is no one address to check — can't verify the deploy."
   site_case p6 github https://ship-test.example.invalid "// site: 'https://old.example.invalid'
 export default { site: 'https://ship-test.example.invalid' };"
-  want "the first line names the address the build uses" eq "$(first_line)" "→ Site: https://ship-test.example.invalid · GitHub repo: p6/origin"
-  want "the live check reads that address" last_starts "✓ LIVE — verified: https://ship-test.example.invalid is serving GitHub's main as of the fetch (${m:0:12})"
-  want "... never the commented one" lacks "old.example.invalid is serving"
+  want "the first line says there are several addresses" eq "$(first_line)" "→ Site: (more than one site: address in astro.config.mjs — check which one is live) · GitHub repo: p6/origin"
+  want "says why it checks none" has "$many"
+  want "asks the owner to check it" last_has "Check it yourself in a few minutes: your live URL should show GitHub's main as of the fetch (${m:0:12})."
+  want "checks no address" test ! -e "$M/curl"
   site_case p7 folder https://ship-test.example.invalid "const old = { site: 'https://old.example.invalid' };
 export default { site: 'https://ship-test.example.invalid' };"
-  want "says it has several addresses" has "⚠ astro.config.mjs has more than one site: address, so there is no one address to check — can't verify the deploy."
+  want "says why it checks none" has "$many"
   want "asks the owner to check it" last_has "Check it yourself in a few minutes: your live URL should show the change."
   want "checks no address" test ! -e "$M/curl"
 
```
