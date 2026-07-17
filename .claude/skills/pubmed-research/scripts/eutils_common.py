"""Shared helpers for the pubmed-research skill.

Handles configuration loading (.env), rate limiting, retry-with-backoff, and the
low-level HTTP calls to NCBI E-utilities and the companion services (Europe PMC,
Unpaywall, OpenAlex, PMC ID Converter). All the scripts in this skill import from
here so that rate-limit and courtesy-parameter behavior is consistent.

No third-party dependencies beyond `requests`. XML parsing uses the stdlib
`xml.etree.ElementTree`; if `lxml` is installed it is used automatically for
speed/robustness but it is not required.
"""

from __future__ import annotations

import io
import os
import re
import sys
import time
import random
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

# ─── Force UTF-8 stdio ────────────────────────────────────────────────────────
# On Windows, console/pipe encoding defaults to the system's legacy code page
# (e.g. cp932 on Japanese Windows), which cannot represent many characters that
# show up in article titles/abstracts/author names (accented letters, micro
# signs, superscripts, etc). Without this, `json.dump(..., sys.stdout)` raises
# UnicodeEncodeError as soon as such a character appears. Reconfigure every
# script's stdio to UTF-8 unconditionally at import time so this never depends
# on the user remembering to set PYTHONIOENCODING.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

# ─── Endpoints (mirrors the cyanheads/pubmed-mcp-server service layer) ────────
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PMC_IDCONV_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"

# Publisher hosts routinely reject the default python-requests UA, so the
# Unpaywall stage of `fulltext` needs a real one to fetch OA PDFs/landing pages.
USER_AGENT_VERSION = "1.0"

# ─── Config loading ──────────────────────────────────────────────────────────
_CONFIG_CACHE: Optional[Dict[str, str]] = None


def _find_env_file() -> Optional[Path]:
    """Look for a .env file next to the skill (skill root), then CWD."""
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent / ".env",  # skill root
        Path.cwd() / ".env",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _parse_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def load_config() -> Dict[str, str]:
    """Load config from .env file (if present) then process environment.

    Process environment variables take precedence over the .env file, so a user
    can override anything at the shell without editing files. Recognized keys:

      NCBI_API_KEY     - optional. Raises the rate limit from 3 to 10 req/s.
      NCBI_TOOL        - courtesy 'tool' parameter sent to E-utilities.
      NCBI_EMAIL       - courtesy 'email' parameter sent to E-utilities.
      UNPAYWALL_EMAIL  - required to enable the Unpaywall full-text fallback.
    """
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cfg: Dict[str, str] = {}
    env_file = _find_env_file()
    if env_file:
        cfg.update(_parse_env_file(env_file))

    for key in ("NCBI_API_KEY", "NCBI_TOOL", "NCBI_EMAIL", "UNPAYWALL_EMAIL"):
        if os.environ.get(key):
            cfg[key] = os.environ[key]

    # Sensible defaults for the courtesy parameters.
    cfg.setdefault("NCBI_TOOL", "pubmed-research-skill")
    cfg.setdefault("NCBI_API_KEY", "")
    cfg.setdefault("NCBI_EMAIL", "")
    cfg.setdefault("UNPAYWALL_EMAIL", "")

    _CONFIG_CACHE = cfg
    return cfg


def has_api_key() -> bool:
    return bool(load_config().get("NCBI_API_KEY"))


def user_agent() -> str:
    """Identify this client to NCBI, publishers, Unpaywall and OpenAlex.

    The contact is whoever is *running* the skill — never a third party's URL.
    An abuse report about this traffic has to reach the operator, not the author
    of some project the code was modelled on. Unpaywall and OpenAlex ask for a
    `mailto:` for exactly this reason; set NCBI_EMAIL in .env to supply one.
    """
    cfg = load_config()
    ua = f"{cfg.get('NCBI_TOOL') or 'pubmed-research-skill'}/{USER_AGENT_VERSION}"
    email = cfg.get("NCBI_EMAIL")
    return f"{ua} (mailto:{email})" if email else ua


# ─── Rate limiting ───────────────────────────────────────────────────────────
# NCBI allows 3 req/s without a key, 10 req/s with one. We pace requests with a
# minimum inter-request interval and a small safety margin.
_LAST_REQUEST_TS = 0.0


def _min_interval() -> float:
    return (1.0 / 10.0) if has_api_key() else (1.0 / 3.0)


def _throttle() -> None:
    global _LAST_REQUEST_TS
    now = time.monotonic()
    wait = _min_interval() - (now - _LAST_REQUEST_TS)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_TS = time.monotonic()


# ─── Core request helper with retry/backoff ──────────────────────────────────
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
MAX_BACKOFF_MS = 30_000


def _courtesy_params(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = load_config()
    params: Dict[str, Any] = {"tool": cfg["NCBI_TOOL"]}
    if cfg.get("NCBI_EMAIL"):
        params["email"] = cfg["NCBI_EMAIL"]
    if cfg.get("NCBI_API_KEY"):
        params["api_key"] = cfg["NCBI_API_KEY"]
    if extra:
        params.update(extra)
    return params


def eutils_request(
    endpoint: str,
    params: Dict[str, Any],
    *,
    method: str = "GET",
    timeout: int = 60,
) -> requests.Response:
    """Call an E-utilities endpoint (e.g. 'esearch.fcgi') with retry/backoff.

    Automatically appends tool/email/api_key. For large payloads pass
    method='POST' (E-utilities accepts POST for esearch/efetch/elink).
    """
    url = f"{EUTILS_BASE}/{endpoint}"
    full = _courtesy_params(params)
    return _request_with_retry(url, full, method=method, timeout=timeout)


def _request_with_retry(
    url: str,
    params: Dict[str, Any],
    *,
    method: str = "GET",
    timeout: int = 60,
    headers: Optional[Dict[str, str]] = None,
) -> requests.Response:
    last_exc: Optional[Exception] = None
    hdrs = {"User-Agent": user_agent()}
    if headers:
        hdrs.update(headers)
    for attempt in range(MAX_RETRIES + 1):
        _throttle()
        try:
            if method == "POST":
                resp = requests.post(url, data=params, timeout=timeout, headers=hdrs)
            else:
                resp = requests.get(url, params=params, timeout=timeout, headers=hdrs)
        except requests.RequestException as exc:  # network-level failure
            last_exc = exc
            if attempt >= MAX_RETRIES:
                raise
            _backoff_sleep(attempt)
            continue

        if resp.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
            _backoff_sleep(attempt)
            continue

        resp.raise_for_status()
        return resp

    if last_exc:
        raise last_exc
    raise RuntimeError(f"Request to {url} failed after {MAX_RETRIES} retries")


def _backoff_sleep(attempt: int) -> None:
    base = min(MAX_BACKOFF_MS, (2 ** attempt) * 500)  # ms
    jitter = random.uniform(0, base * 0.25)
    time.sleep((base + jitter) / 1000.0)


def external_request(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    method: str = "GET",
    timeout: int = 60,
    headers: Optional[Dict[str, str]] = None,
) -> requests.Response:
    """Rate-limited request to a non-E-utilities service (EPMC/Unpaywall/OpenAlex)."""
    return _request_with_retry(
        url, params or {}, method=method, timeout=timeout, headers=headers
    )


# ─── XML parsing (lxml if available, else stdlib) ────────────────────────────
try:  # pragma: no cover - import guard
    from lxml import etree as _ET  # type: ignore

    def parse_xml(text: str):
        return _ET.fromstring(text.encode("utf-8"))

    _USING_LXML = True
except Exception:  # pragma: no cover
    import xml.etree.ElementTree as _ET  # type: ignore

    def parse_xml(text: str):
        return _ET.fromstring(text)

    _USING_LXML = False


def localname(el: Any) -> str:
    """Tag name without its XML namespace. Returns '' for comments/PIs (lxml
    gives those a callable tag)."""
    tag = getattr(el, "tag", None)
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def normalize_ws(text: str) -> str:
    return " ".join(text.split())


# ─── Document text extraction (for the Unpaywall full-text stage) ────────────
class _HTMLToMarkdown(HTMLParser):
    """Convert an OA article's HTML into Markdown.

    Markdown rather than flat text because headings, lists and link targets are
    exactly the structure a reader needs to navigate a paper, and flattening
    throws them away. Chrome (nav/footer/forms) is dropped outright.
    """

    # Only elements with a real end tag may suppress: a void element like <meta>
    # never fires handle_endtag, so counting it would swallow the rest of the page.
    _SKIP = {"script", "style", "noscript", "head", "svg",
             "nav", "footer", "header", "form", "button", "aside"}
    _VOID = {"meta", "link", "br", "hr", "img", "input", "source", "col", "area", "embed"}
    _BLOCK = {"div", "section", "article", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: List[str] = []
        self._suppress = 0
        self._hrefs: List[str] = []
        self._lists: List[List[Any]] = []
        self._pre = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self._SKIP and tag not in self._VOID:
            self._suppress += 1
            return
        if self._suppress:
            return
        attr = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "p":
            self._out.append("\n\n")
        elif tag == "br":
            self._out.append("\n")
        elif tag == "hr":
            self._out.append("\n\n---\n\n")
        elif tag in ("strong", "b"):
            self._out.append("**")
        elif tag in ("em", "i"):
            self._out.append("*")
        elif tag == "pre":
            self._pre += 1
            self._out.append("\n\n```\n")
        elif tag == "code" and not self._pre:
            self._out.append("`")
        elif tag == "blockquote":
            self._out.append("\n\n> ")
        elif tag in ("ul", "ol"):
            self._lists.append([tag, 0])
            self._out.append("\n")
        elif tag == "li":
            indent = "  " * max(len(self._lists) - 1, 0)
            if self._lists and self._lists[-1][0] == "ol":
                self._lists[-1][1] += 1
                self._out.append(f"\n{indent}{self._lists[-1][1]}. ")
            else:
                self._out.append(f"\n{indent}- ")
        elif tag == "a":
            href = attr.get("href", "") or ""
            if href.startswith("#") or href.startswith("javascript:"):
                href = ""
            self._hrefs.append(href)
            if href:
                self._out.append("[")
        elif tag in ("td", "th"):
            self._out.append(" | ")
        elif tag in self._BLOCK:
            self._out.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and tag not in self._VOID:
            if self._suppress:
                self._suppress -= 1
            return
        if self._suppress:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._out.append("\n")
        elif tag in ("strong", "b"):
            self._out.append("**")
        elif tag in ("em", "i"):
            self._out.append("*")
        elif tag == "pre":
            self._pre = max(self._pre - 1, 0)
            self._out.append("\n```\n")
        elif tag == "code" and not self._pre:
            self._out.append("`")
        elif tag in ("ul", "ol"):
            if self._lists:
                self._lists.pop()
            self._out.append("\n")
        elif tag == "a":
            href = self._hrefs.pop() if self._hrefs else ""
            if href:
                self._out.append(f"]({href})")
        elif tag in self._BLOCK or tag == "p":
            self._out.append("\n")

    def handle_data(self, data: str) -> None:
        if self._suppress:
            return
        if self._pre:
            self._out.append(data)
            return
        text = re.sub(r"\s+", " ", data)
        if not text.strip():
            if self._out and not self._out[-1].endswith((" ", "\n")):
                self._out.append(" ")
            return
        self._out.append(text)

    def markdown(self) -> str:
        text = "".join(self._out)
        text = re.sub(r"[ \t]+\n", "\n", text)          # trailing spaces
        text = re.sub(r"(?<=\S)[ \t]{2,}", " ", text)   # runs of spaces, sparing list indents
        text = re.sub(r"\n{3,}", "\n\n", text)          # at most one blank line
        return text.strip()


def html_to_markdown(html: str) -> str:
    parser = _HTMLToMarkdown()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - malformed markup shouldn't kill the run
        pass
    return parser.markdown()


def pdf_to_text(data: bytes) -> str:
    """Extract text from PDF bytes. Requires the optional `pypdf` dependency;
    returns '' when it isn't installed or the PDF has no text layer."""
    try:
        import pypdf  # type: ignore
    except Exception:  # noqa: BLE001
        return ""
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception:  # noqa: BLE001 - encrypted/corrupt PDFs
        return ""
    return normalize_ws(" ".join(pages))


def have_pdf_support() -> bool:
    try:
        import pypdf  # type: ignore  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def fetch_document(url: str, timeout: int = 90) -> Tuple[str, str]:
    """Fetch a URL and return (text, contentFormat).

    contentFormat is 'pdf-text', 'html-markdown', 'plain-text', or '' when
    nothing could be extracted. Dispatch is on the response Content-Type rather
    than the URL suffix, because OA landing URLs and PDF URLs are frequently the
    same string (Unpaywall reports both for e.g. medRxiv).
    """
    try:
        resp = external_request(url, timeout=timeout)
    except Exception:  # noqa: BLE001 - paywalls, 403s, dead links
        return "", ""
    ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if ctype == "application/pdf" or resp.content[:5] == b"%PDF-":
        text = pdf_to_text(resp.content)
        return (text, "pdf-text") if text else ("", "")
    if ctype in ("text/html", "application/xhtml+xml"):
        text = html_to_markdown(resp.text)
        return (text, "html-markdown") if text else ("", "")
    if ctype.startswith("text/"):
        text = normalize_ws(resp.text)
        return (text, "plain-text") if text else ("", "")
    return "", ""


def eprint(*args: Any, **kwargs: Any) -> None:
    """Print to stderr (progress/diagnostics that shouldn't pollute stdout JSON)."""
    print(*args, file=sys.stderr, **kwargs)


def chunked(seq: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]
