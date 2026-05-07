"""BeautifulSoup / parsel extraction for ZAP listing detail pages."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from parsel import Selector

from zap_parser.json_extractors import iptu_monthly_from_rental, rental_pricing_info
from zap_parser.normalizers import (
    datestr_from_zap_ha_relative_phrase,
    decode_json_string_fragment,
    detail_rsc_value_to_datestr,
    normalize_street_number,
    parse_first_int,
    parse_int_digits,
    zap_iso_to_datestr,
)
from zap_parser.rsc_extractors import (
    html_to_plain_chunk,
    regex_detail_prices_fallback,
    rsc_quoted_field,
    zap_detail_listing_cached,
    zap_detail_listing_chunk_cached,
    zap_detail_rsc_snippets_cached,
)


def get_detail_endereco_rua(html: str) -> str | None:
    listing = zap_detail_listing_cached(html)
    if listing:
        addr = listing.get("address") or {}
        street = (addr.get("street") or "").strip()
        if street:
            return street
    chunk = zap_detail_listing_chunk_cached(html)
    s = rsc_quoted_field(chunk, "street")
    return s if s else None


def get_detail_endereco_numero(html: str) -> str | None:
    listing = zap_detail_listing_cached(html)
    if listing:
        addr = listing.get("address") or {}
        n = normalize_street_number(addr.get("streetNumber"))
        if n:
            return n
    chunk = zap_detail_listing_chunk_cached(html)
    if not chunk:
        return None
    m = re.search(r'"streetNumber"\s*:\s*"((?:[^"\\]|\\.)*)"', chunk)
    if m:
        s = decode_json_string_fragment(m.group(1)).strip()
        if s and s not in ("$undefined", "undefined"):
            return s
    m = re.search(r'"streetNumber"\s*:\s*(\d+)', chunk)
    if m:
        return m.group(1)
    return None


def get_detail_bairro(html: str) -> str | None:
    listing = zap_detail_listing_cached(html)
    if listing:
        addr = listing.get("address") or {}
        b = (addr.get("neighborhood") or "").strip() or None
        if b:
            return b
    chunk = zap_detail_listing_chunk_cached(html)
    s = rsc_quoted_field(chunk, "neighborhood")
    return s if s else None


def get_detail_cidade(html: str) -> str | None:
    listing = zap_detail_listing_cached(html)
    if listing:
        addr = listing.get("address") or {}
        c = (addr.get("city") or "").strip() or None
        if c:
            return c
    chunk = zap_detail_listing_chunk_cached(html)
    s = rsc_quoted_field(chunk, "city")
    return s if s else None


def get_detail_estado(html: str) -> str | None:
    listing = zap_detail_listing_cached(html)
    if listing:
        addr = listing.get("address") or {}
        e = (addr.get("stateAcronym") or addr.get("state") or "").strip() or None
        if e:
            return e
    chunk = zap_detail_listing_chunk_cached(html)
    s = rsc_quoted_field(chunk, "stateAcronym")
    if not s:
        s = rsc_quoted_field(chunk, "state")
    if not s and chunk:
        m = re.search(r'"state"\s*:\s*"((?:[^"\\]|\\.)*)"', chunk)
        if m:
            s = decode_json_string_fragment(m.group(1)).strip()
    return s if s else None


def get_detail_endereco_completo(html: str) -> str | None:
    listing = zap_detail_listing_cached(html)
    if listing:
        addr = listing.get("address") or {}
        street = (addr.get("street") or "").strip()
        numero = normalize_street_number(addr.get("streetNumber"))
        bairro = (addr.get("neighborhood") or "").strip() or None
        cidade = (addr.get("city") or "").strip() or None
        estado = (addr.get("stateAcronym") or addr.get("state") or "").strip() or None
        rua_num = ", ".join(p for p in [street, numero] if p)
        line = ", ".join(p for p in [rua_num, bairro, cidade, estado] if p)
        if line:
            return line
    street = (get_detail_endereco_rua(html) or "").strip()
    numero = (get_detail_endereco_numero(html) or "").strip()
    bairro = get_detail_bairro(html)
    cidade = get_detail_cidade(html)
    estado = get_detail_estado(html)
    rua_num = ", ".join(p for p in [street, numero] if p)
    line = ", ".join(p for p in [rua_num, bairro, cidade, estado] if p)
    return line if line else None


def get_detail_endereco(html: str) -> str | None:
    sel_addr = Selector(text=html)
    for xp in (
        "normalize-space(//*[@data-testid='location-address'])",
        "normalize-space(//*[@data-cy='ldp-overview-address'])",
        "normalize-space(//*[@data-cy='property-address'])",
        "normalize-space(//*[contains(@data-cy,'Address')][contains(@data-cy,'property')])",
    ):
        t = sel_addr.xpath(xp).get()
        if t and len(t) > 12 and ("," in t or "-" in t):
            return t.strip()
    return None


def get_detail_preco_aluguel_mensal(html: str) -> int | None:
    from zap_parser.normalizers import to_int

    listing = zap_detail_listing_cached(html)
    if listing:
        rental = rental_pricing_info(listing)
        if rental and rental.get("price") is not None:
            v = to_int(rental.get("price"))
            if v is not None:
                return v
    rsc = zap_detail_rsc_snippets_cached(html)
    v = rsc.get("preco_aluguel_mensal")
    if v is not None:
        return int(v)
    reg = regex_detail_prices_fallback(html).get("preco_aluguel_mensal")
    return reg


def get_detail_preco_condominio_mensal(html: str) -> int | None:
    from zap_parser.normalizers import to_int

    listing = zap_detail_listing_cached(html)
    if listing:
        rental = rental_pricing_info(listing)
        if rental and rental.get("monthlyCondoFee") is not None:
            v = to_int(rental.get("monthlyCondoFee"))
            if v is not None:
                return v
    rsc = zap_detail_rsc_snippets_cached(html)
    v = rsc.get("preco_condominio_mensal")
    if v is not None:
        return int(v)
    t = Selector(text=html).xpath("normalize-space(//*[@data-testid='condoFee'])").get()
    if t:
        v = parse_first_int(t)
        if v is not None:
            return v
    return regex_detail_prices_fallback(html).get("preco_condominio_mensal")


def get_detail_preco_iptu_mensal(html: str) -> int | None:
    listing = zap_detail_listing_cached(html)
    if listing:
        rental = rental_pricing_info(listing)
        v = iptu_monthly_from_rental(rental or {})
        if v is not None:
            return v
    rsc = zap_detail_rsc_snippets_cached(html)
    v = rsc.get("preco_iptu_mensal")
    if v is not None:
        return int(v)
    t = Selector(text=html).xpath("normalize-space(//*[@data-testid='iptu'])").get()
    if t:
        low = t.lower()
        if "isento" in low or "não informado" in low or "nao informado" in low:
            return 0
        dv = parse_first_int(t)
        if dv is not None:
            return dv
    reg = regex_detail_prices_fallback(html).get("preco_iptu_mensal")
    if reg is not None:
        return reg
    plain = html_to_plain_chunk(html)
    if re.search(r"\bIPTU\b.*?\bIsento\b", plain, flags=re.IGNORECASE):
        return 0
    if re.search(r"IPTU\s+n[aã]o\s+informado", plain, flags=re.IGNORECASE):
        return 0
    return None


def get_detail_preco_total_previsto_mensal(html: str) -> int | None:
    from zap_parser.normalizers import to_int

    listing = zap_detail_listing_cached(html)
    if listing:
        rental = rental_pricing_info(listing)
        if rental:
            for cand in (
                "chargingMonthlyTotal",
                "monthlyTotal",
                "totalPrice",
                "value",
                "fullRentPrice",
            ):
                if rental.get(cand) is not None:
                    v = to_int(rental.get(cand))
                    if v is not None:
                        return v
    rsc = zap_detail_rsc_snippets_cached(html)
    v = rsc.get("preco_total_previsto_mensal")
    if v is not None:
        return int(v)
    return regex_detail_prices_fallback(html).get("preco_total_previsto_mensal")


def get_detail_publicado(soup: BeautifulSoup) -> str | None:
    el = soup.find(string=lambda s: s and "publicado" in s.lower())
    if not el:
        return None
    plain = el.parent.text
    d = datestr_from_zap_ha_relative_phrase(plain, "publicado")
    if d:
        return d
    return None


def get_detail_atualizado_ha(html: str) -> str | None:
    plain = html
    d = datestr_from_zap_ha_relative_phrase(plain, "atualizado")
    if d:
        return d
    listing = zap_detail_listing_cached(html)
    if listing:
        ua = listing.get("updatedAt")
        if isinstance(ua, str):
            p = zap_iso_to_datestr(ua)
            if p:
                return p
    rsc = zap_detail_rsc_snippets_cached(html)
    s = rsc.get("atualizado_há")
    return detail_rsc_value_to_datestr(s) if s else None


def get_detail_publicado_atualizado(html: str) -> str | None:
    pub = get_detail_publicado(BeautifulSoup(html, "html.parser"))
    atu = get_detail_atualizado_ha(html)
    if pub or atu:
        parts = []
        if pub:
            parts.append(f"publicado em {pub}")
        if atu:
            parts.append(f"atualizado em {atu}")
        return ", ".join(parts) + "."
    rsc = zap_detail_rsc_snippets_cached(html)
    s = rsc.get("publicado_atualizado")
    return s if s else None


def anchor_html_to_selector(anchor: object) -> Selector:
    html = anchor if isinstance(anchor, str) else str(anchor)
    return Selector(text=html)


def parse_price_value_text(raw: str | None) -> int | None:
    t = (raw or "").strip()
    if not t:
        return None
    if re.fullmatch(r"(?i)isento", t):
        return 0
    if re.fullmatch(r"(?i)n[aã]o\s+informado", t):
        return None
    return parse_int_digits(t)


def value_item_price_by_tooltip_label(
    soup: BeautifulSoup,
    label: str,
    *,
    label_case_insensitive: bool = False,
) -> int | None:
    for wrapper in soup.select(".value-item__tooltip-wrapper"):
        title = wrapper.get_text(" ", strip=True)
        if label_case_insensitive:
            if label.lower() not in title.lower():
                continue
        elif label not in title:
            continue
        parent = wrapper.parent
        if not parent:
            continue
        value_el = parent.select_one(".value-item__value")
        if value_el is None:
            continue
        raw = value_el.get_text(" ", strip=True)
        v = parse_price_value_text(raw)
        if v is not None:
            return v
    return None


def get_area(soup: BeautifulSoup) -> int | None:
    el = soup.find(attrs={"itemprop": "floorSize"})
    if el:
        return parse_int_digits(el.get_text(" ", strip=True))
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d+)\s*m²", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def get_banheiros(soup: BeautifulSoup) -> int | None:
    el = soup.find(attrs={"itemprop": "numberOfBathroomsTotal"})
    if el:
        return parse_int_digits(el.get_text(" ", strip=True))
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d+)\s*banheiros?", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def get_vagas(soup: BeautifulSoup) -> int | None:
    el = soup.find(attrs={"itemprop": "numberOfParkingSpaces"})
    if el:
        return parse_int_digits(el.get_text(" ", strip=True))
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d+)\s*vagas?", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def get_aluguel(soup: BeautifulSoup) -> int | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        content = script.string or script.get_text()
        if not content:
            continue
        match = re.search(r'"price"\s*:\s*(\d+)', content)
        if match:
            return int(match.group(1))
    price_section = soup.find(id="price-section")
    if price_section:
        text = price_section.get_text(" ", strip=True)
        match = re.search(r"Aluguel\s*R\$\s*([\d\.\,]+)", text, re.IGNORECASE)
        if match:
            return parse_int_digits(match.group(1))
    return None


def get_condominio(soup: BeautifulSoup) -> int | None:
    v = value_item_price_by_tooltip_label(soup, "Condomínio")
    if v is not None:
        return v
    el = soup.find(attrs={"data-testid": "condoFee"})
    if el:
        raw = el.get_text(" ", strip=True)
        v = parse_price_value_text(raw)
        if v is not None:
            return v
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Condom[ií]nio\s*R\$\s*([\d\.\,]+)", text, re.IGNORECASE)
    if match:
        return parse_int_digits(match.group(1))
    html = str(soup)
    match = re.search(r'"condoFees"\s*:\s*\[(\d+)\]', html)
    return int(match.group(1)) if match else None


def get_iptu(soup: BeautifulSoup) -> int | None:
    v = value_item_price_by_tooltip_label(soup, "iptu", label_case_insensitive=True)
    if v is not None:
        return v
    el = soup.find(attrs={"data-testid": "iptu"})
    if el:
        raw = el.get_text(" ", strip=True)
        v = parse_price_value_text(raw)
        if v is not None:
            return v
    text = soup.get_text(" ", strip=True)
    match = re.search(r"IPTU\s*R\$\s*([\d\.\,]+)", text, re.IGNORECASE)
    if match:
        return parse_int_digits(match.group(1))
    html = str(soup)
    match = re.search(r'"iptuPrices"\s*:\s*\[(\d+)\]', html)
    return int(match.group(1)) if match else None


def get_property_data(soup: BeautifulSoup) -> dict:
    return {
        "area": get_area(soup),
        "banheiros": get_banheiros(soup),
        "vagas": get_vagas(soup),
        "aluguel": get_aluguel(soup),
        "condominio": get_condominio(soup),
        "iptu": get_iptu(soup),
    }
