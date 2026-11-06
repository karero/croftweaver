# Fixtures for check_page_text.py

`astro-7.4.2_built-page_shape-capture.html` is the markup of a real page built with Astro 7.4.2
(`astro build` on a private production site, one article page with a FAQ):
the head, the four JSON-LD blocks, the section and `data-astro-cid-*` structure, the byline,
the footer, and the entity forms the build produced (`&amp;`, `&#39;`, `&ndash;`, `&middot;`,
`&copy;`). Parts were cut (the navigation's extra links, the stylesheet, the theme script's
comments, the footer's address and contact blocks); the markup that stayed was not edited. The
site's brand name, its people and every word of its copy were replaced with made-up text, because
the site is private and this repository is public. The structure and the entity forms are the
build's own.

`astro-7.4.2_built-page_approved-draft.md` is the page document's draft, written by hand from
the made-up copy. Typographic apostrophe in the draft, `&#39;` in the page: that pair is on
purpose.
