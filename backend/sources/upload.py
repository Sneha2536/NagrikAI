"""
upload.py: add a document by uploading a PDF from your own computer.

Why: some documents (draft policies, municipal laws, old gazette scans) have no stable official
link, and some government websites fail to download. Uploading always works.

The uploaded file is NOT checked against an official website, so it is clearly labelled
"Uploaded by you" and "not verified as an official document".
"""
import hashlib
import re

from config import settings
from pdf_reader import UPLOAD_SOURCE, ingest_upload
from sources.base import Policy, make_id

NAME = UPLOAD_SOURCE


class InvalidUpload(Exception):
    """The uploaded file cannot be accepted."""


def _title_from_filename(filename: str) -> str:
    stem = re.sub(r"\.pdf$", "", (filename or "").strip(), flags=re.I)
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:140] if len(stem) >= 4 else "Uploaded document"


def add_upload(filename: str, body: bytes) -> Policy:
    limit = settings.MAX_DOCUMENT_BYTES
    if not body:
        raise InvalidUpload("The file is empty.")
    if len(body) > limit:
        raise InvalidUpload(f"The file is too large. The limit is {limit // (1024 * 1024)} MB.")
    if not body.startswith(b"%PDF-"):
        raise InvalidUpload("Only PDF files are supported.")

    digest = hashlib.sha1(body).hexdigest()
    policy = Policy(
        id=make_id(f"upload:{digest}"),     # same file uploaded twice = same policy
        title=_title_from_filename(filename),
        source=NAME,
        authority="Uploaded document",
        url="",                             # there is no website to open: the file lives on this server
        category="Uploaded PDF",
        summary="Uploaded by you. NagrikAI cannot verify that this is an official document.",
    )
    ingest_upload(policy, body)             # parses and caches; raises DocumentError if unreadable
    return policy
