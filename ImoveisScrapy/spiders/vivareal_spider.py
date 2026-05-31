# -*- coding: utf-8 -*-
"""
VivaReal spider – rental listings for BH (and optionally Betim, Contagem) via v4 API.
Uses glue-api.vivareal.com/v4/listings (no browser/Selenium).
Yields items in NetImoveis-like shape: id, aluguel, condominio, area, iptu, endereco, vagas, quartos, banheiros, lat, long, fulljson, etc.
"""
import json
import logging
import math
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import quote
from enum import Enum

class VivarealBusiness(str, Enum):
    RENTAL = "RENTAL"
    SALE = "SALE"
    def __str__(self) -> str:
        return self.value


import scrapy
from botasaurus.request import Request, request
from utils.scrape_output import output_json_path
from scrapers.zap.parser import BH_VIEWPORT, ZapMapViewport

LOG = logging.getLogger(__name__)


# includeFields from working browser request (exact string from curl)
#_INCLUDE_FIELDS_RAW = "expansion(search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)),fullUriFragments,nearby(search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)),page,search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)"
_INCLUDE_FIELDS_RAW = "fullUriFragments,page,search(result(listings(listing(expansionType,contractType,listingsCount,propertyDevelopers,sourceId,displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,portals,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usageTypes,totalAreas,advertiserId,advertiserContact,whatsappNumber,bedrooms,acceptExchange,pricingInfos,showPrice,resale,buildings,capacityLimit,status,priceSuggestion,condominiumName,modality,enhancedDevelopment),account(config,id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,createdDate,tier,trustScore,totalCountByFilter,totalCountByAdvertiser),medias,accountLink,link,children(id,usableAreas,totalAreas,bedrooms,bathrooms,parkingSpaces,pricingInfos))),totalCount)"




# v4 API base URL (page, size, from_ are filled per request)
VIVAREAL_V4_BASE = (
    "https://glue-api.vivareal.com/v4/listings"
    "?user={user}"
    "&portal=VIVAREAL"
    "&includeFields=" + quote(_INCLUDE_FIELDS_RAW, safe="")
    + "&categoryPage=RESULT"
    "&business={business}"
    "&sort=MOST_RECENT"
    "&parentId=null"
    #"&listingType=USED"
    "&__zt=mtc:deduplication2023"
    "&addressCity=Belo+Horizonte"
    "&addressZone="
    "&addressStreet="
    "&addressLocationId=BR>Minas+Gerais>NULL>Belo+Horizonte"
    "&addressState=Minas+Gerais"
    "&addressNeighborhood="
    "&addressPointLat=-19.919052"
    "&addressPointLon=-43.938669"
    "&addressType=city"
    "&unitTypes=APARTMENT,HOME,HOME,APARTMENT,APARTMENT,HOME"
    "&unitTypesV3=APARTMENT,HOME,CONDOMINIUM,PENTHOUSE,FLAT,TWO_STORY_HOUSE"
    "&unitSubTypes=UnitSubType_NONE,DUPLEX,LOFT,STUDIO,TRIPLEX|UnitSubType_NONE,SINGLE_STOREY_HOUSE,VILLAGE_HOUSE,KITNET|CONDOMINIUM|PENTHOUSE|FLAT|TWO_STORY_HOUSE"
    "&usageTypes=RESIDENTIAL,RESIDENTIAL,RESIDENTIAL,RESIDENTIAL,RESIDENTIAL,RESIDENTIAL"
    "&page={page}"
    "&size={size}"
    "&from={from_}"
    "&images=webp"
    #"&categoryPage=RESULT"
    #&includeFields=facets,search(totalCount)
)
PAGE_SIZE = 30
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 120
MAX_IMV_PER_VIEWPORT = 600
_MAX_VIEWPORT_SPLIT_DEPTH = 24
MAX_PAGES = 50
PAGE_DELAY_SMALL = 1

VIVAREAL_VIEWPORT_QUERY = (
    "&amenities=PETS_ALLOWED"
    "&business={business}"
    "&sort=MOST_RECENT"
    "&parentId=null"
    "&listingType=USED"
    "&__zt=mtc:deduplication2023"
    "&viewport={viewport}"
    "&unitTypes=APARTMENT,HOME,HOME,APARTMENT,APARTMENT,HOME"
    "&unitTypesV3=APARTMENT,HOME,CONDOMINIUM,PENTHOUSE,FLAT,TWO_STORY_HOUSE"
    "&unitSubTypes=UnitSubType_NONE,DUPLEX,LOFT,STUDIO,TRIPLEX|UnitSubType_NONE,SINGLE_STOREY_HOUSE,VILLAGE_HOUSE,KITNET|CONDOMINIUM|PENTHOUSE|FLAT|TWO_STORY_HOUSE"
    "&usageTypes=RESIDENTIAL,RESIDENTIAL,RESIDENTIAL,RESIDENTIAL,RESIDENTIAL,RESIDENTIAL"
    "&page={page}"
    "&size={size}"
    "&from={from_}"
    "&images=webp"
)

VIVAREAL_V4_VIEWPORT_LISTINGS_BASE = (
    "https://glue-api.vivareal.com/v4/listings"
    "?user={user}"
    "&portal=VIVAREAL"
    "&includeFields=" + quote(_INCLUDE_FIELDS_RAW, safe="")
    + "&categoryPage=RESULT"
    + VIVAREAL_VIEWPORT_QUERY
)

VIVAREAL_V1_VIEWPORT_MAPS_BASE = (
    "https://glue-api.vivareal.com/v1/maps"
    "?user={user}"
    "&portal=VIVAREAL"
    "&includeFields=maps"
    + VIVAREAL_VIEWPORT_QUERY
    + "&categoryPage=RESULT"
)


def _default_headers(device_id: str):
    return {
        "Accept": "*/*",
        "Accept-Language": "en-CA,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,en-GB;q=0.6,en-US;q=0.5",
        "Cache-Control": "no-cache",
        "Origin": "https://www.vivareal.com.br",
        "Pragma": "no-cache",
        "Priority": "u=1, i",
        "Referer": "https://www.vivareal.com.br/",
        "Sec-Ch-Ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "X-DeviceId": device_id,
        "x-domain": ".vivareal.com.br",
    }


def _rental_pricing(listing: dict):
    for p in listing.get("pricingInfos") or []:
        if p.get("businessType") == "RENTAL":
            return p
    return None


def _sale_pricing(listing: dict):
    for p in listing.get("pricingInfos") or []:
        if p.get("businessType") == "SALE":
            return p
    return None


def _point_lat_lon(address: dict):
    if not address:
        return None, None
    point = address.get("point") or {}
    lat = point.get("lat") or point.get("approximateLat")
    lon = point.get("lon") or point.get("approximateLon")
    return (lat, lon)


def _get_first_value(seq, default=None):
    """Return the first element of seq if non-null and non-empty; otherwise default."""
    if seq is None:
        return default
    if not isinstance(seq, (list, tuple)):
        return default
    if len(seq) == 0:
        return default
    return seq[0]


def _get_item(item: dict) -> dict:
    """Build a single yielded item from the API listing wrapper (listing + link, etc.)."""
    listing = item.get("listing") or {}
    address = listing.get("address") or {}
    map_data = item.get("map") or {}
    link = item.get("link") or {}
    link_data = link.get("data") or {}
    rental = _rental_pricing(listing)
    sale = _sale_pricing(listing)
    lat, lon = _point_lat_lon(address)
    map_point = map_data.get("point") or {}
    lat = lat or map_point.get("lat") or map_point.get("approximateLat")
    lon = lon or map_point.get("lon") or map_point.get("approximateLon")

    # endereco as string (state, city, neighborhood, street, number)
    endereco_parts = [
        address.get("stateAcronym") or "",
        address.get("city") or "",
        address.get("neighborhood") or "",
        address.get("street") or "",
        link_data.get("streetNumber") or "",
    ]
    endereco = ", ".join(p for p in endereco_parts if p)

    iptu_monthly = None
    if rental and rental.get("yearlyIptu") is not None:
        try:
            iptu_monthly = rental["yearlyIptu"] / 12.0
        except (TypeError, ZeroDivisionError):
            iptu_monthly = None

    return {
        "id": listing.get("id"),
        "aluguel": rental.get("price") if rental else None,
        "condominio": rental.get("monthlyCondoFee") if rental else None,
        "area": _get_first_value(listing.get("totalAreas") or listing.get("usableAreas")),
        "iptu": iptu_monthly,
        "atualizado": listing.get("updatedAt") or listing.get("createdAt"),
        "venda": sale.get("price") if sale else None,
        "tem_locacao": 1 if rental else 0,
        "tem_venda": 1 if sale else 0,
        "endereco": endereco,
        "vagas": _get_first_value(listing.get("parkingSpaces")),
        "quartos": _get_first_value(listing.get("bedrooms")),
        "banheiros": _get_first_value(listing.get("bathrooms")),
        "lat": lat,
        "long": lon,
        "titulo": listing.get("title") or "",
        "descricao": listing.get("description") or "",
        "url": "https://www.vivareal.com.br" + (link.get("href") or ""),
        "fulljson": json.dumps(item),
    }


def _botasaurus_get_with_retry(
    request_obj: Request,
    url: str,
    *,
    headers: dict,
    max_attempts: int = MAX_RETRIES,
    backoff_seconds: float = RETRY_DELAY_SECONDS,
):
    last_exc: BaseException | None = None
    answer = None
    for attempt in range(1, max_attempts + 1):
        try:
            answer = request_obj.get(url, headers=headers, timeout=60)
            code = getattr(answer, "status_code", None)
            if code == 200:
                return answer
            LOG.warning(
                "VivaReal v4 HTTP %s on attempt %s/%s: %s",
                code,
                attempt,
                max_attempts,
                getattr(answer, "text", "")[:300],
            )
        except (RuntimeError, OSError, TimeoutError) as exc:
            last_exc = exc
            LOG.warning(
                "VivaReal v4 request failed on attempt %s/%s: %s",
                attempt,
                max_attempts,
                exc,
            )
        if attempt < max_attempts:
            time.sleep(backoff_seconds * attempt)

    LOG.error(
        "VivaReal v4 GET failed after %s attempts (last HTTP=%s, exc=%s) url=%s",
        max_attempts,
        getattr(answer, "status_code", None) if answer is not None else None,
        last_exc,
        url,
    )
    return answer


def _format_vivareal_viewport(viewport: ZapMapViewport) -> str:
    return quote(viewport.as_query_string(), safe="")


def _vivareal_listing_url(
    device_id: str,
    viewport: ZapMapViewport,
    page: int,
    business: VivarealBusiness,
    page_size: int = PAGE_SIZE
) -> str:
    return VIVAREAL_V4_VIEWPORT_LISTINGS_BASE.format(
        user=device_id,
        business=business,
        viewport=_format_vivareal_viewport(viewport),
        page=page,
        size=page_size,
        from_=(page - 1) * page_size,
    )


def _vivareal_maps_url(
    device_id: str,
    viewport: ZapMapViewport,
    page: int,
    page_size: int = PAGE_SIZE,
    *,
    business: VivarealBusiness,
) -> str:
    return VIVAREAL_V1_VIEWPORT_MAPS_BASE.format(
        user=device_id,
        business=business,
        viewport=_format_vivareal_viewport(viewport),
        page=page,
        size=page_size,
        from_=(page - 1) * page_size,
    )


def _load_json_response(response, label: str) -> dict | None:
    if response is None or response.status_code != 200:
        LOG.warning(
            "VivaReal %s stopped: HTTP %s",
            label,
            getattr(response, "status_code", None) if response is not None else None,
        )
        return None
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        LOG.warning("VivaReal %s invalid JSON: %s", label, exc)
        return None


def _search_total_count(payload: dict) -> int | None:
    search = payload.get("search") or {}
    total = search.get("totalCount")
    if total is None:
        total = (search.get("result") or {}).get("totalCount")
    if total is None:
        return None
    try:
        return int(total)
    except (TypeError, ValueError):
        return None


def _merge_listing_and_map_data(listings: list[dict], maps: list[dict]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for raw_item in listings:
        listing = raw_item.get("listing") or {}
        listing_id = str(listing.get("id") or "")
        if not listing_id:
            continue
        merged[listing_id] = raw_item

    for map_item in maps:
        listing_id = str(map_item.get("id") or "")
        if not listing_id:
            continue
        item = merged.setdefault(listing_id, {"listing": {"id": listing_id}})
        item["map"] = map_item

    return merged


def _vivareal_total_for_viewport(
    request_obj: Request,
    device_id: str,
    viewport: ZapMapViewport,
    *,
    business: VivarealBusiness,
) -> int | None:
    response = _botasaurus_get_with_retry(
        request_obj,
        _vivareal_listing_url(device_id, viewport, page=1, business=business),
        headers=_default_headers(device_id),
    )
    payload = _load_json_response(response, "listing count")
    if payload is None:
        return None
    return _search_total_count(payload)


def _leaf_viewports_under_vivareal_cap(
    request_obj: Request,
    device_id: str,
    viewport: ZapMapViewport,
    *,
    depth: int = 0,
    business: VivarealBusiness,
) -> list[tuple[ZapMapViewport, int]]:
    total = _vivareal_total_for_viewport(request_obj, device_id, viewport, business=business)
    LOG.info(
        "[VivaReal split] depth %s viewport %s -> %s imoveis",
        depth,
        viewport.as_query_string(),
        total,
    )
    if total is None or total == 0:
        return []
    if total <= MAX_IMV_PER_VIEWPORT or depth >= _MAX_VIEWPORT_SPLIT_DEPTH:
        return [(viewport, total)]
    acc: list[tuple[ZapMapViewport, int]] = []
    for sub_viewport in viewport.split_grid(total / MAX_IMV_PER_VIEWPORT):
        acc.extend(
            _leaf_viewports_under_vivareal_cap(
                request_obj,
                device_id,
                sub_viewport,
                depth=depth + 1,
                business=business,
            )
        )
    return acc


def _scrape_vivareal_viewports(
    request_obj: Request,
    device_id: str,
    business: VivarealBusiness,
) -> dict[str, dict]:
    bh_viewport = ZapMapViewport.from_string(BH_VIEWPORT)
    leaf_viewports = _leaf_viewports_under_vivareal_cap(request_obj, device_id, bh_viewport, business=business)
    time.sleep(PAGE_DELAY_SMALL)
    total_pages = sum(math.ceil(imv_quantity / PAGE_SIZE) for _, imv_quantity in leaf_viewports)
    LOG.info(
        "[VivaReal split] business=%s %s leaf viewport(s) total pages %s",
        business,
        len(leaf_viewports),
        total_pages,
    )

    all_imv_data: dict[str, dict] = {}
    current_page = 0
    for vp_idx, (viewport, imv_quantity) in enumerate(leaf_viewports):
        qnt_pages = min(max(1, math.ceil(imv_quantity / PAGE_SIZE)), MAX_PAGES)
        for page in range(1, qnt_pages + 1):
            current_page += 1
            list_url = _vivareal_listing_url(device_id, viewport, page, business=business)
            maps_url = _vivareal_maps_url(device_id, viewport, page, business=business)
            LOG.info(
                "[VivaReal page] viewport %s/%s page %s/%s expected %s page %s of %s",
                vp_idx + 1,
                len(leaf_viewports),
                page,
                qnt_pages,
                imv_quantity,
                current_page,
                total_pages,
            )
            list_payload = _load_json_response(
                _botasaurus_get_with_retry(
                    request_obj,
                    list_url,
                    headers=_default_headers(device_id),
                ),
                "listings",
            )
            if list_payload is None:
                break
            maps_payload = _load_json_response(
                _botasaurus_get_with_retry(
                    request_obj,
                    maps_url,
                    headers=_default_headers(device_id),
                ),
                "maps",
            )
            if maps_payload is None:
                break

            listings = (
                list_payload.get("search", {}).get("result", {}).get("listings", [])
            )
            maps = maps_payload.get("search", {}).get("result", {}).get("maps", [])
            page_items = _merge_listing_and_map_data(listings, maps)
            all_imv_data.update(page_items)
            LOG.info(
                "[VivaReal page] listings=%s maps=%s merged_page=%s total_keys=%s",
                len(listings),
                len(maps),
                len(page_items),
                len(all_imv_data),
            )
            if not listings and not maps:
                break
            time.sleep(PAGE_DELAY_SMALL)
    return all_imv_data


@request(max_retry=2)
def vivareal_viewport_listing_pages(request_obj: Request, data):
    device_id = data.get("device_id") or str(uuid.uuid4())
    imv_data_sale = _scrape_vivareal_viewports(request_obj, device_id, business=VivarealBusiness.SALE)
    imv_data_rent = _scrape_vivareal_viewports(request_obj, device_id, business=VivarealBusiness.RENTAL)
    return list({**imv_data_rent, **imv_data_sale}.values())


class VivaRealSpider(scrapy.Spider):
    name = "VivaReal"
    allowed_domains = ["glue-api.vivareal.com"]
    custom_settings = {"ROBOTSTXT_OBEY": False}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device_id = str(uuid.uuid4())

    def start_requests(self):
        listings = vivareal_viewport_listing_pages(
            {
                "device_id": self._device_id,
            }
        )
        
        out_path = output_json_path("vivareal")
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(listings, fp, ensure_ascii=False, indent=2)
        LOG.info("[VivaReal output] wrote %s listing(s) to %s", len(listings), out_path)
        for idx, raw_item in enumerate(listings or []):
            try:
                yield _get_item(raw_item)
            except Exception as e:
                self.logger.warning("VivaReal v4 error: %s, index: %s", e, idx)
                continue
