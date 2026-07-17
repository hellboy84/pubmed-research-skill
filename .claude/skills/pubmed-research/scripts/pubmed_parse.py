"""Parse PubMed EFetch XML (PubmedArticleSet) into normalized article dicts.

The normalization mirrors the field set the cyanheads/pubmed-mcp-server returns:
title, abstract (structured sections joined), authors (with deduplicated
affiliations), journal info, dates, identifiers (PMID/DOI/PMCID), MeSH terms,
publication types, keywords.

Kept dependency-free (stdlib ElementTree via eutils_common.parse_xml, which
transparently upgrades to lxml when available).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from eutils_common import parse_xml


def _text(el) -> str:
    """All descendant text of an element, flattened and whitespace-normalized."""
    if el is None:
        return ""
    parts = list(el.itertext())
    return " ".join(" ".join(parts).split())


def _first(parent, path) -> Optional[Any]:
    if parent is None:
        return None
    return parent.find(path)


def _findall(parent, path) -> List[Any]:
    if parent is None:
        return []
    return parent.findall(path)


def _extract_abstract(article) -> str:
    """Join structured abstract sections; prefix labels like 'BACKGROUND:'."""
    sections: List[str] = []
    for ab in _findall(article, ".//Abstract/AbstractText"):
        label = ab.get("Label")
        body = _text(ab)
        if not body:
            continue
        sections.append(f"{label}: {body}" if label else body)
    return "\n".join(sections)


def _author_from_el(auth) -> Optional[Dict[str, Any]]:
    last = _text(_first(auth, "LastName"))
    fore = _text(_first(auth, "ForeName"))
    collective = _text(_first(auth, "CollectiveName"))
    initials = _text(_first(auth, "Initials"))
    affs = []
    for aff in _findall(auth, ".//AffiliationInfo/Affiliation"):
        a = _text(aff)
        if a and a not in affs:
            affs.append(a)
    if collective:
        name = collective
    elif last:
        name = f"{last} {initials}".strip() if initials else last
    else:
        name = fore
    if not name:
        return None
    return {
        "lastName": last,
        "firstName": fore,
        "initials": initials,
        "name": name,
        "affiliations": affs,
    }


def _extract_authors(article) -> List[Dict[str, Any]]:
    authors: List[Dict[str, Any]] = []
    for auth in _findall(article, ".//AuthorList/Author"):
        rec = _author_from_el(auth)
        if rec:
            authors.append(rec)
    return authors


def _extract_ids(article_container) -> Dict[str, str]:
    ids = {"pmid": "", "doi": "", "pmcid": ""}
    pmid_el = _first(article_container, ".//MedlineCitation/PMID")
    if pmid_el is not None:
        ids["pmid"] = _text(pmid_el)
    # Scoped to PubmedData's own ArticleIdList only — a recursive ".//" search
    # would also match ArticleIdList elements nested inside PubmedData/
    # ReferenceList/Reference (each cited reference's own DOI/PMID/PMCID),
    # silently overwriting the article's real identifiers with a reference's.
    for aid in _findall(article_container, "PubmedData/ArticleIdList/ArticleId"):
        idtype = aid.get("IdType", "").lower()
        val = _text(aid)
        if idtype == "doi" and val:
            ids["doi"] = val
        elif idtype == "pmc" and val:
            ids["pmcid"] = val
    # Fallback DOI in ELocationID
    if not ids["doi"]:
        for eloc in _findall(article_container, ".//Article/ELocationID"):
            if eloc.get("EIdType", "").lower() == "doi":
                ids["doi"] = _text(eloc)
                break
    return ids


def _extract_journal(article) -> Dict[str, str]:
    journal = _first(article, ".//Journal")
    pubdate = _first(article, ".//Journal/JournalIssue/PubDate")
    year = _text(_first(pubdate, "Year"))
    if not year:
        medline = _text(_first(pubdate, "MedlineDate"))
        if medline:
            for token in medline.split():
                if token[:4].isdigit():
                    year = token[:4]
                    break
    return {
        "title": _text(_first(journal, "Title")),
        "isoAbbreviation": _text(_first(journal, "ISOAbbreviation")),
        "issn": _text(_first(journal, "ISSN")),
        "volume": _text(_first(article, ".//Journal/JournalIssue/Volume")),
        "issue": _text(_first(article, ".//Journal/JournalIssue/Issue")),
        "pages": _text(_first(article, ".//Pagination/MedlinePgn")),
        "year": year,
        "month": _text(_first(pubdate, "Month")),
        "day": _text(_first(pubdate, "Day")),
    }


def _extract_mesh(article_container) -> List[str]:
    terms: List[str] = []
    for mh in _findall(article_container, ".//MeshHeadingList/MeshHeading/DescriptorName"):
        t = _text(mh)
        if t and t not in terms:
            terms.append(t)
    return terms


def _extract_pubtypes(article) -> List[str]:
    out: List[str] = []
    for pt in _findall(article, ".//PublicationTypeList/PublicationType"):
        t = _text(pt)
        if t and t not in out:
            out.append(t)
    return out


def _extract_grants(article) -> List[Dict[str, str]]:
    grants: List[Dict[str, str]] = []
    for gr in _findall(article, ".//GrantList/Grant"):
        entry = {
            "grantId": _text(_first(gr, "GrantID")),
            "agency": _text(_first(gr, "Agency")),
            "country": _text(_first(gr, "Country")),
        }
        if any(entry.values()) and entry not in grants:
            grants.append(entry)
    return grants


def _extract_keywords(article_container) -> List[str]:
    out: List[str] = []
    for kw in _findall(article_container, ".//KeywordList/Keyword"):
        t = _text(kw)
        if t and t not in out:
            out.append(t)
    return out


def parse_article(pubmed_article) -> Dict[str, Any]:
    """Parse a single <PubmedArticle> element into a normalized dict."""
    article = _first(pubmed_article, ".//Article")
    ids = _extract_ids(pubmed_article)
    journal = _extract_journal(article)
    pmid = ids["pmid"]
    return {
        "pmid": pmid,
        "title": _text(_first(article, "ArticleTitle")),
        "abstract": _extract_abstract(article),
        "authors": _extract_authors(article),
        "journal": journal,
        "doi": ids["doi"],
        "pmcid": ids["pmcid"],
        "meshTerms": _extract_mesh(pubmed_article),
        "publicationTypes": _extract_pubtypes(article),
        "keywords": _extract_keywords(pubmed_article),
        "grants": _extract_grants(article),
        "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "pmcUrl": (
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/{ids['pmcid']}/"
            if ids["pmcid"]
            else ""
        ),
    }


def _book_ids(book_doc, pubmed_book_data) -> Dict[str, str]:
    ids = {"pmid": "", "doi": "", "pmcid": ""}
    pmid_el = _first(book_doc, "PMID")
    if pmid_el is not None:
        ids["pmid"] = _text(pmid_el)
    # A book's identifiers are split across BookDocument/ArticleIdList (holds the
    # NBK bookaccession, sometimes a DOI) and PubmedBookData/ArticleIdList (holds
    # the pubmed id). Scan both, but only these two — not the per-reference
    # ArticleIdLists inside ReferenceList, which carry each citation's own IDs.
    aid_els = _findall(book_doc, "ArticleIdList/ArticleId")
    if pubmed_book_data is not None:
        aid_els = aid_els + _findall(pubmed_book_data, "ArticleIdList/ArticleId")
    for aid in aid_els:
        idtype = aid.get("IdType", "").lower()
        val = _text(aid)
        if idtype == "doi" and val:
            ids["doi"] = val
        elif idtype == "pmc" and val:
            ids["pmcid"] = val
        elif idtype == "pubmed" and val and not ids["pmid"]:
            ids["pmid"] = val
    return ids


def _book_journal(book_doc) -> Dict[str, str]:
    """Map a book's imprint onto the same journal shape articles use, so that
    citation formatters and CSV export treat both record kinds uniformly."""
    book = _first(book_doc, "Book")
    pubdate = _first(book, "PubDate") if book is not None else None
    year = _text(_first(pubdate, "Year")) if pubdate is not None else ""
    if not year:
        cdate = _first(book_doc, "ContributionDate")
        year = _text(_first(cdate, "Year")) if cdate is not None else ""
    return {
        "title": _text(_first(book, "BookTitle")) if book is not None else "",
        "isoAbbreviation": "",
        "issn": "",
        "volume": "",
        "issue": "",
        "pages": "",
        "year": year,
        "month": _text(_first(pubdate, "Month")) if pubdate is not None else "",
        "day": _text(_first(pubdate, "Day")) if pubdate is not None else "",
    }


def _extract_book_authors(book_doc) -> List[Dict[str, Any]]:
    """Chapter authors, not the book's editors.

    A GeneReviews chapter carries both a BookDocument/AuthorList (Type=authors)
    and, under Book, an editors AuthorList — six standing GeneReviews editors.
    A descendant search would concatenate the two and bury the real authors, so
    pick the authors list and use editors only when there is no author list.
    """
    lists = _findall(book_doc, ".//AuthorList")
    chosen = next((al for al in lists if al.get("Type", "authors") == "authors"), None)
    if chosen is None:
        chosen = lists[0] if lists else None
    if chosen is None:
        return []
    out: List[Dict[str, Any]] = []
    for auth in _findall(chosen, "Author"):
        rec = _author_from_el(auth)
        if rec:
            out.append(rec)
    return out


def _book_pubtypes(book_doc) -> List[str]:
    out: List[str] = []
    for pt in _findall(book_doc, "PublicationType"):
        t = _text(pt)
        if t and t not in out:
            out.append(t)
    return out


def parse_book_article(pubmed_book_article) -> Dict[str, Any]:
    """Parse a <PubmedBookArticle> (StatPearls, GeneReviews, NCBI Bookshelf).

    These carry their content under BookDocument rather than Article, so the
    Article-centric parse_article yields a blank record for them. StatPearls in
    particular is one of the most heavily indexed sources in PubMed, so a topic
    search routinely includes book entries; returning them blank would drop real
    hits (and feed empty rows to CSV and '..' to the citation formatter)."""
    book_doc = _first(pubmed_book_article, ".//BookDocument")
    if book_doc is None:
        return {}
    ids = _book_ids(book_doc, _first(pubmed_book_article, ".//PubmedBookData"))
    pmid = ids["pmid"]
    # The chapter title lives in ArticleTitle; fall back to the volume's BookTitle
    # for entries that are the whole book rather than a chapter.
    title = _text(_first(book_doc, "ArticleTitle"))
    if not title:
        book = _first(book_doc, "Book")
        title = _text(_first(book, "BookTitle")) if book is not None else ""
    journal = _book_journal(book_doc)
    # _extract_abstract / _extract_authors use descendant (.//) paths, so they
    # work unchanged when handed the BookDocument.
    return {
        "pmid": pmid,
        "title": title,
        "abstract": _extract_abstract(book_doc),
        "authors": _extract_book_authors(book_doc),
        "journal": journal,
        "doi": ids["doi"],
        "pmcid": ids["pmcid"],
        "meshTerms": _extract_mesh(book_doc),
        "publicationTypes": _book_pubtypes(book_doc),
        "keywords": _extract_keywords(book_doc),
        "grants": [],
        "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "pmcUrl": (
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/{ids['pmcid']}/"
            if ids["pmcid"]
            else ""
        ),
    }


def parse_efetch_xml(xml_text: str) -> List[Dict[str, Any]]:
    """Parse a full PubmedArticleSet EFetch response into a list of records."""
    root = parse_xml(xml_text)
    records: List[Dict[str, Any]] = []
    for art in root.iter("PubmedArticle"):
        try:
            records.append(parse_article(art))
        except Exception:
            continue
    # Book articles nest their content differently and need a dedicated parser.
    for art in root.iter("PubmedBookArticle"):
        try:
            rec = parse_book_article(art)
            if rec:
                records.append(rec)
        except Exception:
            continue
    return records


def author_string(authors: List[Dict[str, Any]], max_authors: int = 0) -> str:
    """Render authors as 'Last AB; Last CD; ...'. max_authors=0 means all."""
    names = [a.get("name", "") for a in authors if a.get("name")]
    if max_authors and len(names) > max_authors:
        names = names[:max_authors] + ["et al."]
    return "; ".join(names)
