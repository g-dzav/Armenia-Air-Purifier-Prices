"""Shared machinery for the sites that need a real browser: the Cloudflare/
captcha-gated ones (manual weekly solve) and the plain JS-rendered ones
(fully automated, no human needed).

Uses undetected-chromedriver (a patched Selenium that strips out the
`navigator.webdriver` flag and other automation tells), not plain Selenium
or Playwright. Plain Selenium was the first attempt, and it technically
worked — until a real manual run got stuck in a Cloudflare verification
loop: solving the checkbox correctly did nothing, because Cloudflare's
managed challenge wasn't actually failing the click, it was detecting that
the browser itself was automated and re-challenging regardless of what a
human did in it. undetected-chromedriver patches that out (confirmed live:
`navigator.webdriver` reads `false` instead of `true`). Playwright was
ruled out earlier still — its bundled Node driver process can't even start
on a Mac running an older macOS (a `dyld` symbol error, unrelated to any
website).

We deliberately do NOT override the User-Agent string here: spoofing an
arbitrary/stale UA while the real installed Chrome binary answers every
other fingerprinting question (Client Hints, JS feature detection, GPU
info, ...) is itself an inconsistency sharp bot-detection can catch -
undetected-chromedriver's whole premise is "just look like the real,
unmodified browser," so let it.

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

import os
import re
import shutil
import subprocess

# undetected-chromedriver's own update-check needs valid CA certs to reach
# GitHub; on some local Python installs (notably python.org's macOS
# installer) the system cert store isn't wired up, so fall back to
# certifi's bundle rather than erroring - this is a no-op if the system
# certs already work fine (e.g. on GitHub Actions' ubuntu-latest runners).
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

import undetected_chromedriver as uc

from .. import db
from ..fx import fetch_and_store_today
from ..store import store_products


def _detect_chrome_major_version() -> int | None:
    """undetected-chromedriver needs to patch a chromedriver binary that
    matches the installed Chrome's major version - auto-detection in some
    uc releases picks the latest release instead of the one actually
    installed, so detect it explicitly rather than trust that."""
    candidates = [
        "google-chrome", "google-chrome-stable", "chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for exe in candidates:
        path = exe if exe.startswith("/") else shutil.which(exe)
        if not path:
            continue
        try:
            out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10).stdout
            match = re.search(r"(\d+)\.", out)
            if match:
                return int(match.group(1))
        except Exception:  # noqa: BLE001 - fall through to uc's own auto-detect
            continue
    return None


def _make_driver(headless: bool) -> uc.Chrome:
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,1600")
    major = _detect_chrome_major_version()
    return uc.Chrome(options=opts, version_main=major) if major else uc.Chrome(options=opts)


def _store_products(site_name: str, products, source: str) -> int:
    fx = fetch_and_store_today()
    return store_products(site_name, products, fx, source)


def _save_debug_dump(site_name: str, driver) -> str:
    """Called when a manual run clears a challenge but scrape() still finds
    nothing - saves the actual rendered page (HTML + screenshot) so the
    real markup can be inspected and the site's selectors fixed, without
    needing to replay the session (which often won't work anyway - cookies
    like Cloudflare's cf_clearance are commonly IP-bound, so a session
    captured on one network can't just be loaded and re-inspected from
    another)."""
    from datetime import datetime
    from pathlib import Path

    debug_dir = Path("debug")
    debug_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = debug_dir / f"{site_name}_{stamp}.html"
    png_path = debug_dir / f"{site_name}_{stamp}.png"
    html_path.write_text(driver.page_source, encoding="utf-8")
    driver.save_screenshot(str(png_path))
    return f"{html_path} and {png_path}"


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
                real_ua = driver.execute_script("return navigator.userAgent")
                db.save_site_session(mod.SITE_NAME, cookies, real_ua)
                count = _store_products(mod.SITE_NAME, products, source="manual")
                db.finish_run(run_id, "ok", count)
                print(f"[{mod.SITE_NAME}] stored {count} price snapshots.")
                if count == 0:
                    debug_path = _save_debug_dump(mod.SITE_NAME, driver)
                    print(
                        f"[{mod.SITE_NAME}] the challenge cleared but the scraper found "
                        f"zero products - its selectors likely need fixing. Saved the "
                        f"real page to {debug_path} - send that file along so the "
                        f"selectors can be corrected against real markup."
                    )
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
