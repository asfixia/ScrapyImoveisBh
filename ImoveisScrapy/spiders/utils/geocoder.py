"""Geocoding behind explicit calls (Google with embed key, else Nominatim)."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from ImoveisScrapy.spiders.utils.constants import NOMINATIM_USER_AGENT

LOG = logging.getLogger(__name__)

_GOOGLE_MAPS_EMBED_URL_RES = (
    re.compile(r"(?:https?:)?//(?:www\.)?google\.com/maps/embed[^\"'<>]+", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?google\.com/maps/embed[^\"'<>]+", re.IGNORECASE),
)


def normalize_maps_embed_url(url: str) -> str:
    u = (url or "").strip()
    if u.startswith("//"):
        u = "https:" + u
    return u.replace("&amp;", "&").replace("&#38;", "&")


def embed_query_params_from_url(url: str) -> dict[str, str]:
    u = normalize_maps_embed_url(url)
    try:
        parsed = urlparse(u)
    except ValueError:
        return {}
    if not parsed.query:
        return {}
    qs = parse_qs(parsed.query, keep_blank_values=False)
    out: dict[str, str] = {}
    for k, v in qs.items():
        if v and v[0] is not None:
            out[k] = unquote(v[0].strip())
    return out


def iter_google_maps_embed_urls(html: str):
    seen: set[str] = set()
    for cre in _GOOGLE_MAPS_EMBED_URL_RES:
        for m in cre.finditer(html):
            raw = m.group(0)
            if raw not in seen:
                seen.add(raw)
                yield raw


def first_google_maps_embed_query_params(html: str) -> dict[str, str]:
    for url in iter_google_maps_embed_urls(html):
        params = embed_query_params_from_url(url)
        if params:
            return params
    return {}


def maps_embed_api_key_from_html(html: str, params: dict[str, str] | None = None) -> str:
    if params:
        k = (params.get("key") or "").strip()
        if k:
            return k
    for url in iter_google_maps_embed_urls(html):
        p = embed_query_params_from_url(url)
        k = (p.get("key") or "").strip()
        if k:
            return k
    return ""


def coords_from_two_numeric_csv_parts(s: str) -> tuple[float, float] | None:
    s = (s or "").strip()
    if "," not in s:
        return None
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 2:
        return None
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None


def geocode_google(address: str, api_key: str, *, timeout: float = 20.0) -> tuple[float | None, float | None]:
    if not address or not api_key:
        return None, None
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json?" + urlencode(
            {"address": address, "key": api_key}
        )
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError, ValueError) as e:
        LOG.debug("Google geocode failed: %s", e)
        return None, None
    if data.get("status") != "OK" or not data.get("results"):
        return None, None
    loc = (data["results"][0].get("geometry") or {}).get("location") or {}
    try:
        lat, lon = float(loc["lat"]), float(loc["lng"])
    except (KeyError, TypeError, ValueError):
        return None, None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None, None


def geocode_nominatim(address: str, *, timeout: float = 20.0) -> tuple[float | None, float | None]:
    if not address or len(address) < 3:
        return None, None
    try:
        url = "https://nominatim.openstreetmap.org/search?" + urlencode(
            {"q": address, "format": "json", "limit": "1"}
        )
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": NOMINATIM_USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError, ValueError) as e:
        LOG.debug("Nominatim geocode failed: %s", e)
        return None, None
    if not data:
        return None, None
    try:
        lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, TypeError, ValueError):
        return None, None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None, None


def get_geo_from_address(
    address: str,
    apikey: str = "",
    *,
    timeout: float = 20.0,
) -> tuple[float | None, float | None]:
    addr = (address or "").strip()
    if len(addr) < 3:
        return None, None
    low = addr.lower()
    if "brazil" not in low and "brasil" not in low:
        addr_q = f"{addr}, Brazil"
    else:
        addr_q = addr
    key = (apikey or "").strip()
    if key:
        return geocode_google(addr_q, key, timeout=timeout)
    return geocode_nominatim(addr_q, timeout=timeout)


def skip_embed_geocode() -> bool:
    return os.environ.get("ZAP_SKIP_EMBED_GEOCODE", "").strip() in ("1", "true", "yes")
