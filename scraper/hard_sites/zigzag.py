"""zigzag.am — Cloudflare-protected. Needs the weekly manual solve
(run_manual_weekly.py). Selectors are generic/best-effort (see
generic_extract.py) since the real markup is only visible once past the
challenge — tighten this module once you've seen a real run.
"""
from __future__ import annotations

from . import generic_extract
from ..sites.base import ScrapedProduct

SITE_NAME = "zigzag"
LISTING_URL = "https://www.zigzag.am/en/air-conditioning-equipment/ir-purifiers.html"


def looks_blocked(page) -> bool:
    return generic_extract.looks_blocked(page)


def scrape(page) -> list[ScrapedProduct]:
    return generic_extract.extract(page)
