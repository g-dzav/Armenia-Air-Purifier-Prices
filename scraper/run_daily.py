"""Entrypoint for the GitHub Actions daily cron. Only touches sites that
need no human: the plain-HTTP easy tier, plus a best-effort automated pass
over the JS-rendered-but-not-gated sites and a cookie-reuse attempt on the
Cloudflare-gated ones (which will usually just no-op until the next manual
weekly run refreshes the cookies).
"""
from __future__ import annotations

from . import db
from .fx import fetch_and_store_today
from .store import store_products
from .sites import karcher, microless, redstore, threedplanet, vega
from .hard_sites import eldorado, homemart, ozon, vlv, wildberries, zigzag, allsell
from .hard_sites.playwright_base import run_automated, try_automated_with_saved_cookies

EASY_TIER = [microless, vega, threedplanet, karcher, redstore]
AUTOMATED_NO_CHALLENGE = [vlv]
COOKIE_REUSE_ATTEMPT = [zigzag, eldorado, allsell, ozon, homemart, wildberries]


def run_easy_tier(fx: dict) -> None:
    for mod in EASY_TIER:
        run_id = db.start_run(mod.SITE_NAME)
        try:
            products = mod.scrape()
            count = store_products(mod.SITE_NAME, products, fx, source="auto")
            db.finish_run(run_id, "ok", count)
            print(f"[{mod.SITE_NAME}] stored {count} price snapshots.")
        except Exception as exc:  # noqa: BLE001 - one bad site shouldn't kill the run
            db.finish_run(run_id, "error", 0, error=str(exc))
            print(f"[{mod.SITE_NAME}] FAILED: {exc}")


def main() -> None:
    fx = fetch_and_store_today()
    print(f"FX rate for today: 1 USD = {fx['usd_amd']} AMD = {fx['usd_kzt']} KZT")

    run_easy_tier(fx)

    print("Running automated (no-challenge) tier: " + ", ".join(m.SITE_NAME for m in AUTOMATED_NO_CHALLENGE))
    run_automated(AUTOMATED_NO_CHALLENGE)

    print("Attempting saved-cookie reuse on Cloudflare/captcha-gated sites...")
    still_blocked = try_automated_with_saved_cookies(COOKIE_REUSE_ATTEMPT)
    if still_blocked:
        print(
            "Still blocked (no change needed - this is expected until the next "
            f"manual weekly run): {', '.join(still_blocked)}"
        )


if __name__ == "__main__":
    main()
