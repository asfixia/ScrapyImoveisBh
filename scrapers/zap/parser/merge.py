"""Build :class:`~zap_parser.models.ZapDetailPageMetadata` from list JSON-LD vs map point payloads."""

from __future__ import annotations

from typing import Any

from scrapers.zap.parser.json_extractors import image_urls_from_image_list
from scrapers.zap.parser.models import ZapDetailPageMetadata
from scrapers.zap.parser.normalizers import nested_get
from scrapers.zap.parser.urls import url_remove_parameters


def price_from_buy_action(cur_imv: dict) -> object | None:
    pa = cur_imv.get("offers", {}).get("potentialAction", None)
    if pa is None:
        return None
    if pa.get("@type", "") == "BuyAction":
        return pa.get("priceSpecification", {}).get("price", None)
    return None


def metadata_from_ld_json_item(cur_imv: dict) -> ZapDetailPageMetadata:
    """Structured-data card row (``itemListElement`` → ``item``)."""
    offers = cur_imv.get("offers") or {}
    pot = offers.get("potentialAction") or {}
    url_raw = offers.get("url") or pot.get("target")
    images = cur_imv.get("image")
    fotos: list[str] | None = None
    if isinstance(images, str) and images.strip():
        fotos = [images.strip()]
    elif isinstance(images, list):
        fotos = [str(x) for x in images if x]

    return ZapDetailPageMetadata(
        aluguel=offers.get("price")
        or (pot.get("priceSpecification") or {}).get("price", None),
        amenidades=[a["value"] for a in cur_imv.get("amenityFeature", [])],
        andares=None,
        area=(cur_imv.get("floorSize") or {}).get("value", None),
        atualizadoHa=None,
        bairro=None,
        banheiros=cur_imv.get("numberOfBathroomsTotal", None),
        cidade=(cur_imv.get("address") or {}).get("addressLocality", None),
        compra=price_from_buy_action(cur_imv),
        condominio=(offers.get("propertyValue") or {}).get("value", None),
        detailsUrl=url_remove_parameters(url_raw),
        enderecoNumero=None,
        enderecoRua=ZapDetailPageMetadata.replace_undefined_str(
            (cur_imv.get("address") or {}).get("streetAddress")
        ),
        estado=ZapDetailPageMetadata.replace_undefined_str(
            (cur_imv.get("address") or {}).get("addressRegion")
        ),
        externalId=None,
        fotos=fotos,
        geoSource=None,
        id=cur_imv.get("@id", None),
        iptu=None,
        isAbsoluteLocation=False,
        jsonDetailsData=None,
        jsonGeneralData=dict(cur_imv) if isinstance(cur_imv, dict) else None,
        jsonPointData=None,
        lat=None,
        locationId=None,
        lon=None,
        publicadoHa=None,
        quartos=cur_imv.get("numberOfBedrooms", None) or cur_imv.get("numberOfRooms", None),
        tipoImovel=None,
        vagas=None,
    )


def metadata_from_point_item(cur_imv: dict) -> ZapDetailPageMetadata:
    """Map/listing-point slice (coordinates + card fields)."""
    cur_imv_id = nested_get(cur_imv, "id", default=None)
    image_list = nested_get(cur_imv, "imageList", default=[]) or []
    fotos = image_urls_from_image_list(image_list if isinstance(image_list, list) else [])

    lat_raw: Any = nested_get(cur_imv, "address", "point", "lat", default=None)
    lon_raw: Any = nested_get(cur_imv, "address", "point", "lon", default=None)
    lat: float | None = None
    lon: float | None = None
    if isinstance(lat_raw, (int, float)) and isinstance(lon_raw, (int, float)):
        la, lo = float(lat_raw), float(lon_raw)
        if -90 <= la <= 90 and -180 <= lo <= 180:
            lat, lon = la, lo

    amenities_first = (nested_get(cur_imv, "amenities", "values", default=[None]) or [None])[0]

    geo_source = "listing_page" if lat is not None and lon is not None else None

    return ZapDetailPageMetadata(
        aluguel=nested_get(cur_imv, "prices", "rent", default=None),
        amenidades=amenities_first,
        andares=(nested_get(cur_imv, "amenities", "floors", default=[None]) or [None])[0],
        area=(nested_get(cur_imv, "amenities", "usableAreas", default=[None]) or [None])[0],
        atualizadoHa=None,
        bairro=nested_get(cur_imv, "address", "neighborhood", default=None),
        banheiros=(nested_get(cur_imv, "amenities", "bathrooms", default=[None]) or [None])[0],
        cidade=nested_get(cur_imv, "address", "city", default=None),
        compra=nested_get(cur_imv, "prices", "mainValue", default=None)
        if nested_get(cur_imv, "business", default="") == "SALE"
        else None,
        condominio=nested_get(cur_imv, "prices", "condominium", default=None),
        detailsUrl=url_remove_parameters(nested_get(cur_imv, "href", default=None)),
        enderecoNumero=nested_get(cur_imv, "address", "streetNumber", default=None),
        enderecoRua=nested_get(cur_imv, "address", "street", default=None),
        estado=nested_get(cur_imv, "address", "stateAcronym", default=None),
        externalId=nested_get(cur_imv, "externalId", default=None),
        fotos=fotos if fotos else None,
        geoSource=geo_source,
        id=cur_imv_id,
        iptu=nested_get(cur_imv, "prices", "iptu", default=None),
        isAbsoluteLocation=nested_get(cur_imv, "address", "approximateLocation", default=None),
        jsonDetailsData=None,
        jsonGeneralData=None,
        jsonPointData=dict(cur_imv) if isinstance(cur_imv, dict) else None,
        lat=lat,
        locationId=nested_get(cur_imv, "address", "locationId", default=None),
        lon=lon,
        publicadoHa=None,
        quartos=(nested_get(cur_imv, "amenities", "bedrooms", default=[None]) or [None])[0],
        tipoImovel=nested_get(cur_imv, "unitType", default=None),
        vagas=(nested_get(cur_imv, "amenities", "parkingSpaces", default=[None]) or [None])[0],
    )