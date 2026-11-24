from __future__ import annotations

import re

KNOWN_BRANDS = [
    # Multi-word brands must come before any single-word brand that's also
    # a substring of them (e.g. "Green Lion" before anything starting "Green").
    "Green Lion", "Xiaomi", "Dyson", "Karcher", "Kärcher", "Philips", "Beurer",
    "Levoit", "Ballu", "Boneco", "AENO", "Tesla", "Electrolux", "Samsung",
    "Sharp", "Panasonic", "Viomi", "Smartmi", "Deerma", "Ufesa", "Porodo",
    "Powerology", "Honeywell", "LG", "Renon", "Vitesy", "Blueair",
]


def guess_brand(name: str) -> str | None:
    for brand in KNOWN_BRANDS:
        if re.search(rf"\b{re.escape(brand)}\b", name, re.IGNORECASE):
            return "Karcher" if brand == "Kärcher" else brand
    return name.split()[0] if name else None


def parse_amd(text: str) -> float | None:
    """Turn '316 350 ֏' / '94,900 AMD' / '199000.00' into 316350.0."""
    if text is None:
        return None
    digits = re.sub(r"[^\d.]", "", text.replace(",", ""))
    return float(digits) if digits else None


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


# Category listing pages on several sites mix real air purifier units in with
# adjacent gadgets (air coolers, deodorizers/scent diffusers, standalone
# replacement filters) that this tracker isn't meant to cover. Keyword rules
# catch the clear cases; the price floor catches cheap accessories that
# don't announce themselves by name (the cheapest real purifier unit seen
# across every site so far is ~25,000 AMD, so anything well under that is
# almost certainly an accessory, not a unit).
_EXCLUDE_NAME_PATTERNS = [
    r"\bair\s*cooler\b",
    r"\bcooler\b",
    r"\bdeodoriz(er|ing|ation)\b",
    r"\bscent\s*diffuser\b",
    r"\baroma\b",
    r"\bozoniz(er|ation)\b",
    r"\b(fridge|refrigerator)\b",
]
_MIN_PLAUSIBLE_PRICE_AMD = 15_000


def is_excluded_accessory(name: str, price_amd: float | None) -> bool:
    lower = name.lower()
    if any(re.search(p, lower) for p in _EXCLUDE_NAME_PATTERNS):
        return True
    has_filter_word = re.search(r"\bfilters?\b", lower)
    has_purifier_word = re.search(r"\bpurifier\b", lower)
    if has_filter_word and not has_purifier_word:
        return True  # a standalone filter/replacement-part listing, not a unit
    if price_amd is not None and price_amd < _MIN_PLAUSIBLE_PRICE_AMD:
        return True
    return False
