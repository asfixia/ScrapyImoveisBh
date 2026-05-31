# -*- coding: utf-8 -*-
"""
NetImoveis spider – rental listings for BH, Betim, Contagem (MG).

- Listing: the site loads results via JS and the old /pesquisa API returns 404,
  so we use scrapy-playwright only to load the search page and extract detail URLs.
- Detail: each apartment page is fetched with a plain Scrapy Request (no browser)
  and we parse all data from the HTML.

If you discover the list API (e.g. from DevTools → Network while loading the search
page), you can replace the Playwright request with a simple GET/POST to that URL.
"""
import math
import re
import json
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
import scrapy
from scrapy.http import HtmlResponse
import re

from ImoveisScrapy.spiders.utils.scrape_output import output_json_path
# User-Agent for HTTP requests (no browser)
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "x-requested-with": "XMLHttpRequest"}
#EXPANDIFY_URL_TEMPLATE = "https://widget.expandify.com.br/v2/netimoveis.com/{}?cacheVersion=2.0.4&version=2"

#BASE_SEARCH = (
#    "https://www.netimoveis.com/locacao/minas-gerais/belo-horizonte/apartamento"
#    "?transacao=locacao"
#    "&localizacao=BR-MG-belo-horizonte---,BR-MG-betim---,BR-MG-contagem---"
#    "&tipo=apartamento,casa"
#    "&pagina={page}"
#)

BASE_API = (
    "https://www.netimoveis.com/pesquisa?transacao={transacao}&localizacao="
    '[{{"urlPais":"BR","urlEstado":"minas-gerais","urlCidade":"contagem","urlRegiao":"","urlBairro":"","urlLogradouro":"","idAgrupamento":"","tipo":"cidade","idLocalizacao":"BR-MG-contagem---"}},'
    '{{"urlPais":"BR","urlEstado":"minas-gerais","urlCidade":"betim","urlRegiao":"","urlBairro":"","urlLogradouro":"","idAgrupamento":"","tipo":"cidade","idLocalizacao":"BR-MG-betim---"}},'
    '{{"urlPais":"BR","urlEstado":"minas-gerais","urlCidade":"belo-horizonte","urlRegiao":"","urlBairro":"","urlLogradouro":"","idAgrupamento":"","tipo":"cidade","idLocalizacao":"BR-MG-belo-horizonte---"}}]'
    "&tipo=apartamento,casa,area-privativa,barracao,cobertura"
    "&pagina={page}"
    "&retornaPaginacao=true"
    "&outrasPags=true"
)

# API list: stop when lista is empty; retry when erro is truthy
API_LIST_MAX_RETRIES = 3
API_LIST_RETRY_DELAY_SECONDS = 10
PAGE_DELAY_SMALL = 3



class NetImoveisSpider(scrapy.Spider):
    name = "NetImoveis"
    MAX_PAGES = 200
    allowed_domains = ["www.netimoveis.com", "netimoveis.com", "widget.expandify.com.br"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen: set = set()
        self._accumulated_listings: list[dict] = []

    def start_requests(self):
        """Yield plain HTTP requests only (no Playwright/browser)."""
        yield self._request_list_page_api(1, transacao="venda")
        yield self._request_list_page_api(1, transacao="locacao")

    def _request_list_page_api(self, page: int, transacao: str = "locacao", retry_count: int = 0):
        """Return a plain Scrapy Request for the list page (no browser)."""
        url = BASE_API.format(page=page, transacao=transacao)
        return scrapy.Request(
            url,
            headers=DEFAULT_HEADERS,
            meta={"page_num": page, "retry_count": retry_count, "transacao": transacao},
            callback=self.parse_list_page_api,
            errback=self.errback_list_api,
            dont_filter=(retry_count > 0),
        )

    def errback_list_api(self, failure):
        """Retry list API request with delay on HTTP/connection error."""
        req = failure.request
        page_num = req.meta.get("page_num", 1)
        retry_count = req.meta.get("retry_count", 0)
        transacao = req.meta.get("transacao", "locacao")
        self.logger.warning("List API request failed page=%s: %s", page_num, failure.value)
        if retry_count < API_LIST_MAX_RETRIES:
            from twisted.internet import reactor
            retry_req = self._request_list_page_api(page_num, transacao=transacao, retry_count=retry_count + 1)
            retry_req.dont_filter = True
            reactor.callLater(
                API_LIST_RETRY_DELAY_SECONDS,
                lambda: self.crawler.engine.crawl(retry_req, self),
            )
        else:
            self.logger.error("List API page %s failed after %s retries", page_num, API_LIST_MAX_RETRIES)

    def parse_list_page_api(self, response):
        """
        api_json is the dict from response.json().
        - If erro is truthy: retry same page with delay (until max retries).
        - Yield items from 'lista'; request next page only when lista is non-empty.
        - Stop when lista is empty.
        """
        try:
            api_json = response.json()
        except Exception as e:
            self.logger.warning("Invalid JSON for list API: %s", e)
            return
        page_num = response.meta.get("page_num", 1)
        retry_count = response.meta.get("retry_count", 0)
        transacao = response.meta.get("transacao", "locacao")

        if api_json.get("erro"):
            if retry_count < API_LIST_MAX_RETRIES:
                from twisted.internet import reactor
                waiting_time = API_LIST_RETRY_DELAY_SECONDS * retry_count
                self.logger.warning(
                    "API returned erro=true for page %s, retrying in %ss (attempt %s)",
                    page_num, waiting_time, retry_count + 1,
                )
                time.sleep(waiting_time)
                retry_req = self._request_list_page_api(page_num, transacao=transacao, retry_count=retry_count + 1)
                retry_req.dont_filter = True
                reactor.callLater(
                    waiting_time,
                    lambda: self.crawler.engine.crawl(retry_req, self),
                )
            else:
                self.logger.error("API erro=true for page %s after %s retries", page_num, API_LIST_MAX_RETRIES)
            return

        newOnPage = False
        lista = api_json.get("lista") or []
        if not lista:
            self.logger.info("List API returned empty lista for page %s, stopping pagination", page_num)
            return
        for it in lista:
            imvId = it.get("imovelSan_Id")
            if imvId is None or imvId in self.seen:
                continue
            self.seen.add(imvId)
            newOnPage = True
            item = {
                "id": imvId,
                "aluguel": it.get("valorLocacao"),
                "condominio": it.get("valorCondominio"),
                "area": it.get("areaRealPrivativa"),
                "iptu": it.get("valorIptu"),
                "atualizado": it.get("dataHora"),
                "venda": it.get("valorImovel"),
                "tem_locacao": it.get("exibeLocacao"),
                "tem_venda": it.get("exibeVenda"),
                "endereco": ", ".join([it.get("siglaEstado", ""), it.get("nomeCidade", ""), it.get("nomeBairro", ""), it.get("tipoLogradouro", ""), it.get("logradouroPublico")]),
                "vagas": it.get("vagaGaragem", 0) or it.get("vagasGaragem", 0),
                "quartos": it.get("quartos", 0) + it.get("dce", 0),
                "banheiros": it.get("banho", 0) + it.get("suites", 0),
                "lat": it.get("latitude2"),
                "long": it.get("longitude2"),
                "url": self.get_url_from_hit(it),
                "fulljson": json.dumps(it),
            }
            self._accumulated_listings.append(item)
            yield item
        if newOnPage:
            self.logger.info("NetImoveis: page %s found %s going to new page", page_num, len(self.seen))
            time.sleep(PAGE_DELAY_SMALL)
            yield self._request_list_page_api(page_num + 1, transacao=transacao)
        else:
            self.logger.info("NetImoveis: page %s found %s stopping pagination", page_num, len(self.seen))

    def get_url_from_hit(self, hit):
        details_url = hit.get("urlDetalheImovel", None) or hit.get("url", None)
        return ("https://www.netimoveis.com/venda/" + details_url) if details_url else None

    def closed(self, reason):
        out_path = output_json_path("netimoveis")
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(
                self._accumulated_listings,
                fp,
                ensure_ascii=False,
                indent=2,
            )
        self.logger.info(
            "NetImoveis: wrote %s unique listing(s) to %s (reason=%s)",
            len(self._accumulated_listings),
            out_path,
            reason,
        )


def str_to_int(str):
    str_float = str_to_float(str)
    if str_float is None:
        return None
    return int(math.floor(str_float))

def str_to_float(str):
    if str is None:
        return None
    return float(str.replace('.', '').replace(',', '.'))

def get_numbers(contents, idx = None):
    if contents is None:
        return None
    parts = [p for p in re.sub(r'[^0-9\., ]', '', contents).strip().split(' ') if p.strip() if len(p) > 0]
    if idx is not None and len(parts) <= idx:
        return None
    elif idx is None:
        return parts
    else:
        return parts[idx]

def _parse_expandify_coords(data):
    """Extract (lat, lng) from Expandify widget JSON. Returns (None, None) if not found."""
    if not isinstance(data, dict):
        return (None, None)
    lat = data.get("lat") or data.get("latitude")
    lng = data.get("lng") or data.get("lon") or data.get("longitude")
    if lat is not None and lng is not None:
        try:
            return (float(lat), float(lng))
        except (TypeError, ValueError):
            pass
    geom = data.get("geom") or data.get("geometry") or data.get("geo")
    if isinstance(geom, dict):
        coords = geom.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            try:
                return (float(coords[1]), float(coords[0]))
            except (TypeError, ValueError):
                pass
    loc = data.get("location") or data.get("address")
    if isinstance(loc, dict):
        return _parse_expandify_coords(loc)
    return (None, None)

