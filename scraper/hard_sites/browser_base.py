"""Shared machinery for the sites that need a real browser: the Cloudflare/
captcha-gated ones (manual weekly solve) and the plain JS-rendered ones
(fully automated, no human needed).

Uses Selenium driving system Chrome (via Selenium 4.6+'s built-in driver
manager — no separate browser download/setup needed), not Playwright.
Playwright was the original choice but its bundled Node driver process
flat-out can't start on a Mac running an older macOS (a `dyld` symbol
error, unrelated to any website) — a real constraint on the machine this
was built on, so Selenium is both more portable here and avoids installing
a second, large browser binary when a perfectly good Chrome is likely
already on the machine.

Two entrypoints:
  run_manual(modules)      -- a visible Chrome window, for your weekly
                               check-in. Opens each site, waits for you to
                               clear any challenge, scrapes, saves the
                               resulting cookies to Supabase so a *future
                               automated* attempt can try to reuse them,
                               then writes prices.
  run_automated(modules)   -- headless, for sites with no challenge at all
                               (VLV, and Wildberries as a fallback).
                               No cookie reuse needed here.

Cookie reuse caveat: Cloudflare's cf_clearance cookie is sometimes tied to
the solving IP. A cookie captured on your home connection may not work from
a different network. Worth trying (see try_automated_with_saved_cookies)
but the manual weekly run is the reliable fallback regardless.
"""
from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .. import db
from ..fx import fetch_and_store_today
from ..store import store_products

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def _make_driver(headless: bool) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--user-agent={USER_AGENT}")
    opts.add_argument("--window-size=1280,1600")
    return webdriver.Chrome(options=opts)


def _store_products(site_name: str, products, source: str) -> int:
    fx = fetch_and_store_today()
    return store_products(site_name, products, fx, source)


def run_manual(modules: list) -> None:
    """Visible-Chrome run for your weekly check-in. One window, one site at
    a time — solve whatever challenge appears, then press Enter in this
    terminal to let it continue."""
    driver = _make_driver(headless=False)
    try:
        for mod in modules:
            run_id = db.start_run(mod.SITE_NAME)
            try:
                driver.get(mod.LISTING_URL)
                input(
                    f"\n[{mod.SITE_NAME}] Browser window opened to {mod.LISTING_URL}\n"
                    f"Solve any checkbox/challenge shown, wait for the real page to "
                    f"load, then press Enter here to scrape it... "
                )
                products = mod.scrape(driver)
                cookies = driver.get_cookies()
                db.save_site_session(mod.SITE_NAME, cookies, USER_AGENT)
                count = _store_products(mod.SITE_NAME, products, source="manual")
                db.finish_run(run_id, "ok", count)
                print(f"[{mod.SITE_NAME}] stored {count} price snapshots.")
            except Exception as exc:  # noqa: BLE001 - one bad site shouldn't kill the run
                db.finish_run(run_id, "error", 0, error=str(exc))
                print(f"[{mod.SITE_NAME}] FAILED: {exc}")
    finally:
        driver.quit()


def run_automated(modules: list) -> None:
    """Headless run for sites with no human-facing challenge at all."""
    driver = _make_driver(headless=True)
    try:
        for mod in modules:
            run_id = db.start_run(mod.SITE_NAME)
            try:
                driver.get(mod.LISTING_URL)
                products = mod.scrape(driver)
                count = _store_products(mod.SITE_NAME, products, source="auto")
                db.finish_run(run_id, "ok", count)
            except Exception as exc:  # noqa: BLE001
                db.finish_run(run_id, "error", 0, error=str(exc))
    finally:
        driver.quit()


def try_automated_with_saved_cookies(modules: list) -> list[str]:
    """Best-effort: try the hard-tier sites headlessly using cookies saved
    from the last manual solve. Returns the list of site names that still
    came back blocked (so you know the weekly manual run is still needed
    for those). Safe to run daily alongside run_daily.py — sites that work
    get a free daily update; sites that don't just no-op until next manual run.
    """
    still_blocked = []
    driver = _make_driver(headless=True)
    try:
        for mod in modules:
            session = db.get_site_session(mod.SITE_NAME)
            if not session:
                still_blocked.append(mod.SITE_NAME)
                continue
            run_id = db.start_run(mod.SITE_NAME)
            try:
                # cookies must be set on the right origin, so load the page once
                # first (ignoring its content), then add cookies, then reload.
                driver.get(mod.LISTING_URL)
                for cookie in session["cookies"]:
                    cookie = {k: v for k, v in cookie.items() if k in
                              ("name", "value", "domain", "path", "secure", "httpOnly", "expiry")}
                    try:
                        driver.add_cookie(cookie)
                    except Exception:  # noqa: BLE001 - a stale/invalid cookie shouldn't abort the rest
                        continue
                driver.get(mod.LISTING_URL)
                if mod.looks_blocked(driver):
                    still_blocked.append(mod.SITE_NAME)
                    db.finish_run(run_id, "error", 0, error="challenge still present (stale cookies)")
                    continue
                products = mod.scrape(driver)
                count = _store_products(mod.SITE_NAME, products, source="auto")
                db.finish_run(run_id, "ok", count)
            except Exception as exc:  # noqa: BLE001
                still_blocked.append(mod.SITE_NAME)
                db.finish_run(run_id, "error", 0, error=str(exc))
    finally:
        driver.quit()
    return still_blocked
