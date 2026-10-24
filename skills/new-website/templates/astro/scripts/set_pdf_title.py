#!/usr/bin/env python3
"""Set a descriptive doc-title (+ author) on a hosted PDF — Info dict AND XMP.

Why this exists: a PDF has no <title>, so Bing/Google print its embedded
doc-title as the search-result title. PowerPoint/Keynote/Word leave a placeholder
("PowerPoint-Präsentation") or a working-filename slug, which Bing flags as "page
title too short". Crawlers read the title from TWO places — the Info dict /Title
and the XMP dc:title — so both must be set; fixing only one leaves the stale title
visible. tests/seo.spec.ts gates this in CI; this script is the fix.

Convention: match the page's title for the document, e.g.
"Talk Title — Speaker | Brand". Keep it >=15 chars and not the authoring placeholder.

Requires pypdf:  python3 -m pip install pypdf
Run from repo root:
  python3 scripts/set_pdf_title.py public/<file>.pdf "Descriptive Title | Brand" --author "Author"
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf not installed — run: python3 -m pip install pypdf")


def set_title(path: Path, title: str, author: str | None) -> None:
    reader = PdfReader(str(path))
    old = (reader.metadata or {}).get("/Title")
    writer = PdfWriter(clone_from=str(path))

    info = {"/Title": title}
    if author:
        info["/Author"] = author
    writer.add_metadata(info)

    # XMP packet (plaintext metadata stream): replace dc:title (and dc:creator)
    # in place so the stale value can't shadow the Info dict for crawlers.
    meta = writer._root_object.get("/Metadata")
    if meta is not None:
        raw = bytes(meta.get_data()).decode("utf-8", "replace")
        raw = re.sub(r"(<dc:title>.*?<rdf:li[^>]*>).*?(</rdf:li>)",
                     lambda m: m.group(1) + title + m.group(2), raw, flags=re.S)
        if author:
            raw = re.sub(r"(<dc:creator>.*?<rdf:li[^>]*>).*?(</rdf:li>)",
                         lambda m: m.group(1) + author + m.group(2), raw, flags=re.S)
        meta.set_data(raw.encode("utf-8"))

    with open(path, "wb") as fh:
        writer.write(fh)

    # Verify and report (fail loud if it didn't take).
    check = PdfReader(str(path))
    new = (check.metadata or {}).get("/Title")
    if new != title:
        sys.exit(f"FAILED: /Title is {new!r} after write, expected {title!r}")
    print(f"{path}: /Title {old!r} -> {new!r}"
          + (f", /Author -> {author!r}" if author else "")
          + f"  ({len(check.pages)} pages)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Set a hosted PDF's doc-title (Info + XMP).")
    ap.add_argument("pdf", type=Path, help="path to the PDF (e.g. public/<file>.pdf)")
    ap.add_argument("title", help='"Descriptive Title | Brand"')
    ap.add_argument("--author", help="document author")
    args = ap.parse_args()
    if not args.pdf.is_file():
        sys.exit(f"no such file: {args.pdf}")
    if len(args.title) < 15:
        sys.exit(f"title too short ({len(args.title)} chars) — seo.spec.ts requires >=15")
    set_title(args.pdf, args.title, args.author)


if __name__ == "__main__":
    main()
