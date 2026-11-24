"""3dplanet.am — Dyson specialist, server-rendered HTML (Tailwind, no semantic
classes on the card itself, but each product carries clean data-* attributes
on its `.favorite-btn` button: data-id, data-name, data-price, data-url).

Only scrapes page 1: their robots.txt disallows any URL with a query string
(`Disallow: /*?*`), which is how their own sort/pagination controls work, so
this intentionally doesn't follow "page 2" links. Fine for a boutique
single-brand catalog (2 products as of Nov 2026); revisit if their catalog
grows past one page.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from ..normalize import guess_brand
from .base import ScrapedProduct

SITE_NAME = "3dplanet"
LISTING_URL = "https://3dplanet.am/en/store/air-purifiers"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; price-tracker/1.0)"}


def scrape() -> list[ScrapedProduct]:
    resp = httpx.get(LISTING_URL, headers=HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    products = []
    for btn in soup.select(".favorite-btn[data-id]"):
        name = btn["data-name"]
        url = btn["data-url"]
        price_amd = float(btn["data-price"])
        image_url = btn.get("data-image")

        # stock badge lives in the same product card, a few levels up
        card = btn
        for _ in range(4):
            if card.parent is None:
                break
            card = card.parent
        in_stock = None
        badge = card.find(string=lambda s: s and "STOCK" in s.upper())
        if badge:
            in_stock = "OUT" not in badge.upper()

        products.append(ScrapedProduct(
            external_id=btn["data-id"],
            name=name,
            product_url=url,
            price_amd=price_amd,
            brand=guess_brand(name) or "Dyson",
            image_url=image_url,
            in_stock=in_stock,
        ))
    return products
