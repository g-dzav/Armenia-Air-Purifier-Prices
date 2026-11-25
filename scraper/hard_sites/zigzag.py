"""zigzag.am — Cloudflare-protected (needs the weekly manual solve), but
once past the challenge the page turns out to have excellent structured
data: every product card's name link carries an `onclick` handler that
pushes a Google Analytics 4 ecommerce event, embedding a clean JSON object
with item_id/item_name/price/stock status right in the HTML — far more
reliable than scraping rendered price text. Confirmed against a real
manual-run debug dump (Nov 2026): 12 products, each appearing twice
(two onclick pushes per card — view_item_list and select_item — so this
dedupes by item_id).

Markup:
  a.product_name[href][onclick]
    onclick contains: ...,"items":[{"item_id":"51039","item_name":
    "Karcher AF 30 (1.024-821.0)","price":104300,"item_stock_status":
    "In stock", ...}]...

This category page mixes real air purifiers in with plain humidifiers and
air coolers (its own title translates to "Air purifying/humidifying
devices") — store.py's shared is_excluded_accessory() filters those out
centrally, same as every other site.
"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from ..normalize import extract_model_from_name, guess_brand
from ..sites.base import ScrapedProduct

SITE_NAME = "zigzag"
LISTING_URL = "https://www.zigzag.am/en/air-conditioning-equipment/ir-purifiers.html"

_ITEM_RE = re.compile(r'"items":\[(\{.*?\})\]\}\}')


def looks_blocked(driver) -> bool:
    from . import generic_extract
    return generic_extract.looks_blocked(driver)


def scrape(driver) -> list[ScrapedProduct]:
    soup = BeautifulSoup(driver.page_source, "lxml")

    products = {}
    for a in soup.select("a.product_name[href]"):
        onclick = a.get("onclick", "")
        match = _ITEM_RE.search(onclick)
        if not match:
            continue
        try:
            item = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        item_id = item.get("item_id")
        if not item_id or item_id in products:
            continue
        name = item.get("item_name", "").strip()
        price_amd = item.get("price")
        if not name or price_amd is None:
            continue

        products[item_id] = ScrapedProduct(
            external_id=item_id,
            name=name,
            product_url=a["href"],
            price_amd=float(price_amd),
            brand=guess_brand(name),
            model=extract_model_from_name(name),
            in_stock=(item.get("item_stock_status") or "").strip().lower() == "in stock",
        )
    return list(products.values())
