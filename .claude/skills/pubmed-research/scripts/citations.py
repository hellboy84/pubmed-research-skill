"""Citation formatting from normalized PubMed records.

Generated in-code from the article metadata (no external citation API), matching
the approach of the pubmed_format_citations tool. Vancouver is the primary style
for this skill; apa/mla/bibtex/ris are also supported.

A normalized record is the dict produced by pubmed_parse.parse_article.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


# ─── BibTeX / LaTeX escaping ─────────────────────────────────────────────────
# A .bib field is LaTeX source, and biomedical titles are full of characters that
# LaTeX reads as markup. '%' is the dangerous one: it opens a comment, so
# `title = {The neglected 95%: ...}` swallows the closing brace and the comma with
# it, and BibTeX keeps parsing into the next entry. Nothing warns; the
# bibliography simply comes out wrong.
_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
# One pass over the string: each character is rewritten once, so the braces and
# backslashes introduced by a replacement are never themselves re-escaped. A
# sequence of .replace() calls cannot do this — whichever runs first corrupts the
# output of the ones after it.
_LATEX_RE = re.compile("|".join(re.escape(k) for k in _LATEX_SPECIAL))


def _tex(value: Any) -> str:
    """Escape a string for use inside a BibTeX field value."""
    return _LATEX_RE.sub(lambda m: _LATEX_SPECIAL[m.group()], str(value or ""))


def _authors_vancouver(authors: List[Dict[str, Any]], limit: int = 6) -> str:
    names = []
    for a in authors:
        last = a.get("lastName", "")
        initials = a.get("initials", "")
        if not initials and a.get("firstName"):
            initials = "".join(p[0] for p in a["firstName"].split() if p)
        # ICMJE keeps the generational suffix, unpunctuated, after the initials:
        # 'Glass DA 2nd'.
        names.append(" ".join(p for p in (last, initials, a.get("suffix", "")) if p)
                     if last else a.get("name", ""))
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
        if last:
            entry = f"{last}, {initials}".strip().rstrip(",")
            if a.get("suffix"):
                entry += f", {a['suffix']}"
        else:
            entry = a.get("name", "")
        parts.append(entry)
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
        if first.get("suffix"):
            lead += f", {first['suffix']}"
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


def _bibtex_author(a: Dict[str, Any]) -> str:
    last = a.get("lastName", "")
    if last:
        # BibTeX has a slot of its own for the suffix — the three-part
        # 'Last, Jr, First' form. Appending it to the first name instead would
        # render 'David A. 2nd' as a given name.
        if a.get("suffix"):
            return _tex(f"{last}, {a['suffix']}, {a.get('firstName', '')}".rstrip(", "))
        return _tex(f"{last}, {a.get('firstName', '')}".strip().rstrip(","))
    # A group author ('SURMOUNT-1 Investigators') carries no lastName, only name.
    # Selecting on lastName drops it silently — and on a large trial the group is
    # part of the citation. The extra braces are load-bearing: they tell BibTeX
    # the string is one literal name, otherwise it splits it into first/last and
    # renders 'Investigators, SURMOUNT-1'.
    name = a.get("name", "")
    return "{%s}" % _tex(name) if name else ""


def _bibtex_key(rec: Dict[str, Any]) -> str:
    authors = rec.get("authors") or []
    lead = ""
    if authors:
        lead = authors[0].get("lastName") or authors[0].get("name") or ""
    year = (rec.get("journal") or {}).get("year", "")
    # The key is BibTeX syntax rather than a field value, so it cannot carry
    # escapes — strip to characters that are always safe instead. A key of ''
    # (group-led paper) or a bare year collides across entries, so fall back to
    # the PMID, which is unique by construction.
    key = re.sub(r"[^A-Za-z0-9]", "", f"{lead}{year}")
    return key if lead else f"ref{rec.get('pmid', '')}".strip() or "ref"


def format_bibtex(rec: Dict[str, Any]) -> str:
    j = rec.get("journal", {})
    authors = " and ".join(
        s for s in (_bibtex_author(a) for a in rec.get("authors", [])) if s
    )
    lines = [f"@article{{{_bibtex_key(rec)},"]
    if authors:
        lines.append(f"  author = {{{authors}}},")
    lines.append(f"  title = {{{_tex(rec.get('title', ''))}}},")
    if j.get("title"):
        lines.append(f"  journal = {{{_tex(j['title'])}}},")
    if j.get("year"):
        lines.append(f"  year = {{{_tex(j['year'])}}},")
    if j.get("volume"):
        lines.append(f"  volume = {{{_tex(j['volume'])}}},")
    if j.get("issue"):
        lines.append(f"  number = {{{_tex(j['issue'])}}},")
    if j.get("pages"):
        lines.append(f"  pages = {{{_tex(j['pages'])}}},")
    if rec.get("doi"):
        lines.append(f"  doi = {{{_tex(rec['doi'])}}},")
    if rec.get("pmid"):
        lines.append(f"  pmid = {{{_tex(rec['pmid'])}}},")
    lines.append("}")
    return "\n".join(lines)


def format_ris(rec: Dict[str, Any]) -> str:
    j = rec.get("journal", {})
    lines = ["TY  - JOUR"]
    for a in rec.get("authors", []):
        last = a.get("lastName", "")
        fore = a.get("firstName", "")
        if last:
            # RIS name form is 'Last, First, Suffix'.
            entry = f"{last}, {fore}".rstrip(", ")
            if a.get("suffix"):
                entry += f", {a['suffix']}"
            lines.append(f"AU  - {entry}")
        elif a.get("name"):
            # Group author. Written without a comma, which is how RIS readers
            # tell a corporate name from a 'Last, First' personal one.
            lines.append(f"AU  - {a['name']}")
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
