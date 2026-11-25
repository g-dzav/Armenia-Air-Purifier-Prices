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

# Wildberries' Russian catalog and Eldorado/AllSell's Armenian one both
# surfaced the same problem: "Фильтр для очистителя воздуха" / "Օդը մաքրող
# սարքի ֆիլտր" both literally mean "filter FOR an air purifier" - the local
# word for "purifier" is right there, since it's describing what the filter
# fits, so a simple "has filter AND NOT has purifier" check wrongly keeps it.
#
# The fix has two parts:
#  - A product's OWN identity reliably leads its name (word 1): "Purifier",
#    "Очиститель", "Մաքրող" (lit. "purifying"). If that's there, a filter/
#    ozonizer/ionizer mention anywhere else is a feature, not the category -
#    see Dyson's legitimate "Purifier Humidify+Cool" combo units.
#  - Otherwise, if filter/ozonizer/ionizer (any of the three languages)
#    appears within the first few words, that's the product's real category
#    regardless of a "...for an air purifier" compatibility phrase later on.
_LEADING_EXCLUDE_PREFIXES = (
    "filter", "фильтр", "ֆիլտր", "զտիչ",  # զտիչ: native Armenian word for
                                          # "filter" (ֆիլտր is the loanword)
    "ozoniz", "озонатор", "օզոնատոր",
    "ioniz", "ионизатор", "իոնիզատոր",
)
_LEADING_INCLUDE_PREFIXES = ("purifier", "cleaner", "очистител", "մաքր")
_LEADING_EXCLUDE_WINDOW = 4


def _leading_words_say_accessory(lower_name: str) -> bool:
    words = [w.strip(",.-") for w in lower_name.split()]
    if not words:
        return False
    if any(words[0].startswith(p) for p in _LEADING_INCLUDE_PREFIXES):
        return False  # leads with its own purifier identity
    return any(w.startswith(p) for w in words[:_LEADING_EXCLUDE_WINDOW] for p in _LEADING_EXCLUDE_PREFIXES)


def is_excluded_accessory(name: str, price_amd: float | None) -> bool:
    lower = name.lower()
    if any(re.search(p, lower) for p in _EXCLUDE_NAME_PATTERNS):
        return True
    if _leading_words_say_accessory(lower):
        return True
    has_purifier_word = re.search(r"\bpurifier\b|մաքր", lower)
    has_filter_word = re.search(r"\bfilters?\b", lower)
    if has_filter_word and not has_purifier_word:
        return True  # a standalone filter/replacement-part listing, not a unit
    has_humidifier_word = re.search(r"\bhumidif(y|ier|iers)\b|խոնավ", lower)
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


# Several Armenian/Russian storefronts wrap a product's brand+model (always
# Latin script) in native-script description - leading ("Օդը մաքրող սարք
# Ballu AP-125" = "air purifying device Ballu AP-125"), trailing ("Очиститель
# воздуха Core 300S с HEPA-фильтром и Wi-Fi" = "...with a HEPA filter and
# Wi-Fi"), or both. Rather than assume one shape, pull out every Latin-script
# token (allowing internal -/.() so "AC-M18-SC" and "BHR5860EU" survive
# whole) and join them, dropping the native-script words around and between.
# Must only ever be applied to a name AFTER is_excluded_accessory() has
# already judged it - that check depends on the native-script keywords this
# strips out.
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-./()+]*")
_FOREIGN_SCRIPT_RE = re.compile(r"[Ѐ-ӿ԰-֏]")  # Cyrillic, Armenian


def clean_display_name(name: str) -> str:
    if not _FOREIGN_SCRIPT_RE.search(name):
        return name  # already plain Latin script - leave it exactly as scraped
    tokens = _LATIN_TOKEN_RE.findall(name)
    cleaned = " ".join(t.strip("-./()") for t in tokens).strip()
    if len(cleaned) < 8:
        # Too sparse to trust - either the listing is genuinely generic/
        # brandless (no English name exists to extract - a real, if rare,
        # case on marketplace sites) or a homoglyph character (Cyrillic "С"
        # standing in for Latin "C", etc.) broke a token apart. Showing a
        # two-letter fragment is worse than the original name.
        return name
    return cleaned
