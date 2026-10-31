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
import socket
import ssl
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

import certifi
import httpx
import truststore
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import AuthorityInformationAccessOID
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
MAX_CERT_BYTES = 100_000


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


def _is_cert_error(e: Exception) -> bool:
    return "CERTIFICATE_VERIFY_FAILED" in str(e)


# ---- Missing intermediate certificates ------------------------------------------------
# Many .gov.in servers send only their own certificate and omit the "intermediate" one.
# Browsers repair this by downloading the intermediate from the address written inside the
# certificate (the "CA Issuers" link). Python does not. We do the same, safely:
#   * only NON-self-signed certificates are added (we never add a new trusted root),
#   * the chain must still end at a root your system already trusts.

def _load_cert(data: bytes) -> x509.Certificate:
    try:
        return x509.load_der_x509_certificate(data)
    except ValueError:
        return x509.load_pem_x509_certificate(data)


def _issuer_url(cert: x509.Certificate) -> str | None:
    try:
        aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
    except x509.ExtensionNotFound:
        return None
    for d in aia:
        if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS and isinstance(
            d.access_location, x509.UniformResourceIdentifier
        ):
            value = d.access_location.value
            if value.lower().startswith(("http://", "https://")):
                return value
    return None


def _missing_intermediates(url: str) -> list[bytes]:
    """DER bytes of the intermediate certificates the server forgot to send (may be empty)."""
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port or 443
    if not host:
        return []
    found: list[bytes] = []
    try:
        probe = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)   # only used to READ the certificate
        probe.check_hostname = False
        probe.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=15) as raw, probe.wrap_socket(
            raw, server_hostname=host
        ) as tls:
            cert = _load_cert(tls.getpeercert(binary_form=True))
        for _ in range(4):                       # leaf -> intermediate -> intermediate ...
            issuer_url = _issuer_url(cert)
            if not issuer_url:
                break
            r = httpx.get(issuer_url, timeout=15, follow_redirects=True)
            r.raise_for_status()
            if len(r.content) > MAX_CERT_BYTES:
                break
            cert = _load_cert(r.content)
            if cert.issuer == cert.subject:      # self-signed = a root: never add it
                break
            found.append(cert.public_bytes(serialization.Encoding.DER))
    except (OSError, ValueError, httpx.HTTPError):
        pass                                     # keep whatever we found; the caller re-checks
    return found


def _retry_context(extra_der: list[bytes]) -> ssl.SSLContext:
    """Strict context: trusted roots + the recovered intermediates (as chain helpers only)."""
    context = ssl.create_default_context(cafile=certifi.where())
    context.load_default_certs()
    # Without this flag an intermediate in the store would itself be trusted. We want the
    # chain to reach a real root.
    context.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
    for der in extra_der:
        context.load_verify_locations(cadata=der)
    if settings.PDF_CA_BUNDLE:
        try:
            context.load_verify_locations(cafile=settings.PDF_CA_BUNDLE)
        except (OSError, ssl.SSLError) as e:
            raise DocumentError(f"Could not load the configured PDF_CA_BUNDLE: {e}") from e
    return context


def _fetch(url: str, context: ssl.SSLContext, limit: int) -> tuple[bytes, str, str]:
    with httpx.stream(
        "GET",
        url,
        headers=HEADERS,
        timeout=60,
        follow_redirects=True,
        verify=context,
    ) as response:
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > limit:
                    raise DocumentError(f"Document exceeds the {limit:,}-byte download limit.")
            except ValueError:
                pass  # A malformed header is still bounded while streaming below.

        chunks = []
        total = 0
        for chunk in response.iter_bytes(chunk_size=DOWNLOAD_CHUNK_BYTES):
            total += len(chunk)
            if total > limit:
                raise DocumentError(f"Document exceeds the {limit:,}-byte download limit.")
            chunks.append(chunk)
        return b"".join(chunks), response.headers.get("content-type", ""), response.encoding or "utf-8"


def _download_document(url: str) -> tuple[bytes, str, str]:
    """Stream a document with verified TLS and enforce the configured response-size cap."""
    limit = settings.MAX_DOCUMENT_BYTES
    if limit <= 0:
        raise DocumentError("MAX_DOCUMENT_BYTES must be greater than zero.")
    try:
        try:
            return _fetch(url, _verification_context(), limit)
        except httpx.ConnectError as e:
            if not _is_cert_error(e):
                raise
            extra = _missing_intermediates(url)
            if not extra:
                raise
            return _fetch(url, _retry_context(extra), limit)   # still fully verified
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
