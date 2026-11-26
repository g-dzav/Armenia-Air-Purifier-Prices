# Reusable prompt template

This is the prompt I'd write if starting this project over, with everything
learned along the way (the macOS/Playwright incompatibility, the Cloudflare
verification loop, the distutils/CI crash, the Armenian/Russian keyword
gaps, the dashboard layout bugs) folded in from the beginning instead of
discovered one at a time. Useful as a starting point for a similar
scrape-and-compare project.

---

Build a price-comparison tool for air purifiers sold in Armenia — both
backend (scraping + database) and frontend (dashboard + analytics), fully
hosted online, nothing running on my local machine except an occasional
manual-assist script.

## Scope and data model

Track air purifiers only — not air coolers, humidifiers, ionizers/ozonizers,
scent diffusers, or standalone replacement filters, even when a retailer
lists them in the same category page. For each product, capture: product
name, brand, model/SKU (when the retailer exposes one), retailer, price in
AMD, price converted to USD and KZT, stock status, rating, review count,
shipping time, shipping price (when shown separately from the item price),
and when it was last checked. Store this as real price *history*
(append-only snapshots keyed to a product), not just a "latest price" row,
since the whole point is tracking change over time.

Product names on Armenian and Russian retailers are frequently in native
script with the brand/model embedded in Latin characters either as a
prefix, a suffix, or interleaved with descriptive text. Display only the
clean Latin brand/model — never a transliteration or a native-script
description — but don't strip the native-script text before using it to
decide whether a listing is actually an air purifier, since the
language-specific keywords for "humidifier," "filter," "ozonizer," and
"ionizer" are exactly what that decision depends on, in English, Russian,
*and* Armenian. Watch for the specific trap where a replacement filter's
own title says "...for an air purifier" — the local word for "purifier"
being present doesn't mean the listing itself is a purifier unit; what
matters is whether the product's own leading identity is the
filter/ozonizer/ionizer or the purifier, and real purifier units reliably
lead their own name with their own identity, so check word order, not just
keyword presence. A price floor (filter out anything implausibly cheap
relative to genuine units, roughly under 15,000 AMD) catches accessories
that don't announce themselves by name at all.

Identify the real online retailers people in Armenia actually use (do this
by live web research, not from memory, and search in Russian as well as
English — a lot of the real market context only surfaces that way) —
expect a mix of straightforward sites, sites fully behind Cloudflare, and
at least one marketplace (Wildberries) with its own interstitial.
Explicitly exclude List.am (individual-seller classifieds, not a store).

## Hosting and architecture

This needs to live entirely online and be easy to share with other people,
not something that only works from my machine. Use a free-tier hosted
Postgres database (Supabase is a good fit — it bundles a database, row-level
security, auth, and a REST API in one place), a scheduled job that runs
daily without any server to maintain (GitHub Actions is a natural fit
alongside a GitHub-hosted repo), and a static, no-build dashboard page
hosted for free (GitHub Pages) that talks directly to the database from the
browser. Set up the database schema's access grants (not just RLS policies
— Postgres requires both an object-level GRANT *and* a policy before a role
can touch a table at all) and get them right for anon, authenticated, and
service_role from the start, including on any view, which also needs
`security_invoker` set explicitly or it'll silently check permissions as
its owner instead of the caller.

Gate the dashboard behind a real authentication system (magic-link email
sign-in, invite-only — turn off public self-signup so a found link alone
isn't enough to get in), enforced in the database itself via row-level
security, not merely in the page's own client-side JavaScript — a check
that only runs in the visitor's browser is advisory, not real access
control, since the visitor controls that browser completely.

## Scraping

Split sites into two tiers from the start: plain-HTTP sites that can be
scraped headlessly and automatically every day, and sites behind Cloudflare
or their own CAPTCHA/anti-bot system that need an actual human to clear a
challenge. For the second tier, build a local tool that opens a real,
visible browser window, lets a person clear the challenge once per site,
scrapes immediately after, and saves the resulting cookies so the next
day's automated attempt can try reusing them before falling back to "still
blocked, needs the next manual run" — note up front that cookies like
Cloudflare's `cf_clearance` are commonly tied to the solving IP, so reuse
from a different network is a best-effort bonus, not something to rely on.

For browser automation, go straight to Selenium driving the system's
already-installed Chrome via `undetected-chromedriver` (which strips the
automation fingerprints Cloudflare's managed challenge specifically checks
for) rather than Playwright — Playwright's bundled Node driver can fail to
start entirely on an older macOS, unrelated to any website, and plain
Selenium will get stuck in an infinite "solved but re-challenged" loop on a
real Cloudflare checkbox because the challenge isn't actually evaluating
whether the click was genuine, it's detecting that the browser itself is
automated. Pin `setuptools` alongside it in requirements —
`undetected-chromedriver`'s own update checker imports `distutils`, which
was removed from the Python standard library in 3.10+, and that exact gap
will silently crash the import (and therefore every CI run, instantly, with
no useful error) on both a modern local Python and GitHub Actions' runner
unless the compatibility shim is explicitly pulled in.

Make every scraper self-diagnosing from day one: after every manual-tier
site, whether it looks like it succeeded or not, save the actual rendered
HTML and a screenshot to a local debug folder. A scraper that returns zero
results is an obvious, visible signal something broke; a scraper that
confidently returns the *wrong* data — a parser that's drifted onto a
"recommended products" widget spanning the whole site, or one that's
concatenated a model number into a price — looks identical to success
unless there's a saved artifact to actually inspect. Never trust a selector
written from guesswork or from an old search-result snippet; build every
parser against a real captured page and verify its output against that
real data before relying on it.

Never attempt to defeat a CAPTCHA, slider puzzle, or proof-of-work
checkbox programmatically — those need a human, by design, and that's a
hard line, not a scraping challenge to solve.

## Frontend

Build the main view as a real spreadsheet, not a web-app table dressed up
to look like one: visible gridlines on every cell, a sticky header row, row
numbers, right-aligned numeric columns, and — critically — every column
individually sortable (click the header) and filterable (checkboxes for
categorical columns, min/max range for numeric ones, text-contains for free
text), plus a CSV export that respects whatever filter/sort is currently
active. Watch cell layout carefully for anything that can overflow the
page's right edge and force horizontal scrolling — a value positioned by
"100% + a few pixels" rather than given its own reserved space in the
layout will do exactly that.

Build a second page for an at-a-glance analytics snapshot: a few stat tiles
up top, then full-width charts stacked one per row (not a 2×2 grid
competing for horizontal space) — average price by brand, product count by
brand, stock availability, and price trend over time (grouped by brand, not
by retailer, since comparing retailers isn't the useful axis once the same
product is tracked across several of them — comparing brands is). Every bar
and every line/dot needs its own distinct color with no reuse and no fixed
cap on how many colors are available — derive the palette from however many
distinct entities actually exist (e.g. evenly spaced hues around the color
wheel) rather than a fixed-size list that runs out and starts reusing a
fallback gray past some arbitrary count. Keep the same color for the same
entity across every chart on the page, and make sure every chart has a
working hover tooltip.

## Working process

Confirm before any destructive database action (deleting rows, dropping
anything) and before any action with real-world cost (purchases, account
creation, anything needing a payment method) — this project should never
need either, but flag it immediately if something would. Prefer small,
frequent, clearly-scoped commits over one giant one. When investigating
"why is X broken," check the actual run history/logs before guessing, and
when a fix depends on something no one running the actual browser has
verified, ask for a live run rather than assuming the first plausible
theory is correct.
