-- Armenia Air Purifier Price Tracker — Supabase/Postgres schema
-- Run this once in the Supabase SQL editor (Project > SQL Editor > New query).

create extension if not exists "pgcrypto";

-- One row per distinct product we've ever seen on a given site.
create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  site text not null,                 -- e.g. 'microless', 'vega', 'zigzag'
  external_id text not null,          -- site's own product id/handle/sku
  brand text,
  model text,
  name text not null,
  product_url text not null,
  image_url text,
  first_seen_at timestamptz not null default now(),
  unique (site, external_id)
);

-- One row per scrape of a product. Append-only — never update, so this is a
-- real price history, not just "latest price".
create table if not exists price_snapshots (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references products(id) on delete cascade,
  scraped_at timestamptz not null default now(),
  price_amd numeric,
  list_price_amd numeric,             -- pre-discount price, if the site shows one
  in_stock boolean,
  rating numeric,                     -- 0-5 stars, null if the site shows none
  review_count integer,
  shipping_price_amd numeric,         -- null if shipping is free or bundled into price_amd
  shipping_time_text text,            -- free-text, e.g. "2-5 days" — too inconsistent across sites to normalize
  price_usd numeric,                  -- computed at insert time using that day's fx_rates row
  price_kzt numeric,
  fx_rate_date date,
  source text not null default 'auto' check (source in ('auto', 'manual'))
);
create index if not exists price_snapshots_product_idx on price_snapshots (product_id, scraped_at desc);

-- Daily FX snapshot. One row per day.
create table if not exists fx_rates (
  rate_date date primary key,
  usd_amd numeric not null,
  usd_kzt numeric not null,
  fetched_at timestamptz not null default now()
);

-- One row per scraper run, for the dashboard's health view and for catching
-- silently-broken selectors (a site going from 15 products to 0 is a signal).
create table if not exists scrape_runs (
  id uuid primary key default gen_random_uuid(),
  site text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check (status in ('running', 'ok', 'error')),
  products_found integer,
  error text
);

-- Cookie/session jar for the hard-tier (Cloudflare-protected) sites. The
-- local weekly manual-run script writes here after a human solves the
-- challenge; nothing else needs to read or write this table.
create table if not exists site_sessions (
  site text primary key,
  cookies jsonb not null,
  user_agent text,
  updated_at timestamptz not null default now()
);

-- Convenience view: latest snapshot per product, joined with product info.
-- Explicit column list (rather than p.*, s.*) because both tables have an
-- `id` column, which errors as an ambiguous duplicate in a wildcard select.
create or replace view latest_prices as
select
  p.id,
  p.site,
  p.external_id,
  p.brand,
  p.model,
  p.name,
  p.product_url,
  p.image_url,
  p.first_seen_at,
  s.id as snapshot_id,
  s.scraped_at,
  s.price_amd,
  s.list_price_amd,
  s.in_stock,
  s.rating,
  s.review_count,
  s.shipping_price_amd,
  s.shipping_time_text,
  s.price_usd,
  s.price_kzt,
  s.fx_rate_date,
  s.source
from products p
join lateral (
  select *
  from price_snapshots ps
  where ps.product_id = p.id
  order by ps.scraped_at desc
  limit 1
) s on true;

-- Row Level Security: the dashboard uses the public anon key and should only
-- ever be able to read. All writes go through the service role key, which
-- bypasses RLS entirely (used only by the scraper, never shipped to the browser).
alter table products enable row level security;
alter table price_snapshots enable row level security;
alter table fx_rates enable row level security;
alter table scrape_runs enable row level security;
alter table site_sessions enable row level security;

create policy "public read products" on products for select using (true);
create policy "public read price_snapshots" on price_snapshots for select using (true);
create policy "public read fx_rates" on fx_rates for select using (true);
create policy "public read scrape_runs" on scrape_runs for select using (true);
-- no policy on site_sessions: it holds cookies, so it's not exposed to anon/public at all.
