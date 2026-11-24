from __future__ import annotations

import re

KNOWN_BRANDS = [
    "Xiaomi", "Dyson", "Karcher", "Kärcher", "Philips", "Beurer", "Levoit",
    "Ballu", "Boneco", "AENO", "Tesla", "Electrolux", "Samsung", "Sharp",
    "Panasonic", "Viomi", "Smartmi", "Deerma", "Ufesa",
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
