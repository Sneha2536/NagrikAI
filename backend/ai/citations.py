"""
citations.py: the anti-hallucination guard.

The AI gives us a claim plus a "quote" it says is copied from the document.
We do NOT trust it. We search the real document for that quote:
  - found     -> attach the true page number and clause, keep the point
  - not found -> DROP the point (the AI probably made it up)

This confirms that a returned quotation appears in the document. It does not prove
that the associated explanation is entailed by that quotation.
"""
import re

from pdf_reader import Document

# Matches lines like "5. Eligibility", "Clause 5.", "Section 2.1)", "Rule 7 "
# Either a keyword + number ("Clause 5", "Section 2.1") or a number WITH a dot/bracket ("5.", "2.1)").
# A bare number such as "30 OCT 2026" is a date, not a clause.
CLAUSE_RE = re.compile(
    r"^[ \t]*(?:(?P<kw>Clause|Section|Para|Paragraph|Article|Rule)\s+(?P<kw_num>\d+(?:\.\d+)*[A-Za-z]?)[.)]?"
    r"|(?P<plain_num>\d+(?:\.\d+)*[A-Za-z]?)[.)])\s+\S",
    re.M,
)
# Matches sub-clauses like "(a) ...", "(iv) ..."
SUB_RE = re.compile(r"^[ \t]*\(([a-z]{1,3}|[ivx]+|\d+)\)\s+\S", re.M)


def _normalise(text: str) -> tuple[str, list[int]]:
    """Lowercase, keep only letters/digits. Also return where each kept char was originally."""
    chars, index = [], []
    for i, ch in enumerate(text):
        if ch.isalnum():
            chars.append(ch.lower())
            index.append(i)
    return "".join(chars), index


def clause_at(page_text: str, offset: int) -> str:
    """Find the clause heading that most recently appeared before `offset` on the page."""
    label = ""
    clause_start = 0
    for m in CLAUSE_RE.finditer(page_text):
        if m.start() > offset:
            break
        # A bare "2. Eligibility" may be a list heading or a document section;
        # retain a clause label only when the source explicitly names its type.
        if m.group("kw"):
            label = f"{m.group('kw')} {m.group('kw_num')}"
            clause_start = m.start()
        else:
            label = ""
            clause_start = 0
    if not label:
        return ""
    sub = ""
    for m in SUB_RE.finditer(page_text, clause_start):
        if m.start() > offset:
            break
        sub = f"({m.group(1)})"
    return f"{label}{sub}"


def locate_quote(quote: str, doc: Document, hint_page: int | None = None):
    """Return (page_number, clause) if the quote exists in the document, else None."""
    if not isinstance(quote, str):
        return None
    needle_full, _ = _normalise(quote or "")
    if len(needle_full) < 15:
        return None
    pages = sorted(doc.pages, key=lambda p: 0 if p.number == hint_page else 1)
    for page in pages:
        norm, idx = _normalise(page.text)
        pos = norm.find(needle_full)
        if pos >= 0:
            return page.number, clause_at(page.text, idx[pos])
    return None


def verify_points(points, doc: Document, text_key: str = "text"):
    """
    Check a list of AI points. Returns (verified_points, dropped_count).
    Each verified point: {text, quote, page, clause}
    """
    verified, dropped = [], 0
    for p in points or []:
        if not isinstance(p, dict):
            dropped += 1
            continue
        hit = locate_quote(p.get("quote", ""), doc, _as_int(p.get("page")))
        text = p.get(text_key) or p.get("criterion") or ""
        if not hit or not isinstance(text, str) or not text.strip():
            dropped += 1
            continue
        page, clause = hit
        verified.append({**p, "text": text, "page": page, "clause": clause})
    return verified, dropped


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
