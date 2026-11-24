"""vega.am — OpenCart storefront, server-rendered HTML.

Verified structure (Nov 2026): each product is a `.product-thumb` card.
`.product-name a` gives name+url. `.price[data-price-value][data-special-value]`
carries the raw numeric prices as attributes, so no string parsing needed.
Stock status is a sibling `.stock-status.outofstock` div.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from ..normalize import guess_brand, slug_from_url
from .base import ScrapedProduct

SITE_NAME = "vega"
LISTING_URL = "https://vega.am/en/home-appliances/cooling-heating/air-purifiers"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; price-tracker/1.0)"}


def scrape() -> list[ScrapedProduct]:
    resp = httpx.get(LISTING_URL, headers=HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    products = []
    for card in soup.select(".product-thumb"):
        name_a = card.select_one(".product-name a")
        price_el = card.select_one(".price[data-price-value]")
        if not name_a or not price_el:
            continue

        url = name_a["href"]
        name = name_a.get_text(strip=True)
        base_price = float(price_el["data-price-value"])
        special = price_el.get("data-special-value")
        special_price = float(special) if special else None

        img_el = card.select_one("img")
        image_url = img_el.get("data-src") or img_el.get("src") if img_el else None

        out_of_stock = card.select_one(".stock-status.outofstock") is not None

        products.append(ScrapedProduct(
            external_id=slug_from_url(url),
            name=name,
            product_url=url,
            price_amd=special_price if special_price else base_price,
            brand=guess_brand(name),
            image_url=image_url,
            list_price_amd=base_price if special_price else None,
            in_stock=not out_of_stock,
        ))
    return products
