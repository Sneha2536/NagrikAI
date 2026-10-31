"""
eligibility.py: the "Eligibility Checker" screen.

POST /api/eligibility/rules   AI extracts eligibility / documents / process from the policy (cited)
POST /api/eligibility/check   compares the citizen's details against those extracted rules

We never decide eligibility from the AI's memory: only from criteria that were found
in the official document AND verified by citations.py.
"""
import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai.citations import verify_points
from ai.llm import generate_json
from ai.prompts import CHECK_SYSTEM, RULES_SYSTEM
from ai.translate import LANGUAGES, ensure_english
from config import settings
from routes._common import read_json, require_document, require_policy, write_json

router = APIRouter(prefix="/api/eligibility", tags=["eligibility"])


class RulesRequest(BaseModel):
    policy_id: str


class Profile(BaseModel):
    age: int | None = None
    gender: str | None = None
    state: str | None = None
    annual_income: int | None = None
    category: str | None = None      # General / OBC / SC / ST / EWS
    occupation: str | None = None
    education: str | None = None
    disability: bool | None = None


class CheckRequest(BaseModel):
    policy_id: str
    profile: Profile
    language: str = "en"
    answers: dict[str, Any] = Field(default_factory=dict)
    follow_up_submitted: bool = False


PROFILE_FIELDS = {
    "age": "age",
    "income": "annual_income",
    "gender": "gender",
    "state": "state",
    "category": "category",
    "occupation": "occupation",
    "education": "education",
    "disability": "disability",
}
FIELD_QUESTIONS = {
    "age": ("number", "What is your age?"),
    "income": ("number", "What is your annual family income in rupees?"),
    "gender": ("text", "What is your gender, as relevant to this requirement?"),
    "state": ("text", "Which State or Union Territory applies to you?"),
    "category": ("text", "What social category applies to you, if any?"),
    "occupation": ("text", "What is your occupation?"),
    "education": ("text", "What is your education level?"),
    "disability": ("choice", "Does the complete requirement below describe your situation?"),
}


def _missing(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _question_specs(criteria: list[dict], profile: dict) -> list[dict]:
    """Build deterministic questions from source-verified criteria, never from model-made rules."""
    groups: dict[str, dict] = {}
    for index, criterion in enumerate(criteria):
        field = criterion.get("field")
        profile_field = PROFILE_FIELDS.get(field)
        criterion_text = criterion.get("text", "")
        normalized = criterion_text.casefold()
        # A broad profile education value does not answer these separate facts.
        specialized_education = field == "education" and any(
            term in normalized for term in ("percentile", "regular degree", "correspondence", "distance mode", "recognized", "regulatory body", "regulatory bodies", "aicte")
        )
        if profile_field and not _missing(profile.get(profile_field)) and not specialized_education:
            continue
        if specialized_education:
            question_id = f"criterion:{index}"
            profile_field = None
            if "percentile" in normalized or re.search(r"\b(?:score|marks)\b", normalized):
                answer_type = "number"
                question = "What percentile or qualifying examination score did you receive? Enter the value stated in your result."
            elif "recogniz" in normalized or "regulatory body" in normalized or "aicte" in normalized:
                answer_type = "choice"
                question = "Is your college or institution recognized by the regulatory body required by this criterion?"
            else:
                answer_type = "choice"
                question = "Are you enrolled in a regular degree course, rather than correspondence, distance education, or a diploma course?"
        elif field in FIELD_QUESTIONS:
            question_id = f"field:{field}"
            answer_type, question = FIELD_QUESTIONS[field]
        else:
            question_id = f"criterion:{index}"
            answer_type = "choice"
            question = "Does the complete requirement below describe your situation?"
        group = groups.setdefault(question_id, {
            "id": question_id,
            "question": question,
            "answer_type": answer_type,
            "answer_help": "Answer Yes only when the whole requirement is true for you. For a rule saying ‘must not’, answer Yes only if you do not do the restricted thing.",
            "profile_field": profile_field,
            "criteria": [],
        })
        group["criteria"].append({
            "criterion_id": index,
            "text": criterion.get("text", ""),
            "page": criterion.get("page"),
            "clause": criterion.get("clause", ""),
            "quote": criterion.get("quote", ""),
        })
    return list(groups.values())


def _validate_answers(specs: list[dict], answers: dict, profile: dict):
    """Accept only answers matching a current server-defined question and type."""
    by_id = {spec["id"]: spec for spec in specs}
    accepted, unknown_ids, boolean_statuses, not_sure_ids = {}, set(), {}, set()
    for answer_id, value in answers.items():
        spec = by_id.get(answer_id)
        if not spec:
            continue
        if value == "not_sure":
            unknown_ids.update(c["criterion_id"] for c in spec["criteria"])
            not_sure_ids.add(answer_id)
            continue
        if spec["answer_type"] == "choice":
            if not isinstance(value, str) or value.lower() not in ("yes", "no"):
                unknown_ids.update(c["criterion_id"] for c in spec["criteria"])
                continue
            for criterion in spec["criteria"]:
                boolean_statuses[criterion["criterion_id"]] = "met" if value.lower() == "yes" else "not_met"
            accepted[answer_id] = value.lower()
        elif spec["answer_type"] == "number":
            try:
                if isinstance(value, bool):
                    raise ValueError
                number = int(value)
                if str(value).strip() not in (str(number), f"{number}.0"):
                    raise ValueError
                if number < 0 or (spec["id"] == "field:age" and number > 120) or number > 1_000_000_000_000:
                    raise ValueError
            except (TypeError, ValueError, OverflowError):
                unknown_ids.update(c["criterion_id"] for c in spec["criteria"])
                continue
            if spec["profile_field"]:
                profile[spec["profile_field"]] = number
            accepted[answer_id] = number
        else:
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > 300:
                unknown_ids.update(c["criterion_id"] for c in spec["criteria"])
                continue
            if spec["profile_field"]:
                profile[spec["profile_field"]] = value.strip()
            accepted[answer_id] = value.strip()
    return accepted, unknown_ids, boolean_statuses, not_sure_ids


def _get_rules(policy_id: str) -> dict:
    # Re-extract once under the clarified positive-condition / exclusion wording.
    cache = settings.INDEX_DIR / "rules" / f"{policy_id}.v3.json"
    cached = read_json(cache)
    if cached:
        return cached
    policy = require_policy(policy_id)
    doc = require_document(policy)
    raw = generate_json(
        RULES_SYSTEM,
        f"POLICY TITLE: {policy.title}\n\nDOCUMENT:\n{doc.text_for_llm()}",
    )
    eligibility, _ = verify_points(raw.get("eligibility", []), doc, text_key="criterion")
    documents, _ = verify_points(raw.get("documents", []), doc)
    process, _ = verify_points(raw.get("process", []), doc)
    fixed = ensure_english({"eligibility": eligibility, "documents": documents, "process": process})
    rules = {"policy": policy.to_dict(), **fixed}
    write_json(cache, rules)
    return rules


@router.post("/rules")
def rules(req: RulesRequest):
    return _get_rules(req.policy_id)


@router.post("/check")
def check(req: CheckRequest):
    if req.language not in LANGUAGES:
        raise HTTPException(400, f"Unsupported language '{req.language}'.")
    rules_ = _get_rules(req.policy_id)
    criteria = rules_["eligibility"]
    if not criteria:
        return {
            "verdict": "no_criteria",
            "message": "This document does not state clear eligibility criteria, so NagrikAI cannot assess it.",
            "results": [],
            "follow_up_questions": [],
        }

    profile = req.profile.model_dump()
    question_specs = _question_specs(criteria, profile)
    accepted_answers, forced_unknown, boolean_statuses, not_sure_ids = _validate_answers(
        question_specs, req.answers, profile
    )

    prompt = (
        f"LANGUAGE FOR REASONS: {LANGUAGES[req.language]}\n"
        f"CITIZEN DETAILS: {json.dumps(profile, ensure_ascii=False)}\n"
        f"FOLLOW-UP ANSWERS: {json.dumps(accepted_answers, ensure_ascii=False)}\n"
        f"CRITERIA: {json.dumps([c['text'] for c in criteria], ensure_ascii=False)}"
    )
    raw = generate_json(CHECK_SYSTEM, prompt)
    raw_results = raw.get("results", []) if isinstance(raw, dict) else []
    by_index = {r.get("index"): r for r in raw_results if isinstance(r, dict)} if isinstance(raw_results, list) else {}

    missing_criteria = {
        criterion["criterion_id"]
        for spec in question_specs
        if spec["id"] not in accepted_answers and spec["id"] not in not_sure_ids
        for criterion in spec["criteria"]
    }
    results = []
    unanswered_criteria = set()
    if req.follow_up_submitted:
        for spec in question_specs:
            if spec["id"] not in accepted_answers:
                unanswered_criteria.update(c["criterion_id"] for c in spec["criteria"])
    for i, c in enumerate(criteria):
        r = by_index.get(i, {})
        status = r.get("status") if r.get("status") in ("met", "not_met", "unknown") else "unknown"
        reason = r.get("reason") if isinstance(r.get("reason"), str) else ""
        if i in boolean_statuses:
            status = boolean_statuses[i]
            reason = "You reported that the complete stated requirement " + ("describes your situation." if status == "met" else "does not describe your situation.")
        elif not req.follow_up_submitted and i in missing_criteria:
            status = "unknown"
            reason = "A required detail has not been provided yet."
        elif i in forced_unknown or i in unanswered_criteria:
            status = "unknown"
            reason = "This information was not provided or you selected Not sure."
        results.append(
            {
                "criterion": c["text"],
                "status": status,
                "reason": reason,
                "page": c["page"],
                "clause": c["clause"],
                "quote": c.get("quote", ""),
                "manual_verification": False,
            }
        )

    follow_up_questions = []
    if not req.follow_up_submitted:
        for spec in question_specs:
            if spec["id"] in accepted_answers or spec["id"] in not_sure_ids:
                continue
            unresolved = [c for c in spec["criteria"] if results[c["criterion_id"]]["status"] == "unknown"]
            if unresolved:
                follow_up_questions.append({**spec, "criteria": unresolved})

    question_criterion_ids = {
        criterion["criterion_id"]
        for question in follow_up_questions
        for criterion in question["criteria"]
    }
    for index, result in enumerate(results):
        if result["status"] == "unknown" and (req.follow_up_submitted or index not in question_criterion_ids):
            result["manual_verification"] = True
            result["reason"] = "The available details and answers do not establish this requirement. Please verify it with the scheme authority or source document."

    statuses = {r["status"] for r in results}
    verdict = "not_eligible" if "not_met" in statuses else "need_more_info" if "unknown" in statuses else "eligible"
    return {"verdict": verdict, "results": results, "follow_up_questions": follow_up_questions}
