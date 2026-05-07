"""Tests for :mod:`zap_parser` (main parser paths and helpers)."""

from __future__ import annotations

from datetime import date

import pytest

from zap_parser.constants import TRANSACAO_ALUGUEL
from zap_parser.json_extractors import (
    get_endereco_numero_from_json,
    get_fotos_from_json,
    get_id_from_json,
)
from zap_parser.merge import metadata_from_ld_json_item
from zap_parser.models import ZapDetailPageMetadata, ZapMapViewport
from zap_parser.normalizers import nested_get, value_is_absent
from zap_parser.parser import extract_lat_lon_from_detail_html, parse_detail_page_metadata
from zap_parser.urls import listing_base_path, page_url, url_remove_parameters


def test_value_is_absent() -> None:
    assert value_is_absent(None) is True
    assert value_is_absent("") is True
    assert value_is_absent("$undefined") is True
    assert value_is_absent("null") is True
    assert value_is_absent(0) is False
    assert value_is_absent(False) is False


def test_nested_get() -> None:
    d = {"a": {"b": {"$undefined": 1}}}
    assert nested_get(d, "a", "b", "c", default=7) == 7


def test_url_remove_parameters() -> None:
    assert url_remove_parameters("https://x.com/a?b=1") == "https://x.com/a"
    assert url_remove_parameters(None) is None


def test_page_url_contains_transacao() -> None:
    u = page_url(1, transacao=TRANSACAO_ALUGUEL)
    assert TRANSACAO_ALUGUEL in u
    assert "pagina=1" in u


def test_listing_base_path() -> None:
    assert "aluguel" in listing_base_path("aluguel")
    assert "venda" in listing_base_path("venda")


def test_zap_map_viewport_split() -> None:
    v = ZapMapViewport.from_string("0,10|0,0")
    subs = v.split_grid(2)
    assert len(subs) == 4


def test_merge_respects_none_vs_other() -> None:
    a = ZapDetailPageMetadata(
        aluguel=100,
        amenidades=None,
        andares=None,
        area=None,
        atualizadoHa=None,
        bairro=None,
        banheiros=None,
        cidade=None,
        compra=None,
        condominio=None,
        detailsUrl="u",
        enderecoNumero=None,
        enderecoRua="Rua A",
        estado=None,
        externalId=None,
        fotos=None,
        geoSource=None,
        id="1",
        iptu=None,
        isAbsoluteLocation=None,
        jsonDetailsData=None,
        jsonGeneralData=None,
        jsonPointData=None,
        lat=None,
        locationId=None,
        lon=None,
        publicadoHa=None,
        quartos=None,
        tipoImovel=None,
        vagas=None,
    )
    b = ZapDetailPageMetadata(
        aluguel=None,
        amenidades=["Piscina"],
        andares=None,
        area=50,
        atualizadoHa=None,
        bairro="Centro",
        banheiros=None,
        cidade=None,
        compra=None,
        condominio=None,
        detailsUrl="u",
        enderecoNumero="10",
        enderecoRua=None,
        estado=None,
        externalId=None,
        fotos=None,
        geoSource=None,
        id="1",
        iptu=None,
        isAbsoluteLocation=None,
        jsonDetailsData=None,
        jsonGeneralData=None,
        jsonPointData=None,
        lat=-19.9,
        locationId=None,
        lon=-43.9,
        publicadoHa=None,
        quartos=None,
        tipoImovel=None,
        vagas=None,
    )
    m = a.merge(b)
    assert m.aluguel == 100
    assert m.amenidades == ["Piscina"]
    assert m.area == 50
    assert m.enderecoRua == "Rua A"
    assert m.enderecoNumero == "10"
    assert m.lat == -19.9


def test_merge_with_none_returns_self() -> None:
    a = ZapDetailPageMetadata(
        aluguel=1,
        amenidades=None,
        andares=None,
        area=None,
        atualizadoHa=None,
        bairro=None,
        banheiros=None,
        cidade=None,
        compra=None,
        condominio=None,
        detailsUrl=None,
        enderecoNumero=None,
        enderecoRua=None,
        estado=None,
        externalId=None,
        fotos=None,
        geoSource=None,
        id=None,
        iptu=None,
        isAbsoluteLocation=None,
        jsonDetailsData=None,
        jsonGeneralData=None,
        jsonPointData=None,
        lat=None,
        locationId=None,
        lon=None,
        publicadoHa=None,
        quartos=None,
        tipoImovel=None,
        vagas=None,
    )
    assert a.merge(None) is a


def test_get_endereco_numero_from_json_undefined() -> None:
    data = {
        "baseData": {
            "pageData": {
                "listing": {"address": {"streetNumber": "$undefined"}},
            }
        }
    }
    assert get_endereco_numero_from_json(data) is None


def test_get_endereco_numero_from_json_none() -> None:
    data = {
        "baseData": {"pageData": {"listing": {"address": {"streetNumber": None}}}}
    }
    assert get_endereco_numero_from_json(data) is None


def test_get_id_from_json() -> None:
    assert (
        get_id_from_json({"baseData": {"pageData": {"listingId": "abc-123"}}})
        == "abc-123"
    )
    assert get_id_from_json({}) is None


def test_get_fotos_from_json() -> None:
    data = {
        "baseData": {
            "pageData": {
                "listing": {
                    "imageList": [
                        {"dangerousSrc": "https://img/a.jpg"},
                        {"dangerousSrc": None},
                    ]
                }
            }
        }
    }
    assert get_fotos_from_json(data) == ["https://img/a.jpg"]


def test_extract_lat_lon_rsc_approximate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZAP_SKIP_EMBED_GEOCODE", "1")
    html = '<script>x "approximateLat": -19.93, "approximateLon": -43.94 y</script>'
    la, lo, src = extract_lat_lon_from_detail_html(html)
    assert src == "rsc_approximateLatLon"
    assert la is not None and lo is not None
    assert abs(la + 19.93) < 0.01


def test_parse_detail_page_uses_next_data_listing(monkeypatch: pytest.MonkeyPatch) -> None:
    """``__NEXT_DATA__`` listing drives address and coords when flight JSON is absent."""
    monkeypatch.setenv("ZAP_SKIP_EMBED_GEOCODE", "1")
    html = """
    <html><head>
    <script type="application/ld+json">{"@type":"Product","offers":{"price":1200}}</script>
    <script id="__NEXT_DATA__" type="application/json">
    {"baseData":{"pageData":{"listingId":"L1","listing":{"address":{"street":"Rua X",
      "locationId":"loc-1","point":{"lat":-19.0,"lon":-43.0}},
      "prices":{"rent":1200,"condominium":300,"iptu":0},"amenities":{"values":["POOL"]}}}}}
    </script></head><body></body></html>
    """
    meta = parse_detail_page_metadata(html, None, "https://zap/imovel/x")
    assert meta.enderecoRua == "Rua X"
    assert meta.lat == -19.0 and meta.lon == -43.0
    assert meta.aluguel == 1200


def test_metadata_json_general_data_is_dict_not_str() -> None:
    item = {
        "@id": "id1",
        "offers": {"price": 500, "url": "https://zap/imovel/a?utm=1"},
        "amenityFeature": [],
        "address": {"streetAddress": "Rua Teste", "addressLocality": "BH"},
        "floorSize": {"value": 60},
        "numberOfBathroomsTotal": 1,
        "numberOfBedrooms": 2,
        "image": [],
    }
    m = metadata_from_ld_json_item(item)
    assert isinstance(m.jsonGeneralData, dict)
    assert m.jsonGeneralData["@id"] == "id1"


def test_to_dict_dates_iso() -> None:
    m = ZapDetailPageMetadata(
        aluguel=None,
        amenidades=None,
        andares=None,
        area=None,
        atualizadoHa=date(2026, 1, 2),
        bairro=None,
        banheiros=None,
        cidade=None,
        compra=None,
        condominio=None,
        detailsUrl=None,
        enderecoNumero=None,
        enderecoRua=None,
        estado=None,
        externalId=None,
        fotos=None,
        geoSource=None,
        id=None,
        iptu=None,
        isAbsoluteLocation=None,
        jsonDetailsData=None,
        jsonGeneralData=None,
        jsonPointData=None,
        lat=None,
        locationId=None,
        lon=None,
        publicadoHa=None,
        quartos=None,
        tipoImovel=None,
        vagas=None,
    )
    d = m.to_dict()
    assert d["atualizadoHa"] == "2026-01-02"
