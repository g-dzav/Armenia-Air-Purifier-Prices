"""vlv.am — not Cloudflare-gated, just a client-rendered SPA (React/Next),
so plain httpx gets an empty shell and the generic heuristic extractor
(generic_extract.py) also failed here — it kept matching the page's own
breadcrumb/category heading instead of real product cards. So this has its
own real selectors instead, found by inspecting a live render:

The "Air purifiers" tile on the Ventilation Devices category page isn't a
plain link either (no href, no onclick — a React click handler), so its
real URL had to be found by clicking it in a live browser:
https://vlv.am/en/category/filter/air-purifiers (confirmed live, 14 items).

Each card (CSS-module class names, hashed suffix — matched by prefix with
[class*=...] so a hash change on redeploy doesn't break this outright):
  a[href^="/en/Product/"]
    img[class*="brandImg"][alt]       <- brand name, e.g. "XIAOMI"
    p[class*="productName"]           <- e.g. "VLK SAN REMO300"
    p[class*="newPrice"]              <- current price, "25,000 ֏"
    p[class*="oldPrice"]              <- pre-discount price, if on sale
No visible out-of-stock marker was found on the listing — VLV may simply
not list items that are out of stock, so in_stock is left unset here.
"""
from __future__ import annotations

import re

from ..normalize import parse_amd
from ..sites.base import ScrapedProduct

# VLV doesn't expose a separate SKU field — it's just appended to the product
# name, e.g. "KARCHER AF20 1.024-820.0" or "...4 Compact (BHR5860EU)". Those
# two patterns are common enough across their catalog (and match the exact
# SKU format Karcher's own store uses) to be worth pulling out, since it lets
# the same physical product sold by two retailers group together correctly.
_MODEL_PATTERNS = [
    re.compile(r"\((\w[\w-]{3,})\)\s*$"),   # "... (BHR5860EU)"
    re.compile(r"(\d\.\d{3}-\d{3}\.\d)\s*$"),  # "... 1.024-820.0" (Karcher SKU format)
]


def _extract_model(name: str) -> str | None:
    for pattern in _MODEL_PATTERNS:
        m = pattern.search(name)
        if m:
            return m.group(1)
    return None

SITE_NAME = "vlv"
LISTING_URL = "https://vlv.am/en/category/filter/air-purifiers"

_EXTRACT_JS = """
return [...document.querySelectorAll('a[href^="/en/Product/"]')].map(a => {
  const nameEl = a.querySelector('[class*="productName"]');
  const newPriceEl = a.querySelector('[class*="newPrice"]');
  const oldPriceEl = a.querySelector('[class*="oldPrice"]');
  const brandImg = a.parentElement?.querySelector('[class*="brandImg"]');
  return {
    href: a.href,
    name: nameEl ? nameEl.textContent.trim() : null,
    newPrice: newPriceEl ? newPriceEl.textContent.trim() : null,
    oldPrice: oldPriceEl ? oldPriceEl.textContent.trim() : null,
    brand: brandImg ? brandImg.getAttribute('alt') : null,
  };
}).filter(p => p.name && p.newPrice);
"""


def looks_blocked(driver) -> bool:
    from . import generic_extract
    return generic_extract.looks_blocked(driver)


def scrape(driver) -> list[ScrapedProduct]:
    raw = driver.execute_script(_EXTRACT_JS)
    products = []
    for item in raw:
        price_amd = parse_amd(item["newPrice"])
        if price_amd is None:
            continue
        list_price_amd = parse_amd(item["oldPrice"]) if item.get("oldPrice") else None
        products.append(ScrapedProduct(
            external_id=item["href"].rstrip("/").split("/")[-1],
            name=item["name"],
            product_url=item["href"],
            price_amd=price_amd,
            brand=(item.get("brand") or "").title() or None,
            model=_extract_model(item["name"]),
            list_price_amd=list_price_amd,
        ))
    return products
