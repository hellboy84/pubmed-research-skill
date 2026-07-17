#!/usr/bin/env python3
"""to_csv.py — export PubMed article records to CSV.

Column layout mirrors the PubMed2ExcelDownloader output. Reads JSON from a file
or stdin. The JSON may be:
  - the output of `pubmed.py fetch`, `search --summaries`, `related`, or
    `fulltext` (an object with an "articles" list),
  - the output of `pubmed.py epmc-search` (an object with a "results" list of
    Europe PMC hits), or
  - a bare list of article records.

Output of `cite` and `lookup-cite` is not an article list; passing it produces a
JSON error rather than a half-empty CSV.

Usage:
    python pubmed.py fetch 31978945 12345678 | python to_csv.py -o out.csv
    python to_csv.py results.json -o out.csv

Date-safety note: fields like volume/issue/pages can look like dates (e.g.
"3-5", "10/12") and spreadsheet apps love to auto-convert them. We write a plain
CSV with everything as text; when the user opens it, importing as text (or the
fact that these are quoted strings) avoids silent conversion. For hard
guarantees against Excel auto-conversion, the xlsx skill with string-typed cells
is the right tool — this script keeps it to portable CSV as requested.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any, Dict, List

# See eutils_common.py for why this is unconditional: Windows consoles/pipes
# default to a legacy code page (e.g. cp932) that can't represent characters
# common in article metadata, and this script doesn't import eutils_common.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


COLUMNS = [
    "PMID",
    "Title",
    "Authors",
    "First Author",
    "Journal",
    "Journal Abbreviation",
    "Year",
    "Volume",
    "Issue",
    "Pages",
    "DOI",
    "PMCID",
    "Publication Types",
    "MeSH Terms",
    "Keywords",
    "Abstract",
    "PubMed URL",
    "PMC URL",
]


def _authors_joined(authors: List[Dict[str, Any]]) -> str:
    return "; ".join(a.get("name", "") for a in authors if a.get("name"))


def _epmc_to_record(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Reshape a Europe PMC search hit into the article-record shape.

    EPMC flattens what EFetch nests: `journal` is a bare string, authors arrive
    as one comma-joined `authorString`. Feeding a hit straight to record_to_row
    would call .get() on a string and, for the rows that survive, leave most
    columns blank without saying why.
    """
    pmid = str(hit.get("pmid") or "")
    pmcid = str(hit.get("pmcid") or "")
    names = [n.strip() for n in (hit.get("authorString") or "").rstrip(".").split(",")]
    return {
        "pmid": pmid,
        "title": hit.get("title", ""),
        "authors": [{"name": n} for n in names if n],
        "journal": {"title": hit.get("journal", ""), "year": str(hit.get("year") or "")},
        "doi": hit.get("doi", ""),
        "pmcid": pmcid,
        "abstract": hit.get("abstract", ""),
        "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "pmcUrl": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else "",
    }


def _brief_to_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Reshape a `related` brief summary into the article-record shape.

    ESummary flattens what EFetch nests, the same way an EPMC hit does: `authors`
    arrives as one comma-joined string and the journal as `source`. Passed
    through untouched, record_to_row calls .get() on a string and dies. The
    columns the summary cannot fill (DOI, volume, MeSH, abstract) stay empty —
    `related --fetch` is what populates those.
    """
    pmid = str(rec.get("pmid") or "")
    names = [n.strip() for n in (rec.get("authors") or "").rstrip(".").split(",")]
    names = [n for n in names if n and n.lower() not in ("et al", "et al.")]
    return {
        "pmid": pmid,
        "title": rec.get("title", ""),
        "authors": [{"name": n} for n in names],
        "journal": {"title": rec.get("source", ""),
                    "year": str(rec.get("pubDate") or "")[:4]},
        "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
    }


def record_to_row(rec: Dict[str, Any]) -> Dict[str, str]:
    j = rec.get("journal") or {}
    authors = rec.get("authors", []) or []
    first_author = authors[0].get("name", "") if authors else ""
    return {
        "PMID": rec.get("pmid", ""),
        "Title": rec.get("title", ""),
        "Authors": _authors_joined(authors),
        "First Author": first_author,
        "Journal": j.get("title", ""),
        "Journal Abbreviation": j.get("isoAbbreviation", ""),
        "Year": j.get("year", ""),
        "Volume": j.get("volume", ""),
        "Issue": j.get("issue", ""),
        "Pages": j.get("pages", ""),
        "DOI": rec.get("doi", ""),
        "PMCID": rec.get("pmcid", ""),
        "Publication Types": "; ".join(rec.get("publicationTypes", []) or []),
        "MeSH Terms": "; ".join(rec.get("meshTerms", []) or []),
        "Keywords": "; ".join(rec.get("keywords", []) or []),
        "Abstract": rec.get("abstract", ""),
        "PubMed URL": rec.get("pubmedUrl", ""),
        "PMC URL": rec.get("pmcUrl", ""),
    }


def _load_records(text: str) -> List[Dict[str, Any]]:
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if data.get("error"):
            raise ValueError(f"Input JSON reports an error: {data['error']}")
        if "articles" in data:
            # `related` without --fetch fills `articles` with brief summaries that
            # carry a string `authors`; everything else nests it. Normalize here
            # so record_to_row only ever sees the one shape.
            return [_brief_to_record(r) if isinstance(r.get("authors"), str) else r
                    for r in data["articles"]]
        rows = data.get("results") or []
        # `results` is not unique to epmc-search: `cite` and `lookup-cite` use it
        # too, and neither carries article metadata. Match on a field only an
        # EPMC hit has rather than writing a CSV of empty columns.
        if rows and isinstance(rows[0], dict) and "authorString" in rows[0]:
            return [_epmc_to_record(h) for h in rows]
        if rows:
            raise ValueError(
                "The 'results' list holds citation/lookup output, not articles. "
                "Pipe `fetch`, `search --summaries`, `related`, or `epmc-search` instead."
            )
    raise ValueError("Could not find an article list in the input JSON.")


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description="Export PubMed records to CSV.")
    p.add_argument("input", nargs="?", help="Input JSON file (default: stdin).")
    p.add_argument("-o", "--output", required=True, help="Output CSV path.")
    args = p.parse_args(argv)

    # Callers parse stdout as JSON, so bad input has to surface the same way the
    # pubmed.py subcommands surface it: an object with an `error` key, not a
    # traceback. Shaping each row belongs inside this too — a record the columns
    # do not fit is bad input like any other, and it used to escape as a
    # traceback because the write loop sat outside the guard.
    try:
        text = open(args.input, encoding="utf-8").read() if args.input else sys.stdin.read()
        records = _load_records(text)
        with open(args.output, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for rec in records:
                writer.writerow(record_to_row(rec))
    except Exception as exc:  # noqa: BLE001
        json.dump({"error": type(exc).__name__, "message": str(exc)},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 1

    print(f"Wrote {len(records)} rows to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
