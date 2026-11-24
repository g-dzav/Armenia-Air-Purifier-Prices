"""Run this locally, once a week (or whenever the dashboard shows the
Cloudflare-gated sites going stale). Opens a real, visible browser window
one site at a time — solve whatever checkbox/challenge appears, then
switch back to this terminal and press Enter to let it scrape and move on.

Requires a local .env with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
(copy .env.example) and Google Chrome installed (this drives your actual
system Chrome via Selenium — no separate browser download needed):

    pip install -r requirements.txt
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from .hard_sites import allsell, eldorado, homemart, ozon, wildberries, zigzag  # noqa: E402
from .hard_sites.browser_base import run_manual  # noqa: E402

MANUAL_TIER = [zigzag, eldorado, allsell, ozon, homemart, wildberries]

if __name__ == "__main__":
    run_manual(MANUAL_TIER)
