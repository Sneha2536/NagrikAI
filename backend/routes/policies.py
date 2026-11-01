"""
policies.py: the "Policy Explorer" screen talks to these endpoints.

GET  /api/policies/search          search + filters across all official sources
POST /api/policies/from-url        add an official document by pasting its link
POST /api/policies/upload          add a document by uploading a PDF (raw file as the request body)
GET  /api/policies/{id}            details of one policy
GET  /api/policies/{id}/document   the document text, page by page (left pane of Explainer)
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from pdf_reader import DocumentError
from routes._common import require_document, require_policy
from config import settings
from sources import custom, upload
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


@router.post("/upload")
async def upload_pdf(request: Request, filename: str = Query("document.pdf", max_length=200)):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > settings.MAX_DOCUMENT_BYTES:
        raise HTTPException(413, "The file is too large.")
    body = await request.body()
    try:
        policy = await run_in_threadpool(upload.add_upload, filename, body)   # parsing is slow: keep it off the event loop
    except upload.InvalidUpload as e:
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
