"""am.microless.com — server-rendered HTML, plain requests work fine.

Verified structure (Nov 2026): each product is a `.product` card containing
`.product-title a`, `.product-price .new-price .price-amount` / `.old-price`,
`.product-review-stars` (star-full icons + `.reviews-count-container`), and
a `.free-shipping .delivery-by` line.
"""
from __future__ import annotations

from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from ..normalize import guess_brand, parse_amd, slug_from_url
from .base import ScrapedProduct

SITE_NAME = "microless"
LISTING_URL = "https://am.microless.com/en/air-purifiers/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; price-tracker/1.0)"}


def _days_until(date_text: str) -> str | None:
    """Microless shows a calendar date ("Nov 27"), but every other site in
    this tracker shows a day-count ("2-3 days") - convert to the same shape
    so shipping times are comparable across sites, not a mix of the two."""
    today = date.today()
    for fmt in ("%b %d", "%B %d"):
        try:
            parsed = datetime.strptime(date_text, fmt).replace(year=today.year).date()
        except ValueError:
            continue
        if parsed < today:
            parsed = parsed.replace(year=today.year + 1)
        days = (parsed - today).days
        if days <= 0:
            return "today"
        return f"{days} day" + ("s" if days != 1 else "")
    return None


def scrape() -> list[ScrapedProduct]:
    resp = httpx.get(LISTING_URL, headers=HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    products = {}
    for card in soup.select(".product"):
        title_a = card.select_one(".product-title a")
        price_el = card.select_one(".product-price .new-price .price-amount")
        if not title_a or not price_el:
            continue  # carousel/brand cards without a real product

        url = title_a["href"]
        name = title_a.get_text(strip=True)
        price_amd = parse_amd(price_el.get_text())

        old_price_el = card.select_one(".product-price .old-price")
        list_price_amd = parse_amd(old_price_el.get_text()) if old_price_el else None

        rating = None
        review_count = None
        stars_box = card.select_one(".product-review-stars")
        if stars_box:
            full_stars = len(stars_box.select(".star-full"))
            rating = float(full_stars) if full_stars else None
            count_el = stars_box.select_one(".reviews-count-container")
            if count_el:
                digits = "".join(c for c in count_el.get_text() if c.isdigit())
                review_count = int(digits) if digits else None

        shipping_time_text = None
        delivery_el = card.select_one(".delivery-by")
        if delivery_el:
            raw = delivery_el.get_text(" ", strip=True).replace("Delivered by", "").strip()
            shipping_time_text = _days_until(raw) or raw

        img_el = card.select_one("img")
        image_url = img_el.get("src") if img_el else None

        external_id = slug_from_url(url)
        products[external_id] = ScrapedProduct(
            external_id=external_id,
            name=name,
            product_url=url,
            price_amd=price_amd,
            brand=guess_brand(name),
            image_url=image_url,
            list_price_amd=list_price_amd,
            in_stock="product-unavailable" not in card.get("class", []),
            rating=rating,
            review_count=review_count,
            shipping_price_amd=0,  # Microless shows free delivery badges; no separate shipping line seen
            shipping_time_text=shipping_time_text,
        )
    return list(products.values())
