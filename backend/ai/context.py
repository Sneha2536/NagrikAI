"""
context.py: decides WHICH text from the document the AI sees when answering a question.

Old behaviour: keyword search only. A question worded differently from the document
("who can apply?" vs "eligible beneficiaries") found nothing, so the app refused to answer.

Now:
  * Short and medium documents (most schemes): the AI reads the WHOLE document. Nothing to miss.
  * Very long documents: the AI first rewrites the question into the words a government document
    would use (plus keywords), then keyword search (BM25) picks the best passages.
The answer must still quote the document, and citations.py still checks every quote.
"""
from ai.llm import LLMError, generate_json
from ai.prompts import QUERY_REWRITE_SYSTEM
from ai.search_index import get_index
from config import settings
from pdf_reader import Document


def document_length(doc: Document) -> int:
    return sum(len(p.text) for p in doc.pages)


def build_context(doc: Document, question: str, llm_json=generate_json) -> str:
    """Text to show the AI. Empty string means nothing relevant was found."""
    limit = settings.ASK_FULL_DOC_CHARS
    if document_length(doc) <= limit:
        return doc.text_for_llm(limit)

    search_query = question
    try:
        rewritten = llm_json(QUERY_REWRITE_SYSTEM, question)
        if isinstance(rewritten, dict):
            keywords = rewritten.get("keywords")
            extra = " ".join(k for k in keywords if isinstance(k, str)) if isinstance(keywords, list) else ""
            english = rewritten.get("english")
            search_query = " ".join(x for x in (question, english if isinstance(english, str) else "", extra) if x)
    except LLMError:
        pass    # fall back to the question as typed; keyword search may still work

    hits = get_index(doc).search(search_query, k=8)
    return "\n\n".join(f"[[PAGE {h['page']}]]\n{h['text']}" for h in hits)
