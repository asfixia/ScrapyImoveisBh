# -*- coding: utf-8 -*-
"""QuintoAndar spider — botasaurus HTTP client + Scrapy spider in one file."""
from __future__ import annotations

import json
import logging
import math
import sys
import time
import uuid
from pathlib import Path
from typing import Literal

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import scrapy
from botasaurus.request import Request, request

from ImoveisScrapy.spiders.utils import BH_VIEWPORT, MAX_PAGES, ZapMapViewport
from ImoveisScrapy.spiders.utils.scrape_output import output_json_path

LOG = logging.getLogger(__name__)

QuintoAndarSearchType = Literal["RENT", "SALE"]

SEARCH_API_URL = "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/list"
SLUG = "belo-horizonte-mg-brasil"
SMALL_PAGE_SIZE = 12
BIG_PAGE_SIZE = 250
MAX_IMV_PER_VIEWPORT = 1000
_MAX_VIEWPORT_SPLIT_DEPTH = 24


def quint_listing_path_segment(search_type: QuintoAndarSearchType) -> str:
    return "alugar" if search_type == "RENT" else "comprar"


def quint_search_listing_page_url(search_type: QuintoAndarSearchType) -> str:
    return f"https://www.quintoandar.com.br/{quint_listing_path_segment(search_type)}/imovel/{SLUG}"


def quint_property_public_url(hit_id: int | str, search_type: QuintoAndarSearchType) -> str:
    return f"https://www.quintoandar.com.br/imovel/{hit_id}/{quint_listing_path_segment(search_type)}/"


SEARCH_PAGE_URL = quint_search_listing_page_url("RENT")


def _headers() -> dict[str, str]:
    return {
        "accept": "application/json",
        "accept-language": "en-CA,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,en-GB;q=0.6,en-US;q=0.5",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://www.quintoandar.com.br",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "x-ab-test": (
            "ab_beakman_search_services_anonymous_user_embedding_fallback:-1,"
            "ab_beakman_search_services_demand_concentration_v1_map_and_ssr_rent_experiment_v2:1,"
            "ab_beakman_search_services_demand_sufficiency_v1_sale_experiment:-1,"
            "ab_beakman_search_services_demand_sufficiency_v1_sale_experiment_rollout:false,"
            "ab_beakman_search_services_demand_sufficiency_v1_sale_experiment_rollout_v1:false,"
            "ab_beakman_search_services_demand_sufficiency_v1_sale_experiment_v1:-1,"
            "ab_beakman_search_services_feed_filter_search_profile_experiment:0,"
            "ab_beakman_search_services_hue_candidate_generation_experiment_v2:-1,"
            "ab_beakman_search_services_location_embedding_on_cg_experiment:1,"
            "ab_beakman_search_services_open_search_find:1,"
            "ab_beakman_search_services_open_search_migration:false,"
            "ab_beakman_search_services_open_search_migration_rollout:true"
        ),
    }


def _load_json_response(response, label: str) -> dict | None:
    if response is None or response.status_code != 200:
        LOG.warning("QuintoAndar %s stopped: HTTP %s", label, getattr(response, "status_code", None))
        return None
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        LOG.warning("QuintoAndar %s invalid JSON: %s", label, exc)
        return None


def request_get_with_retry(request_obj: Request, url: str, *, max_attempts: int = 4, backoff_seconds: float = 20.0, **kwargs):
    last_exc: BaseException | None = None
    answer = None
    for attempt in range(1, max_attempts + 1):
        try:
            answer = request_obj.get(url, **kwargs)
            code = getattr(answer, "status_code", None)
            if code is not None and ((500 <= code <= 599) or code in (408, 409, 423, 425, 429, 403, 404, 410, 401)):
                raise RuntimeError(f"HTTP {code} on attempt {attempt} for {url}")
            return answer
        except (RuntimeError, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            time.sleep(backoff_seconds * attempt)
    LOG.error("GET failed after %s attempts (last HTTP=%s, exc=%s) url=%s", max_attempts, getattr(answer, "status_code", None) if answer is not None else None, last_exc, url)
    return answer


def request_post_json_with_retry(request_obj: Request, url: str, payload: dict, *, max_attempts: int = 4, backoff_seconds: float = 20.0, **kwargs):
    last_exc: BaseException | None = None
    answer = None
    for attempt in range(1, max_attempts + 1):
        try:
            answer = request_obj.post(url, json=payload, **kwargs)
            code = getattr(answer, "status_code", None)
            if code is not None and ((500 <= code <= 599) or code in (408, 409, 423, 425, 429, 403, 404, 410, 401)):
                raise RuntimeError(f"HTTP {code} on attempt {attempt} for {url}")
            return answer
        except (RuntimeError, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            time.sleep(backoff_seconds * attempt)
    LOG.error("POST failed after %s attempts (last HTTP=%s, exc=%s) url=%s", max_attempts, getattr(answer, "status_code", None) if answer is not None else None, last_exc, url)
    return answer


def get_json_page(request_obj: Request, page: int, page_size: int, viewport: ZapMapViewport,
                  user_id: str = "8CKpWGzaIf1MK0KOqX243aMM91h520_y3htRNjJpCCbr2akc1KHHEg",
                  device_id: str = "8CKpWGzaIf1MK0KOqX243aMM91h520_y3htRNjJpCCbr2akc1KHHEg",
                  *, search_type: QuintoAndarSearchType = "RENT") -> dict:
    parameters = {
        "slug": SLUG, "topics": [],
        "fields": ["id","location","coverImage","rent","totalCost","salePrice","iptuPlusCondominium","area","imageList","imageCaptionList","address","regionName","city","activeSpecialConditions","type","forRent","forSale","bedrooms","parkingSpaces","suites","neighbourhood","categories","bathrooms","installations","amenities","shortRentDescription","shortSaleDescription"],
        "sorting": {"criteria": "MOST_RECENT", "order": "DESC"},
        "pagination": {"pageSize": page_size, "offset": page * page_size},
        "context": {"userId": user_id, "deviceId": device_id, "listShowing": True, "mapShowing": True, "numPhotos": 12, "isSSR": False},
        "filters": {
            "enableFlexibleSearch": True, "businessContext": search_type,
            "location": {"coordinate": {"lat": -19.916681, "lng": -43.934493},
                         "viewport": {"east": viewport.maxX, "north": viewport.maxY, "south": viewport.minY, "west": viewport.minX},
                         "neighborhoods": [], "countryCode": "BR"},
            "priceRange": [], "availability": "ANY", "occupancy": "ANY", "partnerIds": [],
            "specialConditions": [], "excludedSpecialConditions": [], "blocklist": [],
            "selectedHouses": [], "categories": [],
            "houseSpecs": {"area": {"range": {}}, "houseTypes": [], "amenities": [], "installations": [],
                           "bathrooms": {"range": {}}, "bedrooms": {"range": {}}, "parkingSpace": {"range": {}}, "suites": {"range": {}}}},
        "locationDescriptions": [{"description": SLUG}],
    }
    response = request_post_json_with_retry(request_obj, url=SEARCH_API_URL, payload=json.dumps(parameters), headers=_headers(), timeout=60)
    return _load_json_response(response, "search list") or {}


def _get_total_from_json_payload(json_payload: dict) -> int | None:
    return json_payload.get("hits", {}).get("total", {}).get("value", None)


def _leaf_viewports_under_listing_cap(request_obj: Request, viewport: ZapMapViewport, *,
                                       user_id: str, device_id: str, search_type: QuintoAndarSearchType,
                                       depth: int = 0) -> list[tuple[ZapMapViewport, int]]:
    json_payload = get_json_page(request_obj, page=0, page_size=SMALL_PAGE_SIZE, viewport=viewport,
                                  user_id=user_id, device_id=device_id, search_type=search_type)
    total = _get_total_from_json_payload(json_payload)
    LOG.info("[QuintoAndar split] depth %s viewport %s -> %s imoveis", depth, viewport.as_query_string(), total)
    if total is None:
        raise RuntimeError(f"Failed to get JSON total on viewport {viewport.as_query_string()}")
    if total == 0:
        return []
    if total <= MAX_IMV_PER_VIEWPORT or depth >= _MAX_VIEWPORT_SPLIT_DEPTH:
        return [(viewport, total)]
    acc: list[tuple[ZapMapViewport, int]] = []
    for sub_viewport in viewport.split_grid(total / MAX_IMV_PER_VIEWPORT):
        acc.extend(_leaf_viewports_under_listing_cap(request_obj, sub_viewport, user_id=user_id,
                                                      device_id=device_id, depth=depth + 1, search_type=search_type))
    return acc


def _list_get(lst, i, default=None):
    return lst[i] if -len(lst) <= i < len(lst) else default


def _get_thumb(hit: dict) -> str | None:
    thumb_url = hit.get("coverImage") or _list_get(hit.get("orderedImageList", []), 0) or _list_get(hit.get("imageList", []), 0)
    return ("https://www.quintoandar.com.br/img/sml/" + thumb_url) if thumb_url else None


def _scrape_quintoandar(request_obj: Request, *, search_type: QuintoAndarSearchType) -> dict[int, dict]:
    user_id = uuid.uuid4().hex
    device_id = str(uuid.uuid4())
    leaf_viewports = _leaf_viewports_under_listing_cap(
        request_obj, ZapMapViewport.from_string(BH_VIEWPORT),
        user_id=user_id, device_id=device_id, search_type=search_type,
    )
    seen_ids: set = set()
    all_imv_data: dict = {}
    for vp_idx, (viewport, imv_quantity) in enumerate(leaf_viewports):
        page_size = BIG_PAGE_SIZE
        max_pages = min(max(1, math.ceil(imv_quantity / page_size)), MAX_PAGES)
        for page in range(1, max_pages + 1):
            LOG.info("[QuintoAndar page] viewport %s/%s page %s/%s offset=%s expected=%s",
                     vp_idx + 1, len(leaf_viewports), page, max_pages, (page - 1) * page_size, imv_quantity)
            json_payload = get_json_page(request_obj, viewport=viewport, page=page, page_size=page_size,
                                          user_id=user_id, device_id=device_id, search_type=search_type)
            for cur_hit in json_payload.get("hits", {}).get("hits", []):
                hit = cur_hit.get("_source", {})
                hit_id = hit.get("id") or int(cur_hit.get("id"))
                if hit_id in seen_ids:
                    continue
                seen_ids.add(hit_id)
                all_imv_data[hit_id] = {
                    "id": hit_id,
                    "tipo": hit.get("type"),
                    "aluguel": hit.get("rent"),
                    "iptu_condominio": hit.get("iptuPlusCondominium") or ((hit.get("totalCost") or 0) - (hit.get("rent") or 0)),
                    "area": hit.get("area"),
                    "venda": hit.get("salePrice"),
                    "rua": hit.get("address"),
                    "bairro": hit.get("neighbourhood"),
                    "cidade": hit.get("city"),
                    "estado": hit.get("regionName"),
                    "vagas": hit.get("parkingSpaces"),
                    "quartos": hit.get("bedrooms"),
                    "banheiros": hit.get("bathrooms"),
                    "lat": hit.get("location", {}).get("lat"),
                    "long": hit.get("location", {}).get("lon"),
                    "thumb": _get_thumb(hit),
                    "titulo": hit.get("shortRentDescription") or hit.get("shortSaleDescription") or "",
                    "url": quint_property_public_url(hit_id, search_type),
                    "fulljson": json.dumps(hit),
                }
            time.sleep(5)
    return all_imv_data


@request(max_retry=5)
def quintoandar_get_items(request_obj: Request, data=None):  # noqa: ARG001
    start_cookie = request_get_with_retry(request_obj, SEARCH_PAGE_URL, timeout=60)
    if start_cookie is None or start_cookie.status_code != 200:
        return None

    all_imv_data = {
        **_scrape_quintoandar(request_obj, search_type="SALE"),
        **_scrape_quintoandar(request_obj, search_type="RENT"),
    }
    out_path = output_json_path("quintoandar")
    out_path.write_text(json.dumps(all_imv_data, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.info("[QuintoAndar] wrote %s listing(s) to %s", len(all_imv_data), out_path)
    return all_imv_data


class QuintoAndarSpider(scrapy.Spider):
    name = "QuintoAndar"
    allowed_domains = ["www.quintoandar.com.br", "apigw.prod.quintoandar.com.br"]
    custom_settings = {"ROBOTSTXT_OBEY": False}

    def start_requests(self):
        all_imv_data = quintoandar_get_items()
        for imv_data in all_imv_data.values():
            yield imv_data
