# Fixtures for check_page_links.py

`astro-7.4.13_built-site/built/` is Astro's `dist/` from a real `astro build` (Astro 7.4.13) of the kit's starter with
31 pages added or kept, each shaped for one case in `test_check_page_links.py`. The sources of the
added pages are in `site-src/` (`pages/` and `layouts/Plain.astro`; `Plain.astro` is a layout with
no `<main>`). Two edits were made to the starter's `Base.astro`, which is not copied here: a
`before-main` and an `after-main` slot around `<main id="main">`, and a footer link to
`/footer-only` on every page that uses it (the two no-`<main>` pages use `Plain.astro`, which has no footer). The site is made up (`https://example.com`); every page holds
placeholder text. The folder is not named `dist` because the repo's `.gitignore` skips that name. The build was trimmed, and nothing else was edited: each `<style>` block and
each inline script without `type="application/ld+json"` was removed.

The cases, by path:

- `/hub` with spokes `/hub/spoke-ok` (breadcrumb `<nav>` inside `<main>` back to the hub),
  `/hub/spoke-sib` and `/hub/spoke-noback` (names its hub only in BreadcrumbList JSON-LD).
- `/footer-only`: linked from the footer of every page that uses `Base.astro` and from one `<nav>` inside `/hub`'s `<main>`.
- `/header-only`: linked only from a `<header>` that sits inside `<main>`: on `/hub` the header holds
  a `<nav>`, on `/other` a plain link.
- `/plain-div`: linked from `/div-linker1` and `/div-linker2`, each from a `<div>` outside `<main>`.
- `/one-inbound`: linked from `/other` alone.
- `/chain/c4`: four clicks from home, via `/chain/c3` and `/chain/c3b`.
- `/hub-nav` and `/hub-nav/spoke`: the hub lists the spoke only in a `<nav>`.
- `/hub-nomain` and `/no-main`: pages with no `<main>`; `/via-nomain` is linked from `/no-main`.
- `/hub/x`: linked in the address forms the check must fold (`/fold/s1`, `/fold/s2`, `/fold/s3`,
  `/hub/y` with the page-relative `x`), from another host (`/fold/s5`) and from inside an element
  with `hidden` (`/fold/sh`).

The expected values in the tests were written by hand from this list, not copied from the
script's output.
