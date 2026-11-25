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
    r"\bioniz(er|ation)\b",
    r"\b(fridge|refrigerator)\b",
    r"\buhb-?\d",  # Ballu's humidifier line (e.g. "UHB-1500", "UHB-355 MT") -
                   # confirmed on two different sites' catalogs - the name
                   # alone never says "humidifier", so the generic check below
                   # can't catch it
]
_MIN_PLAUSIBLE_PRICE_AMD = 15_000

# Wildberries' Russian-language catalog surfaced a case the English-only
# whole-string checks get wrong: "Фильтр для очистителя воздуха" (filter FOR
# an air purifier) contains the Russian word for "purifier" too, since it's
# describing what the filter fits - so a "has filter AND NOT has purifier"
# check would wrongly keep it. The fix: when the product's core category
# word (filter/ozonizer/ionizer, either language) leads the name, that's
# reliable regardless of a later compatibility mention - real purifiers
# consistently lead with a brand name or "Purifier"/"Очиститель" themselves.
_LEADING_EXCLUDE_PREFIXES = ("filter", "фильтр", "ozoniz", "озонатор", "ioniz", "ионизатор")
_LEADING_INCLUDE_PREFIXES = ("purifier", "cleaner", "очистител")


def _leading_words_say_accessory(lower_name: str) -> bool:
    first_two = lower_name.split()[:2]
    stripped = [w.strip(",.-") for w in first_two]
    if any(w.startswith(p) for w in stripped for p in _LEADING_INCLUDE_PREFIXES):
        return False  # leads with its own purifier identity - a later mention
        # of filter/ozonizer/ionizer is describing a feature, not the category
    return any(w.startswith(p) for w in stripped for p in _LEADING_EXCLUDE_PREFIXES)


def is_excluded_accessory(name: str, price_amd: float | None) -> bool:
    lower = name.lower()
    if any(re.search(p, lower) for p in _EXCLUDE_NAME_PATTERNS):
        return True
    if _leading_words_say_accessory(lower):
        return True
    has_purifier_word = re.search(r"\bpurifier\b", lower)
    has_filter_word = re.search(r"\bfilters?\b", lower)
    if has_filter_word and not has_purifier_word:
        return True  # a standalone filter/replacement-part listing, not a unit
    has_humidifier_word = re.search(r"\bhumidif(y|ier|iers)\b", lower)
    if has_humidifier_word and not has_purifier_word:
        return True  # a plain humidifier, not an air purifier (Dyson's combo
        # "Purifier Humidify+Cool" units correctly survive this - they say
        # "purifier" too, so the has_purifier_word check keeps them)
    if price_amd is not None and price_amd < _MIN_PLAUSIBLE_PRICE_AMD:
        return True
    return False


# A few sites embed the manufacturer SKU right in the product name instead of
# exposing it as its own field, e.g. "KARCHER AF20 1.024-820.0" or
# "...4 Compact (BHR5860EU)" or "Karcher AF 30 (1.024-821.0)". Shared so any
# site can reuse it rather than re-deriving the same patterns.
_MODEL_PATTERNS = [
    re.compile(r"\((\d\.\d{3}-\d{3}\.\d)\)\s*$"),  # "(1.024-821.0)" - parenthesized Karcher SKU
    re.compile(r"(\d\.\d{3}-\d{3}\.\d)\s*$"),       # "1.024-820.0" - bare Karcher SKU
    re.compile(r"\((\w[\w-]{3,})\)\s*$"),            # "(BHR5860EU)" - generic parenthesized code
]


def extract_model_from_name(name: str) -> str | None:
    for pattern in _MODEL_PATTERNS:
        m = pattern.search(name)
        if m:
            return m.group(1)
    return None
