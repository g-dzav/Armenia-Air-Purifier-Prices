"""am.ozon.com — Armenia storefront of the Ozon marketplace. Its own in-house
anti-bot (a slider-puzzle captcha, not Cloudflare) needs the weekly manual
solve - confirmed this one specifically needs a human every time, cookie
reuse doesn't carry over reliably.

The generic heuristic extractor was quietly wrong here, not just empty: it
grabbed promo badge text ("8 left in stock", "Black Friday") as if it were
the product name - 100% of what it stored was garbage. Confirmed against a
real manual-run debug dump (Nov 2026) and rebuilt properly.

Ozon's build uses fully hashed/compiled CSS class names (no stable
semantic classes, no data-testid, images have no alt text) - there's
nothing reliable to select on by class name alone. What IS reliable:
each product occupies a `div[data-index]` card, and within a card the
visible text nodes follow a predictable shape regardless of class hashes:
  [promo badge?] PRICE [old price ...] [discount%] [stock text?]
  brand title RATING review-count delivery-date
So: price is identified by pattern (digits + the AMD sign), and the title
is the longest remaining text segment that isn't a price/percent/rating/
stock-count/promo-label pattern - verified against 9 real cards, correct
on all of them (including non-discounted ones with no promo badge at all).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..normalize import guess_brand, parse_amd
from ..sites.base import ScrapedProduct

SITE_NAME = "ozon"
LISTING_URL = "https://am.ozon.com/search/?text=%D0%BE%D1%87%D0%B8%D1%81%D1%82%D0%B8%D1%82%D0%B5%D0%BB%D1%8C%20%D0%B2%D0%BE%D0%B7%D0%B4%D1%83%D1%85%D0%B0"

_PRICE_RE = re.compile(r"^\d[\d\s ]{2,10}\s?֏$")
_RATING_RE = re.compile(r"^\d\.\d$")
_NOISE_RE = re.compile(
    r"^[-−]?\d+%$"                              # "-64%"
    r"|^\d[\d\s ]*\s*(ед|шт|отзыв|оценк)"        # "246 ед осталось", "3 417 отзывов"
    r"|^(Чёрная пятница|Скидки.*|Осталось.*)$"        # promo/stock banners
    r"|^\d{1,2}\s*(декабря|ноября|января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября)$",  # delivery date
    re.IGNORECASE,
)


def looks_blocked(driver) -> bool:
    from . import generic_extract
    return generic_extract.looks_blocked(driver)


def scrape(driver) -> list[ScrapedProduct]:
    soup = BeautifulSoup(driver.page_source, "lxml")

    products = {}
    for card in soup.select("div[data-index]"):
        link = card.select_one('a[href^="/product/"]')
        if not link:
            continue

        texts = [t.strip() for t in card.find_all(string=True) if t.strip()]
        price_amd = None
        for t in texts:
            if _PRICE_RE.match(t):
                price_amd = parse_amd(t)
                break
        if price_amd is None:
            continue

        candidates = [t for t in texts if len(t) > 3 and not _PRICE_RE.match(t) and not _NOISE_RE.match(t)]
        if not candidates:
            continue
        name = max(candidates, key=len)

        rating = None
        review_count = None
        for t in texts:
            if rating is None and _RATING_RE.match(t):
                rating = float(t)
            m = re.match(r"^(\d[\d\s ]*)\s*отзыв", t)
            if m:
                review_count = int(re.sub(r"\D", "", m.group(1)))

        url = "https://am.ozon.com" + link["href"].split("?")[0]
        external_id = link["href"].rstrip("/").split("-")[-1].split("?")[0]
        if external_id in products:
            continue

        products[external_id] = ScrapedProduct(
            external_id=external_id,
            name=name,
            product_url=url,
            price_amd=price_amd,
            brand=guess_brand(name),
            rating=rating,
            review_count=review_count,
        )
    return list(products.values())
