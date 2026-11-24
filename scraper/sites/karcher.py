"""karchershop.am — Shopify storefront. Shopify exposes every collection as
JSON for free at /collections/{handle}/products.json — far more reliable
than scraping the rendered grid, and it's a stable, documented Shopify
convention rather than a reverse-engineered endpoint.
"""
from __future__ import annotations

import httpx

from .base import ScrapedProduct

SITE_NAME = "karcher"
LISTING_URL = "https://karchershop.am/collections/air-purifier-1/products.json?limit=100"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; price-tracker/1.0)"}


def scrape() -> list[ScrapedProduct]:
    resp = httpx.get(LISTING_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    products = []
    for p in data.get("products", []):
        variant = p["variants"][0]
        price_amd = float(variant["price"])
        compare_at = variant.get("compare_at_price")
        list_price_amd = float(compare_at) if compare_at and float(compare_at) > price_amd else None
        image_url = p["images"][0]["src"] if p.get("images") else None

        products.append(ScrapedProduct(
            external_id=p["handle"],
            name=p["title"],
            product_url=f"https://karchershop.am/products/{p['handle']}",
            price_amd=price_amd,
            brand="Karcher",
            model=variant.get("sku") or None,
            image_url=image_url,
            list_price_amd=list_price_amd,
            in_stock=variant.get("available", True),
        ))
    return products
