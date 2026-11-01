import pytest

from ai import context
from ai.llm import LLMError
from config import settings
import pdf_reader
from pdf_reader import Document, DocumentError, Page, UPLOAD_SOURCE
from sources import registry, upload
from sources.base import Policy


def make_pdf(lines):
    """A tiny but valid one-page PDF containing the given lines of text."""
    stream = "BT /F1 12 Tf 50 750 Td 14 TL " + " ".join(f"({ln}) Tj T*" for ln in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


@pytest.fixture
def storage(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "pdfs").mkdir()
    monkeypatch.setattr(settings, "INDEX_DIR", tmp_path)
    monkeypatch.setattr(settings, "PDF_DIR", tmp_path / "pdfs")
    return tmp_path


def test_upload_is_parsed_labelled_and_survives_a_cache_loss(storage):
    pdf = make_pdf(["Scholarship for girls", "Annual family income must not exceed 800000 rupees"])
    policy = upload.add_upload("girls_scholarship-scheme.pdf", pdf)

    assert policy.source == UPLOAD_SOURCE and policy.url == ""
    assert policy.title == "girls scholarship scheme"
    assert "cannot verify" in policy.summary
    doc = pdf_reader.load_document(policy)
    assert "800000" in doc.pages[0].text

    # the cache can disappear (server restart); the saved PDF is read again
    (storage / "docs" / f"{policy.id}.json").unlink()
    assert "800000" in pdf_reader.load_document(policy).pages[0].text


def test_same_file_gives_same_policy_id(storage):
    pdf = make_pdf(["Same text"])
    assert upload.add_upload("a.pdf", pdf).id == upload.add_upload("b.pdf", pdf).id


@pytest.mark.parametrize("body,message", [
    (b"", "empty"),
    (b"not a pdf at all", "PDF"),
])
def test_bad_uploads_are_rejected(storage, body, message):
    with pytest.raises(upload.InvalidUpload, match=message):
        upload.add_upload("x.pdf", body)


def test_oversized_upload_is_rejected(storage, monkeypatch):
    monkeypatch.setattr(settings, "MAX_DOCUMENT_BYTES", 10)
    with pytest.raises(upload.InvalidUpload, match="too large"):
        upload.add_upload("x.pdf", b"%PDF-" + b"0" * 50)


def test_pdf_without_text_gives_a_clear_error(storage):
    with pytest.raises(DocumentError, match="No readable text|Could not read"):
        upload.add_upload("scan.pdf", make_pdf([""]))


# ---------------- Ask: what text the AI sees ----------------

def _doc(texts):
    return Document(policy_id="d", url="", is_pdf=True, pages=[Page(i + 1, t) for i, t in enumerate(texts)])


def test_short_document_goes_to_the_ai_whole_without_any_extra_ai_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no rewrite call expected for a short document")

    text = context.build_context(_doc(["Eligible beneficiaries are farmers.", "Apply at the block office."]), "who can apply?", boom)
    assert "[[PAGE 1]]" in text and "[[PAGE 2]]" in text and "farmers" in text


def test_long_document_question_is_rewritten_so_paraphrases_still_match(monkeypatch):
    monkeypatch.setattr(settings, "ASK_FULL_DOC_CHARS", 50)
    doc = _doc(["Introduction and background. " * 5, "Eligible beneficiaries shall be small farmers owning land.", "Penalties for misuse. " * 5])
    rewrite = lambda system, q: {"english": "Who is eligible", "keywords": ["eligible", "beneficiaries"]}
    text = context.build_context(doc, "who can apply?", rewrite)
    assert "small farmers" in text and "[[PAGE 2]]" in text


def test_long_document_falls_back_to_typed_question_if_rewrite_fails(monkeypatch):
    monkeypatch.setattr(settings, "ASK_FULL_DOC_CHARS", 50)
    doc = _doc(["Background text. " * 5, "Pension is paid monthly to widows.", "Other text. " * 5])

    def fail(*a, **k):
        raise LLMError("quota")

    assert "widows" in context.build_context(doc, "pension widows", fail)


def test_nothing_relevant_returns_empty(monkeypatch):
    monkeypatch.setattr(settings, "ASK_FULL_DOC_CHARS", 10)
    doc = _doc(["alpha beta gamma delta " * 3])
    assert context.build_context(doc, "zzzz qqqq", lambda s, q: {}) == ""


# ---------------- Explorer: filters built from what is really there ----------------

def test_facets_count_only_real_values():
    items = [
        Policy(id="1", title="Scholarship for students", source="PIB", authority="Ministry of Education", url="u", category="Press release", tags=["policy-like"]),
        Policy(id="2", title="Kisan credit", source="PIB", authority="Ministry of Agriculture", url="u", category="Press release", tags=["policy-like"]),
        Policy(id="3", title="Pension rules", source="Official link", authority="x.gov.in", url="u", category="Added by you", states=["Kerala"]),
    ]
    f = registry._facets(items)
    assert f["authority"]["Ministry of Education"] == 1
    assert f["category"] == {"Press release": 2, "Added by you": 1}
    assert f["states"] == {"Kerala": 1}
    assert f["beneficiary"]["students"] == 1 and f["beneficiary"]["farmers"] == 1 and f["beneficiary"]["seniors"] == 1
    assert f["total"] == 3
