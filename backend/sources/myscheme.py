"""
myscheme.py: myScheme (myscheme.gov.in), the national catalogue of welfare schemes.

It exposes a search API that its own website uses. It needs an API key, which you set as
MYSCHEME_API_KEY in .env. If the key is missing we raise SourceUnavailable and the app
says so honestly instead of showing fake data.

NOTE: this endpoint is not officially documented. Run `python scripts/check_sources.py`
to confirm it works for you, and adjust the field names in _to_policy() if the response differs.
"""
import httpx

from config import settings
from sources.base import Policy, SourceNotConfigured, SourceUnavailable, make_id

NAME = "myScheme"
API_URL = "https://api.myscheme.gov.in/search/v4/schemes"
SITE_URL = "https://www.myscheme.gov.in/schemes/"
HEADERS = {
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": "Mozilla/5.0 (compatible; NagrikAI/1.0; civic-info-research)",
}


def _to_policy(hit: dict) -> Policy | None:
    f = hit.get("fields", {})
    slug = f.get("slug") or hit.get("id")
    title = f.get("schemeName")
    if not slug or not title:
        return None
    url = SITE_URL + slug
    states = f.get("beneficiaryState") or []
    return Policy(
        id=make_id(url),
        title=title,
        source=NAME,
        authority=f.get("nodalMinistryName") or "Government of India",
        url=url,
        published="",
        summary=f.get("briefDescription", "")[:400],
        category=", ".join(f.get("schemeCategory") or []),
        states=states if isinstance(states, list) else [states],
        tags=f.get("tags") or [],
    )


def fetch(query: str | None = None, limit: int = 20) -> list[Policy]:
    if not settings.MYSCHEME_API_KEY:
        raise SourceNotConfigured("MYSCHEME_API_KEY is not set in .env")
    try:
        r = httpx.get(
            API_URL,
            params={"lang": "en", "q": "[]", "keyword": query or "", "sort": "", "from": 0, "size": limit},
            headers={**HEADERS, "x-api-key": settings.MYSCHEME_API_KEY},
            timeout=30,
        )
        r.raise_for_status()
        hits = r.json().get("data", {}).get("hits", {}).get("items", [])
    except (httpx.HTTPError, ValueError) as e:
        raise SourceUnavailable(f"myScheme unavailable: {e}") from e
    return [p for p in (_to_policy(h) for h in hits) if p]
