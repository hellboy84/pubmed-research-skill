# PubMed & Europe PMC query syntax reference

Read this before any systematic or exhaustive search, and whenever precision or
recall is the point rather than a quick look-up. Simple keyword searches don't
need it.

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
| `[sh]` | MeSH Subheading — the qualifier alone, unattached | `drug therapy[sh]` |
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

## Proximity search

`"<phrase>"[field:~N]` matches the terms within N words of each other, in any
order. Supported on `[tiab]`, `[ti]`, and `[ad]` — and nowhere else.

```
"knee pain"[tiab]        # exact phrase
"knee pain"[tiab:~3]     # also "pain in the knee", "knee osteoarthritis pain"
```

Two failure modes, both silent — no error, and a hit count that still looks
reasonable:

- **A wildcard voids it.** `"knee pain*"[tiab:~3]` runs as `"knee
  pain*"[Title/Abstract]`. The `:~3` is dropped.
- **An unsupported field voids it.** `[tw:~3]` drops the `:~N` the same way.
  `[mh:~3]` and `[majr:~3]` are worse: the tag is left verbatim and matches
  nothing, so the search returns zero and reads as "no such research".

Confirm from `queryTranslation` in the `search` output. Proximity survived only
if the tag comes back expanded — `[Title/Abstract:~3]`, `[Title:~3]`,
`[Affiliation:~2]`. If the `:~N` is missing there, it did not run.

## MeSH subheadings and explosion

- MeSH terms auto-explode (include narrower terms) by default.
- Disable explosion: `Neoplasms[mh:noexp]`.
- Attach a subheading: `Hypertension/drug therapy[mh]` — the qualifier is bound
  to that descriptor.
- `hypertension[mh] AND drug therapy[sh]` is **not** the same search. `[sh]`
  only requires the qualifier to appear somewhere in the record, attached to any
  descriptor, so it returns more and less precisely — the extra hits are ones
  where the qualifier sits on some other descriptor entirely. Prefer the
  attached form unless the qualifier itself is the subject.
- Qualifiers are per-descriptor, and a bad one fails in two ways. Neither is an
  error, and **neither shows up in `phrasesNotFound`**:
  - *Real qualifier, illegal pairing.* `Semaglutide/epidemiology[mh]` — a drug
    takes no epidemiology. Translates verbatim, returns zero, reads exactly like
    "no such research". Nothing in the output distinguishes it from a legal
    pairing with no literature.
  - *No such qualifier.* `Hypertension/nonsense[mh]` is not preserved at all.
    PubMed drops the `[mh]`, splits the pair, and ATM-expands each half:
    `("hypertension"[All Fields] OR ...) AND "codon, nonsense"[MeSH Terms]` — 63
    hits about nonsense codons. Plausible count, unrelated search. Only
    `queryTranslation` reveals it.
- So run `mesh <descriptor>` and read `allowableQualifiers` before attaching a
  qualifier; it is the only check that catches the first case. `mesh <qualifier>`
  works too (`recordType: qualifier`), and its `scopeNote` carries the usage
  rule — `drug therapy` says "Used with disease headings", which is why it does
  not belong on a drug.

## Common filters (via the `search` subcommand flags)

The `pubmed.py search` command builds these for you:

- `--author "Smith J"` → `"Smith J"[Author]`
- `--journal "Nature"` → `"Nature"[Journal]`
- `--mesh Neoplasms Apoptosis` → each AND'd as `[MeSH Terms]`
- `--pubtype Review "Meta-Analysis"` → OR'd as `[Publication Type]`
- `--language english` → `english[Language]`
- `--species humans` → `humans[MeSH Terms]` — **a MeSH filter, see below**
- `--species animals` → `(animals[mh] NOT humans[mh])` — PubMed's "Other Animals"
- `--exclude-animals` → `NOT (animals[mh] NOT humans[mh])` — **the hedge, see below**
- `--free-full-text` → `"free full text"[Filter]`
- `--min-date 2020/01/01 --max-date 2024/12/31 --date-type pdat`

## Species filtering: the hedge

`--species humans` and `--mesh` AND a `[MeSH Terms]` clause, and only
MEDLINE-indexed records carry MeSH. An article awaiting indexing cannot match
either one whatever its subject, so both silently exclude the newest literature —
and `--species humans` is the one that looks like a subject filter rather than a
vocabulary one. It is what undoes a recall-first query: OR a text-word clause in
for recall, then AND this on, and the recall is gone.

This is PubMed's behaviour, not the skill's: `humans[Filter]` translates to the
identical `"humans"[MeSH Terms]` and returns the identical count. The cost is
yours either way.

**The hedge** — `NOT (animals[mh] NOT humans[mh])`, what `--exclude-animals`
builds — removes animal-only studies without requiring a tag from the keepers. An
un-indexed record carries neither `animals[mh]` nor `humans[mh]`, so it does not
match the excluded set and survives. Measured on tirzepatide (2026-07):

| Query | Hits | of which un-indexed |
|---|---|---|
| `tirzepatide[tiab]` | 2,249 | 971 |
| `... AND humans[MeSH Terms]` (`--species humans`) | **1,216** | 10 |
| `... NOT (animals[mh] NOT humans[mh])` (`--exclude-animals`) | **2,180** | **970** |
| `... AND (animals[mh] NOT humans[mh])` (`--species animals`) | 69 | — |

The hedge drops exactly 69 records — precisely the animal-only set — and keeps
970 of the 971 un-indexed. `--species animals` and `--exclude-animals` partition
the corpus exactly: 69 + 2,180 = 2,249.

Use `--species humans` only when the Humans *tag* is the actual requirement. Use
`--exclude-animals` when the goal is "no animal studies", which is usually what is
meant. `NOT medline[sb]` measures the indexing gap on your own topic.

Two traps around this:

- **`AND NOT` is silently inverted.** `A AND NOT B` runs as `A AND B`: PubMed
  drops the `NOT`, without an error, and returns exactly the set you meant to
  exclude. `tirzepatide[tiab] AND NOT (animals[mh] NOT humans[mh])` returns the
  69 animal-only papers, not the 2,180. The `NOT` must attach to the whole query —
  `(...) NOT (...)` — which is what `--exclude-animals` writes for you. Confirm in
  `queryTranslation`: the hedge appears in full when it parsed.
- **A bare `animals[mh]` is not "animal studies".** MeSH explodes over its
  subtree and Humans sits under Animals, so `animals[mh]` matches every human
  study too — 1,285 hits here, 1,216 of them human. Subtracting humans is exactly
  why PubMed's sidebar names the filter "Other Animals". `animals[Filter]` is no
  escape either: unlike `humans[Filter]` there is no such tag, so it survives
  translation verbatim and returns zero.

`english[Language]` has none of this (2,249 → 2,206): language is on the citation
record from the start, not assigned at indexing. `--has-abstract` and
`--free-full-text` cut hits too (1,913 and 1,360 here), but they mean what they
say — that is the filter working, not indexing lag.

Date types `--date-type` accepts: `pdat` (publication), `edat` (Entrez/added),
`mdat` (last modification). `[mhda]` (MeSH date) is a valid tag in a raw query
string, but the flag rejects it — write it into the query yourself.

## Europe PMC syntax (epmc-search)

Europe PMC uses its own query language. Useful prefixes:

- `SRC:` source — `MED` (PubMed), `PMC`, `PPR` (preprints), `PAT` (patents),
  `AGR` (Agricola). The `--sources` flag sets these.
- `AUTH:"Smith J"` author, `TITLE:"..."`, `JOURNAL:"..."`.
- `PUB_YEAR:2023`, `PUB_YEAR:[2020 TO 2024]`.
- `OPEN_ACCESS:Y` to restrict to OA.
- `DOI:10.1056/...` exact DOI lookup.
- Pagination is cursor-based: pass the returned `nextCursorMark` as `--cursor`.
  A page holds at most 100 records however large `--limit` is.
- `--sort` takes an EPMC sort token, not free text: `P_PDATE_D desc` (date),
  `CITED desc` (citations), `PUB_YEAR desc`. An unrecognized token makes EPMC
  reject the entire request and answer with an empty body — raw, that reads as
  zero hits; the skill turns it into an `epmc_rejected_request` error instead.
  If a sorted search suddenly finds nothing, suspect the token before the topic.

## Tips

- When a search returns zero results, read `phrasesNotFound` first. A term that
  does not exist in the index explains the zero on its own, and no amount of
  relaxing filters will fix it. Only if that field is absent should you `spell`
  the query and relax dates or publication types before concluding there's
  nothing there.
- `mesh` resolves free-text concepts to controlled MeSH descriptors — use it to
  find the right `[mh]` term before a precise search.
- `lookup-cite` is more reliable than free-text search when you already have a
  structured reference (journal + year + volume + first page).
