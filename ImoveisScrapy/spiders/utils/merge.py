"""Build :class:`~zap_parser.models.ZapDetailPageMetadata` from list JSON-LD vs map point payloads."""

from __future__ import annotations

from typing import Any

from ImoveisScrapy.spiders.utils.data_helpers import getFirstValue, normalize_tipo
from ImoveisScrapy.spiders.utils.json_extractors import image_urls_from_image_list
from ImoveisScrapy.spiders.utils.models import ZapDetailPageMetadata
from ImoveisScrapy.spiders.utils.normalizers import nested_get
from ImoveisScrapy.spiders.utils.urls import url_remove_parameters


def _pricing_info(pricing_infos: list | None, business_type: str) -> dict:
    for entry in pricing_infos or []:
        if isinstance(entry, dict) and entry.get("businessType") == business_type:
            return entry
    return {}


def _monthly_iptu(pricing: dict) -> int:
    yearly = pricing.get("yearlyIptu") or 0
    try:
        return int(yearly / 12) if yearly else 0
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


def _format_zap_endereco(
    rua: str | None,
    numero: str | None,
    bairro: str | None,
    cidade: str | None,
    estado: str | None,
) -> str:
    acc = ""
    for value in (rua, numero, bairro, cidade, estado):
        if value:
            acc = f"{acc}, {value}" if acc else str(value)
    return acc


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

    raw_id = cur_imv.get("@id", None)
    try:
        listing_id = int(str(raw_id)) if raw_id is not None else 0
    except (TypeError, ValueError):
        listing_id = 0
    aluguel = offers.get("price") or (pot.get("priceSpecification") or {}).get("price", 0) or 0
    venda = price_from_buy_action(cur_imv) or 0
    area = (cur_imv.get("floorSize") or {}).get("value", 0) or 0
    banheiros = cur_imv.get("numberOfBathroomsTotal", 0) or 0
    quartos = cur_imv.get("numberOfBedrooms", None) or cur_imv.get("numberOfRooms", 0) or 0
    thumb = fotos[0] if fotos else ""
    amenity_raw = cur_imv.get("amenityFeature", [])
    amenity_vals = [a["value"] for a in amenity_raw if isinstance(a, dict) and a.get("value")]
    return ZapDetailPageMetadata(
        id=listing_id,
        url=url_remove_parameters(url_raw) or "",
        thumb=thumb,
        aluguel=int(aluguel),
        amenidades=amenity_vals or None,
        andares=None,
        area=int(area),
        atualizadoHa=None,
        bairro="",
        banheiros=int(banheiros),
        cidade=(cur_imv.get("address") or {}).get("addressLocality", None),
        endereco=_format_zap_endereco(
            ZapDetailPageMetadata.replace_undefined_str(
                (cur_imv.get("address") or {}).get("streetAddress")
            ),
            None,
            "",
            (cur_imv.get("address") or {}).get("addressLocality", None),
            ZapDetailPageMetadata.replace_undefined_str(
                (cur_imv.get("address") or {}).get("addressRegion")
            ),
        ),
        venda=int(venda),
        condominio=int((offers.get("propertyValue") or {}).get("value", 0) or 0),
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
        iptu=0,
        isAbsoluteLocation=False,
        jsonDetailsData=None,
        jsonGeneralData=dict(cur_imv) if isinstance(cur_imv, dict) else None,
        jsonPointData=None,
        lat=0.0,
        locationId=None,
        long=0.0,
        publicadoHa=None,
        quartos=int(quartos),
        tipo_imovel="",
        vagas=0,
        payload=dict(cur_imv) if isinstance(cur_imv, dict) else {},
    )


def metadata_from_point_item(cur_imv: dict) -> ZapDetailPageMetadata:
    """Map/listing-point slice (coordinates + card fields)."""
    cur_imv_id = nested_get(cur_imv, "id", default=0)
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

    amenities_raw = nested_get(cur_imv, "amenities", "values", default=None)
    amenities_list: list[str] | None = None
    if isinstance(amenities_raw, list):
        tmp = [str(x) for x in amenities_raw if x is not None]
        amenities_list = tmp or None
    elif amenities_raw is not None:
        amenities_list = [str(amenities_raw)]

    geo_source = "listing_page" if lat is not None and lon is not None else None
    endereco_rua = nested_get(cur_imv, "address", "street", default=None)
    endereco_numero = nested_get(cur_imv, "address", "streetNumber", default=None)
    bairro = nested_get(cur_imv, "address", "neighborhood", default="") or ""
    cidade = nested_get(cur_imv, "address", "city", default=None)
    estado = nested_get(cur_imv, "address", "stateAcronym", default=None)

    return ZapDetailPageMetadata(
        id=int(cur_imv_id or 0),
        url=url_remove_parameters(nested_get(cur_imv, "href", default=None)) or "",
        thumb=(fotos[0] if fotos else ""),
        aluguel=int(nested_get(cur_imv, "prices", "rent", default=0) or 0),
        amenidades=amenities_list,
        andares=(nested_get(cur_imv, "amenities", "floors", default=[None]) or [None])[0] or 0,
        area=int((nested_get(cur_imv, "amenities", "usableAreas", default=[None]) or [None])[0] or 0),
        atualizadoHa=None,
        bairro=bairro,
        banheiros=int((nested_get(cur_imv, "amenities", "bathrooms", default=[None]) or [None])[0] or 0),
        cidade=cidade,
        endereco=_format_zap_endereco(endereco_rua, endereco_numero, bairro, cidade, estado),
        venda=int(nested_get(cur_imv, "prices", "mainValue", default=0) or 0)
        if nested_get(cur_imv, "business", default="") == "SALE"
        else 0,
        condominio=int(nested_get(cur_imv, "prices", "condominium", default=0) or 0),
        enderecoNumero=endereco_numero,
        enderecoRua=endereco_rua,
        estado=estado,
        externalId=nested_get(cur_imv, "externalId", default=None),
        fotos=fotos if fotos else None,
        geoSource=geo_source,
        iptu=int(nested_get(cur_imv, "prices", "iptu", default=0) or 0),
        isAbsoluteLocation=nested_get(cur_imv, "address", "approximateLocation", default=None),
        jsonDetailsData=None,
        jsonGeneralData=None,
        jsonPointData=dict(cur_imv) if isinstance(cur_imv, dict) else None,
        lat=lat if lat is not None else 0.0,
        locationId=nested_get(cur_imv, "address", "locationId", default=None),
        long=lon if lon is not None else 0.0,
        publicadoHa=None,
        quartos=int((nested_get(cur_imv, "amenities", "bedrooms", default=[None]) or [None])[0] or 0),
        tipo_imovel=nested_get(cur_imv, "unitType", default="") or "",
        vagas=int((nested_get(cur_imv, "amenities", "parkingSpaces", default=[None]) or [None])[0] or 0),
        payload=dict(cur_imv) if isinstance(cur_imv, dict) else {},
    )


def metadata_from_glue_listing(cur_imv: dict) -> ZapDetailPageMetadata:
    """Glue API list row (``search.result.listings[]``)."""
    listing = cur_imv.get("listing") or {}
    addr = listing.get("address") or {}
    point = addr.get("point") or {}
    link = cur_imv.get("link") or {}
    href = link.get("href") or ""
    url = f"https://www.zapimoveis.com.br{href}" if href else ""

    pricing_infos = listing.get("pricingInfos") or []
    rental = _pricing_info(pricing_infos, "RENTAL")
    sale = _pricing_info(pricing_infos, "SALE")
    price_ref = rental or sale

    medias = cur_imv.get("medias") or []
    fotos = [m.get("url") for m in medias if m.get("type") == "IMAGE" and m.get("url")]
    thumb = (fotos[0] if fotos else "").replace("action={action}&dimension={width}x{height}", "action=fit-in&dimension=614x297")

    endereco_rua = ZapDetailPageMetadata.replace_undefined_str(addr.get("street"))
    endereco_numero = ZapDetailPageMetadata.replace_undefined_str(addr.get("streetNumber"))
    bairro = addr.get("neighborhood") or ""
    cidade = addr.get("city")
    estado = addr.get("stateAcronym")

    lat_raw = point.get("lat") if point.get("lat") is not None else point.get("approximateLat")
    lon_raw = point.get("lon") if point.get("lon") is not None else point.get("approximateLon")
    lat = float(lat_raw) if lat_raw is not None else 0.0
    lon = float(lon_raw) if lon_raw is not None else 0.0

    amenities = listing.get("amenities")
    if not amenities:
        amenities = None

    geo_source = point.get("source")
    geo_source = str(geo_source) if geo_source else None

    return ZapDetailPageMetadata(
        id=int(listing.get("id") or 0),
        url=url,
        thumb=thumb,
        aluguel=int(rental.get("price") or 0),
        venda=int(sale.get("price") or 0),
        iptu=_monthly_iptu(price_ref),
        condominio=int(price_ref.get("monthlyCondoFee") or 0),
        banheiros=int(getFirstValue(listing.get("bathrooms"), 0) or 0),
        quartos=int(getFirstValue(listing.get("bedrooms"), 0) or 0),
        vagas=int(getFirstValue(listing.get("parkingSpaces"), 0) or 0),
        area=int(getFirstValue(listing.get("usableAreas"), 0) or 0),
        bairro=bairro,
        tipo_imovel=normalize_tipo(getFirstValue(listing.get("unitTypes"))) or "",
        endereco=_format_zap_endereco(endereco_rua, endereco_numero, bairro, cidade, estado),
        lat=lat,
        long=lon,
        payload=cur_imv,
        amenidades=amenities,
        andares=int(getFirstValue(listing.get("floors"), 0) or 0),
        atualizadoHa=listing.get("updatedAt"),
        cidade=cidade,
        enderecoNumero=endereco_numero,
        enderecoRua=endereco_rua,
        estado=estado,
        externalId=listing.get("externalId"),
        fotos=fotos or None,
        geoSource=geo_source,
        isAbsoluteLocation=not bool(addr.get("approximateLocation")) if lat or lon else None,
        jsonDetailsData=dict(cur_imv) if isinstance(cur_imv, dict) else None,
        jsonGeneralData=None,
        jsonPointData=None,
        locationId=addr.get("locationId"),
        publicadoHa=listing.get("createdAt"),
    )