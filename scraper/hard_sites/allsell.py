"""allsell.am — Cloudflare-protected. Needs the weekly manual solve.
Generic/best-effort extraction (see generic_extract.py) — tighten after a
real run once you can see the actual markup.
"""
from __future__ import annotations

from . import generic_extract
from ..sites.base import ScrapedProduct

SITE_NAME = "allsell"
LISTING_URL = "https://allsell.am/en/heating-and-cooling/air-humidifiers"


def looks_blocked(page) -> bool:
    return generic_extract.looks_blocked(page)


def scrape(page) -> list[ScrapedProduct]:
    return generic_extract.extract(page)
