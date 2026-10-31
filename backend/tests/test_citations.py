"""
Tests for the anti-hallucination guard. Run from backend/:  pytest
The text below is a tiny made-up sample used ONLY to test the matching logic.
It is never shown to users.
"""
from ai.citations import locate_quote, verify_points
from ai.search_index import BM25Index, chunk_document
from pdf_reader import Document, Page

DOC = Document(
    policy_id="t",
    url="http://example.invalid",
    is_pdf=False,
    pages=[
        Page(1, "1. Short title\nThis scheme is called the Sample Scheme.\n"),
        Page(
            2,
            "2. Eligibility\n(a) The applicant must be between 18 and 35 years of age.\n"
            "(b) Annual family income must not exceed rupees two lakh.\n",
        ),
    ],
)


def test_finds_real_quote_with_page_and_clause():
    page, clause = locate_quote("applicant must be between 18 and 35 years of age", DOC)
    assert page == 2
    assert clause == ""


def test_ignores_case_and_spacing():
    assert locate_quote("THE  APPLICANT must be between 18 AND 35 years of age.", DOC)[0] == 2


def test_rejects_invented_quote():
    assert locate_quote("applicants must be over sixty years old and unemployed", DOC) is None


def test_rejects_quote_when_only_its_prefix_matches():
    assert locate_quote("applicant must be between 18 and 35 years of age and receives a laptop", DOC) is None


def test_verify_points_drops_fabricated_claims():
    points = [
        {"text": "Age 18-35", "quote": "must be between 18 and 35 years of age", "page": 2},
        {"text": "Free laptop", "quote": "every applicant receives a free laptop computer", "page": 1},
    ]
    verified, dropped = verify_points(points, DOC)
    assert [v["text"] for v in verified] == ["Age 18-35"]
    assert dropped == 1


def test_bm25_ranks_relevant_chunk_first():
    index = BM25Index(chunk_document(DOC))
    top = index.search("what is the income limit", k=1)[0]
    assert top["page"] == 2


def test_date_line_is_not_mistaken_for_a_clause():
    press = Document(
        policy_id="p", url="http://example.invalid", is_pdf=False,
        pages=[Page(1, "30 OCT 2026 8:19PM by PIB Delhi\nThe deadline has been extended to 13 November 2026 for all stakeholders.\n")],
    )
    page, clause = locate_quote("deadline has been extended to 13 November 2026", press)
    assert page == 1
    assert clause == ""


def test_keyword_clause_with_dot():
    d = Document(policy_id="k", url="x", is_pdf=False,
                 pages=[Page(1, "Section 4. Benefits\nEvery beneficiary shall receive monthly support of rupees five hundred.\n")])
    assert locate_quote("beneficiary shall receive monthly support of rupees five hundred", d) == (1, "Section 4")
