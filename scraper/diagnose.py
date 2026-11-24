"""Diagnostic tool: headlessly visits each hard-tier site and reports what's
actually happening — HTTP-level reachability, page title, whether it looks
challenge-blocked, and (if not blocked) attempts a scrape. Useful whenever a
site that used to work goes quiet, or when deciding whether a site still
belongs in the manual-only tier.

Usage: python -m scraper.diagnose [site_name ...]   (default: all hard-tier sites)
"""
from __future__ import annotations

import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .hard_sites import allsell, eldorado, generic_extract, homemart, ozon, vlv, wildberries, zigzag

ALL_SITES = {m.SITE_NAME: m for m in [zigzag, eldorado, allsell, ozon, homemart, vlv, wildberries]}


def diagnose_one(driver, mod) -> None:
    print(f"\n=== {mod.SITE_NAME} ===")
    print(f"URL: {mod.LISTING_URL}")
    try:
        driver.get(mod.LISTING_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED TO LOAD: {exc}")
        return

    title = driver.title
    current_url = driver.current_url
    blocked = generic_extract.looks_blocked(driver)
    body_excerpt = driver.execute_script(
        "return document.body ? document.body.innerText.slice(0, 300) : ''"
    )

    print(f"Final URL: {current_url}")
    print(f"Page title: {title!r}")
    print(f"Looks blocked: {blocked}")
    print(f"Body excerpt: {body_excerpt!r}")

    if blocked:
        print("-> Confirmed blocked. This one needs the manual weekly solve.")
        return

    try:
        products = mod.scrape(driver)
    except Exception as exc:  # noqa: BLE001
        print(f"-> Not blocked, but scrape() raised: {exc}")
        return

    print(f"-> Not blocked! scrape() found {len(products)} products.")
    for p in products[:5]:
        print(f"   - {p.name[:60]!r}  {p.price_amd} AMD  brand={p.brand}")


def main() -> None:
    names = sys.argv[1:] or list(ALL_SITES.keys())
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=opts)
    try:
        for name in names:
            mod = ALL_SITES.get(name)
            if not mod:
                print(f"Unknown site: {name}")
                continue
            diagnose_one(driver, mod)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
