import json
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Sequence

import psycopg
from psycopg.types.json import Json

def as_json_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value, ensure_ascii=False)


def clean_date(value: Any) -> str | None:
    if not value:
        return None

    if isinstance(value, str) and len(value) >= 10:
        return value[:10]

    return None


ProviderStr = Literal[
    "quintoandar", "vivareal", "netimoveis", "zapimoveis", "casamineira"
]
BATCH_SIZE = 500
IMOVEIS_UNIFICADOS_FQN = "b_dados.imoveis_unificados"

# Base table name per provider; snapshot tables append a file-derived suffix.
PROVIDER_TABLE_FQN: dict[ProviderStr, str] = {
    "quintoandar": "b_dados.quintoandar_imoveis",
    "netimoveis": "b_dados.netimoveis_imoveis",
    "vivareal": "b_dados.vivareal_imoveis",
    "zapimoveis": "b_dados.zap_imoveis",
    "casamineira": "b_dados.casamineira_imoveis",
}

_PROVIDER_SUFFIX_TOKENS: dict[ProviderStr, tuple[str, ...]] = {
    "quintoandar": ("_quintoandar",),
    "netimoveis": ("_netimoveis",),
    "vivareal": ("_vivareal",),
    "zapimoveis": ("_zapimoveis", "_zap"),
    "casamineira": ("_casamineira",),
}

MERGE_PROVIDER_ORDER: tuple[ProviderStr, ...] = (
    "quintoandar",
    "vivareal",
    "casamineira",
    "netimoveis",
    "zapimoveis",
)


def _sanitize_pg_identifier(value: str) -> str:
    value = value.replace("-", "_").lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        raise ValueError(f"Could not derive a Postgres-safe identifier from {value!r}")
    return value[:50]


def snapshot_suffix_from_path(path: Path, provider: ProviderStr) -> str:
    """Date/time portion of the export filename, e.g. 2026_05_04_00_31."""
    stem = path.stem.lower()
    for token in _PROVIDER_SUFFIX_TOKENS.get(provider, ()):
        if stem.endswith(token):
            stem = stem[: -len(token)]
            break
    return _sanitize_pg_identifier(stem.strip("_"))


def snapshot_table_fqn(provider: ProviderStr, json_path: str | Path) -> str:
    path = Path(json_path)
    suffix = snapshot_suffix_from_path(path, provider)
    base_table = PROVIDER_TABLE_FQN[provider].split(".", 1)[1]
    return f"b_dados.{base_table}_{suffix}"


def _index_prefix_from_table_fqn(table_fqn: str) -> str:
    return table_fqn.replace(".", "_")


def _ddl_zap_imoveis(table_fqn: str) -> list[str]:
    idx = _index_prefix_from_table_fqn(table_fqn)
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {table_fqn} (
            id BIGINT PRIMARY KEY,
            details_url TEXT NOT NULL,
            external_id TEXT,
            location_id TEXT,
            aluguel INTEGER,
            compra INTEGER,
            condominio INTEGER,
            iptu INTEGER,
            amenidades TEXT,
            fotos TEXT,
            andares INTEGER,
            area INTEGER,
            banheiros INTEGER,
            quartos INTEGER,
            vagas INTEGER,
            bairro TEXT,
            cidade TEXT,
            estado TEXT,
            endereco_rua TEXT,
            endereco_numero TEXT,
            tipo_imovel TEXT,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            geo_source TEXT,
            is_absolute_location BOOLEAN,
            publicado_ha DATE,
            atualizado_ha DATE,
            json_details_data TEXT,
            json_general_data TEXT,
            json_point_data TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"CREATE INDEX IF NOT EXISTS {idx}_details_url ON {table_fqn} (details_url);",
    ]


def _ddl_quintoandar_imoveis(table_fqn: str) -> list[str]:
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {table_fqn} (
            id BIGINT PRIMARY KEY,
            tipo TEXT,
            aluguel NUMERIC,
            iptu_condominio NUMERIC,
            area NUMERIC,
            venda NUMERIC,
            rua TEXT,
            bairro TEXT,
            cidade TEXT,
            estado TEXT,
            vagas INTEGER,
            quartos INTEGER,
            banheiros INTEGER,
            lat DOUBLE PRECISION,
            long DOUBLE PRECISION,
            thumb TEXT,
            titulo TEXT,
            url TEXT,
            full_json JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
    ]


def _ddl_netimoveis_imoveis(table_fqn: str) -> list[str]:
    idx = _index_prefix_from_table_fqn(table_fqn)
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {table_fqn} (
            id TEXT PRIMARY KEY,
            aluguel DOUBLE PRECISION,
            condominio DOUBLE PRECISION,
            area DOUBLE PRECISION,
            iptu DOUBLE PRECISION,
            atualizado TIMESTAMPTZ,
            venda DOUBLE PRECISION,
            tem_locacao INTEGER,
            tem_venda INTEGER,
            endereco TEXT,
            vagas INTEGER,
            quartos INTEGER,
            banheiros INTEGER,
            lat DOUBLE PRECISION,
            long DOUBLE PRECISION,
            url TEXT,
            full_json JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"CREATE INDEX IF NOT EXISTS {idx}_url ON {table_fqn} (url);",
    ]


def _ddl_vivareal_imoveis(table_fqn: str) -> list[str]:
    idx = _index_prefix_from_table_fqn(table_fqn)
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {table_fqn} (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            city TEXT,
            neighborhood TEXT,
            state_acronym TEXT,
            street TEXT,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            price_rental NUMERIC,
            price_sale NUMERIC,
            monthly_condo NUMERIC,
            yearly_iptu NUMERIC,
            url TEXT,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"CREATE INDEX IF NOT EXISTS {idx}_city ON {table_fqn} (city);",
        f"CREATE INDEX IF NOT EXISTS {idx}_neighborhood ON {table_fqn} (neighborhood);",
    ]


def _ddl_casamineira_imoveis(table_fqn: str) -> list[str]:
    return _ddl_vivareal_imoveis(table_fqn)


def create_provider_snapshot_table(
    dsn: str,
    provider: ProviderStr,
    table_fqn: str,
    *,
    drop_first: bool,
) -> None:
    PROVIDER_DDL_BUILDERS: dict[ProviderStr, Callable[[str], list[str]]] = {
        "zapimoveis": _ddl_zap_imoveis,
        "quintoandar": _ddl_quintoandar_imoveis,
        "netimoveis": _ddl_netimoveis_imoveis,
        "vivareal": _ddl_vivareal_imoveis,
        "casamineira": _ddl_casamineira_imoveis,
    }
    statements = PROVIDER_DDL_BUILDERS[provider](table_fqn)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            if drop_first:
                cur.execute(f"DROP TABLE IF EXISTS {table_fqn} CASCADE")
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
    print(f"Ensured snapshot table {table_fqn}.")


def _merge_quintoandar_branch(table_fqn: str) -> str:
    return f"""
    SELECT
        id::bigint,
        ST_SetSRID(ST_MakePoint(long, lat), 4326)::geometry(Point, 4326) geom_point,
        url as url,
        thumb,
        COALESCE(aluguel, 0) aluguel,
        COALESCE(venda, 0) venda,
        COALESCE(0, 0) iptu,
        COALESCE((full_json::jsonb->>'iptuPlusCondominium')::int, 0) condominio,
        COALESCE(banheiros, 0) banheiros,
        COALESCE(quartos, 0) quartos,
        COALESCE(vagas, 0) vagas,
        COALESCE(area, -1) area,
        COALESCE((full_json->>'type'), '') as tipo_imovel,
        bairro,
        CONCAT_WS(', ', estado, cidade, bairro, rua) endereco,
        lat,
        long,
        'quintoandar' fonte
    FROM {table_fqn}
    """


def _merge_vivareal_branch(table_fqn: str) -> str:
    return f"""
    SELECT
        id::bigint,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geometry(Point, 4326) geom_point,
        url,
        REPLACE(
            (jsonb_path_query_first(payload::jsonb, '$.medias[*] ? (@.type == "IMAGE")')->>'url'),
            '{{description}}.webp?action={{action}}&dimension={{width}}x{{height}}',
            'example.webp?action=fit-in&dimension=614x297'
        ) thumb,
        COALESCE(price_rental, 0) aluguel,
        COALESCE(price_sale, 0) venda,
        COALESCE(yearly_iptu/12, 0) iptu,
        COALESCE(monthly_condo, 0) condominio,
        COALESCE((payload->'listing'->'bathrooms'->>0)::int, 0) banheiros,
        COALESCE((payload->'listing'->'bedrooms'->>0)::int, 0) quartos,
        COALESCE((payload->'listing'->'parkingSpaces'->>0)::int, 0) vagas,
        COALESCE((payload->'listing'->'usableAreas'->>0)::int, -1) area,
        COALESCE(payload->'listing'->'unitTypes'->>0, '') tipo_imovel,
        COALESCE(neighborhood, '') bairro,
        CONCAT_WS(', ', state_acronym, city, neighborhood, street, payload->'link'->'data'->'streetNumber') endereco,
        lat,
        lon as long,
        'vivareal' fonte
    FROM {table_fqn}
    WHERE lat IS NOT NULL
    """


def _merge_casamineira_branch(table_fqn: str) -> str:
    return f"""
    SELECT
        id::bigint,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geometry(Point, 4326) geom_point,
        url,
        COALESCE(
            payload->>'thumb',
            REPLACE(
                (jsonb_path_query_first(payload::jsonb, '$.medias[*] ? (@.type == "IMAGE")')->>'url'),
                '{{description}}.webp?action={{action}}&dimension={{width}}x{{height}}',
                'example.webp?action=fit-in&dimension=614x297'
            ),
            ''
        ) thumb,
        COALESCE(price_rental, 0) aluguel,
        COALESCE(price_sale, 0) venda,
        COALESCE(yearly_iptu/12, 0) iptu,
        COALESCE(monthly_condo, 0) condominio,
        COALESCE(
            (payload->>'banheiros')::int,
            (payload->'listing'->'bathrooms'->>0)::int,
            0
        ) banheiros,
        COALESCE(
            (payload->>'quartos')::int,
            (payload->'listing'->'bedrooms'->>0)::int,
            0
        ) quartos,
        COALESCE(
            NULLIF((payload->>'vagas')::int, 0),
            (payload->'listing'->'parkingSpaces'->>0)::int,
            0
        ) vagas,
        COALESCE(
            NULLIF((payload->>'area')::int, 0),
            (payload->'listing'->'usableAreas'->>0)::int,
            -1
        ) area,
        COALESCE(
            payload->>'tipo_imovel',
            payload->'listing'->'unitTypes'->>0,
            title,
            ''
        ) tipo_imovel,
        COALESCE(neighborhood, payload->>'bairro', '') bairro,
        CONCAT_WS(
            ', ',
            state_acronym,
            city,
            neighborhood,
            street,
            payload->'link'->'data'->'streetNumber'
        ) endereco,
        lat,
        lon as long,
        'casamineira' fonte
    FROM {table_fqn}
    WHERE lat IS NOT NULL
    """


def _merge_netimoveis_branch(table_fqn: str) -> str:
    return f"""
    SELECT
        id::bigint,
        ST_SetSRID(ST_MakePoint(long, lat), 4326)::geometry(Point, 4326) geom_point,
        url,
        full_json->>'nomeArquivoThumb' thumb,
        COALESCE(aluguel, 0) aluguel,
        COALESCE(venda, 0) venda,
        COALESCE(iptu/12, 0) iptu,
        COALESCE(condominio, 0) condominio,
        COALESCE(banheiros, 0) banheiros,
        COALESCE(quartos, 0) quartos,
        COALESCE(vagas, 0) vagas,
        COALESCE(area, -1) area,
        CASE WHEN COALESCE((full_json->>'tipoImovel1_Id')::int, 0) = 3 THEN 'apartamento' ELSE 'casa' END tipo_imovel,
        COALESCE(full_json->>'nomeBairro', '') bairro,
        endereco,
        lat,
        long,
        'netimoveis' fonte
    FROM {table_fqn}
    """


def _merge_zapimoveis_branch(table_fqn: str) -> str:
    return f"""
    SELECT
        id::bigint,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geometry(Point, 4326) geom_point,
        details_url as url,
        (json_general_data::jsonb->'image'->>0) thumb,
        COALESCE(CASE WHEN aluguel = compra THEN 0 ELSE aluguel END, 0) aluguel,
        COALESCE(compra, 0) venda,
        COALESCE(iptu, 0) iptu,
        COALESCE(condominio, 0) condominio,
        COALESCE(banheiros, 0) banheiros,
        COALESCE(quartos, 0) quartos,
        COALESCE(vagas, 0) vagas,
        COALESCE(area, -1) area,
        COALESCE(tipo_imovel, '') bairro,
        COALESCE(bairro, '') tipo_imovel,
        CONCAT_WS(', ', estado, cidade, endereco_rua, endereco_numero) endereco,
        lat,
        lon as long,
        'zapimoveis' fonte
    FROM {table_fqn}
    """


_MERGE_BRANCH_BUILDERS: dict[ProviderStr, Callable[[str], str]] = {
    "quintoandar": _merge_quintoandar_branch,
    "vivareal": _merge_vivareal_branch,
    "casamineira": _merge_casamineira_branch,
    "netimoveis": _merge_netimoveis_branch,
    "zapimoveis": _merge_zapimoveis_branch,
}


def create_imoveis_unificados(dsn: str, tables: dict[ProviderStr, str]) -> None:
    branches: list[str] = []
    for provider in MERGE_PROVIDER_ORDER:
        table_fqn = tables.get(provider)
        if not table_fqn:
            continue
        branches.append(_MERGE_BRANCH_BUILDERS[provider](table_fqn))

    if not branches:
        print("No provider tables to merge; skipping imoveis_unificados.")
        return

    union_sql = "\nUNION ALL\n".join(f"({branch.strip()})" for branch in branches)
    post_statements = [
        f"ALTER TABLE {IMOVEIS_UNIFICADOS_FQN} ADD COLUMN aux_id BIGSERIAL PRIMARY KEY",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__id ON {IMOVEIS_UNIFICADOS_FQN} (id)",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__geom ON {IMOVEIS_UNIFICADOS_FQN} USING GIST (geom_point)",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__area ON {IMOVEIS_UNIFICADOS_FQN} (area)",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__vagas ON {IMOVEIS_UNIFICADOS_FQN} (vagas)",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__quartos ON {IMOVEIS_UNIFICADOS_FQN} (quartos)",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__banheiros ON {IMOVEIS_UNIFICADOS_FQN} (banheiros)",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__condominio ON {IMOVEIS_UNIFICADOS_FQN} (condominio)",
        f"CREATE INDEX idx_b_dados__imoveis_unificados__fonte ON {IMOVEIS_UNIFICADOS_FQN} (fonte)",
        f"""
        UPDATE {IMOVEIS_UNIFICADOS_FQN}
        SET tipo_imovel =
        CASE
            WHEN lower(tipo_imovel) IN (
              'triplex','casa','two_story_house','casacondominio','home', 'casas',
              'single_storey_house','village_house','farm',
              'allotment_land','residential_allotment_land'
            ) THEN 'Casa'
            WHEN lower(tipo_imovel) IN (
              'apartamento','apartment','condominium','flat','studio', 'apartamentos',
              'studiooukitchenette','kitnet','loft','duplex','penthouse'
            ) THEN 'Apartamento'
            ELSE 'Outro'
        END
        """,
    ]

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {IMOVEIS_UNIFICADOS_FQN}")
            cur.execute(f"CREATE TABLE {IMOVEIS_UNIFICADOS_FQN} AS ({union_sql})")
            for stmt in post_statements:
                cur.execute(stmt)
            cur.execute(f"SELECT COUNT(*) FROM {IMOVEIS_UNIFICADOS_FQN}")
            count = cur.fetchone()[0]
        conn.commit()

    print(f"Created {IMOVEIS_UNIFICADOS_FQN} with {count} rows.")


def infer_provider_from_path(path: Path) -> ProviderStr:
    """Infer scraper/provider from filename when --provider is omitted."""
    name = path.name.lower()
    if "quintoandar" in name:
        return "quintoandar"
    if "casamineira" in name:
        return "casamineira"
    if "vivareal" in name:
        return "vivareal"
    if "netimoveis" in name:
        return "netimoveis"
    if "zap" in name or "zapimoveis" in name:
        return "zapimoveis"
    return "zapimoveis"


def jsonb_from_fulljson_string(raw: Any) -> Json | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return Json(raw)
    if isinstance(raw, str):
        try:
            return Json(json.loads(raw))
        except json.JSONDecodeError:
            return Json({"_raw": raw})
    return Json({"_value": raw})


def parse_netimoveis_atualizado(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    # "2026-04-29T08:28:36.66"
    if "T" in s:
        body = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(body)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def _chunks(rows: Sequence[dict[str, Any]], size: int) -> Iterable[Sequence[dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def casamineira_extract_row(obj: dict[str, Any]) -> dict[str, Any]:
    flat_id = obj.get("id")
    if flat_id is not None and "listing" not in obj:
        lon = obj.get("long") if obj.get("long") is not None else obj.get("lon")
        return {
            "id": str(flat_id),
            "title": obj.get("tipo_imovel"),
            "description": None,
            "city": obj.get("cidade") or "Belo Horizonte",
            "neighborhood": obj.get("bairro"),
            "state_acronym": obj.get("estado") or "MG",
            "street": obj.get("endereco"),
            "lat": obj.get("lat"),
            "lon": lon,
            "price_rental": obj.get("aluguel"),
            "price_sale": obj.get("venda"),
            "monthly_condo": obj.get("condominio"),
            "yearly_iptu": obj.get("iptu"),
            "url": obj.get("url"),
            "payload": Json(obj),
        }

    listing = obj.get("listing") if isinstance(obj.get("listing"), dict) else {}
    link = obj.get("link") if isinstance(obj.get("link"), dict) else {}
    address = listing.get("address") if isinstance(listing.get("address"), dict) else {}
    rental: dict[str, Any] | None = None
    sale: dict[str, Any] | None = None
    for p in listing.get("pricingInfos") or []:
        if not isinstance(p, dict):
            continue
        bt = p.get("businessType")
        if bt == "RENTAL":
            rental = p
        elif bt == "SALE":
            sale = p
    pt = address.get("point") if isinstance(address.get("point"), dict) else {}
    lat = pt.get("approximateLat") if pt.get("approximateLat") is not None else pt.get("lat")
    lon = pt.get("approximateLon") if pt.get("approximateLon") is not None else pt.get("lon")
    href = link.get("href") or ""
    base = "https://www.casamineira.com.br"
    if isinstance(href, str) and href.startswith("/"):
        url = base + href
    else:
        url = href or None
    return {
        "id": str(listing.get("id") or ""),
        "title": listing.get("title"),
        "description": listing.get("description"),
        "city": address.get("city"),
        "neighborhood": address.get("neighborhood"),
        "state_acronym": address.get("stateAcronym"),
        "street": address.get("street"),
        "lat": lat,
        "lon": lon,
        "price_rental": rental.get("price") if rental else None,
        "price_sale": sale.get("price") if sale else None,
        "monthly_condo": (rental.get("monthlyCondoFee") if rental else None)
        or (sale.get("monthlyCondoFee") if sale else None),
        "yearly_iptu": (rental.get("yearlyIptu") if rental else None)
        or (sale.get("yearlyIptu") if sale else None),
        "url": url,
        "payload": Json(obj),
    }

def vivareal_extract_row(obj: dict[str, Any]) -> dict[str, Any]:
    listing = obj.get("listing") if isinstance(obj.get("listing"), dict) else {}
    link = obj.get("link") if isinstance(obj.get("link"), dict) else {}
    address = listing.get("address") if isinstance(listing.get("address"), dict) else {}
    rental: dict[str, Any] | None = None
    sale: dict[str, Any] | None = None
    for p in listing.get("pricingInfos") or []:
        if not isinstance(p, dict):
            continue
        bt = p.get("businessType")
        if bt == "RENTAL":
            rental = p
        elif bt == "SALE":
            sale = p
    pt = address.get("point") if isinstance(address.get("point"), dict) else {}
    lat = pt.get("approximateLat") if pt.get("approximateLat") is not None else pt.get("lat")
    lon = pt.get("approximateLon") if pt.get("approximateLon") is not None else pt.get("lon")
    href = link.get("href") or ""
    base = "https://www.vivareal.com.br"
    if isinstance(href, str) and href.startswith("/"):
        url = base + href
    else:
        url = href or None

    return {
        "id": str(listing.get("id") or ""),
        "title": listing.get("title"),
        "description": listing.get("description"),
        "city": address.get("city"),
        "neighborhood": address.get("neighborhood"),
        "state_acronym": address.get("stateAcronym"),
        "street": address.get("street"),
        "lat": lat,
        "lon": lon,
        "price_rental": rental.get("price") if rental else None,
        "price_sale": sale.get("price") if sale else None,
        "monthly_condo": (rental.get("monthlyCondoFee") if rental else None)
        or (sale.get("monthlyCondoFee") if sale else None),
        "yearly_iptu": (rental.get("yearlyIptu") if rental else None)
        or (sale.get("yearlyIptu") if sale else None),
        "url": url,
        "payload": Json(obj),
    }


def insert_quintoandar_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("QuintoAndar JSON root must be an object keyed by listing id.")

    sql = f"""
        INSERT INTO {table_fqn} (
            id, tipo, aluguel, iptu_condominio, area, venda, rua, bairro, cidade, estado,
            vagas, quartos, banheiros, lat, long, thumb, titulo, url, full_json, updated_at
        )
        VALUES (
            %(id)s, %(tipo)s, %(aluguel)s, %(iptu_condominio)s, %(area)s, %(venda)s,
            %(rua)s, %(bairro)s, %(cidade)s, %(estado)s,
            %(vagas)s, %(quartos)s, %(banheiros)s, %(lat)s, %(long)s,
            %(thumb)s, %(titulo)s, %(url)s, %(full_json)s, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            tipo = EXCLUDED.tipo,
            aluguel = EXCLUDED.aluguel,
            iptu_condominio = EXCLUDED.iptu_condominio,
            area = EXCLUDED.area,
            venda = EXCLUDED.venda,
            rua = EXCLUDED.rua,
            bairro = EXCLUDED.bairro,
            cidade = EXCLUDED.cidade,
            estado = EXCLUDED.estado,
            vagas = EXCLUDED.vagas,
            quartos = EXCLUDED.quartos,
            banheiros = EXCLUDED.banheiros,
            lat = EXCLUDED.lat,
            long = EXCLUDED.long,
            thumb = EXCLUDED.thumb,
            titulo = EXCLUDED.titulo,
            url = EXCLUDED.url,
            full_json = EXCLUDED.full_json,
            updated_at = NOW();
    """

    rows: list[dict[str, Any]] = []
    for _key, obj in data.items():
        if not isinstance(obj, dict):
            continue
        oid = obj.get("id")
        if oid is None:
            continue
        rows.append(
            {
                "id": int(oid),
                "tipo": obj.get("tipo"),
                "aluguel": obj.get("aluguel"),
                "iptu_condominio": obj.get("iptu_condominio"),
                "area": obj.get("area"),
                "venda": obj.get("venda"),
                "rua": obj.get("rua"),
                "bairro": obj.get("bairro"),
                "cidade": obj.get("cidade"),
                "estado": obj.get("estado"),
                "vagas": obj.get("vagas"),
                "quartos": obj.get("quartos"),
                "banheiros": obj.get("banheiros"),
                "lat": obj.get("lat"),
                "long": obj.get("long"),
                "thumb": obj.get("thumb"),
                "titulo": obj.get("titulo"),
                "url": obj.get("url"),
                "full_json": jsonb_from_fulljson_string(obj.get("fulljson")),
            }
        )

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()

    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_netimoveis_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("NetImoveis JSON root must be an array of listing objects.")

    sql = f"""
        INSERT INTO {table_fqn} (
            id, aluguel, condominio, area, iptu, atualizado, venda, tem_locacao, tem_venda,
            endereco, vagas, quartos, banheiros, lat, long, url, full_json, updated_at
        )
        VALUES (
            %(id)s, %(aluguel)s, %(condominio)s, %(area)s, %(iptu)s, %(atualizado)s,
            %(venda)s, %(tem_locacao)s, %(tem_venda)s, %(endereco)s,
            %(vagas)s, %(quartos)s, %(banheiros)s, %(lat)s, %(long)s, %(url)s,
            %(full_json)s, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            aluguel = EXCLUDED.aluguel,
            condominio = EXCLUDED.condominio,
            area = EXCLUDED.area,
            iptu = EXCLUDED.iptu,
            atualizado = EXCLUDED.atualizado,
            venda = EXCLUDED.venda,
            tem_locacao = EXCLUDED.tem_locacao,
            tem_venda = EXCLUDED.tem_venda,
            endereco = EXCLUDED.endereco,
            vagas = EXCLUDED.vagas,
            quartos = EXCLUDED.quartos,
            banheiros = EXCLUDED.banheiros,
            lat = EXCLUDED.lat,
            long = EXCLUDED.long,
            url = EXCLUDED.url,
            full_json = EXCLUDED.full_json,
            updated_at = NOW();
    """

    rows: list[dict[str, Any]] = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        rid = obj.get("id")
        if rid is None:
            continue
        rows.append(
            {
                "id": str(rid),
                "aluguel": obj.get("aluguel"),
                "condominio": obj.get("condominio"),
                "area": obj.get("area"),
                "iptu": obj.get("iptu"),
                "atualizado": parse_netimoveis_atualizado(obj.get("atualizado")),
                "venda": obj.get("venda"),
                "tem_locacao": obj.get("tem_locacao"),
                "tem_venda": obj.get("tem_venda"),
                "endereco": obj.get("endereco"),
                "vagas": obj.get("vagas"),
                "quartos": obj.get("quartos"),
                "banheiros": obj.get("banheiros"),
                "lat": obj.get("lat"),
                "long": obj.get("long"),
                "url": obj.get("url"),
                "full_json": jsonb_from_fulljson_string(obj.get("fulljson")),
            }
        )

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()

    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_casamineira_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("CasaMineira JSON root must be an array of listing payloads.")

    sql = f"""
        INSERT INTO {table_fqn} (
            id, title, description, city, neighborhood, state_acronym, street,
            lat, lon, price_rental, price_sale, monthly_condo, yearly_iptu, url, payload, updated_at
        )
        VALUES (
            %(id)s, %(title)s, %(description)s, %(city)s, %(neighborhood)s, %(state_acronym)s,
            %(street)s, %(lat)s, %(lon)s, %(price_rental)s, %(price_sale)s,
            %(monthly_condo)s, %(yearly_iptu)s, %(url)s, %(payload)s, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            city = EXCLUDED.city,
            neighborhood = EXCLUDED.neighborhood,
            state_acronym = EXCLUDED.state_acronym,
            street = EXCLUDED.street,
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            price_rental = EXCLUDED.price_rental,
            price_sale = EXCLUDED.price_sale,
            monthly_condo = EXCLUDED.monthly_condo,
            yearly_iptu = EXCLUDED.yearly_iptu,
            url = EXCLUDED.url,
            payload = EXCLUDED.payload,
            updated_at = NOW();
    """

    rows: list[dict[str, Any]] = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        row = casamineira_extract_row(obj)
        if not row["id"]:
            continue
        rows.append(row)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()

    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_vivareal_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("VivaReal JSON root must be an array of listing payloads.")

    sql = f"""
        INSERT INTO {table_fqn} (
            id, title, description, city, neighborhood, state_acronym, street,
            lat, lon, price_rental, price_sale, monthly_condo, yearly_iptu, url, payload, updated_at
        )
        VALUES (
            %(id)s, %(title)s, %(description)s, %(city)s, %(neighborhood)s, %(state_acronym)s,
            %(street)s, %(lat)s, %(lon)s, %(price_rental)s, %(price_sale)s,
            %(monthly_condo)s, %(yearly_iptu)s, %(url)s, %(payload)s, NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            city = EXCLUDED.city,
            neighborhood = EXCLUDED.neighborhood,
            state_acronym = EXCLUDED.state_acronym,
            street = EXCLUDED.street,
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            price_rental = EXCLUDED.price_rental,
            price_sale = EXCLUDED.price_sale,
            monthly_condo = EXCLUDED.monthly_condo,
            yearly_iptu = EXCLUDED.yearly_iptu,
            url = EXCLUDED.url,
            payload = EXCLUDED.payload,
            updated_at = NOW();
    """

    rows: list[dict[str, Any]] = []
    for obj in data:
        if not isinstance(obj, dict):
            continue
        row = vivareal_extract_row(obj)
        if not row["id"]:
            continue
        rows.append(row)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()

    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_imoveis_from_file(
    json_filepath: str,
    dsn: str,
    provider: ProviderStr | None = None,
    *,
    truncate_before: bool = False,
) -> str:
    path = Path(json_filepath)
    p: ProviderStr = provider or infer_provider_from_path(path)
    table_fqn = snapshot_table_fqn(p, path)
    create_provider_snapshot_table(
        dsn,
        p,
        table_fqn,
        drop_first=truncate_before,
    )

    if p == "zapimoveis":
        insert_zap_imoveis(json_filepath, dsn, table_fqn=table_fqn)
    elif p == "quintoandar":
        insert_quintoandar_imoveis(json_filepath, dsn, table_fqn=table_fqn)
    elif p == "netimoveis":
        insert_netimoveis_imoveis(json_filepath, dsn, table_fqn=table_fqn)
    elif p == "vivareal":
        insert_vivareal_imoveis(json_filepath, dsn, table_fqn=table_fqn)
    elif p == "casamineira":
        insert_casamineira_imoveis(json_filepath, dsn, table_fqn=table_fqn)
    else:
        raise ValueError(f"Unknown provider: {p}")

    return table_fqn


def insert_zap_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Expected JSON root to be an object/dict.")

    sql = f"""
        INSERT INTO {table_fqn} (
            id,
            details_url,
            external_id,
            location_id,
            aluguel,
            compra,
            condominio,
            iptu,
            amenidades,
            fotos,
            andares,
            area,
            banheiros,
            quartos,
            vagas,
            bairro,
            cidade,
            estado,
            endereco_rua,
            endereco_numero,
            tipo_imovel,
            lat,
            lon,
            geo_source,
            is_absolute_location,
            publicado_ha,
            atualizado_ha,
            json_details_data,
            json_general_data,
            json_point_data,
            updated_at
        )
        VALUES (
            %(id)s,
            %(details_url)s,
            %(external_id)s,
            %(location_id)s,
            %(aluguel)s,
            %(compra)s,
            %(condominio)s,
            %(iptu)s,
            %(amenidades)s,
            %(fotos)s,
            %(andares)s,
            %(area)s,
            %(banheiros)s,
            %(quartos)s,
            %(vagas)s,
            %(bairro)s,
            %(cidade)s,
            %(estado)s,
            %(endereco_rua)s,
            %(endereco_numero)s,
            %(tipo_imovel)s,
            %(lat)s,
            %(lon)s,
            %(geo_source)s,
            %(is_absolute_location)s,
            %(publicado_ha)s,
            %(atualizado_ha)s,
            %(json_details_data)s,
            %(json_general_data)s,
            %(json_point_data)s,
            NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            details_url = EXCLUDED.details_url,
            external_id = EXCLUDED.external_id,
            location_id = EXCLUDED.location_id,
            aluguel = EXCLUDED.aluguel,
            compra = EXCLUDED.compra,
            condominio = EXCLUDED.condominio,
            iptu = EXCLUDED.iptu,
            amenidades = EXCLUDED.amenidades,
            fotos = EXCLUDED.fotos,
            andares = EXCLUDED.andares,
            area = EXCLUDED.area,
            banheiros = EXCLUDED.banheiros,
            quartos = EXCLUDED.quartos,
            vagas = EXCLUDED.vagas,
            bairro = EXCLUDED.bairro,
            cidade = EXCLUDED.cidade,
            estado = EXCLUDED.estado,
            endereco_rua = EXCLUDED.endereco_rua,
            endereco_numero = EXCLUDED.endereco_numero,
            tipo_imovel = EXCLUDED.tipo_imovel,
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            geo_source = EXCLUDED.geo_source,
            is_absolute_location = EXCLUDED.is_absolute_location,
            publicado_ha = EXCLUDED.publicado_ha,
            atualizado_ha = EXCLUDED.atualizado_ha,
            json_details_data = EXCLUDED.json_details_data,
            json_general_data = EXCLUDED.json_general_data,
            json_point_data = EXCLUDED.json_point_data,
            updated_at = NOW();
    """

    tableRows = []
    jsonRows = []

    for url, item in data.items():
        if not isinstance(item, dict):
            continue

        real_id = item.get("id")

        if real_id is None:
            raise ValueError(f"Missing real id for URL: {url}")

        row = {
            "id": int(real_id),
            "details_url": item.get("detailsUrl") or url,
            "external_id": item.get("externalId"),
            "location_id": item.get("locationId"),

            "aluguel": item.get("aluguel"),
            "compra": item.get("compra"),
            "condominio": item.get("condominio"),
            "iptu": item.get("iptu"),

            "amenidades": as_json_text(item.get("amenidades")),
            "fotos": as_json_text(item.get("fotos")),

            "andares": item.get("andares"),
            "area": item.get("area"),
            "banheiros": item.get("banheiros"),
            "quartos": item.get("quartos"),
            "vagas": item.get("vagas"),

            "bairro": item.get("bairro"),
            "cidade": item.get("cidade"),
            "estado": item.get("estado"),
            "endereco_rua": item.get("enderecoRua"),
            "endereco_numero": item.get("enderecoNumero"),

            "tipo_imovel": item.get("tipoImovel"),

            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "geo_source": item.get("geoSource"),
            "is_absolute_location": item.get("isAbsoluteLocation"),

            "publicado_ha": clean_date(item.get("publicadoHa")),
            "atualizado_ha": clean_date(item.get("atualizadoHa")),

            "json_details_data": as_json_text(item.get("jsonDetailsData")),
            "json_general_data": as_json_text(item.get("jsonGeneralData")),
            "json_point_data": as_json_text(item.get("jsonPointData")),
        }

        jsonRows.append({
            "id": row["id"],
            "url": row["details_url"],
            "aluguel": row["aluguel"],
            "compra": row["compra"],
            "condominio": row["condominio"],
            "iptu": row["iptu"],
            "area": row["area"],
            "banheiros": row["banheiros"],
            "quartos": row["quartos"],
            "vagas": row["vagas"],
            "bairro": row["bairro"],
            "cidade": row["cidade"],
            "estado": row["estado"],
            "endereco_rua": row["endereco_rua"],
            "endereco_numero": row["endereco_numero"],
            "lat": row["lat"],
            "lon": row["lon"],
            "tipo_imovel": row["tipo_imovel"],
            "atualizado_ha": row["atualizado_ha"],
        })
        tableRows.append(row)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, tableRows)
        conn.commit()

    minified_output_path = path.with_name(f"{path.stem}_minified{path.suffix}")
    with minified_output_path.open("w", encoding="utf-8") as file:
        json.dump(jsonRows, file, ensure_ascii=False, indent=None)

    print(f"Inserted/updated {len(tableRows)} records into {table_fqn}.")


def _provider_jobs_from_args(args: argparse.Namespace) -> list[tuple[ProviderStr, str]]:
    """Ordered list of (provider, filepath) for every non-empty CLI path."""
    pairs: list[tuple[ProviderStr, str | None]] = [
        ("quintoandar", args.quintoandar),
        ("casamineira", args.casamineira),
        ("netimoveis", args.netimoveis),
        ("vivareal", args.vivareal),
        ("zapimoveis", args.zapimoveis),
    ]
    return [(p, fp) for p, fp in pairs if fp]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Load scraped JSON into Postgres (schema b_dados). "
            "Pass one or more --quintoandar/--casamineira/--netimoveis/--vivareal/--zapimoveis "
            "PATH to run multiple uploads in one invocation."
        )
    )
    #{quote_plus(password)}
    parser.add_argument("--dsn", required=True, help="PostgreSQL connection string (psycopg).")
    parser.add_argument(
        "--quintoandar",
        metavar="PATH",
        default=None,
        help="JSON export for QuintoAndar (dict keyed by id).",
    )
    parser.add_argument(
        "--casamineira",
        metavar="PATH",
        default=None,
        help="JSON export for CasaMineira (array of listing payloads).",
    )
    parser.add_argument(
        "--netimoveis",
        metavar="PATH",
        default=None,
        help="JSON export for NetImoveis (array of listings).",
    )
    parser.add_argument(
        "--vivareal",
        metavar="PATH",
        default=None,
        help="JSON export for VivaReal (array of listing payloads).",
    )
    parser.add_argument(
        "--zapimoveis",
        metavar="PATH",
        default=None,
        help="JSON export for Zap / ZapImoveis (URL-keyed dict).",
    )
    parser.add_argument(
        "--truncate-before",
        action="store_true",
        help=(
            "Before each provider upload, DROP the snapshot table for that file "
            "(e.g. b_dados.zap_imoveis_2026_05_06_14_18) and recreate it empty."
        ),
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Skip rebuilding b_dados.imoveis_unificados after uploads.",
    )

    args = parser.parse_args()
    jobs = _provider_jobs_from_args(args)
    if not jobs:
        parser.error(
            "Specify at least one input file: "
            "--quintoandar PATH, --casamineira PATH, --netimoveis PATH, --vivareal PATH, and/or --zapimoveis PATH"
        )

    uploaded: dict[ProviderStr, str] = {}
    for provider, json_filepath in jobs:
        print(f"Inserting/updating listings ({provider}) from {json_filepath}")
        table_fqn = insert_imoveis_from_file(
            json_filepath=json_filepath,
            dsn=args.dsn,
            provider=provider,
            truncate_before=args.truncate_before,
        )
        uploaded[provider] = table_fqn

    if uploaded and not args.no_merge:
        create_imoveis_unificados(args.dsn, uploaded)


# DDL templates and merge SQL live in create_provider_snapshot_table() and
# create_imoveis_unificados() above. export_zap_query_to_json.py reads IMOVEIS_UNIFICADOS_FQN.


"""

SELECT
payload,
id,
ST_SetSRID(ST_MakePoint(lat, lon), 4326)::geometry(Point, 4326) as geom_point,
url,
COALESCE(payload->>'thumb', '') thumb,
COALESCE(payload->>'aluguel', '0')::numeric::int as aluguel,
COALESCE(payload->>'venda', '0')::numeric::int as venda,
COALESCE(payload->>'iptu', '0')::numeric::int iptu,
--COALESCE(payload->>'condominio', 0) condominio,
--COALESCE(payload->>'banheiros', 0) banheiros,
--COALESCE(payload->>'quartos'::int, 0) quartos,
--vagas integer,
--area integer,
--tipo_imovel text COLLATE pg_catalog."default",
--bairro text COLLATE pg_catalog."default",
--endereco text COLLATE pg_catalog."default",
--lat double precision,
--"long" double precision,
--fonte text COLLATE pg_catalog."default",
--aux_id bigint NOT NULL DEFAULT nextval('b_dados.imoveis_unificados_aux_id_seq'::regclass),
TRUE as a
FROM b_dados.casamineira_imoveis_2026_05_14_00_19;

--SELECT * FROM b_dados.casamineira_imoveis_2026_05_14_00_19 limit 10

"""