"""homemart.am — runs its own proof-of-work "I'm not a robot" checkbox
(zhCAPTCHA), not Cloudflare, so needs the weekly manual solve same as the
Cloudflare-gated sites. Once past it, real selectors confirmed against a
live manual-run debug dump (Nov 2026) — this is a CS-Cart storefront:

  div.ut2-gl__item                          <- one product card
    a.product-title[href][title]            <- name (full name is in the
                                                title attr; visible text can
                                                be the same or truncated)
    span[id^="discounted_price_"]           <- current price, if on sale
    span[id^="price_<id>"] (not "price_update_...")
                                             <- current price, if not on sale
    span[id^="list_price_"]                 <- pre-discount price

About a third of this category's listings show "Contact us for a price"
instead of a number (span.ty-no-price) — skipped here, same as any other
site's missing-price listing (store.py already drops price_amd=None rows).
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from ..normalize import guess_brand, parse_amd
from ..sites.base import ScrapedProduct

SITE_NAME = "homemart"
LISTING_URL = "https://homemart.am/texnika-tan-hamar/ody-maqrox-xonavacnox-sarqer/"


def looks_blocked(driver) -> bool:
    from . import generic_extract
    return generic_extract.looks_blocked(driver)


def _find_price_span(card):
    discounted = card.select_one('[id^="discounted_price_"]')
    if discounted:
        return discounted
    for span in card.select("span[id]"):
        if span["id"].startswith("price_") and not span["id"].startswith("price_update"):
            return span
    return None


def scrape(driver) -> list[ScrapedProduct]:
    soup = BeautifulSoup(driver.page_source, "lxml")

    products = []
    for card in soup.select("div.ut2-gl__item"):
        title_a = card.select_one("a.product-title[href]")
        if not title_a:
            continue
        name = (title_a.get("title") or title_a.get_text(strip=True)).strip()
        if not name:
            continue

        price_span = _find_price_span(card)
        price_amd = parse_amd(price_span.get_text(strip=True)) if price_span else None
        if price_amd is None:
            continue  # "Contact us for a price" - nothing to track

        list_price_span = card.select_one('[id^="list_price_"]')
        list_price_amd = parse_amd(list_price_span.get_text(strip=True)) if list_price_span else None

        url = title_a["href"]
        products.append(ScrapedProduct(
            external_id=url.rstrip("/").split("/")[-1],
            name=name,
            product_url=url,
            price_amd=price_amd,
            brand=guess_brand(name),
            list_price_amd=list_price_amd if list_price_amd and list_price_amd > price_amd else None,
        ))
    return products
