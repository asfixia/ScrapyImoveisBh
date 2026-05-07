"""Next.js / RSC string fragments and regex fallbacks over raw HTML."""

from __future__ import annotations

import json
import re
from functools import lru_cache

from parsel import Selector

from zap_parser.normalizers import (
    decode_json_string_fragment,
    parse_first_int,
    valid_lat_lon,
    zap_amenity_code_to_label,
    zap_iso_to_datestr,
)


def html_to_plain_chunk(html: str, max_len: int = 2_000_000) -> str:
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html[:max_len])
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def regex_lat_lon_from_rsc(html: str) -> tuple[float, float] | None:
    m = re.search(
        r'"approximateLat"\s*:\s*(-?\d+\.?\d*)\s*,\s*"approximateLon"\s*:\s*(-?\d+\.?\d*)',
        html,
    )
    if not m:
        m = re.search(
            r'"approximateLon"\s*:\s*(-?\d+\.?\d*)\s*,\s*"approximateLat"\s*:\s*(-?\d+\.?\d*)',
            html,
        )
        if m:
            lo, la = float(m.group(1)), float(m.group(2))
            if valid_lat_lon(la, lo):
                return la, lo
        return None
    la, lo = float(m.group(1)), float(m.group(2))
    if valid_lat_lon(la, lo):
        return la, lo
    return None


def regex_listing_point_lat_lon(html: str) -> tuple[float, float] | None:
    m = re.search(
        r'"listing"[\s\S]{0,60000}?"address"\s*:\s*\{[\s\S]{0,20000}?"point"\s*:\s*\{\s*'
        r'"lat"\s*:\s*(-?\d+\.?\d*)\s*,\s*"lon"\s*:\s*(-?\d+\.?\d*)',
        html,
    )
    if not m:
        return None
    try:
        la, lo = float(m.group(1)), float(m.group(2))
    except ValueError:
        return None
    if valid_lat_lon(la, lo):
        return la, lo
    return None


def parse_rsc_page_data_snippets(html: str) -> dict:
    patch: dict = {}
    mf = re.search(r'"formattedAddress"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if mf:
        patch["endereco"] = decode_json_string_fragment(mf.group(1)).strip()

    mt = re.search(r'"monthlyRentalTotalPrice"\s*:\s*"(\d+)"', html)
    if mt:
        patch["preco_total_previsto_mensal"] = int(mt.group(1))

    iptu_yearly = bool(re.search(r'"iptuPeriod"\s*:\s*"YEARLY"', html))
    m_yearly_iptu = re.search(r'"yearlyIptu"\s*:\s*"(\d+)"', html)
    if iptu_yearly and m_yearly_iptu:
        try:
            yv = int(m_yearly_iptu.group(1))
            patch["preco_iptu_mensal"] = int(round(yv / 12.0)) if yv else 0
            patch["iptu"] = patch["preco_iptu_mensal"]
        except ValueError:
            pass

    m_rent = re.search(r'"monthlyCondoFee"\s*:\s*"(\d+)"', html)
    if m_rent:
        try:
            patch["preco_condominio_mensal"] = int(m_rent.group(1))
        except ValueError:
            pass

    m_price = re.search(
        r'"monthlyRentalTotalPrice"\s*:\s*"\d+"\}\s*,\s*"yearlyIptu"\s*:\s*"\d+"\s*,\s*"price"\s*:\s*"(\d+)"',
        html,
    )
    if not m_price:
        ml = re.search(r'"listing"\s*:\s*\{', html)
        if ml:
            chunk = html[ml.start() : ml.start() + 35000]
            m_price = re.search(r'"prices"\s*:\s*\{[^}]*?"rent"\s*:\s*(\d+)', chunk)
    if m_price:
        try:
            patch["preco_aluguel_mensal"] = int(m_price.group(1))
        except ValueError:
            pass

    m_am = re.search(
        r'"amenities"\s*:\s*\{[^\}]{0,4000}?"values"\s*:\s*\[([^\]]*)\]',
        html,
        flags=re.DOTALL,
    )
    if m_am:
        codes = re.findall(r'"([A-Z][A-Z0-9_]*)"', m_am.group(1))
        labels = [zap_amenity_code_to_label(c) for c in codes]
        labels = [x for x in labels if x]
        if labels:
            patch["amenities"] = labels
            patch["amenidades"] = labels

    pub_dt = atu_dt = None
    ml = re.search(r'"listing"\s*:\s*\{', html)
    if ml:
        lchunk = html[ml.start() : ml.start() + 65000]
        mc = re.search(r'"createdAt"\s*:\s*"([^"]+)"', lchunk)
        mu = re.search(r'"updatedAt"\s*:\s*"([^"]+)"', lchunk)
        if mc:
            pub_dt = zap_iso_to_datestr(mc.group(1))
        if mu:
            atu_dt = zap_iso_to_datestr(mu.group(1))
    if not pub_dt:
        mc = re.search(r'"createdAt"\s*:\s*"([^"]+)"', html)
        if mc:
            pub_dt = zap_iso_to_datestr(mc.group(1))
    if not atu_dt:
        mu = re.search(r'"updatedAt"\s*:\s*"([^"]+)"', html)
        if mu:
            atu_dt = zap_iso_to_datestr(mu.group(1))
    if pub_dt:
        patch["publicado_há"] = pub_dt
    if atu_dt:
        patch["atualizado_há"] = atu_dt
    if pub_dt or atu_dt:
        parts = []
        if pub_dt:
            parts.append(f"publicado em {pub_dt}")
        if atu_dt:
            parts.append(f"atualizado em {atu_dt}")
        patch["publicado_atualizado"] = ", ".join(parts) + "."

    return patch


def load_next_data_json(html: str) -> dict | None:
    sel = Selector(text=html)
    raw = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
    if not raw or not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def find_lat_lon_in_json(obj: object, depth: int = 0) -> tuple[float, float] | None:
    if depth > 30:
        return None
    if isinstance(obj, dict):
        lat = obj.get("lat") or obj.get("approximateLat")
        lon = obj.get("lon") or obj.get("approximateLon")
        pair = None
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            pair = (float(lat), float(lon))
        if pair and valid_lat_lon(pair[0], pair[1]):
            return pair[0], pair[1]
        for v in obj.values():
            found = find_lat_lon_in_json(v, depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for it in obj:
            found = find_lat_lon_in_json(it, depth + 1)
            if found:
                return found
    return None


def collect_listing_like_dicts(obj: object, depth: int = 0, acc: list | None = None) -> list[dict]:
    if acc is None:
        acc = []
    if depth > 42:
        return acc
    if isinstance(obj, dict):
        addr = obj.get("address")
        prices = obj.get("prices")
        has_prices = bool(obj.get("pricingInfos")) or (
            isinstance(prices, dict)
            and (prices.get("rent") is not None or prices.get("mainValue") is not None)
        )
        if isinstance(addr, dict) and addr.get("street") and has_prices:
            acc.append(obj)
        for v in obj.values():
            collect_listing_like_dicts(v, depth + 1, acc)
    elif isinstance(obj, list):
        for it in obj:
            collect_listing_like_dicts(it, depth + 1, acc)
    return acc


def pick_best_listing(candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    def score(d: dict) -> int:
        s = len(json.dumps(d, default=str))
        amps = d.get("amenities") or d.get("features") or d.get("conveniences") or []
        if isinstance(amps, list):
            s += min(len(amps) * 50, 500)
        elif isinstance(amps, dict):
            vals = amps.get("values")
            if isinstance(vals, list):
                s += min(len(vals) * 50, 500)
        return s

    return max(candidates, key=score)


def listing_from_zap_next_data(html: str) -> dict | None:
    data = load_next_data_json(html)
    if not data:
        return None
    pp = (data.get("props") or {}).get("pageProps") or {}
    if isinstance(pp.get("listing"), dict) and (pp["listing"].get("address") or {}).get("street"):
        return pp["listing"]
    return pick_best_listing(collect_listing_like_dicts(data))


def rsc_listing_json_chunk(html: str, max_len: int = 200_000) -> str:
    ml = re.search(r'"listing"\s*:\s*\{', html)
    if not ml:
        return ""
    return html[ml.start() : ml.start() + max_len]


def rsc_quoted_field(chunk: str, field: str) -> str:
    if not chunk:
        return ""
    m = re.search(rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"', chunk)
    if not m:
        return ""
    return decode_json_string_fragment(m.group(1)).strip()


@lru_cache(maxsize=32)
def zap_detail_listing_cached(html: str) -> dict | None:
    return listing_from_zap_next_data(html)


@lru_cache(maxsize=32)
def zap_detail_listing_chunk_cached(html: str) -> str:
    return rsc_listing_json_chunk(html)


@lru_cache(maxsize=32)
def zap_detail_rsc_snippets_cached(html: str) -> dict:
    return parse_rsc_page_data_snippets(html)


def regex_detail_prices_fallback(html: str) -> dict[str, int]:
    d: dict[str, int] = {}
    patterns = (
        ("preco_aluguel_mensal", r"Aluguel\s+R\$\s*([\d\.]+)\s*/\s*mês"),
        ("preco_condominio_mensal", r"Condomínio\s+R\$\s*([\d\.]+)\s*/\s*mês"),
        ("preco_iptu_mensal", r"IPTU\s+R\$\s*([\d\.]+)"),
        ("preco_total_previsto_mensal", r"Valor total previsto\s+R\$\s*([\d\.]+)"),
    )
    for key, pat in patterns:
        m = re.search(pat, html, flags=re.IGNORECASE | re.DOTALL)
        if m:
            v = parse_first_int(m.group(1))
            if v is not None:
                d[key] = v
    return d
