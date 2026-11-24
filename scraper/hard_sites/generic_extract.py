"""Best-effort product extraction for sites we can't pre-inspect (they block
plain HTTP requests, so the only view of their real markup is through a
browser that's already past the challenge). Tries structured data first
(schema.org JSON-LD / Product microdata, which a surprising number of
Armenian e-commerce sites include for SEO even behind Cloudflare), then
falls back to a price-pattern heuristic over the rendered DOM.

This WILL need tightening once you can actually see the rendered page
during your first manual run — if products come back empty or wrong, open
devtools on the real page, find the real card/price selectors, and tell me
so I can tighten the specific site module instead of relying on this
fallback.
"""
from __future__ import annotations

import json
import re

from ..normalize import guess_brand, parse_amd
from ..sites.base import ScrapedProduct

BLOCKED_MARKERS = [
    "just a moment", "checking your browser", "attention required",
    "ddos protection", "i'm not a robot", "captcha", "cf-browser-verification",
]


def looks_blocked(page) -> bool:
    title = (page.title() or "").lower()
    body_sample = page.inner_text("body")[:2000].lower() if page.query_selector("body") else ""
    haystack = title + " " + body_sample
    return any(marker in haystack for marker in BLOCKED_MARKERS)


def _from_json_ld(page) -> list[ScrapedProduct]:
    scripts = page.eval_on_selector_all(
        'script[type="application/ld+json"]', "els => els.map(e => e.textContent)"
    )
    products = []
    for raw in scripts:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            graph = item.get("@graph") if isinstance(item, dict) else None
            for node in (graph or [item]):
                if not isinstance(node, dict) or node.get("@type") != "Product":
                    continue
                offer = node.get("offers") or {}
                if isinstance(offer, list):
                    offer = offer[0] if offer else {}
                price = offer.get("price")
                if price is None:
                    continue
                products.append(ScrapedProduct(
                    external_id=node.get("sku") or node.get("name", "")[:60],
                    name=node.get("name", ""),
                    product_url=offer.get("url") or node.get("url") or page.url,
                    price_amd=float(price),
                    brand=(node.get("brand") or {}).get("name") if isinstance(node.get("brand"), dict) else node.get("brand"),
                    image_url=node.get("image") if isinstance(node.get("image"), str) else None,
                    in_stock="InStock" in (offer.get("availability") or ""),
                ))
    return products


def _from_price_heuristic(page) -> list[ScrapedProduct]:
    """Fallback: find anchor tags that contain both a plausible product name
    and a nearby AMD-looking price. Deliberately conservative — better to
    return fewer, correct products than many wrong ones."""
    cards = page.eval_on_selector_all(
        "a",
        """els => els.map(e => ({
            href: e.href,
            text: e.innerText,
            cardText: (e.closest('li,div,article') || e).innerText
        })).filter(x => x.text && x.text.trim().length > 8)""",
    )
    seen = set()
    products = []
    price_re = re.compile(r"([\d][\d\s,.]{2,10})\s*(֏|AMD|դրամ)", re.IGNORECASE)
    for card in cards:
        if card["href"] in seen:
            continue
        m = price_re.search(card["cardText"])
        if not m:
            continue
        price_amd = parse_amd(m.group(1))
        if not price_amd or price_amd < 1000:
            continue
        name = card["text"].strip().split("\n")[0][:200]
        seen.add(card["href"])
        products.append(ScrapedProduct(
            external_id=card["href"].rstrip("/").split("/")[-1],
            name=name,
            product_url=card["href"],
            price_amd=price_amd,
            brand=guess_brand(name),
        ))
    return products


def extract(page) -> list[ScrapedProduct]:
    products = _from_json_ld(page)
    if products:
        return products
    return _from_price_heuristic(page)
