"""
base.py: the shape of a "policy" shared by every source connector.

Each connector (pib.py, myscheme.py, ...) must return a list of Policy objects.
Adding a new government source = writing one new file that returns Policy objects.
"""
import hashlib
from dataclasses import asdict, dataclass, field


class SourceUnavailable(Exception):
    """A source could not be reached (network error, site down, bad response)."""


class SourceNotConfigured(SourceUnavailable):
    """An optional source is switched off because its API key is not in .env. Not an error."""


@dataclass
class Policy:
    id: str
    title: str
    source: str            # "PIB", "myScheme", ...
    authority: str         # issuing ministry / department
    url: str               # official document link
    published: str = ""    # ISO date (YYYY-MM-DD) or ""
    summary: str = ""
    category: str = ""
    states: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def make_id(url: str) -> str:
    """A short stable id derived from the official URL."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
