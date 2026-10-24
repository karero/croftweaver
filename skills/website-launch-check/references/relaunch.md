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

Count `/page` and `/page/` as one address, and a %-escaped spelling as the same address.

## 2. A decision for each address

The decision comes from the owner's `moves.csv`, which `wordpress-inspector`'s
`make_redirects.py` reads: a new path, a full address on another host, `keep` (same address on
the new site) or `let go`. Without a `moves.csv`, ask the owner per address and record the
answer in the comparison. The launch check writes no redirects itself; `make_redirects.py`
writes `public/_redirects` from the decisions.

Then check each decision against the new site:

- a move: a line for it in `public/_redirects` (it may have several, for `/old`, `/old/` and the
  escaped forms); none is a before-launch item;
- `keep`: the path exists in the new build (`dist/`); missing is a before-launch item;
- `let go`: nothing to check;
- no decision: a before-launch item, by address;
- an address with a query (`/?p=12`): `_redirects` cannot match it, so `make_redirects.py` lists
  it and writes no line; list it the same way, with the owner's decision.

## 3. PageSpeed

The numbers are the owner's own runs on https://pagespeed.web.dev/ (as `website-qa` §2 asks):
the old site's before the switch; the new site's only once it is live, at the live re-check
(12a). Never fill in a number. Until then the new site's row reads "not measured yet: run after
the switch, at 12a".

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
