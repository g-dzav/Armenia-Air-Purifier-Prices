"""eldorado.am — Cloudflare-protected. Needs the weekly manual solve.
Generic/best-effort extraction (see generic_extract.py) has worked fine
here in practice (confirmed live: 9 and 31 products across two manual
runs), so no dedicated parser needed yet.
"""
from __future__ import annotations

from . import generic_extract
from ..sites.base import ScrapedProduct

SITE_NAME = "eldorado"
LISTING_URL = "https://eldorado.am/en/climate/air-purifiers"


def looks_blocked(page) -> bool:
    return generic_extract.looks_blocked(page)


def scrape(page) -> list[ScrapedProduct]:
    return generic_extract.extract(page)
