import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

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


ProviderStr = Literal["quintoandar", "vivareal", "netimoveis", "zapimoveis"]
BATCH_SIZE = 500

# Target table for each provider (TRUNCATE / uploads).
PROVIDER_TABLE_FQN: dict[ProviderStr, str] = {
    "quintoandar": "b_dados.quintoandar_imoveis",
    "netimoveis": "b_dados.netimoveis_imoveis",
    "vivareal": "b_dados.vivareal_imoveis",
    "zapimoveis": "b_dados.zap_imoveis",
}


def truncate_provider_table(dsn: str, provider: ProviderStr) -> None:
    """Remove all rows from the table for this provider. Uses CASCADE for dependent objects."""
    table = PROVIDER_TABLE_FQN[provider]
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
        conn.commit()
    print(f"Truncated {table}.")


def infer_provider_from_path(path: Path) -> ProviderStr:
    """Infer scraper/provider from filename when --provider is omitted."""
    name = path.name.lower()
    if "quintoandar" in name:
        return "quintoandar"
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


def insert_quintoandar_imoveis(json_filepath: str, dsn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("QuintoAndar JSON root must be an object keyed by listing id.")

    sql = """
        INSERT INTO b_dados.quintoandar_imoveis (
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

    print(f"Inserted/updated {len(rows)} records into b_dados.quintoandar_imoveis.")


def insert_netimoveis_imoveis(json_filepath: str, dsn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("NetImoveis JSON root must be an array of listing objects.")

    sql = """
        INSERT INTO b_dados.netimoveis_imoveis (
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

    print(f"Inserted/updated {len(rows)} records into b_dados.netimoveis_imoveis.")


def insert_vivareal_imoveis(json_filepath: str, dsn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("VivaReal JSON root must be an array of listing payloads.")

    sql = """
        INSERT INTO b_dados.vivareal_imoveis (
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

    print(f"Inserted/updated {len(rows)} records into b_dados.vivareal_imoveis.")


def insert_imoveis_from_file(
    json_filepath: str,
    dsn: str,
    provider: ProviderStr | None = None,
    *,
    truncate_before: bool = False,
) -> None:
    path = Path(json_filepath)
    p = provider or infer_provider_from_path(path)
    if truncate_before:
        truncate_provider_table(dsn, p)
    if p == "zapimoveis":
        insert_zap_imoveis(json_filepath, dsn)
    elif p == "quintoandar":
        insert_quintoandar_imoveis(json_filepath, dsn)
    elif p == "netimoveis":
        insert_netimoveis_imoveis(json_filepath, dsn)
    elif p == "vivareal":
        insert_vivareal_imoveis(json_filepath, dsn)
    else:
        raise ValueError(f"Unknown provider: {p}")


def insert_zap_imoveis(json_filepath: str, dsn: str) -> None:
    path = Path(json_filepath)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Expected JSON root to be an object/dict.")

    sql = """
        INSERT INTO b_dados.zap_imoveis (
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

    print(f"Inserted/updated {len(tableRows)} records into zap_imoveis.")


def _provider_jobs_from_args(args: argparse.Namespace) -> list[tuple[ProviderStr, str]]:
    """Ordered list of (provider, filepath) for every non-empty CLI path."""
    pairs: list[tuple[ProviderStr, str | None]] = [
        ("quintoandar", args.quintoandar),
        ("netimoveis", args.netimoveis),
        ("vivareal", args.vivareal),
        ("zapimoveis", args.zapimoveis),
    ]
    return [(p, fp) for p, fp in pairs if fp]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Load scraped JSON into Postgres (schema b_dados). "
            "Pass one or more --quintoandar/--netimoveis/--vivareal/--zapimoveis PATH "
            "to run multiple uploads in one invocation."
        )
    )
    parser.add_argument("--dsn", required=True, help="PostgreSQL connection string (psycopg).")
    parser.add_argument(
        "--quintoandar",
        metavar="PATH",
        default=None,
        help="JSON export for QuintoAndar (dict keyed by id).",
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
            "Before each provider upload, TRUNCATE only that provider's "
            "b_dados table (quintoandar_imoveis, netimoveis_imoveis, vivareal_imoveis, zap_imoveis). "
            "Uses RESTART IDENTITY CASCADE."
        ),
    )

    args = parser.parse_args()
    jobs = _provider_jobs_from_args(args)
    if not jobs:
        parser.error(
            "Specify at least one input file: "
            "--quintoandar PATH, --netimoveis PATH, --vivareal PATH, and/or --zapimoveis PATH"
        )

    for provider, json_filepath in jobs:
        print(f"Inserting/updating listings ({provider}) from {json_filepath}")
        insert_imoveis_from_file(
            json_filepath=json_filepath,
            dsn=args.dsn,
            provider=provider,
            truncate_before=args.truncate_before,
        )


#ignore this block of code, but keep it here for reference
"""
DROP TABLE IF EXISTS b_dados.zap_imoveis;

CREATE TABLE IF NOT EXISTS b_dados.zap_imoveis (
    id BIGINT  PRIMARY KEY,

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
);

CREATE INDEX IF NOT EXISTS idx_zap_imoveis_details_url
ON b_dados.zap_imoveis (details_url);

CREATE INDEX IF NOT EXISTS idx_zap_imoveis_details_url
ON b_dados.zap_imoveis (details_url);

TRUNCATE TABLE b_dados.zap_imoveis RESTART IDENTITY CASCADE;


CREATE TABLE b_dados.zap_imoveis_geoms as
SELECT
id,
ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geometry(Point, 4326) geom_point,
details_url as url,
COALESCE(aluguel, 0) aluguel,
COALESCE(compra, 0) compra,
COALESCE(condominio, 0) condominio,
COALESCE(banheiros, 0) banheiros,
COALESCE(quartos, 0) quartos,
COALESCE(vagas, 0) vagas,
COALESCE(area, -1) area,
COALESCE(tipo_imovel, '') tipo_imovel,
CONCAT_WS(', ', estado, cidade, endereco_rua, endereco_numero) endereco
FROM b_dados.zap_imoveis
;

ALTER TABLE b_dados.zap_imoveis_geoms
ALTER COLUMN id SET NOT NULL;

ALTER TABLE b_dados.zap_imoveis_geoms
ADD CONSTRAINT zap_imoveis_geoms_id_pkey PRIMARY KEY (id);

CREATE INDEX idx_zap_imoveis_geoms_geom_point
ON b_dados.zap_imoveis_geoms
USING GIST (geom_point);

SELECT Find_SRID('b_dados', 'zap_imoveis_geoms', 'geom_point');

"""


# --- DDL: QuintoAndar, NetImoveis, VivaReal (run in Postgres before importing) ---
"""
--quinto andar
CREATE TABLE IF NOT EXISTS b_dados.quintoandar_imoveis (
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
);
TRUNCATE TABLE b_dados.quintoandar_imoveis RESTART IDENTITY CASCADE;

--netimoveis
CREATE TABLE IF NOT EXISTS b_dados.netimoveis_imoveis (
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
);

CREATE INDEX IF NOT EXISTS idx_netimoveis_imoveis_url ON b_dados.netimoveis_imoveis (url);
TRUNCATE TABLE b_dados.netimoveis_imoveis RESTART IDENTITY CASCADE;

--vivareal
CREATE TABLE IF NOT EXISTS b_dados.vivareal_imoveis (
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
);

CREATE INDEX IF NOT EXISTS idx_vivareal_imoveis_city ON b_dados.vivareal_imoveis (city);
CREATE INDEX IF NOT EXISTS idx_vivareal_imoveis_neighborhood ON b_dados.vivareal_imoveis (neighborhood);
TRUNCATE TABLE b_dados.vivareal_imoveis RESTART IDENTITY CASCADE;
"""


""" Table as JSON
SELECT jsonb_agg(to_jsonb(q))::text AS result
FROM (
	SELECT
	'' as "360",
	COALESCE(banheiros, 0) banheiros,
	COALESCE(quartos, 0) quartos,
	COALESCE(iptu, 0) iptu,
	'' as "full",
	0 video,
	COALESCE(compra, 0) venda,
	id,
	COALESCE((json_general_data::jsonb -> 'image') ->> 0, '') thumb,
	area,
	COALESCE(lon, 0) as long,
	json_general_data::jsonb ->> 'description' as descricao,
	CASE WHEN ((json_point_data::jsonb -> 'prices') ->> 'period') = 'MONTHLY' THEN 12 else 1 END as iptu_parcelas,
	'2020-09-14-11:27:48' as "gDate",
	COALESCE(bairro, '') bairro,
	COALESCE(aluguel, 0) aluguel,
	COALESCE(condominio, 0) condominio,
	COALESCE(lat, 0) lat,
	'' as "data",
	CONCAT_WS(', ', estado, cidade, endereco_rua, endereco_numero) logradouro,
	details_url url
	FROM b_dados.zap_imoveis
) as q;
"""

""" Merge all tables
DROP TABLE IF EXISTS b_dados.imoveis_unificados;

CREATE TABLE b_dados.imoveis_unificados as
(
	SELECT
	id::bigint,
	ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geometry(Point, 4326) geom_point,
	details_url as url,
	--description TEXT,
	(json_general_data::jsonb->'image'->>0) thumb,
	COALESCE(aluguel, 0) aluguel,
	COALESCE(compra, 0) compra,
	COALESCE(iptu, 0) iptu,
	COALESCE(condominio, 0) condominio,
	COALESCE(banheiros, 0) banheiros,
	COALESCE(quartos, 0) quartos,
	COALESCE(vagas, 0) vagas,
	COALESCE(area, -1) area,
	COALESCE(tipo_imovel, '') tipo_imovel,
	CONCAT_WS(', ', estado, cidade, endereco_rua, endereco_numero) endereco,
	lat,
	lon,
	'zap' fonte
	FROM b_dados.zap_imoveis
) UNION (
   SELECT
	id::bigint,
	ST_SetSRID(ST_MakePoint(long, lat), 4326)::geometry(Point, 4326) geom_point,
	url as url,
	thumb,
	COALESCE(aluguel, 0) aluguel,
	COALESCE(venda, 0) compra,
	COALESCE(0, 0) iptu,
	COALESCE((full_json::jsonb->>'iptuPlusCondominium')::int, 0) condominio,
	COALESCE(banheiros, 0) banheiros,
	COALESCE(quartos, 0) quartos,
	COALESCE(vagas, 0) vagas,
	COALESCE(area, -1) area,
	COALESCE((full_json->>'type'), '') as tipo_imovel,
	CONCAT_WS(', ', estado, cidade, bairro, rua) endereco,
	lat,
	long lon,
	'5andar' fonte
   FROM b_dados.quintoandar_imoveis
) UNION (
   SELECT
	id::bigint,
	ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geometry(Point, 4326) geom_point,
	url,
	REPLACE((payload::jsonb->'medias'->0->>'url'), '{description}.webp?action={action}&dimension={width}x{height}', 'example.webp?action=fit-in&dimension=614x297') thumb,
	COALESCE(price_rental, 0) aluguel,
	COALESCE(price_sale, 0) compra,
	COALESCE(yearly_iptu/12, 0) iptu,
	COALESCE(monthly_condo, 0) condominio,
	COALESCE((payload->'listing'->'bathrooms'->>0)::int, 0) banheiros,
	COALESCE((payload->'listing'->'bedrooms'->>0)::int, 0) quartos,
	COALESCE((payload->'listing'->'parkingSpaces'->>0)::int, 0) vagas,
	COALESCE((payload->'listing'->'usableAreas'->>0)::int, -1) area,
	COALESCE(payload->'listing'->'unitTypes'->>0, '') tipo_imovel,
	CONCAT_WS(', ', state_acronym, city, neighborhood, street, payload->'link'->'data'->'streetNumber') endereco,
	lat,
	lon,
	'vvreal' fonte
  FROM b_dados.vivareal_imoveis limit 10
) UNION (
 SELECT
	id::bigint,
	ST_SetSRID(ST_MakePoint(long, lat), 4326)::geometry(Point, 4326) geom_point,
	url,
	full_json->>'nomeArquivoThumb' thumb,
	COALESCE(aluguel, 0) aluguel,
	COALESCE(venda, 0) compra,
	COALESCE(iptu/12, 0) iptu,
	COALESCE(condominio, 0) condominio,
	COALESCE(banheiros, 0) banheiros,
	COALESCE(quartos, 0) quartos,
	COALESCE(vagas, 0) vagas,
	COALESCE(area, -1) area,
	CASE WHEN COALESCE((full_json->>'tipoImovel1_Id')::int, 0) = 3 THEN 'apartamento' ELSE 'casa' END tipo_imovel,
	endereco,
	lat,
	long lon,
	'netimov' fonte
   FROM b_dados.netimoveis_imoveis
);


ALTER TABLE b_dados.imoveis_unificados ADD COLUMN aux_id BIGSERIAL PRIMARY KEY;
CREATE INDEX idx_b_dados__imoveis_unificados__id ON b_dados.imoveis_unificados (id);
CREATE INDEX idx_b_dados__imoveis_unificados__geom ON b_dados.imoveis_unificados USING GIST (geom_point);
CREATE INDEX idx_b_dados__imoveis_unificados__area ON b_dados.imoveis_unificados (area);
CREATE INDEX idx_b_dados__imoveis_unificados__vagas ON b_dados.imoveis_unificados (vagas);
CREATE INDEX idx_b_dados__imoveis_unificados__quartos ON b_dados.imoveis_unificados (quartos);
CREATE INDEX idx_b_dados__imoveis_unificados__banheiros ON b_dados.imoveis_unificados (banheiros);
CREATE INDEX idx_b_dados__imoveis_unificados__condominio ON b_dados.imoveis_unificados (condominio);
CREATE INDEX idx_b_dados__imoveis_unificados__fonte ON b_dados.imoveis_unificados (fonte);
--CREATE INDEX idx_b_dados__imoveis_unificados__filtros ON b_dados.imoveis_unificados (quartos, vagas, area, banheiros);

"""
