"""QuintoAndar botasaurus scraper."""
from __future__ import annotations

import json
import logging
import math
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Literal

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

QuintoAndarSearchType = Literal["RENT", "SALE"]

from botasaurus.request import Request, request
from botasaurus.soupify import soupify

from utils.scrape_output import output_json_path
from scrapers.zap.parser import BH_VIEWPORT, MAX_PAGES, ZapMapViewport

LOG = logging.getLogger(__name__)

SEARCH_API_URL = "https://apigw.prod.quintoandar.com.br/house-listing-search/v2/search/list"
SLUG = "belo-horizonte-mg-brasil"


def quint_listing_path_segment(search_type: QuintoAndarSearchType) -> str:
    """Public URL segment: alugar (rent) or comprar (sale)."""
    return "alugar" if search_type == "RENT" else "comprar"


def quint_search_listing_page_url(search_type: QuintoAndarSearchType) -> str:
    """HTML search hub used for cookies / totals (must match businessContext)."""
    return (
        f"https://www.quintoandar.com.br/{quint_listing_path_segment(search_type)}"
        f"/imovel/{SLUG}"
    )


def quint_property_public_url(hit_id: int | str, search_type: QuintoAndarSearchType) -> str:
    return (
        f"https://www.quintoandar.com.br/imovel/{hit_id}/"
        f"{quint_listing_path_segment(search_type)}/"
    )


SEARCH_PAGE_URL = quint_search_listing_page_url("RENT")
SMALL_PAGE_SIZE = 12
BIG_PAGE_SIZE = 250
MAX_IMV_PER_VIEWPORT = 1000
_MAX_VIEWPORT_SPLIT_DEPTH = 24

def _load_json_response(response, label: str) -> dict | None:
    if response is None or response.status_code != 200:
        LOG.warning(
            "QuintoAndar %s stopped: HTTP %s",
            label,
            getattr(response, "status_code", None) if response is not None else None,
        )
        return None
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        LOG.warning("QuintoAndar %s invalid JSON: %s", label, exc)
        return None

def get_json_page(
    request_obj: Request,
    page: int,
    page_size: int,
    viewport: ZapMapViewport,
    user_id: str = "8CKpWGzaIf1MK0KOqX243aMM91h520_y3htRNjJpCCbr2akc1KHHEg",
    device_id: str = "8CKpWGzaIf1MK0KOqX243aMM91h520_y3htRNjJpCCbr2akc1KHHEg",
    *,
    search_type: QuintoAndarSearchType = "RENT",
) -> dict:
    parameters = {"slug": SLUG, "topics": [],
        "fields":["id","location","coverImage","rent","totalCost","salePrice","iptuPlusCondominium","area","imageList","imageCaptionList","address","regionName","city","activeSpecialConditions","type","forRent","forSale","bedrooms","parkingSpaces","suites","neighbourhood","categories","bathrooms","installations","amenities","shortRentDescription","shortSaleDescription"],
        "sorting":{"criteria":"MOST_RECENT","order":"DESC"},
        "pagination":{"pageSize":page_size,"offset":page * page_size},
        "context":{"userId":user_id,"deviceId":device_id,"listShowing":True,"mapShowing":True,"numPhotos":12,"isSSR":False},
        "filters":{"enableFlexibleSearch":True,"businessContext":search_type,"location":{"coordinate":{"lat":-19.916681,"lng":-43.934493},
        "viewport":{"east":viewport.maxX,"north":viewport.maxY,"south":viewport.minY,"west":viewport.minX},
        "neighborhoods":[],"countryCode":"BR"},"priceRange":[],"availability":"ANY","occupancy":"ANY","partnerIds":[],"specialConditions":[],"excludedSpecialConditions":[],"blocklist":[],"selectedHouses":[],"categories":[],"houseSpecs":{"area":{"range":{}},"houseTypes":[],"amenities":[],"installations":[],"bathrooms":{"range":{}},"bedrooms":{"range":{}},"parkingSpace":{"range":{}},"suites":{"range":{}}}},
        "locationDescriptions": [{"description": SLUG}]}
    response = request_post_json_with_retry(request_obj, url=SEARCH_API_URL, payload=json.dumps(parameters), headers=_headers(), timeout=60)
    return _load_json_response(response, "search list") or {}


def request_get_with_retry(
    request_obj: Request,
    url: str,
    *,
    max_attempts: int = 4,
    backoff_seconds: float = 20.0,
    **kwargs,
):
    last_exc: BaseException | None = None
    answer = None
    for attempt in range(1, max_attempts + 1):
        try:
            answer = request_obj.get(url, **kwargs)
            code = getattr(answer, "status_code", None)
            if code is not None and (
                (500 <= code <= 599)
                or code in (408, 409, 423, 425, 429, 403, 404, 410, 401)
            ):
                raise RuntimeError(f"HTTP {code} on attempt {attempt} for {url}")
            return answer
        except (RuntimeError, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            time.sleep(backoff_seconds * attempt)
    LOG.error(
        "GET failed after %s attempts (last HTTP=%s, exc=%s) url=%s",
        max_attempts,
        getattr(answer, "status_code", None) if answer is not None else None,
        last_exc,
        url,
    )
    return answer


def request_post_json_with_retry(
    request_obj: Request,
    url: str,
    payload: dict,
    *,
    max_attempts: int = 4,
    backoff_seconds: float = 20.0,
    **kwargs,
):
    last_exc: BaseException | None = None
    answer = None
    for attempt in range(1, max_attempts + 1):
        try:
            answer = request_obj.post(url, json=payload, **kwargs)
            code = getattr(answer, "status_code", None)
            if code is not None and (
                (500 <= code <= 599)
                or code in (408, 409, 423, 425, 429, 403, 404, 410, 401)
            ):
                raise RuntimeError(f"HTTP {code} on attempt {attempt} for {url}")
            return answer
        except (RuntimeError, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            time.sleep(backoff_seconds * attempt)
    LOG.error(
        "POST failed after %s attempts (last HTTP=%s, exc=%s) url=%s",
        max_attempts,
        getattr(answer, "status_code", None) if answer is not None else None,
        last_exc,
        url,
    )
    return answer


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


def _viewport_to_payload(viewport: ZapMapViewport) -> dict[str, float]:
    return {
        "east": viewport.maxX,
        "north": viewport.maxY,
        "south": viewport.minY,
        "west": viewport.minX,
    }



def _parse_quantity_text(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"[\d.]+", text)
    if not match:
        return None
    return int(match.group(0).replace(".", ""))


def _deep_iter(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _deep_iter(child)
    elif isinstance(value, list):
        for child in value:
            yield from _deep_iter(child)

def _looks_like_house(item: dict) -> bool:
    return "id" in item and any(
        key in item
        for key in (
            "rent",
            "totalCost",
            "salePrice",
            "area",
            "address",
            "bedrooms",
            "parkingSpaces",
        )
    )


def _extract_houses(payload: dict) -> list[dict]:
    preferred_paths = (
        ("hits",),
        ("houses",),
        ("items",),
        ("results",),
        ("listings",),
        ("data", "hits"),
        ("data", "houses"),
        ("data", "items"),
        ("data", "results"),
        ("data", "listings"),
    )
    for path in preferred_paths:
        cur: Any = payload
        for part in path:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if isinstance(cur, list) and cur and all(isinstance(x, dict) for x in cur):
            houses = [x for x in cur if _looks_like_house(x)]
            if houses:
                return houses

    candidates: list[dict] = []
    for obj in _deep_iter(payload):
        if _looks_like_house(obj):
            candidates.append(obj)
    seen: set[str] = set()
    unique: list[dict] = []
    for item in candidates:
        item_id = str(item.get("id"))
        if item_id in seen:
            continue
        seen.add(item_id)
        unique.append(item)
    return unique



def _get_total_from_json_payload(json_payload: dict) -> int | None:
    return json_payload.get("hits", {}).get("total", {}).get("value", None)

def _leaf_viewports_under_listing_cap(
    request_obj: Request,
    viewport: ZapMapViewport,
    *,
    user_id: str,
    device_id: str,
    search_type: QuintoAndarSearchType,
    depth: int = 0,
) -> list[tuple[ZapMapViewport, int]]:
    json_payload = get_json_page(
        request_obj,
        page=0,
        page_size=SMALL_PAGE_SIZE,
        viewport=viewport,
        user_id=user_id,
        device_id=device_id,
        search_type=search_type,
    )
    total = _get_total_from_json_payload(json_payload)
    LOG.info(
        "[QuintoAndar split] depth %s viewport %s -> %s imoveis",
        depth,
        viewport.as_query_string(),
        total,
    )
    if total is None:
        raise Exception("Failed to get JSON total on viewport %s", viewport.as_query_string())
    elif total == 0:
        return []
    elif total <= MAX_IMV_PER_VIEWPORT or depth >= _MAX_VIEWPORT_SPLIT_DEPTH:
        return [(viewport, total)]

    expected_quantity = total / MAX_IMV_PER_VIEWPORT
    acc: list[tuple[ZapMapViewport, int]] = []
    for sub_viewport in viewport.split_grid(expected_quantity):
        acc.extend(
            _leaf_viewports_under_listing_cap(
                request_obj,
                sub_viewport,
                user_id=user_id,
                device_id=device_id,
                depth=depth + 1,
                search_type=search_type,
            )
        )
    return acc


def _item_id(item: dict) -> str | None:
    value = item.get("id") or item.get("houseId") or item.get("listingId")
    return str(value) if value is not None else None

def list_get(lst, i, default=None):
    return lst[i] if -len(lst) <= i < len(lst) else default

def get_thumb_from_json(hit: dict) -> str | None:
    thumb_url = hit.get("coverImage", None) or list_get(hit.get("orderedImageList", []), 0, None) or list_get(hit.get("imageList", []), 0, None)
    return ("https://www.quintoandar.com.br/img/sml/" + thumb_url) if thumb_url else None

def _scrape_quintoandar(
    request_obj: Request, *, search_type: QuintoAndarSearchType
) -> dict[int, dict]:
    user_id = uuid.uuid4().hex
    device_id = str(uuid.uuid4())
    leaf_viewports = _leaf_viewports_under_listing_cap(
        request_obj,
        ZapMapViewport.from_string(BH_VIEWPORT),
        user_id=user_id,
        device_id=device_id,
        search_type=search_type,
    )
    seen_ids = set()

    all_imv_data: dict[str, dict] = {}
    for vp_idx, (viewport, imv_quantity) in enumerate(leaf_viewports):
        #offset = 0
        page_size = BIG_PAGE_SIZE
        max_pages = min(max(1, math.ceil(imv_quantity / page_size)), MAX_PAGES)
        for page in range(1, max_pages + 1):
            cur_offset = (page - 1) * page_size
            LOG.info(
                "[QuintoAndar page] viewport %s/%s page %s/%s offset=%s expected=%s",
                vp_idx + 1,
                len(leaf_viewports),
                page,
                max_pages,
                cur_offset,
                imv_quantity,
            )
            json_payload = get_json_page(
                request_obj,
                viewport=viewport,
                page=page,
                page_size=page_size,
                user_id=user_id,
                device_id=device_id,
                search_type=search_type,
            )
            #api_total = _get_total_from_json_payload(json_payload)
            for cur_hit in json_payload.get('hits', {}).get('hits', []):
                hit = cur_hit.get("_source", {})
                hit_id = hit.get("id", None) or int(cur_hit.get("id"))
                if hit_id in seen_ids:
                    continue
                seen_ids.add(hit_id)
                all_imv_data[hit_id] = {
                    "id": hit_id,
                    "tipo": hit.get("type", None),
                    "aluguel": hit.get("rent", None),
                    "iptu_condominio": hit.get("iptuPlusCondominium", None) or (hit.get("totalCost", None) - hit.get("rent", None)),
                    "area": hit.get("area", None),
                    "venda": hit.get("salePrice", None),
                    "rua": hit.get("address", None),
                    "bairro": hit.get("neighbourhood", None),
                    "cidade": hit.get("city", None),
                    "estado": hit.get("regionName", None),
                    "vagas": hit.get("parkingSpaces", None),
                    "quartos": hit.get("bedrooms", None),
                    "banheiros": hit.get("bathrooms", None),
                    "lat": hit.get("location", {}).get("lat", None),
                    "long": hit.get("location", {}).get("lon", None),
                    "thumb": get_thumb_from_json(hit),
                    "titulo": hit.get("shortRentDescription", None) or hit.get("shortSaleDescription", None) or "",
                    "url": quint_property_public_url(hit_id, search_type),
                    "fulljson": json.dumps(hit),
                }
            time.sleep(5)
            page += 1
    return all_imv_data


def quintoandar_item(raw: dict) -> dict:
    address = raw.get("address")
    if isinstance(address, dict):
        endereco = ", ".join(str(v) for v in address.values() if v)
    else:
        endereco = address
    return {
        "id": _item_id(raw),
        "aluguel": raw.get("rent"),
        "condominio": None,
        "area": raw.get("area"),
        "iptu": raw.get("iptuPlusCondominium"),
        "atualizado": None,
        "venda": raw.get("salePrice"),
        "tem_locacao": 1 if raw.get("forRent") else 0,
        "tem_venda": 1 if raw.get("forSale") else 0,
        "endereco": endereco,
        "vagas": raw.get("parkingSpaces"),
        "quartos": raw.get("bedrooms"),
        "banheiros": raw.get("bathrooms"),
        "lat": raw.get("lat") or raw.get("latitude"),
        "long": raw.get("lng") or raw.get("lon") or raw.get("longitude"),
        "titulo": raw.get("shortRentDescription") or raw.get("shortSaleDescription") or "",
        "descricao": raw.get("shortRentDescription") or raw.get("shortSaleDescription") or "",
        "url": raw.get("url"),
        "fulljson": json.dumps(raw, ensure_ascii=False),
    }


@request(max_retry=5)
def quintoandar_get_items(
    request_obj: Request,
    data=None
):
    startCookie = request_get_with_retry(request_obj, SEARCH_PAGE_URL, timeout=60)
    if startCookie is None or startCookie.status_code != 200:
        return None

    imv_data_sale = _scrape_quintoandar(request_obj, search_type="SALE")
    imv_data_rent = _scrape_quintoandar(request_obj, search_type="RENT")
    all_imv_data = {**imv_data_sale, **imv_data_rent}
    out_path = output_json_path("quintoandar")
    out_path.write_text(
        json.dumps(all_imv_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LOG.info("[QuintoAndar output] wrote %s listing(s) to %s", len(all_imv_data), out_path)

    return all_imv_data


#if __name__ == "__main__":
#    logging.basicConfig(level=logging.INFO)
#    quintoandar_get_items()
