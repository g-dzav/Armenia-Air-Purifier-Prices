"""Thin wrapper around Supabase's PostgREST API — no supabase-py dependency needed."""
from __future__ import annotations

import os
from datetime import date, datetime, timezone

import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def _rest(path: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{path}"


def upsert_product(site: str, external_id: str, brand: str | None, model: str | None,
                    name: str, product_url: str, image_url: str | None) -> str:
    """Insert the product if new, otherwise leave it untouched; return its id."""
    row = {
        "site": site,
        "external_id": external_id,
        "brand": brand,
        "model": model,
        "name": name,
        "product_url": product_url,
        "image_url": image_url,
    }
    resp = httpx.post(
        _rest("products"),
        headers={**_HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
        params={"on_conflict": "site,external_id"},
        json=[row],
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def insert_price_snapshot(product_id: str, **fields) -> None:
    row = {"product_id": product_id, **fields}
    resp = httpx.post(_rest("price_snapshots"), headers=_HEADERS, json=[row], timeout=30)
    resp.raise_for_status()


def get_fx_rate(for_date: date | None = None) -> dict | None:
    for_date = for_date or date.today()
    resp = httpx.get(
        _rest("fx_rates"),
        headers=_HEADERS,
        params={"rate_date": f"eq.{for_date.isoformat()}", "select": "*"},
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def upsert_fx_rate(for_date: date, usd_amd: float, usd_kzt: float) -> None:
    row = {"rate_date": for_date.isoformat(), "usd_amd": usd_amd, "usd_kzt": usd_kzt}
    resp = httpx.post(
        _rest("fx_rates"),
        headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
        params={"on_conflict": "rate_date"},
        json=[row],
        timeout=30,
    )
    resp.raise_for_status()


def start_run(site: str) -> str:
    resp = httpx.post(
        _rest("scrape_runs"),
        headers={**_HEADERS, "Prefer": "return=representation"},
        json=[{"site": site}],
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def finish_run(run_id: str, status: str, products_found: int, error: str | None = None) -> None:
    resp = httpx.patch(
        _rest("scrape_runs"),
        headers=_HEADERS,
        params={"id": f"eq.{run_id}"},
        json={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "products_found": products_found,
            "error": error,
        },
        timeout=30,
    )
    resp.raise_for_status()


def get_site_session(site: str) -> dict | None:
    resp = httpx.get(
        _rest("site_sessions"),
        headers=_HEADERS,
        params={"site": f"eq.{site}", "select": "*"},
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def save_site_session(site: str, cookies: list[dict], user_agent: str) -> None:
    row = {
        "site": site,
        "cookies": cookies,
        "user_agent": user_agent,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = httpx.post(
        _rest("site_sessions"),
        headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
        params={"on_conflict": "site"},
        json=[row],
        timeout=30,
    )
    resp.raise_for_status()
