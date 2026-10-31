"""
pdf_reader.py: downloads an official document and turns it into numbered pages of text.

Government documents come as PDFs (gazette, circulars) or web pages (PIB press releases,
myScheme pages). Both end up as the same thing: a list of Page(number, text).
Keeping page numbers is what lets us show "Page 3 · Clause 5" next to every AI statement.

Downloaded files and parsed text are cached in /data so the demo still works if a
government site is slow (the cache holds REAL documents we fetched, not mock data).
"""
import io
import json
import ssl
from dataclasses import asdict, dataclass

import httpx
import truststore
from bs4 import BeautifulSoup
from pypdf import PdfReader

from config import settings
from sources.base import Policy

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NagrikAI/1.0; civic-info-research)",
    "Accept": "text/html,application/pdf,*/*",
}
HTML_PAGE_SIZE = 3000  # web pages have no pages, so we cut them into ~3000 char "pages"
DOWNLOAD_CHUNK_BYTES = 64 * 1024


class DocumentError(Exception):
    """The document could not be fetched or read."""


def _verification_context() -> ssl.SSLContext:
    """Use native system chain building, optionally extended with an explicitly trusted CA."""
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ca_bundle = settings.PDF_CA_BUNDLE
    if ca_bundle:
        try:
            # Extend (do not replace) system trust so ordinary public roots remain trusted.
            context.load_verify_locations(cafile=ca_bundle)
        except (OSError, ssl.SSLError) as e:
            raise DocumentError(f"Could not load the configured PDF_CA_BUNDLE: {e}") from e
    return context


def _download_document(url: str) -> tuple[bytes, str, str]:
    """Stream a document with verified TLS and enforce the configured response-size cap."""
    limit = settings.MAX_DOCUMENT_BYTES
    if limit <= 0:
        raise DocumentError("MAX_DOCUMENT_BYTES must be greater than zero.")
    try:
        with httpx.stream(
            "GET",
            url,
            headers=HEADERS,
            timeout=60,
            follow_redirects=True,
            verify=_verification_context(),
        ) as response:
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > limit:
                        raise DocumentError(
                            f"Document exceeds the {limit:,}-byte download limit."
                        )
                except ValueError:
                    pass  # A malformed header is still bounded while streaming below.

            chunks = []
            total = 0
            for chunk in response.iter_bytes(chunk_size=DOWNLOAD_CHUNK_BYTES):
                total += len(chunk)
                if total > limit:
                    raise DocumentError(
                        f"Document exceeds the {limit:,}-byte download limit."
                    )
                chunks.append(chunk)
            return b"".join(chunks), response.headers.get("content-type", ""), response.encoding or "utf-8"
    except httpx.HTTPError as e:
        raise DocumentError(f"Could not download the official document: {e}") from e


@dataclass
class Page:
    number: int
    text: str


@dataclass
class Document:
    policy_id: str
    url: str
    is_pdf: bool
    pages: list[Page]

    def text_for_llm(self, limit: int | None = None) -> str:
        """All pages joined, each marked [[PAGE n]], cut to a size the AI can handle."""
        limit = limit or settings.MAX_CONTEXT_CHARS
        out, used = [], 0
        for p in self.pages:
            block = f"[[PAGE {p.number}]]\n{p.text}"
            if used + len(block) > limit:
                out.append("\n[document truncated: remaining pages omitted]")
                break
            out.append(block)
            used += len(block)
        return "\n\n".join(out)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Document":
        return Document(
            policy_id=d["policy_id"],
            url=d["url"],
            is_pdf=d["is_pdf"],
            pages=[Page(**p) for p in d["pages"]],
        )


# ---------- parsing helpers ----------

def _parse_pdf(data: bytes) -> list[str]:
    try:
        reader = PdfReader(io.BytesIO(data))
        return [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as e:  # pypdf raises many different errors
        raise DocumentError(f"Could not read this PDF: {e}") from e


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    # PIB press releases keep the article in this container; fall back to the whole page.
    main = soup.select_one(".innner-page-main-about-us-content-right-part") or soup.body or soup
    lines = [ln.strip() for ln in main.get_text("\n").splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _split_text(text: str, size: int = HTML_PAGE_SIZE) -> list[str]:
    pages, current = [], ""
    for para in text.split("\n"):
        if current and len(current) + len(para) > size:
            pages.append(current)
            current = ""
        current += para + "\n"
    if current.strip():
        pages.append(current)
    return pages


# ---------- main entry point ----------

def _cache_path(policy_id: str):
    return settings.INDEX_DIR / "docs" / f"{policy_id}.json"


def load_document(policy: Policy) -> Document:
    cache = _cache_path(policy.id)
    if cache.exists():
        return Document.from_dict(json.loads(cache.read_text(encoding="utf-8")))

    body, content_type, encoding = _download_document(policy.url)
    is_pdf = body[:5] == b"%PDF-" or "pdf" in content_type.lower()
    if is_pdf:
        (settings.PDF_DIR / f"{policy.id}.pdf").write_bytes(body)
        page_texts = _parse_pdf(body)
    else:
        page_texts = _split_text(_html_to_text(body.decode(encoding, errors="replace")))

    if not any(t.strip() for t in page_texts):
        raise DocumentError(
            "No readable text found in this document (it may be a scanned image; OCR is not enabled)."
        )

    doc = Document(
        policy_id=policy.id,
        url=policy.url,
        is_pdf=is_pdf,
        pages=[Page(i + 1, t) for i, t in enumerate(page_texts)],
    )
    cache.write_text(json.dumps(doc.to_dict(), ensure_ascii=False), encoding="utf-8")
    return doc
