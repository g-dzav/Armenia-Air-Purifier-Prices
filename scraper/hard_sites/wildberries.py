"""wildberries.am — Armenia storefront of Wildberries.

Wildberries' storefront normally talks to open, unauthenticated JSON
endpoints (search.wb.ru / card.wb.ru) that plenty of unofficial tools rely
on. From the environment this was built in, both that API and the
wildberries.am search page itself came back blocked (HTTP 403 / 498 —
Wildberries' own "invalid token" status), which may just be a side effect
of that environment's outbound IP rather than something that'll also block
GitHub Actions or your own connection.

Worth trying as a cheap automated win:
  curl -A "Mozilla/5.0" "https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm=<some_nm_id>"
If that returns real JSON from GitHub Actions, switch run_daily.py to call
it directly with httpx instead of going through this module (much
cheaper/faster than a browser). Until confirmed, this ships as part of the
manual weekly tier to be safe.
"""
from __future__ import annotations

from . import generic_extract
from ..sites.base import ScrapedProduct

SITE_NAME = "wildberries"
LISTING_URL = "https://www.wildberries.am/catalog/0/search.aspx?search=очиститель воздуха"


def looks_blocked(page) -> bool:
    if generic_extract.looks_blocked(page):
        return True
    # Wildberries' own soft-block page doesn't match the generic markers.
    return "invalid token" in (page.inner_text("body") or "").lower()


def scrape(page) -> list[ScrapedProduct]:
    return generic_extract.extract(page)
