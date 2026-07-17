# PubMed & Europe PMC query syntax reference

Read this when constructing non-trivial searches. For simple keyword searches
you don't need it.

## PubMed field tags

Append a bracketed tag to scope a term to a field:

| Tag | Field | Example |
|-----|-------|---------|
| `[tiab]` | Title/Abstract | `crispr[tiab]` |
| `[ti]` | Title only | `melanoma[ti]` |
| `[au]` | Author | `Smith J[au]` |
| `[1au]` / `[lastau]` | First / last author | `Zhang[1au]` |
| `[ta]` | Journal (Title Abbreviation) | `N Engl J Med[ta]` |
| `[mh]` | MeSH Terms | `Neoplasms[mh]` |
| `[majr]` | MeSH Major Topic | `Diabetes Mellitus[majr]` |
| `[pt]` | Publication Type | `Review[pt]`, `Randomized Controlled Trial[pt]` |
| `[la]` | Language | `english[la]`, `japanese[la]` |
| `[dp]` | Date of Publication | `2020:2024[dp]` |
| `[pdat]` | Publication date (range) | `2023/01/01:2023/12/31[pdat]` |
| `[edat]` | Entrez date | for "recently added" |
| `[tw]` | Text word | broad text match |
| `[ad]` | Affiliation | `Toho University[ad]` |

## Boolean operators

- `AND`, `OR`, `NOT` (uppercase).
- Parenthesize to control precedence: `(aspirin OR ibuprofen) AND headache`.
- Phrase search with quotes: `"myocardial infarction"`.

## MeSH subheadings and explosion

- MeSH terms auto-explode (include narrower terms) by default.
- Disable explosion: `Neoplasms[mh:noexp]`.
- Attach a subheading: `Hypertension/drug therapy[mh]`.

## Common filters (via the `search` subcommand flags)

The `pubmed.py search` command builds these for you:

- `--author "Smith J"` → `"Smith J"[Author]`
- `--journal "Nature"` → `"Nature"[Journal]`
- `--mesh Neoplasms Apoptosis` → each AND'd as `[MeSH Terms]`
- `--pubtype Review "Meta-Analysis"` → OR'd as `[Publication Type]`
- `--language english` → `english[Language]`
- `--species humans` → `humans[MeSH Terms]`
- `--free-full-text` → `"free full text"[Filter]`
- `--min-date 2020/01/01 --max-date 2024/12/31 --date-type pdat`

Date types: `pdat` (publication), `edat` (Entrez/added), `mhda` (MeSH date).

## Europe PMC syntax (epmc-search)

Europe PMC uses its own query language. Useful prefixes:

- `SRC:` source — `MED` (PubMed), `PMC`, `PPR` (preprints), `PAT` (patents),
  `AGR` (Agricola). The `--sources` flag sets these.
- `AUTH:"Smith J"` author, `TITLE:"..."`, `JOURNAL:"..."`.
- `PUB_YEAR:2023`, `PUB_YEAR:[2020 TO 2024]`.
- `OPEN_ACCESS:Y` to restrict to OA.
- `DOI:10.1056/...` exact DOI lookup.
- Pagination is cursor-based: pass the returned `nextCursorMark` as `--cursor`.

## Tips

- When a search returns zero results, run `spell` on the query, then relax
  filters (dates, publication types) before concluding there's nothing there.
- `mesh` resolves free-text concepts to controlled MeSH descriptors — use it to
  find the right `[mh]` term before a precise search.
- `lookup-cite` is more reliable than free-text search when you already have a
  structured reference (journal + year + volume + first page).
