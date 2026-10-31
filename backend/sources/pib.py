"""
pib.py: Press Information Bureau (pib.gov.in), the Government of India's official
announcements. We read PIB's public RSS feed: real, live, no API key needed.

Limit: an RSS feed only holds the most recent releases, so search here means
"filter recent releases". Use myscheme.py for the full scheme catalogue.
"""
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup

from config import settings
from sources.base import Policy, SourceUnavailable, make_id

NAME = "PIB"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NagrikAI/1.0; civic-info-research)"}


def _iso_date(raw: str) -> str:
    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _clean(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


# PIB publishes everything: speeches, ship visits, awards... A release is "policy-like" if its
# title or summary contains one of these words. Such releases get the tag "policy-like";
# the Explorer hides the others unless the user unticks "Policy-related only".
POLICY_WORDS = [
    "scheme", "yojana", "policy", "guideline", "notification", "notified", "cabinet", "approves",
    "approved", "mission", "subsidy", "benefit", "eligib", "regulation", "rules", "draft",
    "consultation", "stakeholder", "amendment", "bill", "circular", "advisory", "pension",
    "scholarship", "insurance", "portal", "launches", "framework", "msp", "support price",
    "योजना", "नीति", "दिशानिर्देश", "अधिसूचना", "मंत्रिमंडल", "मंजूरी", "अनुमोदन", "मिशन",
    "सब्सिडी", "लाभ", "पात्र", "नियम", "मसौदा", "परामर्श", "हितधारक", "संशोधन", "अधिनियम",
    "विधेयक", "परिपत्र", "एडवाइजरी", "पेंशन", "छात्रवृत्ति", "बीमा", "पोर्टल", "शुभारंभ",
    "समर्थन मूल्य",
]


def _looks_like_policy(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(w in text for w in POLICY_WORDS)


def fetch(query: str | None = None, limit: int = 30) -> list[Policy]:
    try:
        r = httpx.get(settings.PIB_RSS_URL, headers=HEADERS, timeout=30, follow_redirects=True)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except (httpx.HTTPError, ET.ParseError) as e:
        raise SourceUnavailable(f"PIB feed unavailable: {e}") from e

    items = []
    for item in root.iter("item"):
        title = _clean(item.findtext("title", ""))
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        summary = _clean(item.findtext("description", ""))[:400]
        if query and query.lower() not in f"{title} {summary}".lower():
            continue
        items.append(
            Policy(
                id=make_id(link),
                title=title,
                source=NAME,
                authority=_clean(item.findtext("author", "")) or "Press Information Bureau",
                url=link,
                published=_iso_date(item.findtext("pubDate", "")),
                summary=summary,
                category=_clean(item.findtext("category", "")) or "Press release",
                tags=["policy-like"] if _looks_like_policy(title, summary) else [],
            )
        )
        if len(items) >= limit:
            break
    return items
