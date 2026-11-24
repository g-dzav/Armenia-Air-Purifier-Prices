"""vlv.am — not Cloudflare-gated, just a client-rendered SPA (React/Vue),
so plain httpx gets an empty shell. No human challenge, so this runs
headless and automated daily via run_automated(), not the manual tier.

Generic/best-effort extraction (see generic_extract.py) — their JS bundle
didn't reveal an easy JSON API to call directly in the time spent looking,
so this renders the page and reads the DOM/JSON-LD. Tighten with real
selectors once you've watched a run (it's headless, so take a screenshot
with page.screenshot() locally if you want to see what it saw).
"""
from __future__ import annotations

from . import generic_extract
from ..sites.base import ScrapedProduct

SITE_NAME = "vlv"
LISTING_URL = "https://vlv.am/en/category/air-purifiers"


def looks_blocked(page) -> bool:
    return generic_extract.looks_blocked(page)


def scrape(page) -> list[ScrapedProduct]:
    return generic_extract.extract(page)
