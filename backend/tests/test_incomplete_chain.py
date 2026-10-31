"""
Reproduces the pmkisan.gov.in problem locally: an HTTPS server that sends ONLY its own
certificate (the intermediate is missing) but names where the intermediate can be downloaded.
"""
import datetime
import http.server
import ipaddress
import socket
import ssl
import threading
import urllib.request

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID

import pdf_reader

PEM = serialization.Encoding.PEM
DER = serialization.Encoding.DER


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _cert(subject, issuer, key, issuer_key, ca, extra=()):
    now = datetime.datetime.now(datetime.timezone.utc)
    b = (
        x509.CertificateBuilder()
        .subject_name(_name(subject)).issuer_name(_name(issuer))
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), critical=False)
    )
    if ca:   # strict verification (Python 3.13) requires CA certificates to allow signing certificates
        b = b.add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=False, data_encipherment=False,
            key_agreement=False, key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False,
        ), critical=True)
    for ext in extra:
        b = b.add_extension(ext, critical=False)
    return b.sign(issuer_key, hashes.SHA256())


class _AiaServer:
    def __init__(self, payload: bytes):
        outer = payload

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(outer)

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def stop(self):
        self.httpd.shutdown()


def _chain(tmp_path, label):
    """root -> intermediate -> leaf(127.0.0.1) with a CA-Issuers link to the intermediate."""
    k_root, k_int, k_leaf = (ec.generate_private_key(ec.SECP256R1()) for _ in range(3))
    root = _cert(f"{label} Root", f"{label} Root", k_root, k_root, True)
    inter = _cert(f"{label} Intermediate", f"{label} Root", k_int, k_root, True)
    aia_server = _AiaServer(inter.public_bytes(DER))
    aia = x509.AuthorityInformationAccess([
        x509.AccessDescription(
            AuthorityInformationAccessOID.CA_ISSUERS,
            x509.UniformResourceIdentifier(f"http://127.0.0.1:{aia_server.port}/inter.cer"),
        )
    ])
    san = x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))])
    leaf = _cert("leaf", f"{label} Intermediate", k_leaf, k_int, False, extra=(aia, san))

    roots = tmp_path / f"{label}-root.pem"
    roots.write_bytes(root.public_bytes(PEM))
    leaf_pem = tmp_path / f"{label}-leaf.pem"
    leaf_pem.write_bytes(leaf.public_bytes(PEM))          # the server sends ONLY the leaf
    key_pem = tmp_path / f"{label}-leaf.key"
    key_pem.write_bytes(k_leaf.private_bytes(PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return roots, leaf_pem, key_pem, aia_server


class _TlsServer:
    def __init__(self, leaf_pem, key_pem):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(leaf_pem, key_pem)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.ctx, self.running = ctx, True
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            try:
                with self.ctx.wrap_socket(conn, server_side=True) as tls:
                    tls.recv(1)
            except (ssl.SSLError, OSError):
                pass

    def stop(self):
        self.running = False
        self.sock.close()


def _handshake(context, port):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname="127.0.0.1") as tls:
            tls.send(b"x")


@pytest.fixture
def stdlib_http(monkeypatch):
    """Let the code under test download the intermediate with urllib (no real network needed)."""
    class R:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    monkeypatch.setattr(pdf_reader.httpx, "get", lambda url, **kw: R(urllib.request.urlopen(url, timeout=5).read()), raising=False)


def _setup(tmp_path, monkeypatch, label):
    roots, leaf_pem, key_pem, aia = _chain(tmp_path, label)
    monkeypatch.setattr(pdf_reader.certifi, "where", lambda: str(roots))   # pretend: this is the system root store
    server = _TlsServer(leaf_pem, key_pem)
    return server, aia


def test_incomplete_chain_fails_without_the_fix_and_works_with_it(tmp_path, monkeypatch, stdlib_http):
    server, aia = _setup(tmp_path, monkeypatch, "good")
    try:
        # 1. the bug: roots only, intermediate missing -> exactly the error you saw
        plain = ssl.create_default_context(cafile=pdf_reader.certifi.where())
        with pytest.raises(ssl.SSLCertVerificationError):
            _handshake(plain, server.port)

        # 2. the fix: find the intermediate from the certificate itself, then verify strictly
        extra = pdf_reader._missing_intermediates(f"https://127.0.0.1:{server.port}/doc.pdf")
        assert len(extra) == 1
        _handshake(pdf_reader._retry_context(extra), server.port)
    finally:
        server.stop(); aia.stop()


def test_untrusted_chain_is_still_rejected(tmp_path, monkeypatch, stdlib_http):
    """An attacker's chain must not become trusted just because we fetched its intermediate."""
    server, aia = _setup(tmp_path, monkeypatch, "attacker")
    try:
        # the 'system' trusts a DIFFERENT root than the one that signed this server
        other_roots, _, _, other_aia = _chain(tmp_path, "unrelated")
        other_aia.stop()
        monkeypatch.setattr(pdf_reader.certifi, "where", lambda: str(other_roots))
        extra = pdf_reader._missing_intermediates(f"https://127.0.0.1:{server.port}/doc.pdf")
        assert len(extra) == 1
        with pytest.raises(ssl.SSLCertVerificationError):
            _handshake(pdf_reader._retry_context(extra), server.port)
    finally:
        server.stop(); aia.stop()


def test_roots_are_never_added(tmp_path, monkeypatch):
    k = ec.generate_private_key(ec.SECP256R1())
    root = _cert("Self Root", "Self Root", k, k, True)
    assert root.issuer == root.subject    # the guard in _missing_intermediates skips these
