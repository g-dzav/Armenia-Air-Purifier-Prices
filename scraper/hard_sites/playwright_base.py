"""Shared machinery for the sites that need a real browser: the Cloudflare/
captcha-gated ones (manual weekly solve) and the plain JS-rendered ones
(fully automated, no human needed).

Two entrypoints:
  run_manual(modules)      -- headful, for your weekly check-in. Opens each
                               site, waits for you to clear any challenge,
                               scrapes, saves the resulting cookies to
                               Supabase so a *future automated* attempt can
                               try to reuse them, then writes prices.
  run_automated(modules)   -- headless, for sites with no challenge at all
                               (VLV, and Wildberries as a browser fallback).
                               No cookie reuse needed here.

Cookie reuse caveat: Cloudflare's cf_clearance cookie is sometimes tied to
the solving IP. A cookie captured on your home connection may not work from
a different network. Worth trying (see run_attempt_with_saved_cookies in
run_daily.py) but the manual weekly run is the reliable fallback regardless.
"""
from __future__ import annotations

from playwright.sync_api import sync_playwright

from .. import db
from ..fx import fetch_and_store_today
from ..store import store_products

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def _store_products(site_name: str, products, source: str) -> int:
    fx = fetch_and_store_today()
    return store_products(site_name, products, fx, source)


def run_manual(modules: list) -> None:
    """Headful run for your weekly check-in. One browser window, one tab per
    site in turn — solve whatever challenge appears, then press Enter in
    this terminal to let it continue."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        for mod in modules:
            run_id = db.start_run(mod.SITE_NAME)
            try:
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.goto(mod.LISTING_URL, wait_until="load", timeout=60_000)
                input(
                    f"\n[{mod.SITE_NAME}] Browser window opened to {mod.LISTING_URL}\n"
                    f"Solve any checkbox/challenge shown, wait for the real page to "
                    f"load, then press Enter here to scrape it... "
                )
                products = mod.scrape(page)
                cookies = context.cookies()
                db.save_site_session(mod.SITE_NAME, cookies, USER_AGENT)
                count = _store_products(mod.SITE_NAME, products, source="manual")
                db.finish_run(run_id, "ok", count)
                print(f"[{mod.SITE_NAME}] stored {count} price snapshots.")
                context.close()
            except Exception as exc:  # noqa: BLE001 - one bad site shouldn't kill the run
                db.finish_run(run_id, "error", 0, error=str(exc))
                print(f"[{mod.SITE_NAME}] FAILED: {exc}")
        browser.close()


def run_automated(modules: list) -> None:
    """Headless run for sites with no human-facing challenge at all."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for mod in modules:
            run_id = db.start_run(mod.SITE_NAME)
            try:
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.goto(mod.LISTING_URL, wait_until="networkidle", timeout=45_000)
                products = mod.scrape(page)
                count = _store_products(mod.SITE_NAME, products, source="auto")
                db.finish_run(run_id, "ok", count)
                context.close()
            except Exception as exc:  # noqa: BLE001
                db.finish_run(run_id, "error", 0, error=str(exc))
        browser.close()


def try_automated_with_saved_cookies(modules: list) -> list[str]:
    """Best-effort: try the hard-tier sites headlessly using cookies saved
    from the last manual solve. Returns the list of site names that still
    came back blocked (so you know the weekly manual run is still needed
    for those). Safe to run daily alongside run_daily.py — sites that work
    get a free daily update; sites that don't just no-op until next manual run.
    """
    still_blocked = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for mod in modules:
            session = db.get_site_session(mod.SITE_NAME)
            if not session:
                still_blocked.append(mod.SITE_NAME)
                continue
            run_id = db.start_run(mod.SITE_NAME)
            try:
                context = browser.new_context(user_agent=session.get("user_agent") or USER_AGENT)
                context.add_cookies(session["cookies"])
                page = context.new_page()
                page.goto(mod.LISTING_URL, wait_until="networkidle", timeout=45_000)
                if mod.looks_blocked(page):
                    still_blocked.append(mod.SITE_NAME)
                    db.finish_run(run_id, "error", 0, error="challenge still present (stale cookies)")
                    context.close()
                    continue
                products = mod.scrape(page)
                count = _store_products(mod.SITE_NAME, products, source="auto")
                db.finish_run(run_id, "ok", count)
                context.close()
            except Exception as exc:  # noqa: BLE001
                still_blocked.append(mod.SITE_NAME)
                db.finish_run(run_id, "error", 0, error=str(exc))
        browser.close()
    return still_blocked
