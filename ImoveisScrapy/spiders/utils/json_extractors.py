"""Fields from ZAP ``pageData`` / ``__NEXT_DATA__`` / embedded flight JSON."""

from __future__ import annotations

import ast
import json
import logging
from collections.abc import Mapping

from bs4 import BeautifulSoup

from ImoveisScrapy.spiders.utils.normalizers import (
    nested_get,
    to_int,
    zap_amenity_code_to_label,
    zap_iso_to_datestr,
)

LOG = logging.getLogger(__name__)


def resolve_zap_page_data(json_data: dict | None) -> dict | None:
    if not json_data or not isinstance(json_data, dict):
        return None
    pd = json_data.get("pageData")
    if isinstance(pd, dict):
        return pd
    bd = json_data.get("baseData")
    if isinstance(bd, dict):
        pd = bd.get("pageData")
        if isinstance(pd, dict):
            return pd
    if isinstance(json_data.get("listingId"), (str, int)):
        return json_data
    return None


def zap_page_data_field(json_data: dict | None, field: str) -> object | None:
    if not json_data or not isinstance(json_data, dict):
        return None
    bd = json_data.get("baseData")
    if isinstance(bd, dict):
        pd = bd.get("pageData")
        if isinstance(pd, dict) and field in pd:
            return pd[field]
    pd = resolve_zap_page_data(json_data)
    if isinstance(pd, dict) and field in pd:
        return pd[field]
    return None


def first_rental_price_row(page_data: dict) -> dict | None:
    rows = page_data.get("prices")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("businessType") == "RENTAL" or row.get("business") == "RENTAL":
            return row
    for row in rows:
        if isinstance(row, dict):
            return row
    return None


def zap_json_listing_bundle(
    json_data: dict | None,
) -> tuple[dict | None, dict, dict, dict | None, dict, dict]:
    pd = resolve_zap_page_data(json_data)
    if not pd:
        return None, {}, {}, None, {}, {}
    listing = pd.get("listing") if isinstance(pd.get("listing"), dict) else {}
    lp = listing.get("prices") if isinstance(listing.get("prices"), dict) else {}
    price_row = first_rental_price_row(pd)
    lt = pd.get("listingTrackingData") if isinstance(pd.get("listingTrackingData"), dict) else {}
    am = listing.get("amenities") if isinstance(listing.get("amenities"), dict) else {}
    return pd, listing, lp, price_row, lt, am


def rental_pricing_info(listing: dict) -> dict:
    for p in listing.get("pricingInfos") or []:
        if p.get("businessType") == "RENTAL":
            return p if isinstance(p, dict) else {}
    pd = listing.get("prices")
    if isinstance(pd, dict):
        rent = pd.get("rent") if pd.get("rent") is not None else pd.get("mainValue")
        condo = pd.get("condominium")
        iptu_raw = pd.get("iptu")
        syn: dict = {"businessType": "RENTAL", "price": rent, "monthlyCondoFee": condo}
        if iptu_raw is not None and iptu_raw != "":
            try:
                syn["yearlyIptu"] = float(iptu_raw)
            except (TypeError, ValueError):
                pass
        tot = pd.get("monthlyRentalTotalPrice")
        if tot is not None and str(tot).strip():
            try:
                syn["chargingMonthlyTotal"] = int(float(tot))
            except (TypeError, ValueError):
                pass
        if syn.get("price") is not None or syn.get("monthlyCondoFee") is not None:
            return syn
    return {}


def iptu_monthly_from_rental(rental: dict) -> int | None:
    if not rental:
        return None
    iptu_exempt = bool(
        rental.get("iptuExempt")
        or rental.get("iptuIsExempt")
        or rental.get("exemptIptu")
        or (str(rental.get("iptuInformation") or "").lower().find("isento") >= 0)
    )
    if iptu_exempt:
        return 0
    if rental.get("monthlyIptu") is not None:
        return to_int(rental.get("monthlyIptu"))
    if rental.get("iptu") is not None:
        return to_int(rental.get("iptu"))
    if rental.get("yearlyIptu") is not None:
        try:
            yv = float(rental["yearlyIptu"])
            if yv == 0:
                return 0
            return int(round(yv / 12.0))
        except (TypeError, ValueError):
            return None
    return None


def label_from_amenity_item(x: object) -> str | None:
    if isinstance(x, str):
        t = x.strip()
        return t or None
    if isinstance(x, dict):
        for k in ("name", "label", "text", "description", "title"):
            v = x.get(k)
            if v and isinstance(v, str) and v.strip():
                return v.strip()
    return None


def extract_amenities_from_listing(listing: dict) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    am0 = listing.get("amenities")
    if isinstance(am0, dict):
        vals = am0.get("values")
        if isinstance(vals, list):
            for code in vals:
                if not isinstance(code, str):
                    continue
                label = zap_amenity_code_to_label(code)
                if label and label not in seen:
                    seen.add(label)
                    out.append(label)

    explicit_keys = (
        "amenities",
        "features",
        "conveniences",
        "nonFunctionalAmenities",
        "propertyAmenities",
        "comforts",
        "characteristics",
        "tags",
        "listingTagFeatures",
        "highlights",
        "differentials",
        "infrastructure",
        "buildingAmenities",
        "condominiumFeatures",
        "leisure",
        "propertyFeatures",
    )
    for k in explicit_keys:
        v = listing.get(k)
        if not isinstance(v, list):
            continue
        for x in v:
            if isinstance(x, str) and x.isupper() and "_" in x:
                label = zap_amenity_code_to_label(x)
            else:
                label = label_from_amenity_item(x)
            if label and label not in seen:
                seen.add(label)
                out.append(label)
    for k, v in listing.items():
        if not isinstance(v, list) or not v or k in explicit_keys:
            continue
        lk = k.lower()
        if not any(
            s in lk
            for s in (
                "amenit",
                "comfort",
                "feature",
                "tag",
                "highlight",
                "differential",
                "infra",
                "lazer",
                "condomin",
                "leisure",
            )
        ):
            continue
        for x in v:
            if isinstance(x, str) and x.isupper() and "_" in x:
                label = zap_amenity_code_to_label(x)
            else:
                label = label_from_amenity_item(x)
            if label and label not in seen:
                seen.add(label)
                out.append(label)
    return out


def image_urls_from_image_list(image_list: object) -> list[str]:
    if not isinstance(image_list, list):
        return []
    out: list[str] = []
    for item in image_list:
        if not isinstance(item, dict):
            continue
        src = item.get("dangerousSrc")
        if isinstance(src, str) and src.strip():
            out.append(src.strip())
    return out


def get_geo_from_json(json_data: dict | None) -> tuple[float, float, str] | None:
    from ImoveisScrapy.spiders.utils.normalizers import coerce_lat_lon

    pd, listing, _, _, _, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    for addr in (listing.get("address"), pd.get("address")):
        if not isinstance(addr, dict):
            continue
        pt = addr.get("point")
        if isinstance(pt, dict):
            pair = coerce_lat_lon(pt.get("lat"), pt.get("lon"))
            if pair:
                return pair[0], pair[1], "zap_page_json_point"
    return None


def get_area_from_json(json_data: dict | None) -> int | None:
    from ImoveisScrapy.spiders.utils.normalizers import parse_first_int

    pd, _, _, _, _, am = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    if isinstance(am.get("usableAreas"), list) and am["usableAreas"]:
        a = to_int(am["usableAreas"][0])
        if a is not None:
            return a
    if isinstance(pd.get("mainAmenities"), dict):
        ua = pd["mainAmenities"].get("usableAreas")
        if isinstance(ua, str) and ua:
            return parse_first_int(ua)
    return None


def get_banheiros_from_json(json_data: dict | None) -> int | None:
    _, _, _, _, _, am = zap_json_listing_bundle(json_data)
    if isinstance(am.get("bathrooms"), list) and am["bathrooms"]:
        return to_int(am["bathrooms"][0])
    return None


def get_vagas_from_json(json_data: dict | None) -> int | None:
    _, _, _, _, _, am = zap_json_listing_bundle(json_data)
    if isinstance(am.get("parkingSpaces"), list) and am["parkingSpaces"]:
        return to_int(am["parkingSpaces"][0])
    return None


def get_aluguel_from_json(json_data: dict | None) -> int | None:
    pd, _, lp, price_row, lt, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    aluguel = to_int(lp.get("rent"))
    if aluguel is None:
        aluguel = to_int(lp.get("mainValue"))
    if aluguel is None and price_row:
        aluguel = to_int(price_row.get("price"))
        ri = price_row.get("rentalInfo") if isinstance(price_row.get("rentalInfo"), dict) else {}
        if aluguel is None:
            aluguel = to_int(ri.get("monthlyRentalTotalPrice"))
    if aluguel is None and isinstance(lt.get("rentalPrices"), list) and lt["rentalPrices"]:
        aluguel = to_int(lt["rentalPrices"][0])
    return aluguel


def get_condominio_from_json(json_data: dict | None) -> int | None:
    pd, _, lp, price_row, lt, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    condominio = to_int(lp.get("condominium"))
    if condominio is None and price_row:
        condominio = to_int(price_row.get("monthlyCondoFee"))
    if condominio is None and isinstance(lt.get("condoFees"), list) and lt["condoFees"]:
        condominio = to_int(lt["condoFees"][0])
    return condominio


def get_iptu_from_json(json_data: dict | None) -> int | None:
    pd, _, lp, price_row, lt, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    iptu = to_int(lp.get("iptu"))
    if iptu is None and price_row:
        iptu = to_int(price_row.get("iptu"))
    if iptu is None and price_row:
        iptu = to_int(price_row.get("yearlyIptu"))
    if iptu is None and isinstance(lt.get("iptuPrices"), list) and lt["iptuPrices"]:
        iptu = to_int(lt["iptuPrices"][0])
    return iptu


def get_location_id_from_json(json_data: dict | None) -> str | None:
    """``pageData.address.locationId`` (top-level address on page payload)."""
    if not json_data:
        return None
    v = nested_get(json_data, "baseData", "pageData", "address", "locationId", default=None)
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def get_endereco_rua_from_json(json_data: dict | None) -> str | None:
    pd, listing, _, _, _, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    addr = listing.get("address") if isinstance(listing.get("address"), dict) else None
    if not addr:
        addr = pd.get("address") if isinstance(pd.get("address"), dict) else {}
    if addr.get("street"):
        return str(addr["street"]).strip()
    return None


def get_endereco_numero_from_json(json_data: dict | None) -> str | None:
    pd, listing, _, _, _, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    addr = listing.get("address") if isinstance(listing.get("address"), dict) else None
    if not addr:
        addr = pd.get("address") if isinstance(pd.get("address"), dict) else {}
    sn = addr.get("streetNumber")
    if sn is None:
        return None
    s = str(sn).strip()
    if not s:
        return None
    low = s.lower()
    if "$undefined" in s or "undefined" in low:
        return None
    return s


def get_bairro_from_json(json_data: dict | None) -> str | None:
    pd, listing, _, _, _, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    addr = listing.get("address") if isinstance(listing.get("address"), dict) else None
    if not addr:
        addr = pd.get("address") if isinstance(pd.get("address"), dict) else {}
    if addr.get("neighborhood"):
        return str(addr["neighborhood"]).strip()
    return None


def get_cidade_from_json(json_data: dict | None) -> str | None:
    pd, listing, _, _, _, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    addr = listing.get("address") if isinstance(listing.get("address"), dict) else None
    if not addr:
        addr = pd.get("address") if isinstance(pd.get("address"), dict) else {}
    if addr.get("city"):
        return str(addr["city"]).strip()
    return None


def get_fotos_from_json(json_data: dict | None) -> list[str] | None:
    if not json_data:
        return None
    try:
        imgs = nested_get(
            json_data,
            "baseData",
            "pageData",
            "listing",
            "imageList",
            default=None,
        )
        urls = image_urls_from_image_list(imgs or [])
        return urls if urls else None
    except (TypeError, AttributeError) as e:
        LOG.debug("get_fotos_from_json: %s", e)
        return None


def get_external_id_from_json(json_data: dict | None) -> str | None:
    if not json_data:
        return None
    v = nested_get(json_data, "baseData", "pageData", "listing", "externalId", default=None)
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def get_estado_from_json(json_data: dict | None) -> str | None:
    pd, listing, _, _, _, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    addr = listing.get("address") if isinstance(listing.get("address"), dict) else None
    if not addr:
        addr = pd.get("address") if isinstance(pd.get("address"), dict) else {}
    st = addr.get("stateAcronym") or addr.get("state")
    if st:
        return str(st).strip()
    return None


def get_endereco_from_json(json_data: dict | None) -> str | None:
    pd, listing, _, _, _, _ = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    addr = listing.get("address") if isinstance(listing.get("address"), dict) else None
    if not addr:
        addr = pd.get("address") if isinstance(pd.get("address"), dict) else {}
    if addr.get("fullAddress"):
        return str(addr["fullAddress"]).strip()
    if pd.get("formattedAddress"):
        return str(pd["formattedAddress"]).strip()
    return None


def get_amenities_from_json(json_data: dict | None) -> list[str] | None:
    pd, _, _, _, _, am = zap_json_listing_bundle(json_data)
    if not pd:
        return None
    codes: list[str] = []
    if isinstance(am.get("values"), list):
        codes = [c for c in am["values"] if isinstance(c, str)]
    elif isinstance(pd.get("amenities"), list):
        codes = [c for c in pd["amenities"] if isinstance(c, str)]
    if not codes:
        return None
    labels = [zap_amenity_code_to_label(c) for c in codes]
    labels = [x for x in labels if x]
    return labels if labels else None


def get_bedrooms_from_json(json_data: dict | None) -> int | None:
    if not json_data:
        return None
    raw = nested_get(
        json_data,
        "baseData",
        "pageData",
        "listingTrackingData",
        "bedrooms",
        default=None,
    )
    if isinstance(raw, list) and raw:
        return to_int(raw[0])
    return None


def get_property_type_from_json(json_data: dict | None) -> str | None:
    if not json_data:
        return None
    raw = nested_get(
        json_data,
        "baseData",
        "pageData",
        "listingTrackingData",
        "unitTypes",
        default=None,
    )
    if isinstance(raw, list) and raw and raw[0] is not None:
        return str(raw[0]).strip() or None
    return None


def get_detail_publicado_ha_from_json(json_data: dict | None) -> str | None:
    raw = zap_page_data_field(json_data, "createdAt")
    if isinstance(raw, str) and raw.strip():
        return zap_iso_to_datestr(raw.strip())
    return None


def get_detail_atualizado_ha_from_json(json_data: dict | None) -> str | None:
    raw = zap_page_data_field(json_data, "updatedAt")
    if isinstance(raw, str) and raw.strip():
        return zap_iso_to_datestr(raw.strip())
    return None


def get_id_from_json(json_data: dict | None) -> str | None:
    if not json_data:
        return None
    v = nested_get(json_data, "baseData", "pageData", "listingId", default=None)
    if v is None:
        return None
    return str(v)


def extract_json_data(soup: BeautifulSoup, unique_name: str) -> dict | None:
    try:
        dom_content = soup.find(string=lambda s: unique_name in (s or ""))
        if not dom_content:
            return None
        dom_text = dom_content.string
        if not dom_text:
            return None
        first_quote = dom_text.find('"')
        last_quote = dom_text.rfind('"')
        if first_quote == -1 or last_quote == -1 or last_quote <= first_quote:
            return None
        escaped_payload = dom_text[first_quote : last_quote + 1]
        decoded_payload = ast.literal_eval(escaped_payload)
        brace0 = decoded_payload.find("{")
        brace1 = decoded_payload.rfind("}")
        if brace0 == -1 or brace1 == -1 or brace1 < brace0:
            return None
        return json.loads(decoded_payload[brace0 : brace1 + 1])
    except (SyntaxError, ValueError, TypeError, json.JSONDecodeError) as e:
        LOG.debug("extract_json_data failed for %r: %s", unique_name, e)
        return None