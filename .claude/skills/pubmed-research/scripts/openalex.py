"""OpenAlex provider — last-resort fallback for the `related` subcommand.

Mirrors the three ELink relationships:
  similar(pmid, n)     -> related_works     (mirrors pubmed_pubmed)
  cited_by(pmid, n)    -> cites:W<id> filter (mirrors pubmed_pubmed_citedin)
  references(pmid, n)  -> referenced_works  (mirrors pubmed_pubmed_refs)

OpenAlex is the only provider that can serve `similar`, since Europe PMC has no
content-similarity endpoint. Its similarity is OpenAlex's own `related_works`,
not PubMed's neighbor algorithm — callers should say so when it answers.

Works with no PMID are dropped rather than given a synthetic ID. No dependency
beyond `requests`; requests go through eutils_common so they share the same
rate limiter and retry/backoff policy.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from eutils_common import external_request, load_config

OPENALEX_BASE = "https://api.openalex.org"

# OpenAlex caps an OR-filter (`a|b|c`) at 50 values, so batch resolution chunks.
_MAX_OR_VALUES = 50


def _params(extra: Dict[str, Any]) -> Dict[str, Any]:
    params = dict(extra)
    # Polite-pool identification. Reuses NCBI_EMAIL rather than adding config,
    # the same way the MCP server reuses its adminEmail.
    email = load_config().get("NCBI_EMAIL")
    if email:
        params["mailto"] = email
    return params


def _bare_id(oa_id: str) -> str:
    """'https://openalex.org/W123' -> 'W123'."""
    return oa_id.rsplit("/", 1)[-1]


def _pmid_of(work: Dict[str, Any]) -> str:
    """OpenAlex stores PMIDs as URLs ('https://pubmed.../31295471')."""
    raw = (work.get("ids") or {}).get("pmid") or ""
    match = re.search(r"(\d+)\s*$", str(raw))
    return match.group(1) if match else ""


def _get_work(pmid: str) -> Optional[Dict[str, Any]]:
    """Fetch the Work for a PMID. Returns None when OpenAlex doesn't know it."""
    try:
        resp = external_request(
            f"{OPENALEX_BASE}/works/pmid:{pmid}",
            _params({"select": "id,related_works,referenced_works"}),
        )
    except requests.HTTPError as exc:
        if getattr(exc.response, "status_code", None) == 404:
            return None
        raise
    return resp.json()


def _resolve_pmids(oa_ids: List[str], exclude_pmid: str) -> List[str]:
    """Batch-resolve OpenAlex work IDs to PMIDs, preserving order."""
    pmids: List[str] = []
    seen = set()
    for start in range(0, len(oa_ids), _MAX_OR_VALUES):
        chunk = [_bare_id(x) for x in oa_ids[start : start + _MAX_OR_VALUES]]
        if not chunk:
            continue
        resp = external_request(
            f"{OPENALEX_BASE}/works",
            _params({
                "filter": "openalex:" + "|".join(chunk),
                "select": "id,ids",
                "per_page": str(len(chunk)),
            }),
        )
        for work in resp.json().get("results", []):
            pmid = _pmid_of(work)
            if pmid and pmid != exclude_pmid and pmid not in seen:
                seen.add(pmid)
                pmids.append(pmid)
    return pmids


def similar(pmid: str, n: int) -> Tuple[List[str], int]:
    work = _get_work(pmid)
    if not work:
        return [], 0
    related = work.get("related_works") or []
    if not related:
        return [], 0
    # Over-fetch: many related works carry no PMID and get dropped.
    candidates = related[: min(max(n, 1) * 3, 50)]
    return _resolve_pmids(candidates, pmid)[:n], len(related)


def references(pmid: str, n: int) -> Tuple[List[str], int]:
    work = _get_work(pmid)
    if not work:
        return [], 0
    refs = work.get("referenced_works") or []
    if not refs:
        return [], 0
    candidates = refs[: min(max(n, 1) * 3, 200)]
    return _resolve_pmids(candidates, pmid)[:n], len(refs)


def cited_by(pmid: str, n: int) -> Tuple[List[str], int]:
    work = _get_work(pmid)
    if not work:
        return [], 0
    resp = external_request(
        f"{OPENALEX_BASE}/works",
        _params({
            "filter": f"cites:{_bare_id(work['id'])}",
            "select": "id,ids",
            "per_page": str(min(max(n, 1), 200)),
        }),
    )
    data = resp.json()
    pmids: List[str] = []
    seen = set()
    for work_rec in data.get("results", []):
        candidate = _pmid_of(work_rec)
        if candidate and candidate != pmid and candidate not in seen:
            seen.add(candidate)
            pmids.append(candidate)
    return pmids, int(data.get("meta", {}).get("count", 0) or 0)


def related(pmid: str, relationship: str, n: int) -> Tuple[List[str], int]:
    """Dispatch on relationship. Returns (pmids, totalCount)."""
    fn = {"similar": similar, "cited_by": cited_by, "references": references}.get(relationship)
    if not fn:
        return [], 0
    return fn(pmid, n)
