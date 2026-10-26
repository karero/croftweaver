# Relaunch mode: the current site against the new one

Used when `docs/launch/config.json` names the site the new one replaces (`"replaces"`). The
pre-launch run then also writes `docs/launch/launch-comparison-<YYYY-MM-DD>.md`, from
`comparison-template.md`, and its HTML. The structure is fixed; the content is this site's.

## 1. The old addresses

Take the list from the first source that exists, and say in the comparison which one it was:

1. `wordpress-inspector`'s inventory (`urls.csv`, in the folder where the owner ran it, outside
   the site's repository). Read `inventory.json` first: when it says `"complete": false`, the
   map covers the known addresses only, and the verdict says so with the reasons it gives
   (`incomplete_because`).
2. The old site's `sitemap.xml` (or its sitemap index). Reading the old site's own existing
   addresses before the switch is fine.
3. A list the owner gives.

Count addresses the way `wordpress-inspector`'s `check_move.py` does (`page_form`): the closing
slash dropped (`/page` and `/page/` are one) and each escape's hex digits in upper case, nothing
decoded, so `/a%2Fb` and `/a/b` stay two addresses.

## 2. A decision for each address

The decision comes from the owner's `moves.csv`, which `wordpress-inspector`'s
`make_redirects.py` reads: a new path, a full address on another host, `keep` (same address on
the new site) or `let go`. An empty `new_address` means no decision yet. Without a `moves.csv`, ask the owner per address and record the
answer in the comparison. The launch check writes no redirects itself; `make_redirects.py`
writes `public/_redirects` from the decisions.

Then check each decision against the new site:

- a move: a line for it in `public/_redirects` (it may have several, for `/old`, `/old/` and the
  escaped forms) whose target is where the decisions lead, counted as in §1 (`make_redirects.py`
  follows chains: `/a → /b` and `/b → /c` write `/a /c`), and, for a path on the new site, that
  path in the new build (`dist/`); a missing line, another target or a missing page is a
  before-launch item;
- `keep`: the path exists in the new build (`dist/`); missing is a before-launch item;
- `let go`: nothing to check;
- no decision: a before-launch item, by address;
- an address with a query (`/?p=12`): `_redirects` cannot match it (`make_redirects.py`'s
  header says so and lists such an address without a line); list it the same way, with the
  owner's decision.

## 3. Speed

Measure as `website-qa` §2 does: the assistant runs Lighthouse; PageSpeed Insights in the
built-in browser, and then the owner, are its fallbacks. The table names the tool. The old site:
its public pages, before the switch; if they cannot be measured, the row says why. The new site:
only at a deployed address (`website-qa` §2, step 3): its `main` preview where one exists, and
production after the switch (12a). With no deployed address yet (a pre-launch run before §4's
first deploy), its row reads "not measured yet: no deployed address". Never fill in a number.

## 4. The rest of the comparison

The E-E-A-T rows for both sites (Authority "not checked: no outside data" unless the owner gave
some), the open questions only the owner can answer, a side by side of the topics that matter
to the owner's visitors, what the current site gets wrong, what the new one adds, and what it
does not have yet. Every row states what was seen, with the page; nothing is assumed.

## 5. Where it goes

The comparison holds the old site's paths and the owner's decisions, nothing else from the
inventory: `wordpress-inspector` keeps its inventory out of the site's repository because it
names another party's addresses. In a public site repository, ask before committing it.

## After the switch

At the live re-check, for a WordPress move, point the owner at `wordpress-inspector`'s
`scripts/check_move.py --moves`, which asks the new site for every old address and checks each
ends where the decisions say. A site's bundled skills do not include `wordpress-inspector`;
where it is not installed, say it comes from Croftweaver.
