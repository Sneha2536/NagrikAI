import ssl
from pathlib import Path

import certifi
import pytest

import pdf_reader
from pdf_reader import DocumentError, _download_document, _verification_context
from config import settings
from sources.base import Policy


def test_verification_context_keeps_tls_verification_enabled(monkeypatch):
    monkeypatch.setattr(settings, "PDF_CA_BUNDLE", "")

    context = _verification_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_configured_ca_bundle_is_added_to_verified_system_roots(monkeypatch, tmp_path):
    bundle = tmp_path / "additional-ca.pem"
    bundle.write_bytes(Path(certifi.where()).read_bytes())
    monkeypatch.setattr(settings, "PDF_CA_BUNDLE", str(bundle))

    context = _verification_context()

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED


def test_invalid_ca_bundle_fails_with_clear_document_error(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "PDF_CA_BUNDLE", str(tmp_path / "missing.pem"))

    with pytest.raises(DocumentError, match="PDF_CA_BUNDLE"):
        _verification_context()


def test_document_download_uses_verified_context_and_keeps_request_options(monkeypatch, tmp_path):
    cache = tmp_path / "document.json"
    monkeypatch.setattr(pdf_reader, "_cache_path", lambda _: cache)
    monkeypatch.setattr(settings, "PDF_CA_BUNDLE", "")
    captured = {}

    class Response:
        content = b"<html><body>Official policy text with enough readable content.</body></html>"
        headers = {"content-type": "text/html"}
        encoding = "utf-8"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        @staticmethod
        def raise_for_status():
            return None

        def iter_bytes(self, chunk_size):
            assert chunk_size == pdf_reader.DOWNLOAD_CHUNK_BYTES
            yield self.content

    def fake_stream(method, url, **kwargs):
        assert method == "GET"
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(pdf_reader.httpx, "stream", fake_stream)
    policy = Policy(id="tls-test", title="Policy", source="test", authority="test", url="https://example.gov.in/policy")

    pdf_reader.load_document(policy)

    context = captured["verify"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert captured["timeout"] == 60
    assert captured["follow_redirects"] is True


@pytest.mark.parametrize("content_length", ["5", None])
def test_download_rejects_oversized_response(monkeypatch, content_length):
    monkeypatch.setattr(settings, "MAX_DOCUMENT_BYTES", 4)

    class Response:
        headers = {"content-type": "application/pdf"}
        if content_length is not None:
            headers["content-length"] = content_length
        encoding = "utf-8"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def iter_bytes(chunk_size):
            yield b"abc"
            yield b"de"

    monkeypatch.setattr(pdf_reader.httpx, "stream", lambda *args, **kwargs: Response())

    with pytest.raises(DocumentError, match="download limit"):
        _download_document("https://example.gov.in/policy.pdf")
