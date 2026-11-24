"""Shared "write a batch of ScrapedProduct into Supabase" used by every
site adapter, whether it came from plain httpx or a Playwright page.
"""
from __future__ import annotations

from . import db
from .fx import convert_amd
from .normalize import is_excluded_accessory


def store_products(site_name: str, products, fx: dict, source: str) -> int:
    count = 0
    for prod in products:
        if prod.price_amd is None:
            continue
        if is_excluded_accessory(prod.name, prod.price_amd):
            continue
        product_id = db.upsert_product(
            site=site_name, external_id=prod.external_id, brand=prod.brand,
            model=prod.model, name=prod.name, product_url=prod.product_url,
            image_url=prod.image_url,
        )
        price_usd, price_kzt = convert_amd(prod.price_amd, fx)
        db.insert_price_snapshot(
            product_id=product_id, price_amd=prod.price_amd,
            list_price_amd=prod.list_price_amd, in_stock=prod.in_stock,
            rating=prod.rating, review_count=prod.review_count,
            shipping_price_amd=prod.shipping_price_amd,
            shipping_time_text=prod.shipping_time_text,
            price_usd=price_usd, price_kzt=price_kzt,
            fx_rate_date=fx["rate_date"], source=source,
        )
        count += 1
    return count
