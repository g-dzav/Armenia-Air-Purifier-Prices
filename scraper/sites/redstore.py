"""redstore.am — Next.js storefront. The category grid is client-rendered
(no plain-HTML product links), but each product PAGE is server-rendered
with a clean schema.org JSON-LD block. So: use a headless browser just to
discover the product URLs in the category page (no challenge to solve,
just JS rendering), then fetch each product page with plain httpx and read
its JSON-LD — much cheaper than rendering every product page in a browser.

Verified end-to-end Nov 2026 — `a[href*="/product/"]` correctly matches the
category grid's product links once rendered.
"""
from __future__ import annotations

import json
import re

import httpx
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..normalize import slug_from_url
from .base import ScrapedProduct

SITE_NAME = "redstore"
LISTING_URL = "https://redstore.am/en/categories/air-purifiers"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; price-tracker/1.0)"}


def _discover_product_urls() -> list[str]:
    opts = Options()
    opts.add_argument("--headless=new")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(LISTING_URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(("css selector", 'a[href*="/product/"]'))
        )
        hrefs = driver.execute_script(
            """return [...document.querySelectorAll('a[href*="/product/"]')].map(e => e.href)"""
        )
    finally:
        driver.quit()
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
