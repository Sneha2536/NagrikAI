"""
check_sources.py: tests every government connector against the LIVE internet.

Run this FIRST when setting up, and before the demo:
    cd backend
    python ../scripts/check_sources.py
"""
import sys
from pathlib import Path

# Government source titles may contain any of India's scripts. On Windows the
# active console encoding is often cp1252, which cannot print those characters.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sources.base import SourceNotConfigured, SourceUnavailable  # noqa: E402
from sources.registry import SOURCES  # noqa: E402

for module in SOURCES:
    try:
        items = module.fetch(None)
        print(f"[OK]   {module.NAME}: {len(items)} policies")
        for p in items[:3]:
            print(f"         - {p.title[:80]}  ({p.published or 'no date'})")
    except SourceNotConfigured as e:
        print(f"[SKIP] {module.NAME}: {e} (optional)")
    except SourceUnavailable as e:
        print(f"[FAIL] {module.NAME}: {e}")
    except Exception as e:
        # Keep checking other connectors when one has an unexpected parsing error.
        print(f"[FAIL] {module.NAME}: unexpected {type(e).__name__}: {e}")
