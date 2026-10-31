"""
registry.py: asks ALL source connectors at once and combines the results.

- Each source runs in parallel (so one slow site doesn't block the others).
- If a source fails, we still return the others and report which one failed.
  That is "graceful failure": the app keeps working and tells the truth.
- Every policy we see is saved in data/index/catalog.json so later requests
  (explain, ask, eligibility) can look it up by id.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from config import settings
from sources import myscheme, pib
from sources.base import Policy, SourceNotConfigured, SourceUnavailable

SOURCES = [pib, myscheme]
CATALOG = settings.INDEX_DIR / "catalog.json"

# Beneficiary chips in the UI -> words we look for in the policy text
BENEFICIARY_KEYWORDS = {
    "students": ["student", "scholarship", "education", "school", "college", "university", "छात्र", "विद्यार्थी", "शिक्षा", "छात्रवृत्ति", "विश्वविद्यालय"],
    "farmers": ["farmer", "agricultur", "kisan", "crop", "irrigation", "किसान", "कृषि", "फसल", "सिंचाई"],
    "parents": ["parent", "child", "mother", "maternity", "women and child", "family", "माता", "बच्चे", "बच्चों", "मातृत्व", "परिवार"],
    "seniors": ["senior citizen", "elderly", "old age", "pension", "aged", "वरिष्ठ नागरिक", "बुजुर्ग", "पेंशन"],
    "other": ["disab", "divyang", "minority", "tribal", "scheduled caste", "transgender", "widow", "दिव्यांग", "अल्पसंख्यक", "जनजाति", "अनुसूचित", "विधवा"],
}
DATE_WINDOWS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}


def _load_catalog() -> dict:
    if CATALOG.exists():
        return json.loads(CATALOG.read_text(encoding="utf-8"))
    return {}


def _save_catalog(policies: list[Policy]) -> None:
    catalog = _load_catalog()
    for p in policies:
        catalog[p.id] = p.to_dict()
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")


def get_policy(policy_id: str) -> Policy | None:
    d = _load_catalog().get(policy_id)
    return Policy(**d) if d else None


def register_policy(policy: Policy) -> None:
    """Make a policy known to the app (used when a user pastes an official link)."""
    _save_catalog([policy])


def _run_source(module, query):
    try:
        return module.NAME, module.fetch(query), None
    except SourceNotConfigured as e:
        return module.NAME, [], ("skipped", str(e))
    except SourceUnavailable as e:
        return module.NAME, [], str(e)
    except Exception as e:  # a bug in one connector must never take the app down
        return module.NAME, [], f"unexpected error: {e}"


def _matches(p: Policy, ministry, state, category, beneficiary, since, policy_only=True) -> bool:
    if policy_only and p.source == "PIB" and "policy-like" not in p.tags:
        return False
    text = f"{p.title} {p.summary} {' '.join(p.tags)} {p.category}".lower()
    if ministry and ministry.lower() not in p.authority.lower():
        return False
    if state and p.states and state not in p.states:
        return False
    if category and category.lower() not in f"{p.category} {' '.join(p.tags)}".lower():
        return False
    if beneficiary and beneficiary in BENEFICIARY_KEYWORDS:
        if not any(k in text for k in BENEFICIARY_KEYWORDS[beneficiary]):
            return False
    if since and p.published and p.published < since:
        return False
    return True


def search_policies(query=None, ministry=None, state=None, category=None,
                    beneficiary=None, date_window=None, policy_only=True) -> dict:
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        results = list(pool.map(lambda m: _run_source(m, query), SOURCES))

    all_policies, status = [], []
    for name, policies, error in results:
        skipped = isinstance(error, tuple)  # optional source with no API key: not a failure
        status.append({
            "source": name,
            "ok": error is None,
            "skipped": skipped,
            "count": len(policies),
            "error": error[1] if skipped else error,
        })
        all_policies.extend(policies)
    _save_catalog(all_policies)

    # Include previously saved custom/pasted documents so they remain discoverable in Explorer
    catalog = _load_catalog()
    combined_by_id = {k: Policy(**v) for k, v in catalog.items()}
    for p in all_policies:
        combined_by_id[p.id] = p
    combined = list(combined_by_id.values())

    since = None
    if date_window in DATE_WINDOWS:
        since = (date.today() - timedelta(days=DATE_WINDOWS[date_window])).isoformat()

    items = [p for p in combined if _matches(p, ministry, state, category, beneficiary, since, policy_only)]
    items.sort(key=lambda p: (1 if p.source == "Official link" else 0, p.published or ""), reverse=True)
    return {"items": [p.to_dict() for p in items], "sources": status}
