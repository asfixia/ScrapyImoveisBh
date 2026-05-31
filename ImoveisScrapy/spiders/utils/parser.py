"""Public entry points: list page parsing, detail enrichment, viewport counts."""

from __future__ import annotations

import json
import logging

from bs4 import BeautifulSoup

from ImoveisScrapy.spiders.utils.geocoder import (
    coords_from_two_numeric_csv_parts,
    first_google_maps_embed_query_params,
    get_geo_from_address,
    maps_embed_api_key_from_html,
    skip_embed_geocode,
)
from ImoveisScrapy.spiders.utils.html_extractors import (
    get_aluguel,
    get_area,
    get_banheiros,
    get_condominio,
    get_detail_atualizado_ha,
    get_detail_bairro,
    get_detail_cidade,
    get_detail_endereco_numero,
    get_detail_endereco_rua,
    get_detail_estado,
    get_detail_publicado,
    get_iptu,
    get_vagas,
)
from ImoveisScrapy.spiders.utils.json_extractors import (
    extract_json_data,
    get_aluguel_from_json,
    get_amenities_from_json,
    get_area_from_json,
    get_bairro_from_json,
    get_banheiros_from_json,
    get_bedrooms_from_json,
    get_cidade_from_json,
    get_condominio_from_json,
    get_detail_atualizado_ha_from_json,
    get_detail_publicado_ha_from_json,
    get_endereco_numero_from_json,
    get_endereco_rua_from_json,
    get_estado_from_json,
    get_external_id_from_json,
    get_fotos_from_json,
    get_geo_from_json,
    get_id_from_json,
    get_iptu_from_json,
    get_location_id_from_json,
    get_property_type_from_json,
    get_vagas_from_json,
)
from ImoveisScrapy.spiders.utils.merge import metadata_from_ld_json_item, metadata_from_point_item
from ImoveisScrapy.spiders.utils.models import ZapDetailPageMetadata
from ImoveisScrapy.spiders.utils.normalizers import coerce_lat_lon
from ImoveisScrapy.spiders.utils.parse_result import log_parse_warning
from ImoveisScrapy.spiders.utils.rsc_extractors import (
    find_lat_lon_in_json,
    load_next_data_json,
    regex_lat_lon_from_rsc,
    regex_listing_point_lat_lon,
)

LOG = logging.getLogger(__name__)


def extract_lat_lon_from_detail_html(
    html: str,
) -> tuple[float | None, float | None, str | None]:
    if skip_embed_geocode():
        pair = regex_listing_point_lat_lon(html)
        if pair:
            return pair[0], pair[1], "rsc_listing_point_lat_lon"
        pair = regex_lat_lon_from_rsc(html)
        if pair:
            return pair[0], pair[1], "rsc_approximateLatLon"
        data = load_next_data_json(html)
        if data:
            pair = find_lat_lon_in_json(data)
            if pair:
                return pair[0], pair[1], "__NEXT_DATA__"
        return None, None, None

    params = first_google_maps_embed_query_params(html)
    embed_key = maps_embed_api_key_from_html(html, params)

    center_raw = (params.get("center") or "").strip()
    if center_raw:
        pair = coords_from_two_numeric_csv_parts(center_raw)
        if pair:
            return pair[0], pair[1], "maps_embed_center"

    q_raw = (params.get("q") or "").strip()
    if q_raw:
        pair = coords_from_two_numeric_csv_parts(q_raw)
        if pair:
            return pair[0], pair[1], "maps_embed_q"
        lat_g, lon_g = get_geo_from_address(q_raw, embed_key)
        if lat_g is not None and lon_g is not None:
            src = (
                "maps_embed_q_geocoded_google"
                if embed_key
                else "maps_embed_q_geocoded_nominatim"
            )
            return lat_g, lon_g, src

    pair = regex_listing_point_lat_lon(html)
    if pair:
        return pair[0], pair[1], "rsc_listing_point_lat_lon"

    pair = regex_lat_lon_from_rsc(html)
    if pair:
        return pair[0], pair[1], "rsc_approximateLatLon"

    data = load_next_data_json(html)
    if data:
        pair = find_lat_lon_in_json(data)
        if pair:
            return pair[0], pair[1], "__NEXT_DATA__"

    return None, None, None


def parse_detail_page_metadata(
    html: str,
    json_imv: ZapDetailPageMetadata | None = None,
    listing_url: str | None = None,
) -> ZapDetailPageMetadata:
    soup = BeautifulSoup(html, "html.parser")
    json_data = extract_json_data(soup, "locationId")
    geo = get_geo_from_json(json_data)
    if geo:
        lat, lon, geo_src = geo[0], geo[1], geo[2]
    else:
        lat, lon, geo_src = extract_lat_lon_from_detail_html(html)

    if lat is not None and lon is not None:
        pair = coerce_lat_lon(lat, lon)
        if pair:
            lat, lon = pair[0], pair[1]
        else:
            lat, lon = None, None

    out = ZapDetailPageMetadata(
        aluguel=get_aluguel_from_json(json_data) or get_aluguel(soup),
        amenidades=get_amenities_from_json(json_data),
        andares=None,
        area=get_area_from_json(json_data) or get_area(soup),
        atualizadoHa=get_detail_atualizado_ha_from_json(json_data)
        or get_detail_atualizado_ha(html),
        bairro=get_bairro_from_json(json_data) or get_detail_bairro(html),
        banheiros=get_banheiros_from_json(json_data) or get_banheiros(soup),
        cidade=get_cidade_from_json(json_data) or get_detail_cidade(html),
        compra=None,
        condominio=get_condominio_from_json(json_data) or get_condominio(soup),
        detailsUrl=listing_url,
        enderecoNumero=get_endereco_numero_from_json(json_data)
        or get_detail_endereco_numero(html),
        enderecoRua=get_endereco_rua_from_json(json_data) or get_detail_endereco_rua(html),
        estado=get_estado_from_json(json_data) or get_detail_estado(html),
        externalId=get_external_id_from_json(json_data),
        fotos=get_fotos_from_json(json_data),
        geoSource=geo_src,
        id=get_id_from_json(json_data),
        iptu=get_iptu_from_json(json_data) or get_iptu(soup),
        isAbsoluteLocation=True,
        jsonDetailsData=json_data if isinstance(json_data, dict) else None,
        jsonGeneralData=None,
        jsonPointData=None,
        lat=lat,
        locationId=get_location_id_from_json(json_data),
        lon=lon,
        publicadoHa=get_detail_publicado_ha_from_json(json_data) or get_detail_publicado(soup),
        quartos=get_bedrooms_from_json(json_data),
        tipoImovel=get_property_type_from_json(json_data),
        vagas=get_vagas_from_json(json_data) or get_vagas(soup),
    )
    return out.merge(json_imv)


def get_imv_quantity_from_list_page(soup_list: BeautifulSoup) -> int | None:
    try:
        json_data = extract_json_data(soup_list, '"totalCount')
        if not json_data:
            return None
        total_count = json_data["children"][0][3]["content"]["totalCount"]
        return int(total_count) if total_count else None
    except (KeyError, TypeError, ValueError, IndexError) as e:
        log_parse_warning(
            "list_total_count",
            f"Failed to read totalCount: {e}",
            url=None,
            exc=e,
        )
        return None


def get_imv_list_from_page(
    soup: BeautifulSoup,
    *,
    warnings: list | None = None,
) -> dict[str, ZapDetailPageMetadata]:
    script = soup.find(
        lambda tag: tag.name == "script" and "numberOfItems" in (tag.string or tag.get_text() or "")
    )
    if not script:
        return {}

    try:
        data_json = json.loads(script.text)
        imoveis = [elem["item"] for elem in data_json["itemListElement"]]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        log_parse_warning(
            "list_ld_json",
            f"Failed to parse itemListElement JSON: {e}",
            exc=e,
            warnings_out=warnings,
        )
        return {}

    lat_str = "\"lat\\\""
    point_json_data = extract_json_data(soup, lat_str)
    point_imv_list: list = []
    if isinstance(point_json_data, dict):
        try:
            point_imv_list = point_json_data["children"][0][3]["content"]["listings"]
        except (KeyError, TypeError, IndexError) as e:
            log_parse_warning(
                "list_point_json",
                f"No listings in point JSON: {e}",
                exc=e,
                warnings_out=warnings,
            )

    acc_general: dict[str, ZapDetailPageMetadata] = {}
    for cur_imv in imoveis:
        listing_id = str(cur_imv.get("@id", "")) or "unknown"
        try:
            tmp = metadata_from_ld_json_item(cur_imv)
            if tmp.id:
                acc_general[tmp.id] = tmp
        except (KeyError, TypeError, ValueError) as e:
            log_parse_warning(
                "list_card_ld",
                f"Failed to build metadata from LD+JSON row: {e}",
                listing_id=listing_id,
                exc=e,
                warnings_out=warnings,
            )

    answer: dict[str, ZapDetailPageMetadata] = {}
    for cur_imv in point_imv_list:
        if not isinstance(cur_imv, dict):
            continue
        cur_imv_id = cur_imv.get("id")
        listing_id = str(cur_imv_id) if cur_imv_id is not None else "unknown"
        tmp_data: ZapDetailPageMetadata | None = None
        try:
            tmp_data = metadata_from_point_item(cur_imv)
            other = acc_general.get(tmp_data.id) if tmp_data.id else None
            merged = tmp_data.merge(other) if isinstance(other, ZapDetailPageMetadata) else tmp_data
            if merged.detailsUrl:
                answer[merged.detailsUrl] = merged
        except (KeyError, TypeError, ValueError) as e:
            log_parse_warning(
                "list_card_point",
                f"Failed to merge point listing: {e}",
                listing_id=listing_id,
                exc=e,
                warnings_out=warnings,
            )
    return answer


# Legacy camelCase names used by callers
getImvListFromPage = get_imv_list_from_page
getImvQuantityFromListPage = get_imv_quantity_from_list_page
