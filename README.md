# Armenia Air Purifier Prices

Internal daily price tracker for air purifiers sold online in Armenia — AMD
prices with USD/KZT equivalents, a shared history (not just "latest price"),
and a shareable live dashboard.

## How it's wired together

- **Database**: Supabase (hosted Postgres). Schema in [`db/schema.sql`](db/schema.sql).
- **Daily scrape**: GitHub Actions ([`.github/workflows/daily-scrape.yml`](.github/workflows/daily-scrape.yml))
  runs [`scraper/run_daily.py`](scraper/run_daily.py) every morning — fully automated, no server to maintain.
- **Dashboard**: a static page ([`docs/index.html`](docs/index.html)) that reads
  straight from Supabase in the browser. Deploy it with GitHub Pages and the
  URL is your shareable link — anyone with it sees live data, no login.
- **Weekly manual pass**: [`scraper/run_manual_weekly.py`](scraper/run_manual_weekly.py), run on
  your own machine. Opens a real, visible Chrome window for the sites that
  need a human to clear a challenge — Cloudflare's checkbox (Zigzag,
  Eldorado, AllSell), Ozon's slider-puzzle captcha, Homemart's proof-of-work
  checkbox, and Wildberries' own interstitial. Confirmed live (not just
  guessed from curl) that all five genuinely require a human — these aren't
  defeatable headlessly, by design. You clear the challenge once per site,
  it scrapes and pushes straight into the same Supabase database the daily
  job uses.
- **Browser automation**: Selenium, driving your installed Chrome directly —
  not Playwright. Playwright's bundled driver can't even start on an older
  macOS (unrelated to any site's defenses), so Selenium is both more
  portable and avoids a second browser download.

### Sites covered

| Tier | Sites | How |
|---|---|---|
| Automated daily (plain HTTP) | Microless, Vega, 3DPlanet, Karcher, RedStore | `scraper/sites/*` |
| Automated daily (headless browser, no challenge) | VLV | `scraper/hard_sites/vlv.py` |
| Manual weekly (you solve a challenge once) | Zigzag, Eldorado, AllSell, Ozon, Homemart, Wildberries | `scraper/hard_sites/*`, run via `run_manual_weekly.py` |
| Explicitly out of scope | List.am | per your instruction — individual-seller classifieds, not a store |

Every automated daily run also *tries* the manual-tier sites headlessly
using cookies saved from your last manual pass, in case they still work —
see `try_automated_with_saved_cookies` in `run_daily.py`. When Cloudflare's
cookie turns out to be IP-locked (common), that attempt just no-ops and you
fall back to the weekly manual run.

## First-time setup

See [`SETUP.md`](SETUP.md) — you'll create a free Supabase project and a
GitHub repo, and I can't do either of those for you since they need your own
accounts, but it's about 10 minutes of clicking.

## Running the weekly manual pass

```bash
pip install -r requirements.txt   # needs Google Chrome installed locally
cp .env.example .env   # then fill in your Supabase URL + service_role key
python -m scraper.run_manual_weekly
```

A browser window opens per site. Clear whatever challenge it shows, then
switch back to the terminal and press Enter to let it scrape and move to the
next site.

## Diagnosing a site that's gone quiet

```bash
python -m scraper.diagnose              # all hard-tier sites
python -m scraper.diagnose zigzag ozon   # just specific ones
```

Headlessly visits each one and reports the real page title, whether it
looks challenge-blocked, and attempts a scrape if it isn't — this is how
VLV's wrong category URL and the "is this site actually still blocked"
question get answered, instead of guessing from curl output.

## Notes on accuracy

- `scraper/hard_sites/generic_extract.py` is a best-effort fallback used by
  the sites I couldn't inspect directly (they block plain requests, so the
  only way to see their real markup is through a solved browser session).
  If a site's rows look empty or wrong after a manual run, that's the place
  to tighten — open devtools on the real page and swap in exact selectors.
  VLV and RedStore have their own real selectors instead (verified live).
- Ratings/shipping times aren't shown consistently across sites; expect nulls.
- FX rates come from a free aggregator (`open.er-api.com`), not the official
  Central Bank of Armenia rate — fine for a comparison tool, not for
  anything that needs the exact CBA-published figure.
