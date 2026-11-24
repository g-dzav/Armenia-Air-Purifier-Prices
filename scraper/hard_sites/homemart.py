"""homemart.am — not Cloudflare, but runs its own proof-of-work "I'm not a
robot" checkbox (zhCAPTCHA) that blocks plain HTTP requests. Their own
robots.txt even has a comment about actively fighting bot traffic, so this
one in particular deserves light, infrequent (weekly) touch rather than any
attempt at a daily automated bypass.
"""
from __future__ import annotations

from . import generic_extract
from ..sites.base import ScrapedProduct

SITE_NAME = "homemart"
LISTING_URL = "https://homemart.am/texnika-tan-hamar/ody-maqrox-xonavacnox-sarqer/"


def looks_blocked(page) -> bool:
    return generic_extract.looks_blocked(page)


def scrape(page) -> list[ScrapedProduct]:
    return generic_extract.extract(page)
