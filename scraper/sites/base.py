from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScrapedProduct:
    external_id: str
    name: str
    product_url: str
    price_amd: float
    brand: str | None = None
    model: str | None = None
    image_url: str | None = None
    list_price_amd: float | None = None
    in_stock: bool | None = None
    rating: float | None = None
    review_count: int | None = None
    shipping_price_amd: float | None = None
    shipping_time_text: str | None = None


# Every site adapter (easy-tier and hard-tier) exposes a module-level
# SITE_NAME and a scrape() -> list[ScrapedProduct] function. Hard-tier
# adapters take an extra `page` (a Playwright Page, already past any
# Cloudflare/captcha challenge) instead of making their own HTTP requests.
