"""Daily USD/AMD and USD/KZT rates from a free, no-key FX API.

open.er-api.com aggregates market rates — it's not the official Central Bank
of Armenia published rate, but pulling AMD and KZT from the same provider in
one call keeps the AMD->KZT cross-rate internally consistent, which matters
more for a comparison tool than matching the CBA rate to the dram.
"""
from __future__ import annotations

from datetime import date

import httpx

from . import db

FX_API_URL = "https://open.er-api.com/v6/latest/USD"


def fetch_and_store_today() -> dict:
    cached = db.get_fx_rate(date.today())
    if cached:
        return cached

    resp = httpx.get(FX_API_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        raise RuntimeError(f"FX API returned non-success: {data}")

    usd_amd = data["rates"]["AMD"]
    usd_kzt = data["rates"]["KZT"]
    db.upsert_fx_rate(date.today(), usd_amd, usd_kzt)
    return {"rate_date": date.today().isoformat(), "usd_amd": usd_amd, "usd_kzt": usd_kzt}


def convert_amd(price_amd: float | None, fx: dict) -> tuple[float | None, float | None]:
    """Return (price_usd, price_kzt) for a given AMD price."""
    if price_amd is None:
        return None, None
    usd = price_amd / fx["usd_amd"]
    kzt = usd * fx["usd_kzt"]
    return round(usd, 2), round(kzt, 2)
