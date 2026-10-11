.PHONY: install install-codex package check test test-facts smoke whats-new refresh push-denylist

install:   ## symlink every skill into ~/.claude/skills/ (Claude Code)
	@bash scripts/install.sh

install-codex:   ## symlink every skill into ~/.agents/skills/ (OpenAI Codex)
	@bash scripts/install-codex.sh

whats-new: ## skill changes since a project was scaffolded: make whats-new PROJECT=<dir> (no PROJECT = recent suite changes)
	@bash scripts/whats-new.sh $(if $(PROJECT),"$(PROJECT)")

refresh:   ## re-copy a project's stale bundled skills + re-stamp (overwrites local edits): make refresh PROJECT=<dir>
	@bash scripts/whats-new.sh --refresh $(if $(PROJECT),"$(PROJECT)")

package: check   ## build dist/croftweaver.zip for handoff (runs check first)
	@bash scripts/package.sh

check:     ## run every suite guard: no personal data or credentials, every script locating itself CDPATH-safely, no pipe into an early-exit consumer (head, grep -q, …) under pipefail, no concrete model in independent-review, every astro template file bucketed, skill descriptions within budget, no failed reviewer hidden, independent-review's validator, prompt-sync and claims-sweep self-checks green, its Perl programs within the Perl they declare (needs Perl::MinimumVersion; skipped without it), no installer clobbering a pinned skill, the handoff zip's leak check catching a large leak, the site pre-push hook gating and blocking the right pushes and being wired only at a repo's root by a line that holds no shell syntax, the site's verify script reinstalling only on a changed package.json or lockfile and stopping at the first red step, the private-name check running in a worktree too and CI's masked mode printing no scanned text, the site's Claude Code sync hook reporting news, failures and retries correctly, whats-new marking a frozen template file the site lacks as MISSING, the throwaway-folder scripts the mktemp test lists stopping with an error when mktemp fails (a new script that calls mktemp must be listed or exempted there), every text file checking out LF even where Git converts to CRLF (each script's header says what it checks; the installer and hook tests need git, the hook test's wiring cases node and npm too, the verify test node, the claims-sweep test git and python3, the sync-hook test git and node, the whats-new test git, the mktemp test git, node and python3 to reach every script it runs)
	@bash scripts/check_clean.sh
	@bash scripts/check_cdpath_safe.sh
	@bash scripts/check_pipefail_pipes.sh
	@bash scripts/check_model_agnostic.sh
	@bash scripts/check_template_coverage.sh
	@bash scripts/check_skill_budgets.sh
	@bash skills/independent-review/scripts/test_failed_tier_report.sh
	@bash skills/independent-review/scripts/test_looks_like_review.sh
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
