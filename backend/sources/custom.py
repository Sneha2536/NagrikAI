"""
custom.py: add ANY official government document by pasting its link.

Why: news feeds are not the same as policies. The documents this project is built for
(gazette notifications, scheme guidelines, draft policies, municipal rules) are usually PDFs
on ministry or department websites. Paste the link, and NagrikAI fetches the real document,
registers it, and the Explainer / Ask / Eligibility screens work on it like any other policy.

Only official Indian government domains (.gov.in, .nic.in) are accepted.
"""
from urllib.parse import urlparse

from pdf_reader import Document, load_document
from sources.base import Policy, make_id

NAME = "Official link"
ALLOWED_SUFFIXES = (".gov.in", ".nic.in")


class InvalidLink(Exception):
    """The pasted link is not an acceptable official document link."""


def _validate(url: str) -> tuple[str, str]:
    url = (url or "").strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or not host:
        raise InvalidLink("Please paste a full link that starts with https://")
    if not any(host.endswith(s) or host == s.lstrip(".") for s in ALLOWED_SUFFIXES):
        raise InvalidLink(
            "Only official Government of India links are accepted (the address must end in .gov.in or .nic.in)."
        )
    return url, host


def _guess_title(doc: Document) -> str:
    """Use the first reasonably long line of the document as its title."""
    lines = [ln.strip() for ln in doc.pages[0].text.splitlines() if ln.strip()]
    for ln in lines[:15]:
        if len(ln) >= 20:
            return ln[:140]
    return (lines[0] if lines else "Official document")[:140]


def add_from_url(url: str, title: str | None = None) -> Policy:
    url, host = _validate(url)
    stub = Policy(
        id=make_id(url),
        title=title or "Official document",
        source=NAME,
        authority=host,
        url=url,
        category="Added by you",
    )
    doc = load_document(stub)  # downloads + parses; raises DocumentError if unreadable
    if not title:
        stub.title = _guess_title(doc)
    return stub
