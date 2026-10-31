"""
_common.py: small helpers shared by several routes.
"""
import json
from pathlib import Path

from fastapi import HTTPException

from pdf_reader import Document, DocumentError, load_document
from sources.base import Policy
from sources.registry import get_policy


def require_policy(policy_id: str) -> Policy:
    policy = get_policy(policy_id)
    if not policy:
        raise HTTPException(
            404,
            "Policy not found. Open it from Policy Explorer first so it is registered.",
        )
    return policy


def require_document(policy: Policy) -> Document:
    try:
        return load_document(policy)
    except DocumentError as e:
        raise HTTPException(422, str(e)) from e


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
