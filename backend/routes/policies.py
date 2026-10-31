"""
policies.py: the "Policy Explorer" screen talks to these endpoints.

GET  /api/policies/search          search + filters across all official sources
POST /api/policies/from-url        add an official document by pasting its link
GET  /api/policies/{id}            details of one policy
GET  /api/policies/{id}/document   the document text, page by page (left pane of Explainer)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from pdf_reader import DocumentError
from routes._common import require_document, require_policy
from sources import custom
from sources.registry import register_policy, search_policies

router = APIRouter(prefix="/api/policies", tags=["policies"])


class FromUrlRequest(BaseModel):
    url: str
    title: str | None = None


@router.get("/search")
def search(
    q: str | None = None,
    ministry: str | None = None,
    state: str | None = None,
    category: str | None = None,
    beneficiary: str | None = Query(None, description="students|farmers|parents|seniors|other"),
    date: str | None = Query(None, description="7d|30d|90d|365d"),
    policy_only: bool = Query(True, description="hide PIB releases that do not look like policies"),
):
    return search_policies(q, ministry, state, category, beneficiary, date, policy_only)


@router.post("/from-url")
def from_url(req: FromUrlRequest):
    try:
        policy = custom.add_from_url(req.url, req.title)
    except custom.InvalidLink as e:
        raise HTTPException(400, str(e)) from e
    except DocumentError as e:
        raise HTTPException(422, str(e)) from e
    register_policy(policy)
    return policy.to_dict()


@router.get("/{policy_id}")
def get_one(policy_id: str):
    return require_policy(policy_id).to_dict()


@router.get("/{policy_id}/document")
def get_document(policy_id: str):
    policy = require_policy(policy_id)
    doc = require_document(policy)
    return {
        "policy": policy.to_dict(),
        "is_pdf": doc.is_pdf,
        "pages": [{"number": p.number, "text": p.text} for p in doc.pages],
    }
