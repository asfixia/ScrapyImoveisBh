import json
import logging
import math
import time

from botasaurus.request import Request
from botasaurus.soupify import soupify

from utils.data_helpers import getFirstValue, normalize_tipo
from scrapers.zap.parser import (
    BH_VIEWPORT,
    MAX_PAGES,
    ZapDetailPageMetadata,
    ZapMapViewport,
    getImvQuantityFromListPage,
    page_url,
    parse_detail_page_metadata,
)
from scrapers.zap.parser.urls import api_listings_url


LOG = logging.getLogger(__name__)

MAX_IMV_PER_VIEWPORT = 1000
PAGE_DELAY_SMALL = 3
PAGE_SIZE = 30
ITEM_DELAY_SMALL = 1

_MAX_VIEWPORT_SPLIT_DEPTH = 24


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
                LOG.warning(f"HTTP {code} on attempt {attempt} for {url}")
                raise RuntimeError(f"HTTP {code} on attempt {attempt} for {url}")
            return answer
        except (RuntimeError, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            time.sleep(backoff_seconds * attempt)
    code = getattr(answer, "status_code", None) if answer is not None else None
    LOG.error(f"GET failed after {max_attempts} attempts (last HTTP={code}, exc={last_exc}) url={url}")
    return answer


def _leaf_viewports_under_listing_cap(
    request_obj: Request,
    viewport: ZapMapViewport,
    transacao: str,
    *,
    depth: int = 0,
    divided_count: int = 0,
) -> list[tuple[ZapMapViewport, int]] | None:
    if depth > _MAX_VIEWPORT_SPLIT_DEPTH:
        resp = request_get_with_retry(
            request_obj,
            page_url(0, viewport, transacao),
            max_attempts=3,
            timeout=60,
        )
        if resp is None or resp.status_code != 200:
            raise RuntimeError(
                f"Viewport listing count failed: HTTP {getattr(resp, 'status_code', None)}"
            )
        viewportTotal = getImvQuantityFromListPage(soupify(resp))
        if viewportTotal == 0:
            return None
        return [(viewport, viewportTotal)]
    time.sleep(PAGE_DELAY_SMALL)
    resp = request_get_with_retry(
        request_obj,
        page_url(0, viewport, transacao),
        max_attempts=3,
        timeout=60,
    )
    if resp is None or resp.status_code != 200:
        raise RuntimeError(
            f"Viewport listing count failed: HTTP {getattr(resp, 'status_code', None)}"
        )
    viewportTotal = getImvQuantityFromListPage(soupify(resp))
    LOG.info(f"Splitting viewport {viewport.as_query_string()} for {transacao} at depth {depth} -> {viewportTotal} imoveis, divided: {divided_count}")
    if viewportTotal == 0:
        return None
    if viewportTotal is None:
        return None
    if viewportTotal <= MAX_IMV_PER_VIEWPORT:
        return [(viewport, viewportTotal)]
    acc: list[tuple[ZapMapViewport, int]] = []
    expected_quantity = math.ceil(viewportTotal / MAX_IMV_PER_VIEWPORT)
    divided_count += expected_quantity
    for sub in viewport.split_grid(expected_quantity):
        chunk = _leaf_viewports_under_listing_cap(
            request_obj, sub, transacao, depth=depth + 1, divided_count=divided_count
        )
        if chunk is not None:
            acc.extend(chunk)
    return acc


def fetch_imv_details(
    request_obj: Request,
    listing_url: str,
    json_imv: ZapDetailPageMetadata | None,
    referer: str | None = None,
) -> ZapDetailPageMetadata | None:
    """GET listing detail HTML; merge geo, full address, amenities, prices, publicado/atualizado."""
    if json_imv is not None and not json_imv.hasMissingDetails():
        return json_imv
    kwargs: dict = {"timeout": 30}
    if referer:
        kwargs["headers"] = {"referer": referer}
    r = request_obj.get(listing_url, **kwargs)
    if r.status_code != 200:
        return None
    return parse_detail_page_metadata(r.text, json_imv, listing_url)


def _scrape_zap_transaction(
    request_obj: Request,
    transacao: str,
) -> dict[str, ZapDetailPageMetadata]:
    """Warm listing path, split BH_VIEWPORT for this transacao, paginate."""
    warm = request_obj.get(page_url(-1, transacao=transacao), timeout=30)
    if warm.status_code != 200:
        raise RuntimeError(f"Warm-up failed for {transacao!r}: HTTP {warm.status_code}")

    bh_viewport = ZapMapViewport.from_string(BH_VIEWPORT)
    leaf_viewports = _leaf_viewports_under_listing_cap(request_obj, bh_viewport, transacao) or []
    time.sleep(PAGE_DELAY_SMALL)
    total_pages = sum(math.ceil(imv_quantity / PAGE_SIZE) for _, imv_quantity in leaf_viewports)

    total_found = 0
    current_page = 0
    all_imv_data: dict[str, ZapDetailPageMetadata] = {}
    for vp_idx, (leaf_vp, imv_quantity) in enumerate(leaf_viewports):
        total_expected = 0
        qnt_pages = min(max(1, math.ceil(imv_quantity / PAGE_SIZE)), MAX_PAGES)
        resp = None
        for page in range(0, qnt_pages + 1):
            current_page += 1
            list_url = page_url(page, leaf_vp, transacao)
            if resp is None:
                resp = request_obj.get(list_url, timeout=30)
                time.sleep(ITEM_DELAY_SMALL)
                if resp.status_code != 200:
                    LOG.warning(f"[ZAP list] {transacao} page {page} stopped: HTTP {resp.status_code}")
                    break
            imv_found = 0
            glueResp = request_obj.get(
                api_listings_url(
                    user=resp.cookies.get("z_user_id"),
                    page=page + 1,
                    size=PAGE_SIZE,
                    listFrom=total_expected,
                    viewport=leaf_vp,
                    transacao=transacao,
                ),
                timeout=30,
                headers={
                    "referer": list_url,
                    "Origin": "https://www.zapimoveis.com.br",
                    "X-Domain": ".zapimoveis.com.br",
                },
            )
            time.sleep(ITEM_DELAY_SMALL)
            if glueResp.status_code != 200:
                LOG.warning(f"[ZAP list] {transacao} page {page} stopped: HTTP {glueResp.status_code}")
            else:
                glueJson = glueResp.json()
                for curImvJson in glueJson.get("search", {}).get("result", {}).get("listings", []):
                    pricinfInfo = (curImvJson.get("listing").get("pricingInfos", None) or [])
                    href = "https://www.zapimoveis.com.br" + curImvJson.get("link", {}).get("href", "")
                    if href in all_imv_data:
                        continue
                    all_imv_data[href] = ZapDetailPageMetadata(
                        aluguel=getFirstValue([p for p in pricinfInfo if p.get("businessType") == "RENTAL"], {}).get("price", 0),
                        amenidades=curImvJson.get("listing", {}).get("amenities", []),
                        andares=getFirstValue(curImvJson.get("listing", {}).get("floors", None), 0),
                        area=getFirstValue(curImvJson.get("listing", {}).get("usableAreas", None), 0),
                        atualizadoHa=curImvJson.get("listing", {}).get("updatedAt", None),
                        bairro=curImvJson.get("listing", {}).get("address", {}).get("neighborhood", None),
                        banheiros=getFirstValue(curImvJson.get("listing", {}).get("bathrooms", None), None),
                        cidade=curImvJson.get("listing", {}).get("address", {}).get("city", ""),
                        compra=None,
                        condominio=None,
                        detailsUrl=href,
                        enderecoNumero=None,
                        enderecoRua=curImvJson.get("listing", {}).get("address", {}).get("street", None),
                        estado=curImvJson.get("listing", {}).get("address", {}).get("stateAcronym", None),
                        externalId=curImvJson.get("listing", {}).get("externalId", None),
                        fotos=None,
                        geoSource=None,
                        id=curImvJson.get("listing", {}).get("id", None),
                        iptu=getFirstValue(pricinfInfo, {}).get("yearlyIptu", 0) / 12,
                        isAbsoluteLocation=None,
                        jsonDetailsData=json.dumps(curImvJson, ensure_ascii=False, indent=2),
                        jsonGeneralData=None,
                        jsonPointData=None,
                        lat=curImvJson.get("listing", {}).get("address", {}).get("point", {}).get("lat", None) or curImvJson.get("listing", {}).get("address", {}).get("point", {}).get("approximateLat", None) or None,
                        locationId=None,
                        lon=curImvJson.get("listing", {}).get("address", {}).get("point", {}).get("lon", None) or curImvJson.get("listing", {}).get("address", {}).get("point", {}).get("approximateLon", None) or None,
                        publicadoHa=None,
                        quartos=getFirstValue(curImvJson.get("listing", {}).get("bedrooms", None), None),
                        tipoImovel=normalize_tipo(getFirstValue(curImvJson.get("listing", {}).get("unitTypes", None), None)),
                        vagas=getFirstValue(curImvJson.get("listing", {}).get("parkingSpaces", None), None),
                        fullJsonData=json.dumps(curImvJson, ensure_ascii=False, indent=0),
                    )
                    imv_found += 1
                    total_found += 1
            total_expected = min(total_expected + PAGE_SIZE, imv_quantity)
            LOG.info(f"[ZapImoveis - {resp.status_code}] {transacao} viewport {vp_idx + 1}/{len(leaf_viewports)} in page {page}/{qnt_pages} (total pages {current_page}/{total_pages}) imovel found {total_found}")
            if imv_found == 0:
                continue
    return all_imv_data
