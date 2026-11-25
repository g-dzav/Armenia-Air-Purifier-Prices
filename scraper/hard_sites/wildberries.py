"""wildberries.am — Armenia storefront of Wildberries. Its own "Checking
your browser" interstitial needs the weekly manual solve (confirmed live:
even undetected-chromedriver alone doesn't get past it headlessly — it
needs an actual human-cleared session). Once past it, real selectors
confirmed against a live manual-run debug dump (Nov 2026) — Wildberries
ships clean `data-testid` attributes on every product card, no scraping-
hostile markup at all once the interstitial is cleared:

  article.product-card[data-nm-id]            <- one product card
    a[data-testid="product-card-link"][href]
    [data-testid="productName"]                <- clean product name
    ins[data-testid="product-card-current-price"]   <- current price
    del                                              <- pre-discount price, if on sale
    [data-testid="catalogCardRating"]               <- e.g. "4,8" (comma decimal)
    [data-testid="catalogCardCommentCount"]         <- e.g. "·  142 оценки"

No explicit brand field on the card — falls back to normalize.guess_brand
same as every other site without one.

Prices render with literal "&nbsp;" thousand separators (e.g.
"50&nbsp;920&nbsp;֏") — BeautifulSoup decodes that to a real non-breaking
space when reading .get_text(), and normalize.parse_amd() already strips
all non-digit characters, so no special handling is needed beyond that.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..normalize import guess_brand, parse_amd
from ..sites.base import ScrapedProduct

SITE_NAME = "wildberries"
LISTING_URL = "https://www.wildberries.am/catalog/0/search.aspx?search=очиститель воздуха"


def looks_blocked(driver) -> bool:
    from . import generic_extract
    if generic_extract.looks_blocked(driver):
        return True
    return "invalid token" in (driver.execute_script(
        "return document.body ? document.body.innerText : ''"
    ) or "").lower()


def scrape(driver) -> list[ScrapedProduct]:
    soup = BeautifulSoup(driver.page_source, "lxml")

    products = []
    for card in soup.select("article.product-card[data-nm-id]"):
        link = card.select_one('a[data-testid="product-card-link"][href]')
        name_el = card.select_one('[data-testid="productName"]')
        price_el = card.select_one('[data-testid="product-card-current-price"]')
        if not link or not name_el or not price_el:
            continue

        price_amd = parse_amd(price_el.get_text())
        if price_amd is None:
            continue

        old_price_el = card.select_one("del")
        list_price_amd = parse_amd(old_price_el.get_text()) if old_price_el else None

        rating_el = card.select_one('[data-testid="catalogCardRating"]')
        rating = None
        if rating_el:
            try:
                rating = float(rating_el.get_text(strip=True).replace(",", "."))
            except ValueError:
                pass

        review_count = None
        count_el = card.select_one('[data-testid="catalogCardCommentCount"]')
        if count_el:
            digits = re.sub(r"[^\d]", "", count_el.get_text())
            review_count = int(digits) if digits else None

        name = name_el.get_text(strip=True)
        products.append(ScrapedProduct(
            external_id=card.get("data-nm-id", link["href"].rstrip("/").split("/")[-1]),
            name=name,
            product_url=link["href"],
            price_amd=price_amd,
            brand=guess_brand(name),
            list_price_amd=list_price_amd if list_price_amd and list_price_amd > price_amd else None,
            rating=rating,
            review_count=review_count,
        ))
    return products
