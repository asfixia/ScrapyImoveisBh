"""ZAP listing URL construction and query-stripping."""

from __future__ import annotations

from urllib.parse import urlencode

from zap_parser.constants import BASE_QUERY, BH_ONDE, TRANSACAO_ALUGUEL, TRANSACAO_VENDA
from zap_parser.models import ZapMapViewport


def listing_base_path(transacao: str) -> str:
    t = (transacao or "").strip().lower()
    if t not in (TRANSACAO_ALUGUEL, TRANSACAO_VENDA):
        raise ValueError(
            f"Unsupported transacao {transacao!r}; use {TRANSACAO_ALUGUEL!r} or {TRANSACAO_VENDA!r}"
        )
    return f"https://www.zapimoveis.com.br/{t}/imoveis/mg+belo-horizonte/"


def page_url(
    page: int,
    viewport: ZapMapViewport | None = None,
    transacao: str = TRANSACAO_ALUGUEL,
) -> str:
    base = listing_base_path(transacao)
    params = dict(BASE_QUERY)
    params["transacao"] = transacao
    if page > 0:
        params["pagina"] = page
    if viewport is not None:
        params["viewport"] = viewport.as_query_string()
    else:
        params["onde"] = BH_ONDE
    if page == -1:
        return base
    return base + "?" + urlencode(params)


def url_remove_parameters(url: str | None) -> str | None:
    return url.split("?")[0] if url is not None else None


# Legacy camelCase export
urlRemoveParameters = url_remove_parameters

BASE_PATH = listing_base_path(TRANSACAO_ALUGUEL)
