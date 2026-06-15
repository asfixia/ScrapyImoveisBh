import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Sequence

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ImoveisScrapy.spiders.utils.scrape_latest import ScrapeLatestFiles

# CLI flags may be omitted when these environment variables are set (CLI wins if both).
ENV_DSN = "IMOVEIS_UPLOAD_DSN"
ENV_QUINTOANDAR = "IMOVEIS_UPLOAD_QUINTOANDAR"
ENV_CASAMINEIRA = "IMOVEIS_UPLOAD_CASAMINEIRA"
ENV_NETIMOVEIS = "IMOVEIS_UPLOAD_NETIMOVEIS"
ENV_VIVAREAL = "IMOVEIS_UPLOAD_VIVAREAL"
ENV_ZAPIMOVEIS = "IMOVEIS_UPLOAD_ZAPIMOVEIS"
ENV_TRUNCATE_BEFORE = "IMOVEIS_UPLOAD_TRUNCATE_BEFORE"
ENV_NO_MERGE = "IMOVEIS_UPLOAD_NO_MERGE"

_TRUTHY_ENV = frozenset({"1", "true", "yes", "on"})


def _env_str(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY_ENV

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


# ---------------------------------------------------
# DDL — standardized ImoveisScrapyItem base + extras
# ---------------------------------------------------

def _ddl_base_columns() -> str:
    """Standard ImoveisScrapyItem columns shared by all provider tables."""
    return """
        id          BIGINT PRIMARY KEY,
        url         TEXT,
        thumb       TEXT,
        aluguel     INTEGER,
        venda       INTEGER,
        iptu        INTEGER,
        condominio  INTEGER,
        banheiros   INTEGER,
        quartos     INTEGER,
        vagas       INTEGER,
        area        INTEGER,
        bairro      TEXT,
        tipo_imovel TEXT,
        endereco    TEXT,
        lat         DOUBLE PRECISION,
        lon         DOUBLE PRECISION,
        payload     JSONB,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    """


def _ddl_standard_provider(table_fqn: str, extra_cols: str = "") -> list[str]:
    idx = _index_prefix_from_table_fqn(table_fqn)
    cols = _ddl_base_columns()
    if extra_cols:
        cols = cols.rstrip() + ",\n        " + extra_cols
    return [
        f"CREATE TABLE IF NOT EXISTS {table_fqn} ({cols})",
        f"CREATE INDEX IF NOT EXISTS {idx}_url ON {table_fqn} (url);",
    ]


def _ddl_quintoandar_imoveis(table_fqn: str) -> list[str]:
    return _ddl_standard_provider(table_fqn, "titulo TEXT, cidade TEXT, estado TEXT")


def _ddl_netimoveis_imoveis(table_fqn: str) -> list[str]:
    return _ddl_standard_provider(
        table_fqn,
        "atualizado TIMESTAMPTZ, tem_locacao INTEGER, tem_venda INTEGER",
    )


def _ddl_vivareal_imoveis(table_fqn: str) -> list[str]:
    return _ddl_standard_provider(
        table_fqn,
        "titulo TEXT, descricao TEXT, atualizado TIMESTAMPTZ, tem_locacao INTEGER, tem_venda INTEGER",
    )


def _ddl_casamineira_imoveis(table_fqn: str) -> list[str]:
    return _ddl_standard_provider(table_fqn)


def _ddl_zap_imoveis(table_fqn: str) -> list[str]:
    idx = _index_prefix_from_table_fqn(table_fqn)
    extra = """
        external_id          TEXT,
        location_id          TEXT,
        amenidades           TEXT,
        fotos                TEXT,
        andares              INTEGER,
        cidade               TEXT,
        estado               TEXT,
        endereco_rua         TEXT,
        endereco_numero      TEXT,
        geo_source           TEXT,
        is_absolute_location BOOLEAN,
        publicado_ha         DATE,
        atualizado_ha        DATE,
        json_details_data    TEXT,
        json_general_data    TEXT,
        json_point_data      TEXT
    """
    stmts = _ddl_standard_provider(table_fqn, extra)
    stmts.append(f"CREATE INDEX IF NOT EXISTS {idx}_external_id ON {table_fqn} (external_id);")
    return stmts


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


# ---------------------------------------------------
# Merge SQL — one generic branch per provider
# ---------------------------------------------------

def _merge_standard_branch(table_fqn: str, fonte: str) -> str:
    return f"""
    SELECT
        id::bigint,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geometry(Point, 4326) geom_point,
        url,
        COALESCE(thumb, '') thumb,
        COALESCE(aluguel, 0) aluguel,
        COALESCE(venda, 0) venda,
        COALESCE(iptu, 0) iptu,
        COALESCE(condominio, 0) condominio,
        COALESCE(banheiros, 0) banheiros,
        COALESCE(quartos, 0) quartos,
        COALESCE(vagas, 0) vagas,
        COALESCE(area, -1) area,
        COALESCE(tipo_imovel, '') tipo_imovel,
        COALESCE(bairro, '') bairro,
        COALESCE(endereco, '') endereco,
        lat,
        lon as long,
        '{fonte}' fonte
    FROM {table_fqn}
    WHERE lat IS NOT NULL AND lat != 0
    """


_MERGE_BRANCH_BUILDERS: dict[ProviderStr, Callable[[str], str]] = {
    provider: (lambda p: lambda t: _merge_standard_branch(t, p))(provider)
    for provider in ("quintoandar", "vivareal", "casamineira", "netimoveis", "zapimoveis")
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


# ---------------------------------------------------
# Row extraction helpers
# ---------------------------------------------------

def _base_row(obj: dict[str, Any]) -> dict[str, Any]:
    """Extract the ImoveisScrapyItem standard fields from a to_dict() result."""
    payload = obj.get("payload")
    return {
        "id": int(obj.get("id") or 0),
        "url": obj.get("url"),
        "thumb": obj.get("thumb"),
        "aluguel": obj.get("aluguel"),
        "venda": obj.get("venda"),
        "iptu": obj.get("iptu"),
        "condominio": obj.get("condominio"),
        "banheiros": obj.get("banheiros"),
        "quartos": obj.get("quartos"),
        "vagas": obj.get("vagas"),
        "area": obj.get("area"),
        "bairro": obj.get("bairro"),
        "tipo_imovel": obj.get("tipo_imovel"),
        "endereco": obj.get("endereco"),
        "lat": obj.get("lat"),
        "lon": obj.get("long") or obj.get("lon"),
        "payload": Json(payload) if isinstance(payload, dict) else Json({}),
    }


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


def infer_provider_from_path(path: Path) -> ProviderStr:
    name = path.name.lower()
    if "quintoandar" in name:
        return "quintoandar"
    if "casamineira" in name:
        return "casamineira"
    if "vivareal" in name:
        return "vivareal"
    if "netimoveis" in name:
        return "netimoveis"
    return "zapimoveis"


# ---------------------------------------------------
# Insert functions — all read list[dict] from to_dict()
# ---------------------------------------------------

def _build_upsert_sql(table_fqn: str, cols: tuple[str, ...]) -> str:
    col_list = ", ".join(cols)
    val_list = ", ".join(f"%({c})s" for c in cols)
    update_set = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in cols if c not in ("id", "created_at")
    )
    return f"""
        INSERT INTO {table_fqn} ({col_list}, updated_at)
        VALUES ({val_list}, NOW())
        ON CONFLICT (id) DO UPDATE SET {update_set}, updated_at = NOW();
    """


_BASE_COLS = (
    "id", "url", "thumb", "aluguel", "venda", "iptu", "condominio",
    "banheiros", "quartos", "vagas", "area", "bairro", "tipo_imovel",
    "endereco", "lat", "lon", "payload",
)


def insert_quintoandar_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("QuintoAndar JSON root must be an array.")

    cols = _BASE_COLS + ("titulo", "cidade", "estado")
    sql = _build_upsert_sql(table_fqn, cols)

    rows = []
    for obj in data:
        if not isinstance(obj, dict) or not obj.get("id"):
            continue
        row = _base_row(obj)
        row["titulo"] = obj.get("titulo")
        row["cidade"] = obj.get("cidade")
        row["estado"] = obj.get("estado")
        rows.append(row)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()
    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_netimoveis_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("NetImoveis JSON root must be an array.")

    cols = _BASE_COLS + ("atualizado", "tem_locacao", "tem_venda")
    sql = _build_upsert_sql(table_fqn, cols)

    rows = []
    for obj in data:
        if not isinstance(obj, dict) or not obj.get("id"):
            continue
        row = _base_row(obj)
        row["atualizado"] = parse_netimoveis_atualizado(obj.get("atualizado"))
        row["tem_locacao"] = obj.get("tem_locacao", 0)
        row["tem_venda"] = obj.get("tem_venda", 0)
        rows.append(row)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()
    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_vivareal_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("VivaReal JSON root must be an array.")

    cols = _BASE_COLS + ("titulo", "descricao", "atualizado", "tem_locacao", "tem_venda")
    sql = _build_upsert_sql(table_fqn, cols)

    rows = []
    for obj in data:
        if not isinstance(obj, dict) or not obj.get("id"):
            continue
        row = _base_row(obj)
        row["titulo"] = obj.get("titulo")
        row["descricao"] = obj.get("descricao")
        row["atualizado"] = parse_netimoveis_atualizado(obj.get("atualizado"))
        row["tem_locacao"] = obj.get("tem_locacao", 0)
        row["tem_venda"] = obj.get("tem_venda", 0)
        rows.append(row)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()
    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_casamineira_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("CasaMineira JSON root must be an array.")

    sql = _build_upsert_sql(table_fqn, _BASE_COLS)

    rows = []
    for obj in data:
        if not isinstance(obj, dict) or not obj.get("id"):
            continue
        rows.append(_base_row(obj))

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for chunk in _chunks(rows, BATCH_SIZE):
                cur.executemany(sql, chunk)
        conn.commit()
    print(f"Inserted/updated {len(rows)} records into {table_fqn}.")


def insert_zap_imoveis(json_filepath: str, dsn: str, *, table_fqn: str) -> None:
    path = Path(json_filepath)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("ZAP JSON root must be an array.")

    zap_extra_cols = (
        "external_id", "location_id", "amenidades", "fotos", "andares",
        "cidade", "estado", "endereco_rua", "endereco_numero",
        "geo_source", "is_absolute_location",
        "publicado_ha", "atualizado_ha",
        "json_details_data", "json_general_data", "json_point_data",
    )
    cols = _BASE_COLS + zap_extra_cols
    sql = _build_upsert_sql(table_fqn, cols)

    rows = []
    for item in data:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        row = _base_row(item)
        row.update({
            "external_id": item.get("externalId"),
            "location_id": item.get("locationId"),
            "amenidades": as_json_text(item.get("amenidades")),
            "fotos": as_json_text(item.get("fotos")),
            "andares": item.get("andares"),
            "cidade": item.get("cidade"),
            "estado": item.get("estado"),
            "endereco_rua": item.get("enderecoRua"),
            "endereco_numero": item.get("enderecoNumero"),
            "geo_source": item.get("geoSource"),
            "is_absolute_location": item.get("isAbsoluteLocation"),
            "publicado_ha": clean_date(item.get("publicadoHa")),
            "atualizado_ha": clean_date(item.get("atualizadoHa")),
            "json_details_data": as_json_text(item.get("jsonDetailsData")),
            "json_general_data": as_json_text(item.get("jsonGeneralData")),
            "json_point_data": as_json_text(item.get("jsonPointData")),
        })
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
    create_provider_snapshot_table(dsn, p, table_fqn, drop_first=truncate_before)

    inserters: dict[ProviderStr, Callable] = {
        "zapimoveis": insert_zap_imoveis,
        "quintoandar": insert_quintoandar_imoveis,
        "netimoveis": insert_netimoveis_imoveis,
        "vivareal": insert_vivareal_imoveis,
        "casamineira": insert_casamineira_imoveis,
    }
    inserters[p](json_filepath, dsn, table_fqn=table_fqn)
    return table_fqn


# ---------------------------------------------------
# CLI
# ---------------------------------------------------

def _resolve_provider_path(provider: ProviderStr, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    path = ScrapeLatestFiles.latest_for_provider(provider)
    if path is None:
        return None
    print(f"[upload] {provider}: using latest scrape {path}")
    return str(path)


def _provider_jobs_from_args(args: argparse.Namespace) -> list[tuple[ProviderStr, str]]:
    pairs: list[tuple[ProviderStr, str | None]] = [
        ("quintoandar", args.quintoandar),
        ("casamineira", args.casamineira),
        ("netimoveis", args.netimoveis),
        ("vivareal", args.vivareal),
        ("zapimoveis", args.zapimoveis),
    ]
    jobs: list[tuple[ProviderStr, str]] = []
    for provider, explicit in pairs:
        resolved = _resolve_provider_path(provider, explicit)
        if resolved:
            jobs.append((provider, resolved))
    return jobs


def _build_upload_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Load scraped JSON into Postgres (schema b_dados). "
            "Pass one or more provider PATH flags, or set the matching IMOVEIS_UPLOAD_* "
            "environment variables."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Environment variables (used when the matching CLI flag is omitted):
  {ENV_DSN}              PostgreSQL DSN (same as --dsn)
  {ENV_QUINTOANDAR}      QuintoAndar JSON path (else latest in scrape output dir)
  {ENV_CASAMINEIRA}      CasaMineira JSON path (else latest)
  {ENV_NETIMOVEIS}       NetImoveis JSON path (else latest)
  {ENV_VIVAREAL}         VivaReal JSON path (else latest)
  {ENV_ZAPIMOVEIS}       ZapImoveis JSON path (else latest)
  {ENV_TRUNCATE_BEFORE}  Set to 1/true/yes/on to enable --truncate-before
  {ENV_NO_MERGE}         Set to 1/true/yes/on to enable --no-merge
""",
    )
    parser.add_argument("--dsn", default=_env_str(ENV_DSN))
    parser.add_argument("--quintoandar", metavar="PATH", default=_env_str(ENV_QUINTOANDAR))
    parser.add_argument("--casamineira", metavar="PATH", default=_env_str(ENV_CASAMINEIRA))
    parser.add_argument("--netimoveis", metavar="PATH", default=_env_str(ENV_NETIMOVEIS))
    parser.add_argument("--vivareal", metavar="PATH", default=_env_str(ENV_VIVAREAL))
    parser.add_argument("--zapimoveis", metavar="PATH", default=_env_str(ENV_ZAPIMOVEIS))
    parser.add_argument(
        "--truncate-before", action="store_true", default=_env_bool(ENV_TRUNCATE_BEFORE),
    )
    parser.add_argument(
        "--no-merge", action="store_true", default=_env_bool(ENV_NO_MERGE),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_upload_parser()
    args = parser.parse_args(argv)

    if not args.dsn:
        parser.error(f"--dsn or {ENV_DSN} is required")

    jobs = _provider_jobs_from_args(args)
    if not jobs:
        parser.error(
            f"Specify at least one input file via CLI, environment, or latest scrape."
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


if __name__ == "__main__":
    main()
