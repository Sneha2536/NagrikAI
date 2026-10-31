"""
ask.py: the "Ask about this policy" chat box.

This is the full RAG loop:
  1. (if the question is not in English) translate it to English so it can match the document
  2. RETRIEVE the best chunks from THIS document only (search_index.py)
  3. GENERATE an answer from only those chunks (llm.py)
  4. VERIFY the quotes (citations.py). No verified citation = we refuse to answer.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.citations import verify_points
from ai.llm import generate_json
from ai.prompts import ASK_SYSTEM, GENERAL_QUERY_TRANSLATE_SYSTEM
from ai.search_index import get_index
from ai.translate import LANGUAGES
from routes._common import require_document, require_policy

router = APIRouter(prefix="/api", tags=["ask"])

REFUSAL = {
    "en": "I could not find this in the selected policy, so I won't guess. Try rephrasing, or open the official document.",
    "hi": "यह जानकारी चुनी गई नीति में नहीं मिली, इसलिए मैं अनुमान नहीं लगाऊँगा। प्रश्न दोबारा लिखें या आधिकारिक दस्तावेज़ देखें।",
}


class AskRequest(BaseModel):
    policy_id: str
    question: str
    language: str = "en"


@router.post("/ask")
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Please type a question.")
    if req.language not in LANGUAGES:
        raise HTTPException(400, f"Unsupported language '{req.language}'.")

    policy = require_policy(req.policy_id)
    doc = require_document(policy)

    search_query = question
    if req.language != "en":
        r = generate_json(GENERAL_QUERY_TRANSLATE_SYSTEM, question)
        search_query = r.get("english", question) if isinstance(r, dict) else question

    hits = get_index(doc).search(search_query, k=5)
    refusal = REFUSAL.get(req.language, REFUSAL["en"])
    if not hits:
        return {"answerable": False, "answer": refusal, "citations": []}

    excerpts = "\n\n".join(f"[[PAGE {h['page']}]]\n{h['text']}" for h in hits)
    prompt = (
        f"LANGUAGE FOR ANSWER: {LANGUAGES[req.language]}\n"
        f"QUESTION: {question}\n\nEXCERPTS:\n{excerpts}"
    )
    raw = generate_json(ASK_SYSTEM, prompt)
    citations, _ = verify_points(raw.get("citations", []), doc, text_key="quote")

    if not raw.get("answerable") or not raw.get("answer") or not citations:
        return {"answerable": False, "answer": refusal, "citations": []}
    return {
        "answerable": True,
        "answer": raw["answer"],
        "citations": [
            {"page": c["page"], "clause": c["clause"], "quote": c["quote"]} for c in citations
        ],
    }
