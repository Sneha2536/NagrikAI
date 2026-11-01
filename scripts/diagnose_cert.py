"""
diagnose_cert.py: find out why a government link fails with a certificate error.

Run from the backend folder (venv active):
    python ../scripts/diagnose_cert.py "https://pmkisan.gov.in/Documents/RevisedPM-KISANOperationalGuidelines(English).pdf"

It prints each server the link passes through, who issued its certificate, and whether the
missing certificate could be recovered. Then it tries the real download.
"""
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pdf_reader  # noqa: E402

if len(sys.argv) != 2:
    sys.exit(__doc__)

url = sys.argv[1]
for hop in pdf_reader._redirect_chain(url):
    found, note = pdf_reader._missing_intermediates(hop)
    print(f"\n{urlparse(hop).hostname}\n  {note}\n  recovered certificates: {len(found)}")

print("\nTrying the real download...")
try:
    body, content_type, _ = pdf_reader._download_document(url)
    print(f"SUCCESS: {len(body):,} bytes ({content_type})")
except pdf_reader.DocumentError as e:
    print(f"FAILED: {e}")
