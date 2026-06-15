# -*- coding: utf-8 -*-
"""
Casa Mineira — listings via /rplis-api/postings (JSON).

HTTP is done with **Botasaurus** ``Request`` (same stack as ``zap_botasaurus_client``):
one session for GET bootstrap + POST /rplis-api/postings so cookies stay aligned.

Flow:
  1) GET session bootstrap URL (cookies: JSESSIONID, sessionId, Cloudflare, etc.)
  2) POST same-origin /rplis-api/postings with JSON body on the same Request session

Edit constants and POSTINGS_JSON_BODY below. Placeholders use str.format, e.g. {page},
{moneda}, {preciomin} (same pattern as BASE_API.format(page=…) on NetImoveis).
Escape literal JSON braces as {{ and }}. Only fields present in the string are passed
to .format (so you can drop {page} for a single-page crawl).
"""
from __future__ import annotations

import json
import logging
import string
import time
from datetime import datetime
from urllib.parse import urljoin

from ImoveisScrapy.spiders.utils import CasaMineiraItem
from ImoveisScrapy.spiders.utils.data_helpers import normalize_tipo, parse_int
import scrapy
from botasaurus.request import Request, request

from ImoveisScrapy.spiders.utils.scrape_output import output_json_path

LOG = logging.getLogger(__name__)

# Retries for Botasaurus HTTP (same spirit as zap_botasaurus_client.request_get_with_retry)
BOTASAURUS_MAX_ATTEMPTS = 4
BOTASAURUS_BACKOFF_S = 20.0
BOTASAURUS_REQUEST_MAX_RETRY = 3

# --- Site / API ---
BASE_ORIGIN = "https://www.casamineira.com.br"
POSTINGS_URL = f"{BASE_ORIGIN}/rplis-api/postings"

# --- Negócio (API: tipoDeOperacion) — ids do payload ---
TIPO_OPERACAO_COMPRA = "1"
TIPO_OPERACAO_ALUGUEL = "2"
TIPO_OPERACAO_ATIVO = TIPO_OPERACAO_COMPRA

# --- Tipos de imóvel (API: tipoDePropiedad) — ids separados por vírgula ---
# O path do Referer (/casa+apartamento/, /apartamento/, …) deriva deste mesmo valor.
TIPO_PROPIEDAD_SOLO_APARTAMENTO = "2"
TIPO_PROPIEDAD_SOLO_CASA = "1"
TIPO_PROPIEDAD_CASA_E_APARTAMENTO = "1,2"

# Cidade no JSON (city) + slug no path do Referer — use CITY_SLUG_BY_ID para manter par id/slug
CITY_ID_BELO_HORIZONTE = "1102754"
CITY_SLUG_BY_ID = {
    "1102754": "belo-horizonte_mg",
}
CITY_SLUG = CITY_SLUG_BY_ID.get(str(CITY_ID_BELO_HORIZONTE), "belo-horizonte_mg")
MONEDA_BRL = "3"

PRECO_MIN = 0
PRECO_MAX = 9_000_000_000

HABITACIONES_MIN = 0
HABITACIONES_MAX = 0

# Referer do POST: URL pública de listagem; ver ``_build_referer_for_listing_post``.

# --- Corpo POST: JSON com .format(page=…, moneda=…, …) — chaves entre {{ }} vão literais ---
POSTINGS_JSON_BODY = (
    '{{"q":null,"direccion":null,"moneda":"{moneda}","preciomin":{preciomin},'
    '"preciomax":{preciomax},"services":"","general":"","searchbykeyword":"","amenidades":"",'
    '"caracteristicasprop":null,"comodidades":"","disposicion":null,"roomType":"","outside":"",'
    '"areaPrivativa":"","areaComun":"","multipleRets":"","tipoDePropiedad":"{tipo_propiedad}",'
    '"subtipoDePropiedad":null,"tipoDeOperacion":"{tipo_operacion}","garages":null,"antiguedad":null,'
    '"expensasminimo":null,"expensasmaximo":null,"withoutguarantor":null,'
    '"habitacionesminimo":{habitaciones_min},"habitacionesmaximo":{habitaciones_max},'
    '"ambientesminimo":0,"ambientesmaximo":0,"banos":null,"superficieCubierta":1,"idunidaddemedida":1,'
    '"metroscuadradomin":null,"metroscuadradomax":null,"tipoAnunciante":"ALL",'
    '"grupoTipoDeMultimedia":"","publicacion":null,"sort":"more_recent","etapaDeDesarrollo":"",'
    '"auctions":null,"polygonApplied":null,"idInmobiliaria":null,"excludePostingContacted":"",'
    '"banks":"","places":"","condominio":"","preTipoDeOperacion":"{pre_tipo}","city":"{city}",'
    '"province":null,"zone":null,"valueZone":null,"subZone":null,"coordenates":null,"pagina":{page}}}'
)

DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "Origin": BASE_ORIGIN,
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
}


def _bota_http_with_retry(
    request_obj: Request,
    label: str,
    call,
    *,
    max_attempts: int = BOTASAURUS_MAX_ATTEMPTS,
    backoff_seconds: float = BOTASAURUS_BACKOFF_S,
):
    """
    Run ``call()`` (no args) returning a Botasaurus/requests-like response.
    Retries on transport errors and retryable HTTP status codes (same policy as
    ``zap_botasaurus_client.request_get_with_retry``).
    """
    last_exc: BaseException | None = None
    answer = None
    for attempt in range(1, max_attempts + 1):
        try:
            answer = call()
            code = getattr(answer, "status_code", None)
            if code is not None and (
                (500 <= code <= 599)
                or code in (408, 409, 423, 425, 429, 403, 404, 410, 401)
            ):
                LOG.warning("CasaMineira [%s] HTTP %s attempt %s/%s", label, code, attempt, max_attempts,)
                raise RuntimeError(f"HTTP {code} on attempt {attempt} for {label}")
            return answer
        except (RuntimeError, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            time.sleep(backoff_seconds * attempt)
    code = getattr(answer, "status_code", None) if answer is not None else None
    LOG.error("CasaMineira [%s] failed after %s attempts (last HTTP=%s, exc=%s)", label, max_attempts, code, last_exc,)
    return answer


def _negocio_url_segment(tipo_operacion: str) -> str:
    """Segmento de URL: venda | aluguel (alinhado a TIPO_OPERACAO_ATIVO)."""
    if str(tipo_operacion) == str(TIPO_OPERACAO_ALUGUEL):
        return "aluguel"
    return "venda"


def _tipo_propiedad_url_path(tipo_propiedad: str) -> str:
    """
    Converte tipoDePropiedad (ids '1','2',…) no trecho do path do site.
    Ex.: '1,2' -> 'casa+apartamento'; '2' -> 'apartamento'; '1' -> 'casa'.
    """
    ids = [p.strip() for p in str(tipo_propiedad).split(",") if p.strip()]
    parts: list[str] = []
    for i in ids:
        if i == "1" and "casa" not in parts:
            parts.append("casa")
        elif i == "2" and "apartamento" not in parts:
            parts.append("apartamento")
    return "+".join(parts) if parts else "casa+apartamento"


# Primeira requisição: alinha negócio + tipos com o mesmo filtro do POST
SESSION_START_URL = (
    f"{BASE_ORIGIN}/"
    f"{_negocio_url_segment(TIPO_OPERACAO_ATIVO)}/imovel/mg"
)


def _build_referer_for_listing_post(post_page: int) -> str:
    """
    Referer para cada POST de listagem: ``/{tipo}/{cidade}/ordem-mais-recente``;
    páginas 1 e 2 iguais; a partir da 3 acrescenta ``/pagina-{post_page - 1}``.
    """
    base = BASE_ORIGIN.rstrip("/")
    tipo_path = _tipo_propiedad_url_path(TIPO_PROPIEDAD_CASA_E_APARTAMENTO)
    url = f"{base}/{tipo_path}/{CITY_SLUG}/ordem-mais-recente"
    p = int(post_page)
    if p >= 3:
        url = f"{url}/pagina-{p - 1}"
    return url


def _postings_format_field_names() -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(POSTINGS_JSON_BODY) if name}


def _build_post_body(page: int) -> str:
    kw = {
        "moneda": str(MONEDA_BRL),
        "preciomin": int(PRECO_MIN),
        "preciomax": int(PRECO_MAX),
        "tipo_propiedad": str(TIPO_PROPIEDAD_CASA_E_APARTAMENTO),
        "tipo_operacion": str(TIPO_OPERACAO_ATIVO),
        "pre_tipo": str(TIPO_OPERACAO_ATIVO),
        "city": str(CITY_ID_BELO_HORIZONTE),
        "habitaciones_min": int(HABITACIONES_MIN),
        "habitaciones_max": int(HABITACIONES_MAX),
        "page": int(page),
    }
    names = _postings_format_field_names()
    body = POSTINGS_JSON_BODY.format(**{k: v for k, v in kw.items() if k in names})
    json.loads(body)
    return body


def _paginates_by_page_field() -> bool:
    return "page" in _postings_format_field_names()


def _main_feature(posting: dict, feature_id: str, default=None):
    mf = posting.get("mainFeatures") or {}
    if not isinstance(mf, dict):
        return default
    node = mf.get(feature_id) or {}
    if not isinstance(node, dict):
        return default
    return node.get("value", default)


def _first_thumb_url(posting: dict) -> str | None:
    vp = posting.get("visiblePictures") or {}
    if not isinstance(vp, dict):
        return None
    pics = vp.get("pictures") or []
    if not pics or not isinstance(pics, list):
        return None
    first = pics[0] if isinstance(pics[0], dict) else {}
    for key in ("url730x532", "url360x266", "url130x70"):
        u = first.get(key)
        if u:
            return u
    return None


def _amount_by_operation(posting: dict, operation_type_id: str) -> float | None:
    for block in posting.get("priceOperationTypes") or []:
        if not isinstance(block, dict):
            continue
        ot = block.get("operationType") or {}
        if str((ot or {}).get("operationTypeId", "")) != str(operation_type_id):
            continue
        for p in block.get("prices") or []:
            if not isinstance(p, dict):
                continue
            if str(p.get("currencyId", "3")) != "3":
                continue
            amt = p.get("amount")
            if amt is None:
                continue
            try:
                return float(amt)
            except (TypeError, ValueError):
                pass
    return None


def _iptu_amount(posting: dict):
    iptu = posting.get("iptu")
    if iptu is None:
        #fullDescription = posting.get("descriptionNormalized", None)
        return None
    if isinstance(iptu, dict):
        return iptu.get("amount")
    return iptu


def _condominio_amount(posting: dict):
    ex = posting.get("expenses") or {}
    if isinstance(ex, dict):
        return ex.get("amount")
    return None


def posting_to_item(posting: dict) -> dict:
    pid = posting.get("postingId")
    rel_url = posting.get("url") or ""
    full_url = urljoin(BASE_ORIGIN + "/", rel_url.lstrip("/"))

    loc = posting.get("postingLocation") or {}
    addr = (loc.get("address") or {}) if isinstance(loc, dict) else {}
    locnode = (loc.get("location") or {}) if isinstance(loc, dict) else {}
    geo_wrap = (loc.get("postingGeolocation") or {}) if isinstance(loc, dict) else {}
    geo = (geo_wrap.get("geolocation") or {}) if isinstance(geo_wrap, dict) else {}

    ret = (posting.get("realEstateType") or {}) if isinstance(posting.get("realEstateType"), dict) else {}
    area = _main_feature(posting, "CFT101") or _main_feature(posting, "CFT100")

    return CasaMineiraItem(
        id=parse_int(str(pid) if pid is not None else "0"),
        url=full_url,
        thumb=_first_thumb_url(posting) or "",
        aluguel=parse_int(_amount_by_operation(posting, TIPO_OPERACAO_ALUGUEL)),
        venda=parse_int(_amount_by_operation(posting, TIPO_OPERACAO_COMPRA)),
        iptu=parse_int(_iptu_amount(posting)),
        condominio=parse_int(_condominio_amount(posting)),
        banheiros=parse_int(_main_feature(posting, "CFT3")),
        quartos=parse_int(_main_feature(posting, "CFT2")),
        vagas=parse_int(_main_feature(posting, "CFT7")),
        area=parse_int(area),
        bairro=locnode.get("name", ""),
        tipo_imovel=normalize_tipo(ret.get("name")),
        endereco=addr.get("name", ""),
        lat=float(geo.get("latitude") or 0.0),
        long=float(geo.get("longitude") or 0.0),
        payload=posting,
    ).to_dict()


@request(max_retry=BOTASAURUS_REQUEST_MAX_RETRY)
def casamineira_listings_via_botasaurus(request_obj: Request, data):
    """
    Fetch all listing pages with one Botasaurus session (cookies shared with POSTs).
    Called from ``CasaMineiraSpider.start_requests`` (same pattern as ``VivaRealSpider``).
    """
    h_get = {k: v for k, v in DEFAULT_HEADERS.items() if k != "Content-Type"}
    warm = _bota_http_with_retry(
        request_obj,
        "session_bootstrap",
        lambda: request_obj.get(SESSION_START_URL, headers=h_get, timeout=60),
    )
    if warm is not None and getattr(warm, "status_code", None) != 200:
        LOG.warning("Session URL HTTP %s — continuing anyway", getattr(warm, "status_code", None), )

    seen: set[str] = set()
    accumulated: list[dict] = []
    page = 1
    total_pages: int | None = None

    while (total_pages is None) or (page <= total_pages):
        try:
            body = _build_post_body(page)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            LOG.error("Invalid POSTINGS_JSON_BODY / format fields: %s", e)
            break

        headers = dict(DEFAULT_HEADERS)
        headers["Referer"] = _build_referer_for_listing_post(page)
        response = _bota_http_with_retry(
            request_obj,
            f"postings_p{page}",
            lambda: request_obj.post(
                POSTINGS_URL,
                data=body.encode("utf-8"),
                headers=headers,
                timeout=60,
            ),
        )
        if response is None or getattr(response, "status_code", None) != 200:
            LOG.error("POST postings page %s: HTTP %s", page, getattr(response, "status_code", None),)
            break

        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError as e:
            LOG.error("Page %s: invalid JSON: %s", page, e)
            break

        if total_pages is None:
            total_pages = payload.get("paging", {}).get("totalPages", 1)

        listings = payload.get("listPostings")
        if listings is None:
            LOG.warning("Page %s: no listPostings key; top-level keys: %s", page, list(payload.keys())[:30] if isinstance(payload, dict) else type(payload))
            listings = []

        if not isinstance(listings, list):
            LOG.error("Page %s: listPostings is not a list", page)
            break

        new_this_page = 0
        for posting in listings:
            if not isinstance(posting, dict):
                continue
            item = posting_to_item(posting)
            pid = item.get("id")
            if pid and pid in seen:
                continue
            if pid:
                seen.add(str(pid))
            accumulated.append(item)
            new_this_page += 1

        LOG.info("Page %s/%s: new items this page=%s, total distinct items so far=%s " "(listPostings rows=%s)", page, total_pages, new_this_page, len(accumulated), len(listings),)

        if not listings:
            LOG.info("Empty listPostings on page %s — stopping pagination", page,)
            break
        if new_this_page == 0:
            LOG.info("No new items on page %s (all duplicates or skipped) — stopping pagination", page,)
            break
        if not _paginates_by_page_field():
            LOG.info("No {{page}} placeholder in POSTINGS_JSON_BODY — single-page crawl only")
            break
        if page >= total_pages:
            LOG.info("Reached last page (page %s / totalPages=%s) — stopping pagination", page, total_pages,)
            break
        page += 1

    return accumulated


class CasaMineiraSpider(scrapy.Spider):
    name = "CasaMineira"
    allowed_domains = ["www.casamineira.com.br", "casamineira.com.br"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._accumulated_listings: list[dict] = []

    def start_requests(self):
        try:
            items = casamineira_listings_via_botasaurus({})
        except Exception:
            self.logger.exception("CasaMineira Botasaurus crawl failed")
            return
        if not items:
            items = []
        self._accumulated_listings = list(items)
        for it in items:
            yield it

    async def start(self):
        for item in self.start_requests():
            yield item

    def closed(self, reason):
        out_path = output_json_path("casamineira")
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(
                {str(item["id"]): item for item in self._accumulated_listings},
                fp,
                ensure_ascii=False,
                indent=2,
            )
        self.logger.info(
            "CasaMineira: wrote %s listing(s) to %s (reason=%s)",
            len(self._accumulated_listings),
            out_path,
            reason,
        )
