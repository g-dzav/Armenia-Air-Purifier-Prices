"""redstore.am — Next.js storefront. The category grid is client-rendered
(no plain-HTML product links), but each product PAGE is server-rendered
with a clean schema.org JSON-LD block. So: use Playwright just to discover
the product URLs in the category page (headless, no challenge to solve),
then fetch each product page with plain httpx and read its JSON-LD —
much cheaper than rendering every product page in a browser.

NOTE: not verified end-to-end against a live run yet (Playwright isn't
available in the environment this was written in) — the category-page
selector below (`a[href*="/product/"]`) is a reasonable guess based on the
URL pattern seen on product pages; confirm it still matches on first run
and adjust if RedStore's markup differs.
"""
from __future__ import annotations

import json
import re

import httpx
from playwright.sync_api import sync_playwright

from ..normalize import slug_from_url
from .base import ScrapedProduct

SITE_NAME = "redstore"
LISTING_URL = "https://redstore.am/en/categories/air-purifiers"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; price-tracker/1.0)"}


def _discover_product_urls() -> list[str]:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"])
        page.goto(LISTING_URL, wait_until="networkidle", timeout=30_000)
        hrefs = page.eval_on_selector_all(
            'a[href*="/product/"]', "els => els.map(e => e.href)"
        )
        browser.close()
    return sorted(set(hrefs))


def _extract_json_ld_product(html: str) -> dict | None:
    for match in re.finditer(r'"@type":"Product".*?"seller":\{[^}]*\}\}', html, re.S):
        try:
            # the match is a fragment, not a full object — wrap and parse defensively
            frag = "{" + match.group(0) + "}"
            return json.loads(frag)
        except json.JSONDecodeError:
            continue
    return None


def scrape() -> list[ScrapedProduct]:
    products = []
    for url in _discover_product_urls():
        resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        if resp.status_code != 200:
            continue
        data = _extract_json_ld_product(resp.text)
        if not data:
            continue

        offer = data.get("offers", {})
        products.append(ScrapedProduct(
            external_id=data.get("sku") or slug_from_url(url),
            name=data.get("name", ""),
            product_url=url,
            price_amd=float(offer["price"]) if offer.get("price") else None,
            brand=(data.get("brand") or {}).get("name"),
            image_url=data.get("image"),
            in_stock="InStock" in (offer.get("availability") or ""),
        ))
    return products
