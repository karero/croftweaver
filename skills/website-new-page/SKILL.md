---
name: website-new-page
description: >
  Add a page to a site, or rewrite one, so it is worth reading and findable before it is built.
  Writes one page document (a brief, then the full draft), has a fresh pair of eyes judge it for
  the reader, for search and AI answers, and for originality, takes the owner's go on the exact
  sentences, builds, then checks the build kept the approved text. It calls the checks other
  skills own (website-seo-geo, ai-seo, seo-audit, copywriting, search-console-insights,
  website-review) and does not repeat them. Use for a new page, a new article, a page rewrite,
  or "is this page any good". Trigger phrases: "add a page", "new page", "write a page about",
  "new article", "rewrite this page", "this page feels thin", "what should this page rank for",
  "review the draft before we build it".
---

# New page

A page can be accurate and still thin: it answers no search, has no FAQ, says nothing the top
results do not. A review of the finished code cannot see that; it checks that the page is built
right, not that it is the right page. This skill moves the judgment in front of the build, where
a change costs a sentence and not a round of code review.

**What you produce:** one page document, `docs/pages/<slug>.md` unless the site keeps such files
elsewhere. It has two parts: a brief of one page at most, then the full draft copy. Start from
`${CLAUDE_SKILL_DIR}/templates/page-document.md`.

## The steps

**1. Intake.** Ask the owner these five questions, unless the request already answers them:

1. Who reads the page?
2. What do they type into a search box, or ask an AI?
3. What should they do after reading?
4. What can we say that others cannot (proof, our own experience, a point of view)?
5. For each document, link or note they hand over: is it a **source**, or **ideas only**?

Ideas-only input may suggest questions to research. It never backs a claim, a citation or a
link, unless the owner reclassifies it after you have read the source itself.

**2. Research.** Read the top results for the main query and ask an AI the same question. Save
what they cover and what they miss in a research file (`docs/pages/<slug>-research.md`), with the
address of every source you read. Read each source at the source, not through a summary. Where
the site has Search Console data and the `search-console-insights` skill is installed, that skill
shows what the page's neighbours already rank for; otherwise skip this.

**3. Write the page document.** The brief fills its fields in plain words: the page type (an
article that answers a question, a home page, a product or service page, a contact or legal
page: the review judges depth and FAQ by it), reader, main query and
two or three related ones, title, H1 and description led by the search words, the one original
angle, the outline with what each section must teach, the graphics, four to six FAQ questions
that each add something the body does not, the inputs with their labels, a claims table, an
outbound-links table, and "what we will not say". Every proof point must be one the reader can
open or understand without access: no internal ticket, pull request or repository names on a
public page. Then write the draft copy in full, to that outline. Drafting is cheap; reviewing
copy after it is built is not.

Call the other skills for their own questions, and do not restate their rules here:

| The brief asks | Ask |
|---|---|
| Title and description length, schema, `llms.txt` | `website-seo-geo` |
| Will an AI answer quote this page? | `ai-seo` |
| Does the page match the search intent? | `seo-audit` |
| Is the copy clear and in the owner's voice? | `copywriting` |
| What does the site already rank for? | `search-console-insights`, where it is installed |

**4. Content review.** One reviewer reads the page document and the research file with the prompt
in `${CLAUDE_SKILL_DIR}/references/content-review.md`. It asks three things: does the page answer
its reader (including graphics and proof the reader can check), is it findable (search, AI
answers, who wrote it and why they know), and is it original next to the top results? The answer
is a ranked list of BUG, RISK and NIT findings.

- **Who reviews is the owner's choice. The default is your own AI**, started fresh: a subagent
  that did not write the page or, where yours cannot start one, a new conversation with the
  three texts pasted in. That needs no second AI provider. A second reviewer is the owner's
  call, as `website-review` says for all site work. If the owner has the `independent-review`
  skill working, `independent_review.sh <page document> --content --evidence <research file>`
  sends the same prompt to its seats.
- Two rounds at most. Fix each finding, or list it for the owner to accept or reject in the go.
  A fix that changes the meaning of a sentence gets one more read.

**5. The owner's go.** Show the owner the reviewed document and a short note of the findings still
open, each with your recommendation. Their go covers the exact sentences, not an outline. Write
"approved by the owner on <date>" at the top of the page document.

**6. Build** the page and everything the site wants around it: the route, `llms.txt`, the share
card, an inbound link from a page that already ranks, and the schema (`FAQPage` where there is a
FAQ). Tests should check that contract, the sentences the site marks as locked (its
`AGENTS.md` or `CLAUDE.md` says which), and the claims-table rows the owner signed off. They need
not pin all of the body copy: the next step watches it.

**7. Check the build kept the text.** After the site builds, run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/check_page_text.py" docs/pages/<slug>.md dist/<slug>.html \
  --title-suffix " | Site name" --skip nav,footer,aside,.byline
```

It compares the draft with the built page's title, description, FAQ schema and every sentence in
its `<main>` (the whole body if there is none), after folding whitespace, HTML entities and
typographic quotes. Dashes and every other character are compared as written. Exit
0 means the build kept the text. Exit 1 lists every changed sentence: put that list in the PR for
the owner to read, as it is. Components that add their own text (a byline, a button) are named
with `--skip`, as tags or `.classes`; if the check names a sentence the owner did not approve,
that is the finding. Exit 2 means the check could not read its input.

**8. Review the code** with the site's usual review (`website-review`, or `independent-review`'s
diff gate where the owner has chosen it). By now the copy has been judged, so this round checks
the build.

## Rules that keep the process short

- **Judge the page before building it.** A copy change after the build costs a code review.
- **Words in tests are for the sentences that must not change.** Not for every paragraph.
- **The research file is evidence, not decoration.** A review that has no research file cannot
  say a page is thin, and says so.
- **The reviewer returns findings, not orders.** The owner decides.

## Done means

- The page document says "approved by the owner" with a date, and its draft is the text on the page.
- `check_page_text.py` exits 0, or its list of changed sentences is in the PR and the owner has read it.
- The site's own checks and review are green.
- You say plainly what you did not check: whether the page ranks, which only time shows.
