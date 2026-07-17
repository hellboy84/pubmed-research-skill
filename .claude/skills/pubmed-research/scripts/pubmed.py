#!/usr/bin/env python3
"""pubmed.py — command-line entry point for the pubmed-research skill.

Replicates the ten tools of cyanheads/pubmed-mcp-server as subcommands.
Every subcommand prints JSON to stdout (progress/diagnostics go to stderr),
so output can be piped into other scripts (e.g. to_csv.py).

Subcommands
    search        Search PubMed (ESearch), optionally fetch brief summaries.
    fetch         Fetch full metadata for PMIDs (EFetch).
    fulltext      Fetch full text via PMC EFetch -> Europe PMC -> Unpaywall.
    epmc-search   Search Europe PMC (preprints, patents, Agricola, etc.).
    convert-ids   Convert between DOI / PMID / PMCID (PMC ID Converter).
    related       Find related / cited-by / references (ELink -> EPMC -> OpenAlex).
    cite          Format citations (vancouver by default; also apa/mla/bibtex/ris).
    lookup-cite   Look up PMIDs from partial citations (ECitMatch).
    mesh          Search the MeSH controlled vocabulary.
    spell         Spell-check a query (ESpell).

Run `python pubmed.py <subcommand> --help` for options.
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import quote_plus
from typing import Any, Dict, List

import requests

from eutils_common import (
    eutils_request,
    external_request,
    load_config,
    has_api_key,
    parse_xml,
    eprint,
    chunked,
    localname,
    normalize_ws,
    fetch_document,
    have_pdf_support,
    redact,
    EUROPEPMC_BASE,
    UNPAYWALL_BASE,
    PMC_IDCONV_URL,
)
from pubmed_parse import parse_efetch_xml, author_string
import citations as cite_mod
import openalex


def _out(obj: Any) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


# ─── search (ESearch + optional ESummary/EFetch) ─────────────────────────────
def _build_query(args) -> str:
    parts: List[str] = []
    if args.query:
        parts.append(f"({args.query})")
    if args.author:
        parts.append(f'"{args.author}"[Author]')
    if args.journal:
        parts.append(f'"{args.journal}"[Journal]')
    # MeSH terms narrow: every one must match, so they are AND'd.
    for mesh in args.mesh or []:
        parts.append(f'"{mesh}"[MeSH Terms]')
    # Publication types widen: an article carries only a few, so AND-ing two of
    # them (e.g. Randomized Controlled Trial + Meta-Analysis) matches almost
    # nothing. OR them into a single clause instead.
    pubtypes = args.pubtype or []
    if pubtypes:
        clause = " OR ".join(f'"{pt}"[Publication Type]' for pt in pubtypes)
        parts.append(f"({clause})" if len(pubtypes) > 1 else clause)
    if args.language:
        parts.append(f"{args.language}[Language]")
    if args.species == "humans":
        parts.append("humans[MeSH Terms]")
    elif args.species == "animals":
        # Not animals[MeSH Terms]: MeSH terms explode over their subtree and
        # Humans sits inside Animals, so that clause matches every human study
        # too — 1,216 of the 1,285 it returned for tirzepatide, i.e. 95% of a
        # filter asking for animal work. Subtracting humans is what PubMed's own
        # sidebar does, which is why it calls the filter 'Other Animals'.
        # (animals[Filter] is not a way out — unlike humans[Filter] no such tag
        # exists, so it survives translation verbatim and matches nothing.)
        parts.append("(animals[mh] NOT humans[mh])")
    if args.free_full_text:
        parts.append('"free full text"[Filter]')
    if args.has_abstract:
        parts.append("hasabstract")
    # PubMed accepts open-ended ranges through sentinel bounds, so a lone
    # --min-date (or --max-date) still narrows the search. Requiring both would
    # silently drop the filter and hand back the unfiltered count as if it had
    # applied.
    if args.min_date or args.max_date:
        field = args.date_type or "pdat"
        lo = args.min_date or "1000"
        hi = args.max_date or "3000"
        parts.append(f"({lo}:{hi}[{field}])")
    term = " AND ".join(parts) if parts else (args.query or "")

    # The animal-exclusion hedge. It has to be NOT'd onto the finished query
    # rather than joined in as another AND clause, because PubMed reads
    # `A AND NOT B` as `A AND B` — it drops the NOT, without an error, and hands
    # back exactly the set that was meant to be excluded. Wrapping the chain and
    # appending a bare NOT is the only form that survives translation; confirm it
    # in queryTranslation, which shows the hedge in full when it parsed.
    if getattr(args, "exclude_animals", False) and term.strip():
        term = f"({term}) NOT (animals[mh] NOT humans[mh])"
    return term


def cmd_search(args) -> None:
    term = _build_query(args)
    if not term.strip():
        _out({"error": "Empty query. Provide --query or at least one filter."})
        return
    params = {
        "db": "pubmed",
        "term": term,
        "retmax": args.limit,
        "retstart": args.offset,
        "retmode": "json",
    }
    # ESearch silently ignores an unrecognized sort schema and returns the
    # default order, so these must be NCBI's exact tokens — 'first_author' and
    # 'journal' are not among them.
    sort_map = {
        "relevance": "relevance",
        "pub_date": "pub_date",
        "author": "Author",
        "journal": "JournalName",
    }
    if args.sort and args.sort in sort_map:
        params["sort"] = sort_map[args.sort]

    resp = eutils_request("esearch.fcgi", params)
    # ESearch refuses a request with HTTP 200 and an ERROR string in the body,
    # and it embeds raw newlines in that string. Strict parsing rejects the body,
    # and because requests raises its JSONDecodeError as a RequestException, the
    # top-level handler then labels a paging-limit refusal 'network_error' — the
    # one diagnosis that invites a pointless retry. Parse leniently, then hand
    # back what NCBI actually said.
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001 - requests wraps JSON errors as RequestException
        payload = json.loads(resp.text, strict=False)
    data = payload.get("esearchresult", {})
    if data.get("ERROR"):
        _out({"error": "esearch_error", "command": "search", "query": term,
              "message": normalize_ws(str(data["ERROR"]))})
        return
    pmids = data.get("idlist", [])
    total = int(data.get("count", "0") or 0)

    # PubMed names the phrases it could not match rather than failing on them.
    # Dropping that turns a diagnosable zero into a mystery: an invented
    # descriptor and a genuinely empty literature both return a valid-looking
    # zero, and `querytranslation` cannot separate them — it echoes a bogus MeSH
    # term exactly as it echoes a real one.
    wl = data.get("warninglist") or {}
    el = data.get("errorlist") or {}
    not_found = list(wl.get("quotedphrasesnotfound") or []) + list(el.get("phrasesnotfound") or [])

    result: Dict[str, Any] = {
        "query": term,
        # What PubMed actually ran, which is not always what we sent: a wildcard
        # inside a proximity phrase drops the `:~N`, and an unrecognized tag is
        # left verbatim to match nothing. Neither is an error, so `query` alone
        # is no evidence of the executed search. Anything reporting the search
        # strategy has to quote this instead.
        "queryTranslation": data.get("querytranslation", ""),
        "totalCount": total,
        "returned": len(pmids),
        "offset": args.offset,
        "pmids": pmids,
        "searchUrl": f"https://pubmed.ncbi.nlm.nih.gov/?term={quote_plus(term)}",
    }
    if not_found:
        result["phrasesNotFound"] = not_found

    notices: List[str] = []

    # ESearch serves at most ~9,999 records per query and truncates in silence:
    # ask for 20,000 and 9,999 come back looking like the whole answer. --offset
    # is no way out either — retstart itself refuses past 9998 — so the only
    # honest advice is to slice the query up.
    if len(pmids) < min(args.limit, total):
        notices.append(
            f"Asked for {args.limit}; ESearch returned {len(pmids)} of {total:,} "
            "matches. One query cannot reach past ~9,999 records, and --offset "
            "cannot either (retstart refuses past 9998). To cover the rest, split "
            "the search into narrower slices — successive --min-date/--max-date "
            "windows work well — and combine them. Do not present this page as the "
            "complete result set."
        )

    # --species is a MeSH filter wearing a plain-English name, and it is the one
    # flag that quietly undoes a recall-first query: an OR'd text-word clause
    # widens the search, then this ANDs a clause only MEDLINE-indexed records can
    # satisfy. Un-indexed articles — the newest ones — are dropped whatever their
    # subject, so the count means 'indexed <species> studies', not '<species>
    # studies'. This is PubMed's own filter, not a quirk of this skill —
    # humans[Filter] translates to the identical humans[MeSH Terms] — but the cost
    # is the caller's either way. Measured on tirzepatide: 2,258 -> 1,225, and 961
    # of the 1,033 lost were un-indexed rather than non-human.
    if args.species == "humans" and not args.exclude_animals:
        notices.append(
            "--species humans was AND'd as humans[MeSH Terms] — the same clause "
            "PubMed's own Species filter uses. Only MEDLINE-indexed records carry "
            "MeSH, so articles awaiting indexing (disproportionately the newest) "
            "cannot match it whatever they are about: this count is 'indexed human "
            "studies', not 'human studies', and it cancels the recall of any "
            "text-word clause OR'd into the query. On a recent topic the cut is "
            "routinely 40%+. If the goal is to drop animal work rather than to "
            "require the Humans tag, use --exclude-animals instead: it removes "
            "animal-only studies and keeps un-indexed records. Measured on "
            "tirzepatide: 2,249 -> 1,216 with this flag, 2,180 with --exclude-animals."
        )
    elif args.species == "animals":
        notices.append(
            "--species animals was AND'd as (animals[mh] NOT humans[mh]) — PubMed's "
            "'Other Animals', not a bare animals[mh], which would explode over the "
            "MeSH tree and match every human study as well. Only MEDLINE-indexed "
            "records carry MeSH, so un-indexed articles are excluded whatever they "
            "studied. Unlike the humans case there is no hedge for this — naming an "
            "animal study requires the index — so this count is 'indexed animal "
            "studies', and report it as such."
        )

    if args.exclude_animals and args.species == "humans":
        notices.append(
            "--exclude-animals was combined with --species humans and did nothing: "
            "every record --species humans keeps carries humans[mh], and the hedge "
            "only removes records that lack it. The un-indexed articles the hedge "
            "exists to preserve were already gone before it ran. Drop --species "
            "humans if you wanted the hedge's recall."
        )
    elif args.exclude_animals and args.species == "animals":
        # AND (X) ... NOT (X) — the same clause required and forbidden. Zero is
        # arithmetic here, not evidence, and a zero from a contradiction reads
        # exactly like a zero from an empty literature.
        notices.append(
            "--exclude-animals contradicts --species animals: one requires "
            "(animals[mh] NOT humans[mh]) and the other excludes that same clause, "
            "so this query matches nothing by construction. A zero here says nothing "
            "about the literature — do not report it as a finding. Pick one flag."
        )

    if notices:
        result["notice"] = " ".join(notices)

    if total == 0 and not_found:
        result["guidance"] = (
            "Zero hits because PubMed matched nothing for: " + ", ".join(not_found)
            + ". Those terms do not exist in the index as written, so this result is "
            "not evidence that the literature is empty — do not report it as such. "
            "Resolve them with `mesh` before relaxing any filter. `spell` will not "
            "help here: it checks spelling against the index, not MeSH validity, so "
            "on a well-spelled non-descriptor it returns a confident correction that "
            "is also not a descriptor."
        )
    elif total == 0:
        result["guidance"] = (
            "No results. Try spell-checking (spell), removing filters, or "
            "broadening the date range."
        )
    elif not_found:
        # The quiet one: under OR, an unmatched clause costs no hits, so the count
        # stays healthy and only names the rest of the query. Without a word here
        # the results look like they answer the search that was asked for.
        result["guidance"] = (
            "These hits came back despite PubMed matching nothing for: "
            + ", ".join(not_found)
            + ". Those clauses contributed no records, so the count reflects the rest "
            "of the query, not the search as written. Resolve the terms with `mesh` "
            "and re-run before reporting these results or the strategy behind them."
        )
    if args.summaries and pmids:
        result["articles"] = _fetch_records(pmids)
    _out(result)


# ─── fetch (EFetch full metadata) ────────────────────────────────────────────
def _fetch_records(
    pmids: List[str],
    *,
    include_grants: bool = False,
    include_mesh: bool = True,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for batch in chunked(pmids, 200):
        method = "POST" if len(batch) >= 100 else "GET"
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
            "rettype": "abstract",
        }
        resp = eutils_request("efetch.fcgi", params, method=method)
        records.extend(parse_efetch_xml(resp.text))
    # Grants are parsed unconditionally but are noise for most callers, so every
    # entry point gets the same default shape unless it opts in.
    for rec in records:
        if not include_grants:
            rec.pop("grants", None)
        if not include_mesh:
            rec.pop("meshTerms", None)
    return records


def _missing_pmids(requested: List[str], records: List[Dict[str, Any]]) -> List[str]:
    """PMIDs that were asked for but did not come back.

    EFetch answers an unknown, withdrawn or merged PMID with HTTP 200 and simply
    omits the record — no error, no placeholder, nothing that distinguishes it
    from an ID that was never asked for. Ask for 50 and `count: 47` is the only
    trace that three vanished, and nothing says which. Diff the two lists.
    """
    got = {str(r.get("pmid", "")) for r in records}
    return [p for p in dict.fromkeys(requested) if p not in got]


def _note_missing(result: Dict[str, Any], requested: List[str],
                  records: List[Dict[str, Any]], *, verb: str) -> None:
    missing = _missing_pmids(requested, records)
    if not missing:
        return
    result["notFound"] = missing
    result["notice"] = (
        f"{len(requested)} PMIDs were requested but only {len(records)} came back. "
        f"PubMed returned no record for: " + ", ".join(missing) + ". EFetch omits "
        "unknown, withdrawn and merged PMIDs silently, so this is a fact about the "
        f"IDs, not about the articles — do not {verb} the rest as if the list were "
        "complete, and do not report the missing ones as retracted or nonexistent "
        "without checking. Verify each with `search <pmid>[uid]`; a merged record "
        "answers under its surviving PMID."
    )


def cmd_fetch(args) -> None:
    pmids = _clean_ids(args.pmids)
    if not pmids:
        _out({"error": "No PMIDs provided."})
        return
    records = _fetch_records(
        pmids, include_grants=args.include_grants, include_mesh=not args.no_mesh
    )
    result: Dict[str, Any] = {"count": len(records), "articles": records}
    _note_missing(result, pmids, records, verb="present")
    _out(result)


# ─── convert-ids (PMC ID Converter) ──────────────────────────────────────────
def _detect_id_type(token: str) -> str:
    tok = token.strip()
    if tok.upper().startswith("PMC"):
        return "pmcid"
    if tok.startswith("10."):
        return "doi"
    if tok.isdigit():
        return "pmid"
    return "unknown"


def _idconv_request(ids: List[str], idtype: str) -> List[Dict[str, Any]]:
    cfg = load_config()
    params = {
        "ids": ",".join(ids),
        "idtype": idtype,
        "format": "json",
        "tool": cfg["NCBI_TOOL"],
    }
    if cfg.get("NCBI_EMAIL"):
        params["email"] = cfg["NCBI_EMAIL"]
    resp = external_request(PMC_IDCONV_URL, params)
    return resp.json().get("records", [])


def cmd_convert_ids(args) -> None:
    ids = _clean_ids(args.ids)
    if not ids:
        _out({"error": "No IDs provided."})
        return

    # The converter rejects a batch whose IDs are not all one type, so group by
    # detected type and issue one request per group (each capped at the API's 50).
    if args.idtype != "auto":
        groups: Dict[str, List[str]] = {args.idtype: ids}
    else:
        groups = {}
        for tok in ids:
            groups.setdefault(_detect_id_type(tok), []).append(tok)

    records: List[Dict[str, Any]] = []
    unknown = groups.pop("unknown", [])
    for idtype, group in groups.items():
        for batch in chunked(group, 50):
            records.extend(_idconv_request(batch, idtype))

    result: Dict[str, Any] = {"count": len(records), "records": records}
    if unknown:
        result["unrecognized"] = unknown
        result["guidance"] = (
            "These IDs matched none of pmid (digits), pmcid (PMC-prefixed), or "
            "doi (10.-prefixed). Pass --idtype to force a type."
        )
    _out(result)


# ─── related (ELink -> Europe PMC -> OpenAlex) ───────────────────────────────
def _elink_related(pmid: str, linkname: str) -> List[str]:
    params = {
        "dbfrom": "pubmed",
        "db": "pubmed",
        "id": pmid,
        "linkname": linkname,
        "retmode": "json",
        "cmd": "neighbor",
    }
    resp = eutils_request("elink.fcgi", params)
    out: List[str] = []
    for ls in resp.json().get("linksets", []):
        for db in ls.get("linksetdbs", []):
            if db.get("linkname") == linkname:
                out.extend(db.get("links", []))
    # `pubmed_pubmed` always echoes the source PMID as its own first neighbor, and
    # for an unknown PMID that self-link is the *only* entry. Strip it here so an
    # empty result means "no neighbors" to every caller downstream.
    return [p for p in dict.fromkeys(out) if p != pmid]


def _epmc_supports(rel_type: str) -> bool:
    """Europe PMC has citation and reference indexes but no similarity endpoint."""
    return rel_type in ("cited_by", "references")


def _epmc_related(pmid: str, rel_type: str, want: int) -> tuple:
    """Europe PMC provider. Returns (pmids, totalCount)."""
    path, list_key, item_key = {
        "cited_by": ("citations", "citationList", "citation"),
        "references": ("references", "referenceList", "reference"),
    }[rel_type]
    resp = external_request(
        f"{EUROPEPMC_BASE}/MED/{pmid}/{path}",
        {"format": "json", "pageSize": max(1, min(want, 1000)), "page": 1},
    )
    data = resp.json()
    items = data.get(list_key, {}).get(item_key, []) or []
    # Only MED-sourced entries carry a PMID; EPMC-only records have none. The
    # authoritative total is EPMC's hitCount, which counts those dropped rows too.
    pmids = [str(it["id"]) for it in items if it.get("source") == "MED" and it.get("id")]
    return pmids, int(data.get("hitCount", len(pmids)) or 0)


def _esummary_brief(pmids: List[str]) -> List[Dict[str, Any]]:
    """Lightweight enrichment: one ESummary call instead of a full EFetch."""
    out: List[Dict[str, Any]] = []
    for batch in chunked(pmids, 200):
        method = "POST" if len(batch) >= 100 else "GET"
        resp = eutils_request(
            "esummary.fcgi", {"db": "pubmed", "id": ",".join(batch), "retmode": "json"},
            method=method,
        )
        result = resp.json().get("result", {})
        for uid in batch:
            item = result.get(uid) or {}
            if not item or item.get("error"):
                continue
            names = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
            authors = ", ".join(names[:3]) + (", et al." if len(names) > 3 else "")
            # sortpubdate ('2020/03/17 00:00') normalizes better than pubdate ('2020 Mar 17')
            sort_date = (item.get("sortpubdate") or "").split(" ")[0].replace("/", "-")
            out.append({
                "pmid": uid,
                "title": item.get("title", ""),
                "authors": authors,
                "source": item.get("source", ""),
                "pubDate": sort_date or item.get("pubdate", ""),
            })
    return out


def _source_article_title(pmid: str):
    """Disambiguate 'invalid PMID' from 'valid PMID with no neighbors'.

    Returns the title, '' when PubMed has no such record, or None when the check
    itself failed (in which case the caller must not conclude anything).
    """
    try:
        resp = eutils_request("esummary.fcgi", {"db": "pubmed", "id": pmid, "retmode": "json"})
        item = resp.json().get("result", {}).get(pmid) or {}
        if item.get("error"):
            return ""
        return item.get("title", "") or ""
    except Exception:  # noqa: BLE001
        return None


def cmd_related(args) -> None:
    pmid = args.pmid.strip()
    rel = args.type
    linkname = {
        "similar": "pubmed_pubmed",
        "cited_by": "pubmed_pubmed_citedin",
        "references": "pubmed_pubmed_refs",
    }[rel]
    need = args.offset + args.limit

    # ── Provider chain: NCBI ELink -> Europe PMC -> OpenAlex ────────────────
    # First success wins; results are never merged across providers.
    provider = None  # (pmids, totalCount, source)
    provider_error = None
    notice = ""

    try:
        elink_pmids = _elink_related(pmid, linkname)
        provider = (elink_pmids, len(elink_pmids), "ncbi")
    except Exception as exc:  # noqa: BLE001
        provider_error = exc
        eprint(f"[related] ELink failed ({exc}); trying fallback providers.")

    # Europe PMC only covers cited_by/references. An empty EPMC result is not
    # "served" — fall through to OpenAlex rather than report zero.
    if provider is None and _epmc_supports(rel):
        try:
            epmc_pmids, epmc_total = _epmc_related(pmid, rel, need)
            if epmc_pmids:
                provider = (epmc_pmids, epmc_total, "europepmc")
            provider_error = None
        except Exception as exc:  # noqa: BLE001
            provider_error = exc
            eprint(f"[related] Europe PMC fallback failed ({exc}); trying OpenAlex.")

    # OpenAlex is the last resort, and the only fallback that serves `similar`.
    if provider is None:
        try:
            oa_pmids, oa_total = openalex.related(pmid, rel, max(need, 1))
            provider = (oa_pmids, oa_total, "openalex")
            provider_error = None
        except Exception as exc:  # noqa: BLE001
            provider_error = exc
            eprint(f"[related] OpenAlex fallback failed ({exc}).")

    if provider is None:
        _out({
            "sourcePmid": pmid, "type": rel, "source": "none", "totalCount": 0,
            "offset": args.offset, "count": 0, "pmids": [],
            "notice": f"All providers failed (NCBI, Europe PMC, OpenAlex). "
                      f"Last error: {redact(provider_error)}. Retry after a brief delay.",
        })
        return

    pmids, total, source = provider

    # ── NCBI answered, but with nothing ─────────────────────────────────────
    # ELink returns an empty set both for an unknown PMID and for a valid PMID
    # with no neighbors. One ESummary tells them apart.
    if source == "ncbi" and not pmids:
        title = _source_article_title(pmid)
        if title == "":
            _out({
                "sourcePmid": pmid, "type": rel, "source": "ncbi", "totalCount": 0,
                "offset": args.offset, "count": 0, "pmids": [],
                "notice": f"Source PMID {pmid} not found in PubMed. Verify the ID with "
                          f"`fetch` or `search`.",
            })
            return
        # Both of NCBI's citation indexes are built from PMC-deposited reference
        # lists, so a valid article outside PMC comes back empty even when the
        # data exists elsewhere. Europe PMC and OpenAlex index the wider corpus.
        # (The MCP server retries `references` only; retrying `cited_by` too
        # recovers citations that ELink's citedin simply does not carry.)
        # `similar` needs no retry — ELink's neighbor set is never empty for a
        # real article.
        if rel in ("references", "cited_by") and title:
            label = "reference list" if rel == "references" else "citing articles"
            for attempt in (
                lambda: _epmc_related(pmid, rel, need) + ("europepmc",),
                lambda: openalex.related(pmid, rel, max(need, 1)) + ("openalex",),
            ):
                try:
                    got, got_total, got_source = attempt()
                except Exception as exc:  # noqa: BLE001
                    eprint(f"[related] {rel} fallback failed ({exc}).")
                    continue
                if got:
                    pmids, total, source = got, got_total, got_source
                    notice = (f"NCBI has no PMC-indexed {label} for PMID {pmid} — "
                              f"{rel} served by {source}.")
                    break
            else:
                notice = (f"No {label} available for PMID {pmid} via NCBI, "
                          f"Europe PMC, or OpenAlex.")
    elif source != "ncbi":
        notice = f"NCBI was unavailable — {rel} served by {source}."
        if source == "openalex" and rel == "similar":
            notice += (" OpenAlex related_works is its own similarity measure, "
                       "not PubMed's neighbor algorithm.")

    pmids = [p for p in dict.fromkeys(pmids) if p != pmid]
    window = pmids[args.offset : args.offset + args.limit] if args.limit else pmids[args.offset :]

    result: Dict[str, Any] = {
        "sourcePmid": pmid,
        "type": rel,
        "source": source,
        "totalCount": max(total, len(pmids)),
        "offset": args.offset,
        "count": len(window),
        "pmids": window,
    }
    if notice:
        result["notice"] = notice
    if window and not args.pmids_only:
        # Bare PMIDs force the caller into a second round trip, so enrich by
        # default: ESummary for titles, or a full EFetch when asked.
        result["articles"] = _fetch_records(window) if args.fetch else _esummary_brief(window)
    _out(result)


# ─── epmc-search (Europe PMC) ────────────────────────────────────────────────
def cmd_epmc_search(args) -> None:
    query = args.query
    sources = args.sources or ["MED", "PMC", "PPR"]
    src_filter = " OR ".join(f"SRC:{s}" for s in sources)
    full_query = f"({query}) AND ({src_filter})"
    params = {
        "query": full_query,
        "format": "json",
        "pageSize": min(args.limit, 100),  # EPMC caps pageSize at 100
        "resultType": args.result_type,
        "cursorMark": args.cursor or "*",
    }
    if args.sort:
        params["sort"] = args.sort
    resp = external_request(f"{EUROPEPMC_BASE}/search", params)
    data = resp.json()
    # A request Europe PMC cannot parse — an unrecognized `sort` token is the
    # easy way in — comes back as HTTP 200 carrying nothing but `version`: no
    # error, no hitCount, no resultList. Defaulting hitCount to 0 there dresses a
    # rejected request as "no such literature", which is the one answer nobody
    # thinks to question.
    if "hitCount" not in data or "resultList" not in data:
        _out({
            "error": "epmc_rejected_request",
            "command": "epmc-search",
            "query": full_query,
            "sort": args.sort or "",
            "message": "Europe PMC returned no result set at all, meaning it rejected "
                       "the request rather than finding nothing. The usual cause is an "
                       "unrecognized --sort token — valid forms look like "
                       "'P_PDATE_D desc', 'CITED desc', 'PUB_YEAR desc'. Re-run without "
                       "--sort to confirm before concluding anything about the "
                       "literature.",
        })
        return
    hits = data.get("resultList", {}).get("result", [])

    def _journal_title(h: Dict[str, Any]) -> str:
        # The two result types disagree on shape: `lite` returns a flat
        # `journalTitle`, `core` nests it under journalInfo.journal.title and has
        # no flat field at all. Reading only the flat one leaves every `core`
        # result — the default — with a blank journal.
        info = h.get("journalInfo") or {}
        nested = (info.get("journal") or {}).get("title", "")
        return nested or h.get("journalTitle", "")

    def _row(h: Dict[str, Any]) -> Dict[str, Any]:
        row = {
            "id": h.get("id"),
            "source": h.get("source"),
            "pmid": h.get("pmid", ""),
            "pmcid": h.get("pmcid", ""),
            "doi": h.get("doi", ""),
            "title": h.get("title", ""),
            "authorString": h.get("authorString", ""),
            "journal": _journal_title(h),
            "year": h.get("pubYear", ""),
            "isOpenAccess": h.get("isOpenAccess", "N"),
        }
        # resultType=core is the only one that carries an abstract; surface it
        # rather than paying for the larger payload and discarding it.
        if args.result_type == "core":
            row["abstract"] = h.get("abstractText", "")
            row["citedByCount"] = h.get("citedByCount", 0)
        return row

    out: Dict[str, Any] = {
        "query": full_query,
        "hitCount": data.get("hitCount", 0),
        "nextCursorMark": data.get("nextCursorMark", ""),
        "returned": len(hits),
        "results": [_row(h) for h in hits],
    }
    # EPMC serves at most 100 per page, so a larger --limit silently comes back
    # short. Unlike ESearch's ~9,999 ceiling this one is pageable, so say so.
    if args.limit > 100:
        out["notice"] = (
            f"--limit {args.limit} was requested but Europe PMC caps a page at 100. "
            f"{len(hits)} came back of {data.get('hitCount', 0):,} matches — page on "
            "by passing the returned nextCursorMark as --cursor rather than treating "
            "this page as the full set."
        )
    _out(out)


# ─── fulltext (PMC EFetch -> Europe PMC -> Unpaywall) ────────────────────────
def _normalize_pmcid(value: str) -> str:
    v = value.strip()
    if not v:
        return ""
    return v if v.upper().startswith("PMC") else f"PMC{v}"


def _resolve_to_pmcid(identifier: str) -> str:
    """Resolve a PMID or DOI to a PMCID via the PMC ID Converter."""
    idtype = _detect_id_type(identifier)
    if idtype == "pmcid":
        return _normalize_pmcid(identifier)
    if idtype == "unknown":
        return ""
    try:
        for rec in _idconv_request([identifier], idtype):
            if rec.get("pmcid"):
                return rec["pmcid"]
    except Exception:  # noqa: BLE001
        pass
    return ""


# ─── JATS parsing (shared by the PMC and Europe PMC stages) ──────────────────
def _find_local(root, name: str):
    for el in root.iter():
        if localname(el) == name:
            return el
    return None


def _sec_to_dict(sec) -> Dict[str, str]:
    title = ""
    texts: List[str] = []
    for child in sec:
        if localname(child) == "title" and not title:
            title = normalize_ws(" ".join(child.itertext()))
            continue
        texts.append(" ".join(child.itertext()))
    return {"title": title, "text": normalize_ws(" ".join(texts))}


def _parse_jats(xml_text: str) -> tuple:
    """Return (sections, references) from a JATS document."""
    root = parse_xml(xml_text)
    body = _find_local(root, "body")
    sections: List[Dict[str, str]] = []
    if body is not None:
        top = [el for el in body if localname(el) == "sec"]
        if top:
            # Paragraphs sitting outside any <sec> (common for a lead-in).
            loose = normalize_ws(
                " ".join(" ".join(el.itertext()) for el in body if localname(el) == "p")
            )
            if loose:
                sections.append({"title": "", "text": loose})
            sections.extend(_sec_to_dict(s) for s in top)
        else:
            flat = normalize_ws(" ".join(body.itertext()))
            if flat:
                sections.append({"title": "", "text": flat})
    sections = [s for s in sections if s["text"] or s["title"]]

    references: List[str] = []
    ref_list = _find_local(root, "ref-list")
    if ref_list is not None:
        for ref in ref_list:
            if localname(ref) != "ref":
                continue
            text = normalize_ws(" ".join(ref.itertext()))
            if text:
                references.append(text)
    return sections, references


def _sections_to_text(sections: List[Dict[str, str]]) -> str:
    blocks = []
    for s in sections:
        blocks.append(f"{s['title']}\n{s['text']}".strip() if s["title"] else s["text"])
    return "\n\n".join(b for b in blocks if b).strip()


def _apply_section_filters(sections, wanted, max_sections):
    if wanted:
        low = [w.lower() for w in wanted]
        sections = [s for s in sections if any(w in s["title"].lower() for w in low)]
    if max_sections:
        sections = sections[:max_sections]
    return sections


# ─── Stage 1: PMC EFetch ─────────────────────────────────────────────────────
def _pmc_efetch_fulltext(pmcid: str) -> Dict[str, Any]:
    numeric = pmcid.replace("PMC", "")
    resp = eutils_request("efetch.fcgi", {"db": "pmc", "id": numeric, "retmode": "xml"})
    if "<body" not in resp.text:
        return {}
    sections, references = _parse_jats(resp.text)
    if not sections:
        return {}
    return {
        "source": "pmc",
        "contentFormat": "jats-text",
        "pmcid": pmcid,
        "sourceUrl": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
        "sections": sections,
        "references": references,
    }


# ─── Stage 2: Europe PMC fullTextXML ─────────────────────────────────────────
def _epmc_fulltext(pmcid: str = "", doi: str = "") -> Dict[str, Any]:
    if not pmcid and doi:
        try:
            r = external_request(
                f"{EUROPEPMC_BASE}/search",
                {"query": f'DOI:"{doi}"', "format": "json", "resultType": "lite", "pageSize": 1},
            )
            hits = r.json().get("resultList", {}).get("result", [])
            if hits:
                pmcid = hits[0].get("pmcid", "") or ""
        except Exception:  # noqa: BLE001
            return {}
    pmcid = _normalize_pmcid(pmcid)
    if not pmcid:
        return {}

    # EPMC's full-text route is /{PMCID}/fullTextXML — the PMC prefix is required
    # and there is no {source} path segment. /PMC/<digits>/... and /MED/<digits>/...
    # both 404.
    url = f"{EUROPEPMC_BASE}/{pmcid}/fullTextXML"
    try:
        r = external_request(url)
    except Exception:  # noqa: BLE001 - no OA full text for this record
        return {}
    if "<body" not in r.text:
        return {}
    sections, references = _parse_jats(r.text)
    if not sections:
        return {}
    return {
        "source": "europepmc",
        "contentFormat": "jats-text",
        "pmcid": pmcid,
        "sourceUrl": url,
        "sections": sections,
        "references": references,
    }


# ─── Stage 3: Unpaywall ──────────────────────────────────────────────────────
def _unpaywall_fulltext(doi: str) -> Dict[str, Any]:
    email = load_config().get("UNPAYWALL_EMAIL")
    if not email:
        return {}
    try:
        data = external_request(f"{UNPAYWALL_BASE}/{doi}", {"email": email}).json()
    except Exception:  # noqa: BLE001
        return {}
    loc = data.get("best_oa_location") or {}
    pdf_url = loc.get("url_for_pdf") or ""
    landing = loc.get("url") or ""
    if not (pdf_url or landing):
        return {}

    rec: Dict[str, Any] = {
        "source": "unpaywall",
        "contentFormat": "url-only",
        "doi": doi,
        "isOA": data.get("is_oa", False),
        "pdfUrl": pdf_url,
        "landingUrl": landing,
        "license": loc.get("license") or "",
        "sourceUrl": pdf_url or landing,
        "fullText": "",
    }
    # Unpaywall reports a location, not text. Fetch it and extract.
    for candidate in [u for u in (pdf_url, landing) if u]:
        text, fmt = fetch_document(candidate)
        if text:
            rec["fullText"] = text
            rec["contentFormat"] = fmt
            rec["sourceUrl"] = candidate
            break
    if not rec["fullText"]:
        # Unpaywall says a copy is open access; that does not mean the host will
        # serve it to a script. Say which of the two happened, or the caller is
        # left with an empty fullText and no explanation.
        if pdf_url and not have_pdf_support():
            rec["hint"] = "Install pypdf (pip install -r requirements.txt) to extract text from OA PDFs."
        else:
            rec["hint"] = (
                "The OA location could not be extracted — the publisher likely refused the "
                "request (403), or the PDF has no text layer. Open pdfUrl/landingUrl directly."
            )
    return rec


def _fulltext_one(identifier: str, kind: str, args) -> Dict[str, Any]:
    pmcid = ""
    doi = ""
    known = None  # True = PubMed has the record, False = it does not, None = unchecked
    if kind == "pmcid":
        pmcid = _normalize_pmcid(identifier)
    elif kind == "pmid":
        pmcid = _resolve_to_pmcid(identifier)
        recs = _fetch_records([identifier])
        # EFetch returning no record for a well-formed PMID is PubMed saying it
        # has no such article, and that is the one fact separating 'the ID is
        # wrong' from 'the paper is paywalled'. Both end this function with
        # nothing to show, so without capturing it here the two become the same
        # answer. It costs no extra request — the DOI lookup already made it.
        known = bool(recs)
        doi = recs[0]["doi"] if recs else ""
    elif kind == "doi":
        doi = identifier
        pmcid = _resolve_to_pmcid(identifier)

    res: Dict[str, Any] = {}
    if pmcid:
        res = _pmc_efetch_fulltext(pmcid)
    if not res:
        res = _epmc_fulltext(pmcid=pmcid, doi=doi)
    if not res and doi:
        res = _unpaywall_fulltext(doi)

    if not res and known is False:
        # Never reached the OA question, so do not answer it.
        return {
            "id": identifier,
            "kind": kind,
            "source": "none",
            "error": "id_not_found",
            "pmcid": pmcid,
            "doi": doi,
            "message": f"PubMed has no record with PMID {identifier}, so no full-text "
                       "lookup was attempted. This says nothing about open access: a "
                       "real but paywalled article also ends at 'source: none', with a "
                       "message saying no OA copy was found. Do not report this ID as "
                       "having no full text. Check it with `search "
                       f"{identifier}[uid]` — a merged record answers under the PMID "
                       "that survived.",
        }

    if not res:
        hint = ""
        if not doi:
            hint = "No DOI resolved for this ID, so the Unpaywall stage was skipped."
        elif not load_config().get("UNPAYWALL_EMAIL"):
            hint = "Set UNPAYWALL_EMAIL in .env to enable the Unpaywall fallback."
        out: Dict[str, Any] = {
            "id": identifier,
            "kind": kind,
            "source": "none",
            "pmcid": pmcid,
            "doi": doi,
            "message": "No open-access full text found via PMC, Europe PMC, or Unpaywall.",
            "hint": hint,
        }
        # known is None only for --kind doi/pmcid: nothing on those paths looks the
        # identifier up, so a typo arrives here wearing the same answer as a real
        # paywalled paper — the confusion --kind pmid used to have. Verifying would
        # cost a Crossref call on every paywalled DOI, which is the common case, so
        # say what is not known instead of paying for it. `idVerified` lets a caller
        # tell the two apart without reading prose.
        if known is None:
            out["idVerified"] = False
            out["message"] += (
                f" Note this is not evidence that the {kind} exists: no step here "
                f"validates it, so a mistyped {kind} produces exactly this answer. "
                "Check that it resolves (https://doi.org/<doi> for a DOI) before "
                "reporting the article as having no open-access copy."
            )
        return out

    res["id"] = identifier
    res["kind"] = kind
    if doi and not res.get("doi"):
        res["doi"] = doi
    if "sections" in res:  # JATS sources only; Unpaywall text has no section structure
        res["sections"] = _apply_section_filters(res["sections"], args.sections, args.max_sections)
        res["fullText"] = _sections_to_text(res["sections"])
    if not args.include_references:
        res.pop("references", None)
    return res


def cmd_fulltext(args) -> None:
    requested = _clean_ids(args.ids)
    ids = requested[:10]  # mirror the MCP server's per-call cap
    if not ids:
        _out({"error": "No IDs provided."})
        return
    articles = [_fulltext_one(i, args.kind, args) for i in ids]
    result: Dict[str, Any] = {"count": len(articles), "articles": articles}
    # Truncating in silence hands back a short list that reads as complete:
    # `count` reports what ran, not what was asked for, so the dropped IDs look
    # like articles that simply have no open-access copy.
    if len(requested) > len(ids):
        result["notice"] = (
            f"{len(requested)} IDs were given; only the first {len(ids)} were fetched "
            f"— this command caps at {len(ids)} per call. Not fetched: "
            + ", ".join(requested[len(ids):])
            + ". Re-run for those rather than reporting them as having no full text."
        )
    _out(result)


# ─── cite (format citations) ─────────────────────────────────────────────────
def cmd_cite(args) -> None:
    pmids = _clean_ids(args.pmids)
    if not pmids:
        _out({"error": "No PMIDs provided."})
        return
    records = _fetch_records(pmids)
    styles = args.style or ["vancouver"]
    out: List[Dict[str, Any]] = []
    for rec in records:
        entry = {"pmid": rec["pmid"], "citations": {}}
        for style in styles:
            entry["citations"][style] = cite_mod.format_citation(rec, style)
        out.append(entry)
    result: Dict[str, Any] = {"count": len(out), "styles": styles, "results": out}
    # A dropped ID here is a reference that silently never reaches the
    # bibliography — the caller pasted N PMIDs and gets N-1 formatted entries.
    _note_missing(result, pmids, records, verb="paste")
    _out(result)


# ─── lookup-cite (ECitMatch) ─────────────────────────────────────────────────
def _citation_line(journal: str, year: str, volume: str, first_page: str,
                   author: str, key: str) -> str:
    # ECitMatch bdata field order: journal|year|volume|first_page|author|key|
    return "|".join([journal, year, volume, first_page, author, key]) + "|"


def _parse_citation_field(spec: str, index: int) -> str:
    parts = spec.split("|")
    return parts[index].strip() if index < len(parts) else ""


def cmd_lookup_cite(args) -> None:
    lines: List[str] = []
    if args.citation:
        for i, spec in enumerate(args.citation[:25], start=1):
            lines.append(_citation_line(
                _parse_citation_field(spec, 0), _parse_citation_field(spec, 1),
                _parse_citation_field(spec, 2), _parse_citation_field(spec, 3),
                _parse_citation_field(spec, 4), _parse_citation_field(spec, 5) or f"ref{i}",
            ))
    else:
        lines.append(_citation_line(
            args.journal or "", args.year or "", args.volume or "",
            args.first_page or "", args.author or "", args.key or "ref1",
        ))

    if not any(l.split("|")[0] or l.split("|")[1] for l in lines):
        _out({"error": "Each citation needs at least a journal or a year. "
                       "ECitMatch keys on journal+volume+page."})
        return

    # Multiple citations go in one bdata payload, separated by carriage returns.
    resp = eutils_request("ecitmatch.cgi", {
        "db": "pubmed", "retmode": "xml", "bdata": "\r".join(lines),
    })
    text = resp.text.strip()

    results: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        cols = line.split("|")
        last = cols[-1].strip() if cols else ""
        pmid = last if last.isdigit() else ""
        results.append({
            "key": cols[5].strip() if len(cols) > 5 else "",
            "pmid": pmid,
            "matched": bool(pmid),
            "status": last if not pmid else "OK",  # NOT_FOUND / AMBIGUOUS
            "raw": line,
        })
    out: Dict[str, Any] = {"count": len(results),
                           "matched": sum(r["matched"] for r in results),
                           "results": results}
    # Same trap as fulltext: past the cap the extra citations are dropped, and a
    # caller comparing `count` against its own list is the only way to notice.
    if args.citation and len(args.citation) > 25:
        out["notice"] = (
            f"{len(args.citation)} citations were given; only the first 25 were looked "
            "up — ECitMatch is capped at 25 per call. Re-run for the rest rather than "
            "reporting them as unmatched."
        )
    _out(out)


# ─── mesh (MeSH vocabulary lookup) ───────────────────────────────────────────
def _mesh_esearch(term: str, retmax: int) -> tuple:
    """ESearch the mesh db. Returns (idlist, totalCount)."""
    resp = eutils_request("esearch.fcgi", {
        "db": "mesh", "term": term, "retmax": retmax, "retmode": "json",
    })
    data = resp.json().get("esearchresult", {})
    return data.get("idlist", []), int(data.get("count", "0") or 0)


def cmd_mesh(args) -> None:
    # ESearch against the mesh db, then ESummary for descriptor details.
    ids, total = _mesh_esearch(args.term, args.limit)

    # The mesh db returns hits in UID order, not by relevance, so a bare term
    # buries the descriptor that carries that very name — 'diabetes' leads with
    # Donohue Syndrome and never reaches Diabetes Mellitus. Run the exact-heading
    # query as well and hoist its hit to the front. Skip it when the caller
    # already wrote a field tag; appending [MH] to 'foo[bar]' is nonsense.
    if "[" not in args.term:
        try:
            exact, _ = _mesh_esearch(f"{args.term}[MH]", 1)
        except Exception:  # noqa: BLE001 - the broad results still stand on their own
            exact = []
        if exact:
            ids = list(dict.fromkeys(exact + ids))[: args.limit]

    if not ids:
        _out({
            "term": args.term, "count": 0, "totalCount": total, "records": [],
            "guidance": "No MeSH descriptor matched. Run `spell` on the term, reduce it to a "
                        "single concept, or fall back to a free-text `search`.",
        })
        return
    su = eutils_request("esummary.fcgi", {
        "db": "mesh", "id": ",".join(ids), "retmode": "json",
    })
    data = su.json().get("result", {})
    records = []
    for uid in ids:
        item = data.get(uid, {})
        if not item:
            continue
        # ESummary carries tree numbers inside ds_idxlinks entries, not as a
        # flat list; pull the treenum out of each so callers get plain strings.
        # Supplementary Concept Records put a mapped-heading pointer ('@218176')
        # in the same field — it is not a navigable tree position, so drop it.
        tree_numbers: List[str] = []
        for link in item.get("ds_idxlinks") or []:
            tn = link.get("treenum") if isinstance(link, dict) else None
            if tn and not tn.startswith("@") and tn not in tree_numbers:
                tree_numbers.append(tn)
        records.append({
            "uid": uid,
            "name": item.get("ds_meshterms", [uid])[0] if item.get("ds_meshterms") else item.get("ds_meshui", uid),
            "meshUi": item.get("ds_meshui", ""),
            # 'descriptor' | 'qualifier' | 'supplementary concept'. The mesh db
            # holds all three and a bare term can match any of them, so callers
            # cannot tell a subheading from a heading without this.
            "recordType": item.get("ds_recordtype", ""),
            "scopeNote": item.get("ds_scopenote", ""),
            "treeNumbers": tree_numbers,
            "entryTerms": item.get("ds_meshterms", []),
            # The qualifiers this descriptor legally takes. An illegal pairing
            # (Semaglutide/epidemiology) is not rejected — PubMed returns zero
            # hits, which reads as "no such research" unless the list was checked
            # first. Empty for qualifier records.
            "allowableQualifiers": item.get("ds_subheading", []),
        })
    _out({"term": args.term, "totalCount": max(total, len(records)),
          "count": len(records), "records": records})


# ─── spell (ESpell) ──────────────────────────────────────────────────────────
def cmd_spell(args) -> None:
    resp = eutils_request("espell.fcgi", {"db": "pubmed", "term": args.query})
    root = parse_xml(resp.text)
    corrected = ""
    for el in root.iter("CorrectedQuery"):
        corrected = (el.text or "").strip()
        break
    _out({
        "query": args.query,
        "correctedQuery": corrected,
        "changed": bool(corrected) and corrected != args.query,
    })


# ─── helpers ─────────────────────────────────────────────────────────────────
def _clean_ids(raw: List[str]) -> List[str]:
    out: List[str] = []
    for chunk in raw:
        for tok in str(chunk).replace(",", " ").split():
            tok = tok.strip()
            if tok:
                out.append(tok)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PubMed research tools (E-utilities + EPMC/Unpaywall/OpenAlex).")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Search PubMed (ESearch).")
    s.add_argument("query", nargs="?", default="", help="Free-text query with PubMed field syntax.")
    s.add_argument("--author"); s.add_argument("--journal")
    s.add_argument("--mesh", nargs="*"); s.add_argument("--pubtype", nargs="*")
    s.add_argument("--language"); s.add_argument("--species", choices=["humans", "animals"])
    s.add_argument("--exclude-animals", action="store_true", dest="exclude_animals",
                   help="Drop animal-only studies without requiring MeSH on every keeper: "
                        "NOT (animals[mh] NOT humans[mh]). Use instead of --species humans "
                        "when recall matters.")
    s.add_argument("--free-full-text", action="store_true", dest="free_full_text")
    s.add_argument("--has-abstract", action="store_true", dest="has_abstract",
                   help="Only articles that have an abstract.")
    s.add_argument("--min-date", help="YYYY/MM/DD. Open-ended if --max-date is omitted.")
    s.add_argument("--max-date", help="YYYY/MM/DD. Open-ended if --min-date is omitted.")
    s.add_argument("--date-type", choices=["pdat", "edat", "mdat"], default="pdat",
                   help="pdat=publication, edat=Entrez, mdat=modification")
    s.add_argument("--sort", choices=["relevance", "pub_date", "author", "journal"], default="relevance")
    s.add_argument("--limit", type=int, default=20); s.add_argument("--offset", type=int, default=0)
    s.add_argument("--summaries", action="store_true", help="Also fetch full metadata for results.")
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("fetch", help="Fetch full metadata by PMID (EFetch).")
    f.add_argument("pmids", nargs="+")
    f.add_argument("--include-grants", action="store_true", dest="include_grants",
                   help="Include funding/grant records.")
    f.add_argument("--no-mesh", action="store_true", dest="no_mesh",
                   help="Omit MeSH terms from the output.")
    f.set_defaults(func=cmd_fetch)

    ft = sub.add_parser("fulltext", help="Fetch full text (PMC -> EPMC -> Unpaywall).")
    ft.add_argument("ids", nargs="+", help="Up to 10 IDs, all of the same --kind.")
    ft.add_argument("--kind", choices=["pmid", "pmcid", "doi"], default="pmid")
    ft.add_argument("--sections", nargs="*", help="Keep only sections whose title matches (case-insensitive).")
    ft.add_argument("--max-sections", type=int, default=0, dest="max_sections")
    ft.add_argument("--include-references", action="store_true", dest="include_references")
    ft.set_defaults(func=cmd_fulltext)

    e = sub.add_parser("epmc-search", help="Search Europe PMC.")
    e.add_argument("query"); e.add_argument("--sources", nargs="*", help="MED PMC PPR PAT AGR")
    e.add_argument("--limit", type=int, default=25); e.add_argument("--cursor", default="*")
    e.add_argument("--result-type", choices=["core", "lite"], default="core", dest="result_type")
    e.add_argument("--sort", help='e.g. "P_PDATE_D desc", "CITED desc", "PUB_YEAR desc"')
    e.set_defaults(func=cmd_epmc_search)

    c = sub.add_parser("convert-ids", help="Convert DOI/PMID/PMCID (50 per request).")
    c.add_argument("ids", nargs="+")
    c.add_argument("--idtype", choices=["auto", "pmid", "pmcid", "doi"], default="auto",
                   help="Force an ID type instead of detecting it per ID.")
    c.set_defaults(func=cmd_convert_ids)

    r = sub.add_parser("related", help="Related / cited-by / references.")
    r.add_argument("pmid"); r.add_argument("--type", choices=["similar", "cited_by", "references"], default="similar")
    r.add_argument("--limit", type=int, default=20)
    r.add_argument("--offset", type=int, default=0)
    r.add_argument("--fetch", action="store_true", help="Full EFetch metadata instead of brief summaries.")
    r.add_argument("--pmids-only", action="store_true", dest="pmids_only",
                   help="Skip enrichment and return PMIDs alone.")
    r.set_defaults(func=cmd_related)

    ci = sub.add_parser("cite", help="Format citations.")
    ci.add_argument("pmids", nargs="+")
    ci.add_argument("--style", nargs="*", choices=["vancouver", "apa", "mla", "bibtex", "ris"], default=["vancouver"])
    ci.set_defaults(func=cmd_cite)

    lc = sub.add_parser("lookup-cite", help="Find PMID from partial citation (ECitMatch).")
    lc.add_argument("--journal"); lc.add_argument("--year"); lc.add_argument("--volume")
    lc.add_argument("--first-page", dest="first_page"); lc.add_argument("--author"); lc.add_argument("--key")
    lc.add_argument("--citation", action="append",
                    help='Batch form, repeatable (max 25): "journal|year|volume|first_page|author|key"')
    lc.set_defaults(func=cmd_lookup_cite)

    m = sub.add_parser("mesh", help="Search MeSH vocabulary.")
    m.add_argument("term"); m.add_argument("--limit", type=int, default=10)
    m.set_defaults(func=cmd_mesh)

    sp = sub.add_parser("spell", help="Spell-check a query (ESpell).")
    sp.add_argument("query"); sp.set_defaults(func=cmd_spell)

    return p


def main(argv: List[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not has_api_key():
        eprint("[pubmed-research] No NCBI_API_KEY set — throttling to 3 req/s.")
    # Callers parse stdout as JSON, so a network/API failure has to surface as a
    # JSON error object rather than a traceback.
    try:
        args.func(args)
    except KeyboardInterrupt:
        raise
    # `requests` puts the full request URL — api_key included — into both
    # response.url and the exception text, so every field below has to be
    # redacted before printing.
    except requests.HTTPError as exc:
        resp = getattr(exc, "response", None)
        _out({
            "error": "http_error",
            "command": args.cmd,
            "status": getattr(resp, "status_code", None),
            "url": redact(getattr(resp, "url", "")),
            "message": redact(exc),
        })
        return 1
    except requests.RequestException as exc:
        _out({"error": "network_error", "command": args.cmd, "message": redact(exc)})
        return 1
    except Exception as exc:  # noqa: BLE001
        _out({"error": type(exc).__name__, "command": args.cmd, "message": redact(exc)})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
