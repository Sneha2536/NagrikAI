"""
ask.py: the "Ask about this policy" chat box.

This is the full RAG loop:
  1. CONTEXT: short documents go to the AI whole; long ones are searched (context.py, search_index.py)
  2. GENERATE an answer from only that text (llm.py)
  3. VERIFY the quotes (citations.py). No verified citation = we refuse to answer.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.citations import verify_points
from ai.llm import generate_json
from ai.context import build_context
from ai.prompts import ASK_SYSTEM
from ai.translate import LANGUAGES
from routes._common import require_document, require_policy

router = APIRouter(prefix="/api", tags=["ask"])

REFUSAL = {
    "en": "I could not find this in the selected policy, so I won't guess. Try rephrasing, or open the official document.",
    "hi": "यह जानकारी चुनी गई नीति में नहीं मिली, इसलिए मैं अनुमान नहीं लगाऊँगा। प्रश्न दोबारा लिखें या आधिकारिक दस्तावेज़ देखें।",
    "bn": "এই তথ্যটি নির্বাচিত নীতিতে পাওয়া যায়নি, তাই আমি অনুমান করব না। অনুগ্রহ করে অন্যভাবে প্রশ্ন করুন অথবা মূল সরকারি নথিটি দেখুন।",
    "ta": "தேர்ந்தெடுக்கப்பட்ட கொள்கையில் இந்தத் தகவல் கிடைக்கவில்லை, எனவே நான் யூகிக்க மாட்டேன். கேள்வியை மாற்றி அமைக்கவும் அல்லது அதிகாரப்பூர்வ ஆவணத்தைப் பார்க்கவும்.",
    "te": "ఎంచుకున్న విధానంలో ఈ సమాచారం కనుగొనబడలేదు, కాబట్టి నేను ఊహించను. దయచేసి ప్రశ్నను మళ్లీ రాయండి లేదా అధికారిక పత్రాన్ని చూడండి.",
    "mr": "ही माहिती निवडलेल्या धोरणात आढळली नाही, म्हणून मी अंदाज लावणार नाही. कृपया प्रश्न पुन्हा लिहा किंवा अधिकृत दस्तऐवज पहा.",
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

    refusal = REFUSAL.get(req.language, REFUSAL["en"])
    context = build_context(doc, question)
    if not context:
        return {"answerable": False, "answer": refusal, "citations": []}

    prompt = (
        f"LANGUAGE FOR ANSWER: {LANGUAGES[req.language]}\n"
        f"QUESTION: {question}\n\nDOCUMENT TEXT:\n{context}"
    )
    raw = generate_json(ASK_SYSTEM, prompt)
    if not isinstance(raw, dict):
        return {"answerable": False, "answer": refusal, "citations": []}
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
