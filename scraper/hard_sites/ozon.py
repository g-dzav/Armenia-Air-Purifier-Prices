"""am.ozon.com — Armenia storefront of the Ozon marketplace. Heavy
in-house bot detection (not just Cloudflare), so this one most likely needs
the manual weekly solve every time, not just an occasional cookie refresh.
Prices on Ozon are shown in AMD for the Armenia storefront.
"""
from __future__ import annotations

from . import generic_extract
from ..sites.base import ScrapedProduct

SITE_NAME = "ozon"
LISTING_URL = "https://am.ozon.com/search/?text=%D0%BE%D1%87%D0%B8%D1%81%D1%82%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%20%D0%B2%D0%BE%D0%B7%D0%B4%D1%83%D1%85%D0%B0"


def looks_blocked(page) -> bool:
    return generic_extract.looks_blocked(page)


def scrape(page) -> list[ScrapedProduct]:
    return generic_extract.extract(page)
