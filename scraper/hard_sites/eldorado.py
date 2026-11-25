"""eldorado.am — Cloudflare-protected. Needs the weekly manual solve. Same
Magento-based platform as Zigzag (clean data-price-amount attributes), but
the generic heuristic extractor was quietly wrong here, not just empty: it
scraped an unrelated "recommended products" sidebar spanning the whole
catalog (sofas, fridges, TVs showed up as "air purifiers"), and for the
real purifier-brand items it concatenated the trailing model-number digits
straight into the price text (e.g. "AP-107" + "44500" read as "10744500").
Confirmed against a real manual-run debug dump (Nov 2026) and rebuilt with
real selectors instead.

Markup:
  li[id^="product-item-info_"]            <- one product card
    a.product_name[href]                  <- name + url
    span[id^="product-price-"][data-price-amount]   <- current price
    span[id^="old-price-"][data-price-amount]       <- pre-discount price, if on sale
There's also a "middle_price credit-price" div showing a formatted monthly/
credit-style number - don't use it, it's just a re-rendering of the old
price, not the real current price (this is what the old heuristic grabbed).

This category heavily mixes real purifier units with their own replacement
filters ("Air purifier filter Levoit Core 200S-RF", "Filter for BONECO
H300") - store.py's shared is_excluded_accessory() already catches these
correctly (confirmed against the real dump: 11 of 16 listings here are
filters, not units).
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from ..normalize import guess_brand, parse_amd
from ..sites.base import ScrapedProduct

SITE_NAME = "eldorado"
LISTING_URL = "https://eldorado.am/en/climate/air-purifiers"


def looks_blocked(driver) -> bool:
    from . import generic_extract
    return generic_extract.looks_blocked(driver)


def scrape(driver) -> list[ScrapedProduct]:
    soup = BeautifulSoup(driver.page_source, "lxml")

    products = []
    for card in soup.select('li[id^="product-item-info_"]'):
        name_a = card.select_one("a.product_name[href]")
        price_el = card.select_one('span[id^="product-price-"][data-price-amount]')
        if not name_a or not price_el:
            continue

        name = " ".join(name_a.get_text(strip=True).split())
        price_amd = parse_amd(price_el["data-price-amount"])
        if price_amd is None:
            continue

        old_price_el = card.select_one('span[id^="old-price-"][data-price-amount]')
        list_price_amd = parse_amd(old_price_el["data-price-amount"]) if old_price_el else None

        url = name_a["href"]
        products.append(ScrapedProduct(
            external_id=url.rstrip("/").split("/")[-1],
            name=name,
            product_url=url,
            price_amd=price_amd,
            brand=guess_brand(name),
            list_price_amd=list_price_amd if list_price_amd and list_price_amd > price_amd else None,
        ))
    return products
