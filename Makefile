.PHONY: install install-codex package check test test-facts test-agy-release test-brand-kit test-wordpress-inventory test-cloudflare-check test-create test-plugin test-codex-plugin smoke whats-new refresh push-denylist

install:   ## symlink every skill into ~/.claude/skills/ (Claude Code)
	@bash scripts/install.sh

install-codex:   ## symlink every skill into ~/.agents/skills/ (OpenAI Codex)
	@bash scripts/install-codex.sh

whats-new: ## skill changes since a project was scaffolded: make whats-new PROJECT=<dir> (no PROJECT = recent suite changes)
	@bash scripts/whats-new.sh $(if $(PROJECT),"$(PROJECT)")

refresh:   ## re-copy a project's stale bundled skills + re-stamp (overwrites local edits): make refresh PROJECT=<dir>
	@bash scripts/whats-new.sh --refresh $(if $(PROJECT),"$(PROJECT)")

package: check   ## build dist/croftweaver.zip for handoff, and its checksum in dist/SHA256SUMS (runs check first)
	@bash scripts/package.sh

check:     ## run every suite guard: no personal data or credentials, every script locating itself CDPATH-safely, no pipe into an early-exit consumer (head, grep -q, …) under pipefail, no concrete model in independent-review, every template file bucketed (and the guard failing on one left out), the starter's Node floor holding (its engines inside Astro's, the lockfile and the docs agreeing, the set of Node lines pinned, and the guard failing on each way that can drift), skill descriptions within budget, no failed reviewer hidden, no diff on the wrong base reviewed, independent-review's validator, prompt-sync and claims-sweep self-checks green, its round checks refusing a round past 3 with no --earned-by and a kind earning two rounds running with no --cut, its Perl programs within the Perl they declare (needs Perl::MinimumVersion; skipped without it), no installer clobbering a pinned skill, the handoff zip's leak check catching a large leak, the site pre-push hook gating and blocking the right pushes and being wired only at a repo's root by a line that holds no shell syntax, the site's verify script reinstalling only on a changed package.json or lockfile and stopping at the first red step, the private-name check running in a worktree too and CI's masked mode printing no scanned text, the site's Claude Code sync hook reporting news, failures and retries correctly, whats-new marking a frozen template file the site lacks as MISSING, the Node-floor test needing node (npm and its bundled semver for two cases, each skipped loudly without them), the throwaway-folder scripts the mktemp test lists stopping with an error when mktemp fails (a new script that calls mktemp must be listed or exempted there), every text file checking out LF even where Git converts to CRLF (each script's header says what it checks; the installer and hook tests need git, the hook test's wiring cases node and npm too, the verify test node, the claims-sweep, round-checks and base-check tests git (the claims-sweep test python3 too, the base-check test perl), the sync-hook test git and node, the whats-new test git, the mktemp test git, node and python3 to reach every script it runs)
	@bash scripts/check_clean.sh
	@bash scripts/check_cdpath_safe.sh
	@bash scripts/check_pipefail_pipes.sh
	@bash scripts/check_model_agnostic.sh
	@bash scripts/check_template_coverage.sh
	@bash scripts/test_template_coverage.sh
	@bash scripts/check_node_floor.sh
	@bash scripts/test_node_floor.sh
	@bash scripts/check_skill_budgets.sh
	@bash skills/independent-review/scripts/test_failed_tier_report.sh
	@bash skills/independent-review/scripts/test_base_check.sh
	@bash skills/independent-review/scripts/test_looks_like_review.sh
	@bash skills/independent-review/scripts/test_round_checks.sh
	@bash skills/independent-review/scripts/check_prompt_sync.sh
	@bash skills/independent-review/scripts/check_perl_minimum.sh
	@bash skills/independent-review/scripts/test_sweep_claims.sh
	@bash scripts/test_install_pin.sh
	@bash scripts/test_whats_new_removed_skill.sh
	@bash scripts/test_package_leak.sh
	@bash scripts/test_pre_push_hook.sh
	@bash scripts/test_verify.sh
	@bash scripts/test_clean_denylist.sh
	@bash scripts/test_git_stand_hook.sh
	@bash scripts/test_whats_new.sh
	@bash scripts/test_mktemp_guard.sh
	@bash scripts/check_lf_checkout.sh

PYTHON ?= python3
test:      ## run the search-console-insights tests (tracker + AI check; needs `requests`; stub servers, no real API calls). Not part of check/package, which must run on a stock python3
	@$(PYTHON) -m unittest discover -s skills/search-console-insights/scripts/tests

test-facts: ## run the facts-check tests (standard library only; a stub site on 127.0.0.1, no real requests)
	@$(PYTHON) -m unittest discover -s skills/facts-check/scripts/tests

test-agy-release: ## run the tests of the Antigravity release test (scripts/antigravity_release_test.py, a maintainer tool for releases; standard library only, needs git, node and npm; a stub agy, no credits spent). Not part of check/package: the handoff zip does not hold the tool or its tests
	@$(PYTHON) -m unittest discover -s scripts/tests -p 'test_antigravity*.py'

test-brand-kit: ## run the website-brand-kit tests (standard library only). The tests that draw icons need Node and an install of the starter to borrow `sharp` from (BRAND_KIT_NODE_MODULES=<its node_modules>), the share-card tests need Pillow; without those they skip, and with REQUIRE_SHARP=1 they fail instead
	@$(PYTHON) -m unittest discover -s skills/website-brand-kit/scripts/tests

test-wordpress-inventory: ## run the wordpress-inspector tests, the count and the move check (standard library only; stub sites on 127.0.0.1, no real requests)
	@$(PYTHON) -m unittest discover -s skills/wordpress-inspector/scripts/tests

NODE ?= node
test-cloudflare-check: ## run the tests of the Cloudflare check and of the Cloudflare setup script (Node 18+ and git, standard library only; stub sites, a stub of Cloudflare's API and a stub nameserver on 127.0.0.1, no real requests; one test waits out the setup script's 55-second deadline)
	@$(NODE) --test skills/new-website/scripts/tests/cloudflare-check.test.mjs skills/new-website/scripts/tests/cloudflare-setup.test.mjs

test-create: ## run the create-croftweaver tests (the `npm create croftweaver` installer; needs node and a git checkout, and on macOS and Linux zip and tar for one test; a stub of the release download on 127.0.0.1, no real requests). Not part of check/package: the handoff zip does not hold packages/
	@cd packages/create-croftweaver && $(NODE) --test

test-plugin: ## run the tests of the Claude Code and Codex plugin (.claude-plugin/, .agents/plugins/) and of the rule that lets the skills run from a plugin's folder: no skill names ~/.claude/skills/<name>/ for its files (needs node 20 or newer, git and bash). Not part of check/package: the handoff zip does not hold .claude-plugin/
	@$(NODE) --test scripts/plugin.test.mjs

test-codex-plugin: ## opt-in: install the Codex plugin from GitHub (the release on `stable`) in a throwaway Codex home, check Codex offers every skill, then update it (needs node 20 or newer, git, the Codex CLI and a connection to GitHub; no sign-in; skips without Codex). Not in CI: it tests the release, not this checkout
	@$(NODE) --test scripts/codex-plugin.test.mjs

# A linked worktree has no copy of the gitignored list; use the main checkout's, as check_clean.sh does.
# It runs in the C locale, as check_clean.sh does, so both read "the names" byte for byte alike
# (an em space is no space to either). It refuses a list with no names, or with an entry
# holding ^ other than right after [ (the check refuses those, a literal \^ included). It reads
# the names once, so what it sends and what it records are the same: the names base64-encoded
# on one line, after a marker line the CI step requires (.github/workflows/clean.yml says why),
# and their checksum in <list>.pushed, so `make check` fails once the names change after that.
push-denylist:   ## maintainer only: copy the private-name list (scripts/.clean-denylist, gitignored) into the repo's CLEAN_DENYLIST Actions secret, so CI checks names too. Run it after every change to the list; needs gh
	@export LC_ALL=C; f=scripts/.clean-denylist; [ -f "$$f" ] || f="$$(git worktree list --porcelain 2>/dev/null | sed -n '1s/^worktree //p')/scripts/.clean-denylist"; \
	[ -f "$$f" ] || { echo "no scripts/.clean-denylist here or in the main checkout"; exit 1; }; \
	names="$$(tr -d '\r' <"$$f" | grep -vE '^[[:space:]]*(#|$$)')"; \
	[ -n "$$names" ] || { echo "$$f lists no names: nothing to send"; exit 1; }; \
	[ "$$(printf '%s\n' "$$names" | grep -cE '(^|[^[])\^')" = 0 ] || { echo "$$f has entries holding ^ (other than right after [), which the check refuses: drop them (a literal \\^ too)"; exit 1; }; \
	repo="$$(gh repo view --json nameWithOwner -q .nameWithOwner)" && [ -n "$$repo" ] || { echo "gh cannot tell which GitHub repo this is"; exit 1; }; \
	b64="$$(printf '# CLEAN_DENYLIST v1\n%s\n' "$$names" | base64)" || { echo "base64 failed on $$f"; exit 1; }; \
	printf '%s' "$$b64" | tr -d '\n' | gh secret set CLEAN_DENYLIST --repo "$$repo" || exit 1; \
	printf '%s\n' "$$names" | cksum >"$$f.pushed" || { echo "CLEAN_DENYLIST set on $$repo, but its checksum could not be written to $$f.pushed: make check cannot tell when the list changes"; exit 1; }; \
	echo "CLEAN_DENYLIST set on $$repo from $$f"

smoke: package   ## shippability check: make check + build zip + verify zip contents
	@echo "smoke OK — suite is clean and the handoff zip is complete"
