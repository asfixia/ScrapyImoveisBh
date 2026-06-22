"""ZAP Imóveis — scraper (aluguel + venda)."""
from __future__ import annotations

import json
import logging
import math
import sys
import time
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from botasaurus.request import Request, request
from botasaurus.soupify import soupify

from ImoveisScrapy.spiders.utils import (
    BH_VIEWPORT,
    MAX_PAGES,
    ZapDetailPageMetadata,
    ZapMapViewport,
    getImvQuantityFromListPage,
    page_url,
    parse_detail_page_metadata,
)
from ImoveisScrapy.spiders.utils.urls import api_listings_url
from ImoveisScrapy.spiders.utils.merge import metadata_from_glue_listing
from ImoveisScrapy.spiders.utils.models import ImoveisScrapyItem
from ImoveisScrapy.spiders.utils.scrape_output import output_json_path

try:
    from botasaurus_requests.exceptions import ClientException as _ClientException
except ImportError:
    _ClientException = type("_ClientException", (Exception,), {})

_REQUEST_RETRY_ERRORS = (RuntimeError, OSError, TimeoutError, _ClientException)

LOG = logging.getLogger(__name__)

MAX_IMV_PER_VIEWPORT = 1000
PAGE_DELAY_SMALL = 3
PAGE_SIZE = 30
ITEM_DELAY_SMALL = 1
_MAX_VIEWPORT_SPLIT_DEPTH = 24


def _listing_output_dict(imv: ZapDetailPageMetadata) -> dict[str, object]:
    """Merge-compatible fields only (no payload / raw API blobs)."""
    out: dict[str, object] = {}
    for name in ImoveisScrapyItem.merge_field_names():
        v = getattr(imv, name)
        if isinstance(v, date):
            out[name] = v.isoformat()
        else:
            out[name] = v
    return out


def _write_listings_json(path: Path, listings: dict[str, ZapDetailPageMetadata]) -> int:
    """Write id-keyed JSON incrementally (one listing at a time) to limit peak memory."""
    count = 0
    with path.open("w", encoding="utf-8") as fp:
        fp.write("{\n")
        first = True
        for imv in listings.values():
            if not first:
                fp.write(",\n")
            first = False
            key = json.dumps(str(imv.id), ensure_ascii=False)
            inner_lines = json.dumps(
                _listing_output_dict(imv),
                ensure_ascii=False,
                indent=2,
            ).split("\n")
            fp.write(f"  {key}: {inner_lines[0]}\n")
            for line in inner_lines[1:-1]:
                fp.write(f"  {line}\n")
            fp.write(f"  {inner_lines[-1]}")
            count += 1
        fp.write("\n}\n")
    return count


def request_get_with_retry(request_obj: Request, url: str, *, max_attempts: int = 4, backoff_seconds: float = 20.0, **kwargs):
    last_exc: BaseException | None = None
    answer = None
    for attempt in range(1, max_attempts + 1):
        try:
            answer = request_obj.get(url, **kwargs)
            code = getattr(answer, "status_code", None)
            if code is not None and ((500 <= code <= 599) or code in (408, 409, 423, 425, 429, 403, 404, 410, 401)):
                LOG.warning(f"HTTP {code} on attempt {attempt} for {url}")
                raise RuntimeError(f"HTTP {code} on attempt {attempt} for {url}")
            return answer
        except _REQUEST_RETRY_ERRORS as exc:
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
        resp = request_get_with_retry(request_obj, page_url(0, viewport, transacao), max_attempts=3, timeout=60)
        if resp is None or resp.status_code != 200:
            raise RuntimeError(f"Viewport listing count failed: HTTP {getattr(resp, 'status_code', None)}")
        viewportTotal = getImvQuantityFromListPage(soupify(resp))
        return None if viewportTotal == 0 else [(viewport, viewportTotal)]
    time.sleep(PAGE_DELAY_SMALL)
    resp = request_get_with_retry(request_obj, page_url(0, viewport, transacao), max_attempts=3, timeout=60)
    if resp is None or resp.status_code != 200:
        raise RuntimeError(f"Viewport listing count failed: HTTP {getattr(resp, 'status_code', None)}")
    viewportTotal = getImvQuantityFromListPage(soupify(resp))
    LOG.info(f"Splitting viewport {viewport.as_query_string()} for {transacao} at depth {depth} -> {viewportTotal} imoveis, divided: {divided_count}")
    if not viewportTotal:
        return None
    if viewportTotal <= MAX_IMV_PER_VIEWPORT:
        return [(viewport, viewportTotal)]
    #return [(viewport, viewportTotal)]
    acc: list[tuple[ZapMapViewport, int]] = []
    expected_quantity = math.ceil(viewportTotal / MAX_IMV_PER_VIEWPORT)
    divided_count += expected_quantity
    for sub in viewport.split_grid(expected_quantity):
        chunk = _leaf_viewports_under_listing_cap(request_obj, sub, transacao, depth=depth + 1, divided_count=divided_count)
        if chunk is not None:
            acc.extend(chunk)
    return acc


def fetch_imv_details(request_obj: Request, listing_url: str, json_imv: ZapDetailPageMetadata | None, referer: str | None = None) -> ZapDetailPageMetadata | None:
    if json_imv is not None and not json_imv.hasMissingDetails():
        return json_imv
    kwargs: dict = {"timeout": 30}
    if referer:
        kwargs["headers"] = {"referer": referer}
    r = request_obj.get(listing_url, **kwargs)
    if r.status_code != 200:
        return None
    return parse_detail_page_metadata(r.text, json_imv, listing_url)


def _scrape_zap_transaction(request_obj: Request, transacao: str) -> dict[str, ZapDetailPageMetadata]:
    warm = request_obj.get(page_url(-1, transacao=transacao), timeout=30)
    if warm.status_code != 200:
        raise RuntimeError(f"Warm-up failed for {transacao!r}: HTTP {warm.status_code}")

    bh_viewport = ZapMapViewport.from_string(BH_VIEWPORT)
    leaf_viewports = _leaf_viewports_under_listing_cap(request_obj, bh_viewport, transacao) or []
    time.sleep(PAGE_DELAY_SMALL)
    total_pages = sum(math.ceil(q / PAGE_SIZE) for _, q in leaf_viewports)

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
            glueResp = request_get_with_retry(
                request_obj,
                api_listings_url(
                    user=resp.cookies.get("z_user_id"),
                    page=page + 1,
                    size=PAGE_SIZE,
                    listFrom=total_expected,
                    viewport=leaf_vp,
                    transacao=transacao,
                ),
                max_attempts=4,
                timeout=60,
                headers={
                    "referer": list_url,
                    "Origin": "https://www.zapimoveis.com.br",
                    "X-Domain": ".zapimoveis.com.br",
                },
            )
            time.sleep(ITEM_DELAY_SMALL)
            if glueResp is None or glueResp.status_code != 200:
                LOG.warning(
                    "[ZAP list] %s page %s stopped: HTTP %s",
                    transacao,
                    page,
                    getattr(glueResp, "status_code", None),
                )
            else:
                for curImvJson in glueResp.json().get("search", {}).get("result", {}).get("listings", []):
                    meta = metadata_from_glue_listing(curImvJson)
                    if not meta.url or meta.url in all_imv_data:
                        continue
                    all_imv_data[meta.url] = meta
                    imv_found += 1
                    total_found += 1
            total_expected = min(total_expected + PAGE_SIZE, imv_quantity)
            LOG.info(f"[ZAP] {transacao} vp {vp_idx + 1}/{len(leaf_viewports)} page {page}/{qnt_pages} (total {current_page}/{total_pages}) found {total_found}")
            if imv_found == 0:
                continue
    return all_imv_data


@request(max_retry=1)
def zap_scraper(request_obj: Request, data=None):
    """Scrape ZAP aluguel and venda listings for BH, writing a single combined JSON file."""
    out_path = output_json_path("zapimoveis")
    LOG.info("Saving to %s", out_path)
    from ImoveisScrapy.spiders.utils import TRANSACAO_ALUGUEL, TRANSACAO_VENDA

    merged: dict[str, ZapDetailPageMetadata] = {}
    for transacao in (TRANSACAO_ALUGUEL, TRANSACAO_VENDA):
        LOG.info("[ZAP] scraping %s", transacao)
        batch = _scrape_zap_transaction(request_obj, transacao)
        LOG.info("[ZAP] collected %s listing(s) for %s", len(batch), transacao)
        merged.update(batch)
        LOG.info("[ZAP] merged total %s listing(s)", len(merged))
        del batch
    LOG.info("[ZAP] collected %s listing(s)", len(merged))

    count = _write_listings_json(out_path, merged)
    merged.clear()
    LOG.info("[ZAP] wrote %s listing(s) to %s", count, out_path)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    zap_scraper()
