"""Citation formatting from normalized PubMed records.

Generated in-code from the article metadata (no external citation API), matching
the approach of the pubmed_format_citations tool. Vancouver is the primary style
for this skill; apa/mla/bibtex/ris are also supported.

A normalized record is the dict produced by pubmed_parse.parse_article.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _authors_vancouver(authors: List[Dict[str, Any]], limit: int = 6) -> str:
    names = []
    for a in authors:
        last = a.get("lastName", "")
        initials = a.get("initials", "")
        if not initials and a.get("firstName"):
            initials = "".join(p[0] for p in a["firstName"].split() if p)
        names.append(f"{last} {initials}".strip() if last else a.get("name", ""))
    names = [n for n in names if n]
    if len(names) > limit:
        return ", ".join(names[:limit]) + ", et al"
    return ", ".join(names)


def _authors_apa(authors: List[Dict[str, Any]]) -> str:
    parts = []
    for a in authors:
        last = a.get("lastName", "")
        initials = a.get("initials", "")
        if not initials and a.get("firstName"):
            initials = "".join(f"{p[0]}." for p in a["firstName"].split() if p)
        elif initials:
            initials = "".join(f"{ch}." for ch in initials)
        parts.append(f"{last}, {initials}".strip().rstrip(",") if last else a.get("name", ""))
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + ", & " + parts[-1]


def format_vancouver(rec: Dict[str, Any]) -> str:
    j = rec.get("journal", {})
    authors = _authors_vancouver(rec.get("authors", []))
    title = rec.get("title", "").rstrip(".")
    abbrev = j.get("isoAbbreviation") or j.get("title", "")
    year = j.get("year", "")
    vol = j.get("volume", "")
    issue = j.get("issue", "")
    pages = j.get("pages", "")
    doi = rec.get("doi", "")

    cite = ""
    if authors:
        cite += f"{authors}. "
    cite += f"{title}. "
    if abbrev:
        cite += f"{abbrev}. "
    if year:
        cite += f"{year}"
    if vol:
        cite += f";{vol}"
    if issue:
        cite += f"({issue})"
    if pages:
        cite += f":{pages}"
    # Terminate with exactly one period. Without stripping first, a record whose
    # trailing element is the already-period-ended title (no journal/year/vol/
    # pages, as with some ahead-of-print or book entries) yields '..'.
    cite = cite.rstrip().rstrip(".") + "."
    if doi:
        cite += f" doi:{doi}."
    return " ".join(cite.split())


def format_apa(rec: Dict[str, Any]) -> str:
    j = rec.get("journal", {})
    authors = _authors_apa(rec.get("authors", []))
    year = j.get("year", "")
    title = rec.get("title", "").rstrip(".")
    journal = j.get("title", "") or j.get("isoAbbreviation", "")
    vol = j.get("volume", "")
    issue = j.get("issue", "")
    pages = j.get("pages", "")
    doi = rec.get("doi", "")

    cite = ""
    if authors:
        cite += f"{authors} "
    if year:
        cite += f"({year}). "
    cite += f"{title}. "
    if journal:
        cite += f"{journal}"
        if vol:
            cite += f", {vol}"
            if issue:
                cite += f"({issue})"
        if pages:
            cite += f", {pages}"
        cite += "."
    if doi:
        cite += f" https://doi.org/{doi}"
    return " ".join(cite.split())


def format_mla(rec: Dict[str, Any]) -> str:
    authors = rec.get("authors", [])
    j = rec.get("journal", {})
    if authors:
        first = authors[0]
        lead = f"{first.get('lastName','')}, {first.get('firstName','')}".strip().rstrip(",")
        if len(authors) > 1:
            lead += ", et al"
    else:
        lead = ""
    title = rec.get("title", "").rstrip(".")
    journal = j.get("title", "") or j.get("isoAbbreviation", "")
    vol = j.get("volume", "")
    issue = j.get("issue", "")
    year = j.get("year", "")
    pages = j.get("pages", "")

    cite = ""
    if lead:
        cite += f"{lead}. "
    cite += f'"{title}." '
    if journal:
        cite += f"{journal}"
        if vol:
            cite += f", vol. {vol}"
        if issue:
            cite += f", no. {issue}"
        if year:
            cite += f", {year}"
        if pages:
            cite += f", pp. {pages}"
        cite += "."
    return " ".join(cite.split())


def format_bibtex(rec: Dict[str, Any]) -> str:
    j = rec.get("journal", {})
    authors = " and ".join(
        f"{a.get('lastName','')}, {a.get('firstName','')}".strip().rstrip(",")
        for a in rec.get("authors", []) if a.get("lastName")
    )
    first_author = rec.get("authors", [{}])[0].get("lastName", "ref") if rec.get("authors") else "ref"
    key = f"{first_author}{j.get('year','')}".replace(" ", "")
    lines = [f"@article{{{key},"]
    if authors:
        lines.append(f"  author = {{{authors}}},")
    lines.append(f"  title = {{{rec.get('title','')}}},")
    if j.get("title"):
        lines.append(f"  journal = {{{j['title']}}},")
    if j.get("year"):
        lines.append(f"  year = {{{j['year']}}},")
    if j.get("volume"):
        lines.append(f"  volume = {{{j['volume']}}},")
    if j.get("issue"):
        lines.append(f"  number = {{{j['issue']}}},")
    if j.get("pages"):
        lines.append(f"  pages = {{{j['pages']}}},")
    if rec.get("doi"):
        lines.append(f"  doi = {{{rec['doi']}}},")
    if rec.get("pmid"):
        lines.append(f"  pmid = {{{rec['pmid']}}},")
    lines.append("}")
    return "\n".join(lines)


def format_ris(rec: Dict[str, Any]) -> str:
    j = rec.get("journal", {})
    lines = ["TY  - JOUR"]
    for a in rec.get("authors", []):
        last = a.get("lastName", "")
        fore = a.get("firstName", "")
        if last:
            lines.append(f"AU  - {last}, {fore}".rstrip(", "))
    lines.append(f"TI  - {rec.get('title','')}")
    if j.get("title"):
        lines.append(f"JO  - {j['title']}")
    if j.get("year"):
        lines.append(f"PY  - {j['year']}")
    if j.get("volume"):
        lines.append(f"VL  - {j['volume']}")
    if j.get("issue"):
        lines.append(f"IS  - {j['issue']}")
    if j.get("pages"):
        lines.append(f"SP  - {j['pages']}")
    if rec.get("doi"):
        lines.append(f"DO  - {rec['doi']}")
    if rec.get("pmid"):
        lines.append(f"AN  - {rec['pmid']}")
    lines.append("ER  - ")
    return "\n".join(lines)


_FORMATTERS = {
    "vancouver": format_vancouver,
    "apa": format_apa,
    "mla": format_mla,
    "bibtex": format_bibtex,
    "ris": format_ris,
}


def format_citation(rec: Dict[str, Any], style: str) -> str:
    fn = _FORMATTERS.get(style, format_vancouver)
    return fn(rec)
