---
name: pubmed-research
description: Search, retrieve, and analyze biomedical literature from PubMed and Europe PMC via NCBI E-utilities. Use this skill whenever the user wants to find medical or life-science papers, look up articles by PMID/DOI/PMCID, fetch abstracts or metadata, get open-access full text, generate Vancouver (or APA/MLA/BibTeX/RIS) citations, resolve MeSH terms, find related or citing articles, or export literature-search results to CSV. Trigger this even when the user just names a topic and asks for "papers," "literature," "references," or "studies" on a biomedical subject, or mentions PubMed, Europe PMC, MeSH, or NCBI, even if they don't explicitly ask to "search PubMed."
---

# PubMed Research

Command-line toolkit that wraps NCBI E-utilities plus Europe PMC, Unpaywall, and
OpenAlex to search and analyze biomedical literature. It reproduces the ten tools
of the `cyanheads/pubmed-mcp-server` as plain Python scripts — no MCP server,
no persistent process. Each tool is a subcommand of `scripts/pubmed.py` that
prints JSON to stdout, so results pipe cleanly into `scripts/to_csv.py` or into
your own analysis.

## Environment requirement

This skill makes outbound HTTPS calls to `eutils.ncbi.nlm.nih.gov` and companion
services. It is meant to run **locally** (Claude Code, a terminal, or any coding
agent with normal network egress). Sandboxes that restrict outbound network
access to package registries — including the claude.ai code-execution
container — cannot reach NCBI and will fail with connection/403 errors. If a call
fails that way, tell the user to run the skill in a local environment.

## Setup

1. Install dependencies: `pip install -r requirements.txt` (`requests`, plus
   `pypdf` for extracting text from open-access PDFs in the Unpaywall stage of
   `fulltext`; `lxml` is optional and used automatically if present).
2. Configuration is optional. To raise the rate limit or enable the Unpaywall
   full-text fallback, copy `.env.example` to `.env` and fill in values:
   - `NCBI_API_KEY` — raises the limit from 3 to 10 requests/second.
   - `NCBI_EMAIL`, `NCBI_TOOL` — courtesy identification for NCBI.
   - `UNPAYWALL_EMAIL` — enables the third-stage Unpaywall fallback in `fulltext`.

   With no `.env` at all, everything still works at 3 req/s. Never hard-code keys
   in commands or commit `.env` — it is git-ignored for that reason.

## Running the tools

`cd` to this skill's base directory first — the paths below are relative to it,
and the current working directory when the skill loads is the user's project, not
the skill. From there every command takes the form
`python scripts/pubmed.py <subcommand> [options]`. Run
`python scripts/pubmed.py <subcommand> --help` for full options.

| Subcommand | What it does | Backing API |
|------------|--------------|-------------|
| `search` | Search PubMed; returns PMIDs (+ optional full metadata via `--summaries`). Supports author/journal/MeSH/pubtype/language/species/date filters, `--has-abstract`, and `--offset` paging. Multiple `--mesh` terms are AND'd; multiple `--pubtype` values are OR'd. `--min-date`/`--max-date` may be given alone for an open-ended range. Output carries `queryTranslation` — read it, see "Building a search strategy". | ESearch |
| `fetch` | Full metadata for one or more PMIDs: title, structured abstract, authors with deduplicated affiliations, journal, IDs, MeSH, publication types. `--include-grants` adds funding records. Batches up to 200 (auto-POST at ≥100). | EFetch |
| `fulltext` | Open-access full text for up to 10 PMIDs/PMCIDs/DOIs via a 3-stage chain: **PMC EFetch → Europe PMC fullTextXML → Unpaywall**. Returns structured `sections` for the JATS stages; `--sections`, `--max-sections`, `--include-references` filter them. | PMC / EPMC / Unpaywall |
| `epmc-search` | Search Europe PMC for preprints (`PPR`), patents (`PAT`), Agricola (`AGR`), and EPMC-only OA records that don't surface in PubMed. Cursor paging via `--cursor`; `--sort`, `--result-type`. | Europe PMC |
| `convert-ids` | Convert between DOI / PMID / PMCID (50 IDs per request; only articles indexed in PMC). Mixed-type batches are grouped automatically. | PMC ID Converter |
| `related` | Find `similar`, `cited_by`, or `references` articles for a source PMID, with `--offset` paging. Returns brief summaries by default (`--fetch` for full metadata, `--pmids-only` for IDs). Provider chain: ELink, then Europe PMC (`cited_by`/`references` only), then OpenAlex. First success wins; results are never merged. | ELink → Europe PMC → OpenAlex |
| `cite` | Format citations for PMIDs. Default style **vancouver**; also `apa`, `mla`, `bibtex`, `ris` (pass multiple with `--style`). | EFetch + in-code formatting |
| `lookup-cite` | Resolve a partial reference (journal/year/volume/page/author) to a PMID — deterministic matching, more reliable than free-text search. Batch up to 25 with repeated `--citation`. | ECitMatch |
| `mesh` | Search the MeSH vocabulary — descriptors **and** qualifiers/subheadings, told apart by `recordType`. Returns tree numbers, scope notes, entry terms, and on a descriptor the `allowableQualifiers` it legally takes. An exact heading match is hoisted to the front of the list. | ESearch/ESummary (mesh db) |
| `spell` | Spell-check a query and get NCBI's suggested correction. | ESpell |

Every subcommand prints JSON on stdout. Failures print a JSON object with an
`error` key and exit non-zero, so callers can always parse stdout.

## Typical workflows

**Topic search → export to CSV** (the PubMed2Excel-style deliverable):
```bash
python scripts/pubmed.py search "GLP-1 receptor agonists cardiovascular" \
    --pubtype "Randomized Controlled Trial" --min-date 2020/01/01 --max-date 2025/12/31 \
    --limit 50 --summaries | python scripts/to_csv.py -o results.csv
```
The CSV has columns PMID, Title, Authors, First Author, Journal, Journal
Abbreviation, Year, Volume, Issue, Pages, DOI, PMCID, Publication Types, MeSH
Terms, Keywords, Abstract, and URLs. Values are written as quoted text and the
file uses a UTF-8 BOM so Excel opens Japanese correctly; still, remind the user
that Excel may reformat date-like cells (volume/issue/pages) on open — importing
as text avoids that. For a hard guarantee against auto-conversion, build an
`.xlsx` with string-typed cells via the xlsx skill instead.

`to_csv.py` also accepts the output of `fetch`, `related`, `fulltext`, and
`epmc-search`. It refuses `cite` and `lookup-cite` output — that is not article
metadata — with a JSON `error` rather than a CSV of empty columns.

**Precise reference lookup then citation:**
```bash
python scripts/pubmed.py lookup-cite --journal "N Engl J Med" --year 2020 \
    --volume 382 --first-page 727
# take the PMID it returns, then:
python scripts/pubmed.py cite 31978945 --style vancouver apa
```

**Find the right MeSH term, then search with it:**
```bash
python scripts/pubmed.py mesh "diabetes"          # → Diabetes Mellitus (D003920) first
python scripts/pubmed.py search --mesh "Diabetes Mellitus, Type 2" --limit 30 --summaries
```
`mesh` matches descriptors, not free text: a lay phrase like `"sugar diabetes"`
returns zero records plus a `guidance` field. Reduce the term to one concept, or
run `spell` on it, before concluding no descriptor exists.

**Full text and related work:**
```bash
python scripts/pubmed.py fulltext 32109013 --kind pmid
python scripts/pubmed.py fulltext 32109013 --sections Methods Results --include-references
python scripts/pubmed.py related 32109013 --type cited_by --limit 25 --offset 25 --fetch
```
`fulltext` returns `{"count": N, "articles": [...]}`. Each article carries
`source` (`pmc` | `europepmc` | `unpaywall` | `none`) and `contentFormat`
(`jats-text` | `pdf-text` | `html-markdown` | `url-only`). The two JATS stages also
return `sections` (a list of `{title, text}`); the Unpaywall stage returns only
flat `fullText`, so `--sections` and `--max-sections` do not apply to it.

`related` returns brief summaries (title, authors, journal, date) in `articles`
by default; `--fetch` upgrades them to full metadata and `--pmids-only` skips
the lookup. It reports which provider answered in `source` (`ncbi` |
`europepmc` | `openalex` | `none`) and explains any non-NCBI answer in `notice`.
Read that notice: OpenAlex's `similar` is its own `related_works` measure, not
PubMed's neighbor algorithm, so the results are not interchangeable.

When ELink returns nothing for `cited_by` or `references`, the skill retries via
Europe PMC and then OpenAlex — both of NCBI's citation indexes are built only
from PMC-deposited reference lists, so an article outside PMC comes back empty
even when the data exists. An empty `similar` needs no retry. A `notice` naming
an unknown source PMID means the ID itself is wrong, not that the article has no
neighbors.

## Building a search strategy

The `search` flags emit `[MeSH Terms]`, `[Publication Type]`, `[Author]`,
`[Journal]`, `[Language]` and a date range — nothing else. That is a precision
search over well-indexed topics, and it is the whole flag surface, so building a
query from flags alone quietly settles for it. Everything below needs raw syntax
in the query string, which passes through to ESearch untouched.

- **MeSH alone under-recalls.** Indexing lags publication by weeks to months, so
  a MeSH-only query drops the newest articles — often the ones being asked
  about. Where recall matters, OR the MeSH clause with text terms:
  `("Obesity"[MeSH Terms] OR obesity[tiab] OR overweight[tiab])`. Say which of
  precision or recall the query was built for.
- **`[majr]`** restricts to articles where the concept is a major topic — reach
  for it when a precision search returns too much noise. `--mesh` cannot emit it.
- **Subheadings** narrow a descriptor to one aspect: `Hypertension/drug
  therapy[mh]`. Run `mesh` on the descriptor first and read
  `allowableQualifiers`; an illegal pairing returns zero hits, not an error.
  `drug therapy[sh]` is a different search — the qualifier need not attach to
  the descriptor you meant.
- **Report `queryTranslation`, never the `query` you sent.** PubMed rewrites
  silently and without error: a wildcard inside a proximity phrase drops the
  `:~N`, `[tw:~3]` drops it too, and `[mh:~3]` is left verbatim to match
  nothing. A plausible hit count is not evidence the query ran as written.
- For field tags, proximity, explosion and Europe PMC prefixes, read
  `references/query_syntax.md`. Read it before any systematic or exhaustive
  search — not only when the syntax is already known to be non-trivial.

## Guidance for good results

- When a search returns zero hits, don't stop — run `spell` on the query, then
  relax filters (dates, publication types) or broaden terms before reporting
  nothing found. The `search` output includes a `guidance` field in this case.
- Prefer `mesh` to pin down controlled vocabulary before a precision search, and
  `lookup-cite` over free-text search when the user already has a structured
  reference.
- Respect the rate limit — the scripts pace requests automatically, so avoid
  launching many overlapping invocations in parallel.
- Every subcommand emits JSON; to post-process, parse that JSON rather than
  scraping the printed text. On failure the JSON has an `error` key — check it
  before assuming a result shape.
- `fulltext` reports which stage answered via `source`. A `source` of `none`
  means no open-access copy exists, not that the article is missing. A
  `source` of `unpaywall` with an empty `fullText` means the article is open
  access but its host refused the download — read `hint` and hand the user
  `pdfUrl`/`landingUrl`.
