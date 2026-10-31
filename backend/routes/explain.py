"""
explain.py: powers "Understand this policy" (the three tabs on the Policy Explainer screen).

Pipeline:
  load document -> AI writes points with quotes -> citations.py verifies every quote
  -> (optional) translate -> cache -> return
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.citations import verify_points
from ai.llm import generate_json
from ai.prompts import EXPLAIN_SYSTEM
from ai.translate import LANGUAGES, ensure_english, translate_sections
from config import settings
from routes._common import read_json, require_document, require_policy, write_json

router = APIRouter(prefix="/api", tags=["explain"])
SECTIONS = ("simple", "detailed", "benefits")


class ExplainRequest(BaseModel):
    policy_id: str
    language: str = "en"
    refresh: bool = False  # the "Re-analyse" button sets this to true


def _cache(policy_id: str, lang: str):
    return settings.INDEX_DIR / "explanations" / f"{policy_id}_{lang}.v2.json"


@router.post("/explain")
def explain(req: ExplainRequest):
    if req.language not in LANGUAGES:
        raise HTTPException(400, f"Unsupported language '{req.language}'.")
    policy = require_policy(req.policy_id)

    if not req.refresh:
        cached = read_json(_cache(policy.id, req.language))
        if cached:
            return cached

    # English version first (the source of truth). Other languages translate from it.
    english = None if req.refresh else read_json(_cache(policy.id, "en"))
    if not english:
        doc = require_document(policy)
        prompt = (
            f"POLICY TITLE: {policy.title}\nISSUED BY: {policy.authority}\n\n"
            f"DOCUMENT:\n{doc.text_for_llm()}"
        )
        raw = generate_json(EXPLAIN_SYSTEM, prompt)
        if not isinstance(raw, dict):
            raise HTTPException(502, "The AI returned an invalid explanation. Please retry.")
        sections, dropped = {}, 0
        for name in SECTIONS:
            points = raw.get(name, [])
            if not isinstance(points, list):
                points = []
            sections[name], d = verify_points(points, doc)
            dropped += d
        sections = ensure_english(sections)
        english = {
            "policy": policy.to_dict(),
            "language": "en",
            "sections": sections,
            "stats": {"verified": sum(len(v) for v in sections.values()), "dropped": dropped},
        }
        write_json(_cache(policy.id, "en"), english)

    if req.language == "en":
        return english

    result = {
        **english,
        "language": req.language,
        "sections": translate_sections(english["sections"], req.language),
    }
    write_json(_cache(policy.id, req.language), result)
    return result
