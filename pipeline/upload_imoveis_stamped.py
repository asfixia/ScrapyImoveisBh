"""Upload all scrape JSON files into one Postgres table with ``scrapy_date``.

Every listing from every ``YYYY-MM-DD_HH-MM_<site>.json`` file goes into
``b_dados.imoveis_stamped``. Rows are not deduplicated across scrapes; ``uid``
is ``{id}_{fonte}_{scrapy_date}`` (e.g. ``895366613_quintoandar_2026-06-01_02-25``).
The ``scrapy_date`` column stores a ``TIMESTAMP`` parsed from the filename stamp.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import psycopg
from psycopg.types.json import Json

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.merge import _to_merged
from pipeline.upload_to_db import (
    BATCH_SIZE,
    DEFAULT_SCHEMA,
    ENV_DSN,
    ENV_OUTPUT_DIR,
    ENV_SCHEMA,
    ENV_TRUNCATE_BEFORE,
    _ensure_schema,
    _env_bool,
    _env_str,
    _table_exists,
    list_scrape_json_files,
    output_directory,
    parse_scrapy_date,
    scrapy_date_from_json_path,
    scrapy_date_to_stamp,
    site_from_json_path,
)

# One JSON scrape file = one (scrapy_date stamp, site/fonte) pair.
SourceKey = tuple[str, str]

ENV_STAMPED_TABLE = "IMOVEIS_STAMPED_TABLE"
DEFAULT_STAMPED_TABLE = "imoveis_stamped"

_STAMPED_COLUMNS: tuple[str, ...] = (
    "uid",
    "internal_id",
    "scrapy_date",
    "id",
    "url",
    "thumb",
    "aluguel",
    "venda",
    "iptu",
    "condominio",
    "banheiros",
    "quartos",
    "vagas",
    "area",
    "bairro",
    "tipo_imovel",
    "endereco",
    "lat",
    "lon",
    "fonte",
    "full_item_json",
)


def stamped_table_name() -> str:
    return os.environ.get(ENV_STAMPED_TABLE, DEFAULT_STAMPED_TABLE).strip() or DEFAULT_STAMPED_TABLE


def stamped_table_fqn(schema: str = DEFAULT_SCHEMA) -> str:
    return f"{schema}.{stamped_table_name()}"


def build_stamped_uid(listing_id: int, fonte: str, scrapy_date_stamp: str) -> str:
    """``uid`` keeps the filename stamp as text (e.g. ``2026-06-01_02-25``)."""
    return f"{listing_id}_{fonte}_{scrapy_date_stamp}"


def source_key_from_json_path(path: Path) -> SourceKey:
    """Identify a scrape file: ``(scrapy_date_stamp, fonte)``."""
    return scrapy_date_from_json_path(path), site_from_json_path(path)


def fetch_loaded_source_keys(
    cur: psycopg.Cursor,
    table_fqn: str,
    *,
    schema_name: str,
    table_name: str,
) -> set[SourceKey]:
    """Distinct ``(scrapy_date stamp, fonte)`` pairs already present in the table."""
    if not _table_exists(cur, schema_name, table_name):
        return set()

    cur.execute(f"SELECT DISTINCT scrapy_date, fonte FROM {table_fqn}")
    return {
        (scrapy_date_to_stamp(scrapy_dt), str(fonte))
        for scrapy_dt, fonte in cur.fetchall()
    }


def get_loaded_sources(dsn: str, *, schema: str = DEFAULT_SCHEMA) -> set[SourceKey]:
    table_fqn = stamped_table_fqn(schema)
    schema_name, table_name = table_fqn.split(".", 1)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            return fetch_loaded_source_keys(
                cur,
                table_fqn,
                schema_name=schema_name,
                table_name=table_name,
            )


def format_source_key(key: SourceKey) -> str:
    stamp, fonte = key
    return f"{stamp} / {fonte}"


def _ddl_create_unified_table(table_fqn: str) -> str:
    cols = ",\n        ".join(
        [
            "uid             TEXT PRIMARY KEY",
            "internal_id     UUID NOT NULL",
            "scrapy_date     TIMESTAMP NOT NULL",
            "id              BIGINT NOT NULL",
            "url             TEXT",
            "thumb           TEXT",
            "aluguel         INTEGER",
            "venda           INTEGER",
            "iptu            INTEGER",
            "condominio      INTEGER",
            "banheiros       INTEGER",
            "quartos         INTEGER",
            "vagas           INTEGER",
            "area            INTEGER",
            "bairro          TEXT",
            "tipo_imovel     TEXT",
            "endereco        TEXT",
            "lat             DOUBLE PRECISION",
            "lon             DOUBLE PRECISION",
            "fonte           TEXT NOT NULL",
            "full_item_json  JSONB NOT NULL",
            "created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        ]
    )
    return f"CREATE TABLE {table_fqn} (\n        {cols}\n        )"


def _ddl_create_unified_indexes(table_fqn: str) -> list[str]:
    idx = table_fqn.replace(".", "_")
    return [
        f"CREATE INDEX {idx}_scrapy_date ON {table_fqn} (scrapy_date)",
        f"CREATE INDEX {idx}_fonte ON {table_fqn} (fonte)",
        f"CREATE INDEX {idx}_scrapy_date_fonte ON {table_fqn} (scrapy_date, fonte)",
        f"CREATE INDEX {idx}_fonte_id ON {table_fqn} (fonte, id)",
        f"CREATE INDEX {idx}_internal_id ON {table_fqn} (internal_id)",
    ]


def _insert_sql(table_fqn: str) -> str:
    col_list = ", ".join(_STAMPED_COLUMNS)
    val_list = ", ".join(f"%({c})s" for c in _STAMPED_COLUMNS)
    return f"INSERT INTO {table_fqn} ({col_list}) VALUES ({val_list})"


def _insert_rows_batched(
    cur: psycopg.Cursor,
    table_fqn: str,
    rows: Iterable[dict[str, Any]],
    *,
    batch_size: int = BATCH_SIZE,
) -> int:
    sql = _insert_sql(table_fqn)
    batch: list[dict[str, Any]] = []
    total = 0
    for row in rows:
        batch.append(row)
        total += 1
        if len(batch) >= batch_size:
            cur.executemany(sql, batch)
            batch.clear()
        if total % 5000 == 0:
            print(f"  {table_fqn}: inserted {total} rows …")
    if batch:
        cur.executemany(sql, batch)
    return total


def build_stamped_row(
    merged: dict[str, Any],
    raw: dict[str, Any],
    scrapy_date_stamp: str,
) -> dict[str, Any]:
    listing_id = int(merged.get("id") or 0)
    fonte = str(merged.get("fonte") or "")
    if not listing_id or not fonte:
        raise ValueError(f"Row missing id or fonte: id={listing_id!r} fonte={fonte!r}")

    return {
        "uid": build_stamped_uid(listing_id, fonte, scrapy_date_stamp),
        "internal_id": str(uuid.uuid4()),
        "scrapy_date": parse_scrapy_date(scrapy_date_stamp),
        "id": listing_id,
        "url": merged.get("url"),
        "thumb": merged.get("thumb"),
        "aluguel": merged.get("aluguel"),
        "venda": merged.get("venda"),
        "iptu": merged.get("iptu"),
        "condominio": merged.get("condominio"),
        "banheiros": merged.get("banheiros"),
        "quartos": merged.get("quartos"),
        "vagas": merged.get("vagas"),
        "area": merged.get("area"),
        "bairro": merged.get("bairro"),
        "tipo_imovel": merged.get("tipo_imovel"),
        "endereco": merged.get("endereco"),
        "lat": merged.get("lat"),
        "lon": merged.get("lon"),
        "fonte": fonte,
        "full_item_json": Json(raw),
    }


def iter_stamped_rows_from_file(path: Path) -> Iterable[dict[str, Any]]:
    fonte = site_from_json_path(path)
    scrapy_date_stamp = scrapy_date_from_json_path(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        items = data.values()
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(f"{path}: JSON root must be an object or array.")

    for raw in items:
        if not isinstance(raw, dict) or raw.get("id") is None:
            continue
        effective_fonte = str(raw.get("fonte") or fonte)
        merged = _to_merged(raw, effective_fonte)
        yield build_stamped_row(merged, raw, scrapy_date_stamp)


@dataclass
class StampedFileReport:
    json_path: Path
    table_fqn: str
    scrapy_date: str
    fonte: str
    status: str
    rows_inserted: int = 0
    error: str | None = None


def upload_json_into_unified_table(
    json_path: Path,
    dsn: str,
    *,
    schema: str = DEFAULT_SCHEMA,
    loaded_source_keys: set[SourceKey] | None = None,
    skip_if_source_loaded: bool = True,
) -> StampedFileReport:
    table_fqn = stamped_table_fqn(schema)
    scrapy_date_stamp, fonte = source_key_from_json_path(json_path)
    source_key = (scrapy_date_stamp, fonte)

    if skip_if_source_loaded and loaded_source_keys is not None and source_key in loaded_source_keys:
        return StampedFileReport(
            json_path=json_path,
            table_fqn=table_fqn,
            scrapy_date=scrapy_date_stamp,
            fonte=fonte,
            status="skipped_source_loaded",
        )

    try:
        with psycopg.connect(dsn) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    print(
                        f"  inserting {json_path.name} "
                        f"(scrapy_date={scrapy_date_stamp}, fonte={fonte}) …"
                    )
                    row_count = _insert_rows_batched(
                        cur,
                        table_fqn,
                        iter_stamped_rows_from_file(json_path),
                    )

        if loaded_source_keys is not None:
            loaded_source_keys.add(source_key)

        return StampedFileReport(
            json_path=json_path,
            table_fqn=table_fqn,
            scrapy_date=scrapy_date_stamp,
            fonte=fonte,
            status="inserted",
            rows_inserted=row_count,
        )
    except Exception as exc:
        return StampedFileReport(
            json_path=json_path,
            table_fqn=table_fqn,
            scrapy_date=scrapy_date_stamp,
            fonte=fonte,
            status="error",
            error=str(exc),
        )


def ensure_unified_table(
    dsn: str,
    *,
    schema: str = DEFAULT_SCHEMA,
    truncate_before: bool = False,
) -> tuple[str, bool, bool]:
    """Create unified table if needed. Returns (table_fqn, existed, recreated)."""
    table_fqn = stamped_table_fqn(schema)
    schema_name, table_name = table_fqn.split(".", 1)

    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                _ensure_schema(cur, schema_name)
                existed = _table_exists(cur, schema_name, table_name)
                recreated = False

                if existed and truncate_before:
                    print(f"Dropping unified table: {table_fqn}")
                    cur.execute(f"DROP TABLE {table_fqn}")
                    existed = False
                    recreated = True

                if not existed:
                    print(f"Creating unified table: {table_fqn}")
                    cur.execute(_ddl_create_unified_table(table_fqn))

    return table_fqn, existed, recreated


def create_unified_indexes(dsn: str, *, schema: str = DEFAULT_SCHEMA) -> None:
    table_fqn = stamped_table_fqn(schema)
    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                print(f"Creating indexes on {table_fqn}")
                for stmt in _ddl_create_unified_indexes(table_fqn):
                    cur.execute(stmt)


def print_stamped_report(reports: Sequence[StampedFileReport]) -> None:
    print("\n" + "=" * 72)
    print("STAMPED UPLOAD REPORT (unified table)")
    print("=" * 72)
    inserted = skipped = errors = 0
    total_rows = 0
    table_fqn = reports[0].table_fqn if reports else stamped_table_fqn()

    for report in reports:
        line = (
            f"{report.json_path.name}\n"
            f"  table:          {report.table_fqn}\n"
            f"  scrapy_date:    {report.scrapy_date}\n"
            f"  fonte:          {report.fonte}\n"
            f"  status:         {report.status}\n"
            f"  rows_inserted:  {report.rows_inserted}"
        )
        if report.error:
            line += f"\n  error:          {report.error}"
            errors += 1
        elif report.status == "skipped_source_loaded":
            skipped += 1
        else:
            inserted += 1
            total_rows += report.rows_inserted
        print(line)
        print("-" * 72)

    print(
        f"Target table: {table_fqn}\n"
        f"Summary: {len(reports)} file(s) | "
        f"inserted={inserted} | skipped={skipped} | errors={errors} | "
        f"rows_inserted={total_rows}"
    )
    print("=" * 72 + "\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Upload all scrape JSON files into one Postgres table (imoveis_stamped). "
            "Each row has scrapy_date from the filename; uid = id_fonte_scrapy_date."
        ),
    )
    parser.add_argument("--dsn", default=_env_str(ENV_DSN))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=output_directory(),
        help=f"Folder with scrape JSON files (default: {ENV_OUTPUT_DIR} or project output/)",
    )
    parser.add_argument(
        "--schema",
        default=_env_str(ENV_SCHEMA) or DEFAULT_SCHEMA,
        help=f"Postgres schema (default: {DEFAULT_SCHEMA})",
    )
    parser.add_argument(
        "--table",
        default=os.environ.get(ENV_STAMPED_TABLE, DEFAULT_STAMPED_TABLE),
        help=f"Unified table name (default: {DEFAULT_STAMPED_TABLE})",
    )
    parser.add_argument(
        "--truncate-before",
        action="store_true",
        default=_env_bool(ENV_TRUNCATE_BEFORE),
        help="Drop and recreate the unified table before loading",
    )
    parser.add_argument(
        "--file",
        action="append",
        metavar="PATH",
        dest="files",
        help="Upload only this JSON file (repeatable). Default: all files in --output-dir",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.dsn:
        parser.error(f"--dsn or {ENV_DSN} is required")

    if args.table:
        os.environ[ENV_STAMPED_TABLE] = args.table

    if args.files:
        json_files = [Path(p) for p in args.files]
    else:
        json_files = list_scrape_json_files(args.output_dir)

    if not json_files:
        parser.error(f"No scrape JSON files found in {args.output_dir}")

    table_fqn = stamped_table_fqn(args.schema)
    print(f"Output dir: {args.output_dir}")
    print(f"Target:     {table_fqn}")
    print(f"Files:      {len(json_files)}")

    _, existed, recreated = ensure_unified_table(
        args.dsn,
        schema=args.schema,
        truncate_before=args.truncate_before,
    )
    skip_if_source = not args.truncate_before and not recreated
    loaded_source_keys = get_loaded_sources(args.dsn, schema=args.schema)

    reports: list[StampedFileReport] = []
    for path in json_files:
        print(f"\n{path.name}")
        report = upload_json_into_unified_table(
            path,
            args.dsn,
            schema=args.schema,
            loaded_source_keys=loaded_source_keys,
            skip_if_source_loaded=skip_if_source,
        )
        reports.append(report)
        if report.error:
            print(f"  ERROR: {report.error}")
        elif report.status == "skipped_source_loaded":
            print(f"  skipped (source already loaded: {format_source_key((report.scrapy_date, report.fonte))})")
        else:
            print(f"  inserted {report.rows_inserted} row(s)")

    if not existed or recreated or args.truncate_before:
        create_unified_indexes(args.dsn, schema=args.schema)

    print_stamped_report(reports)

    if any(r.status == "error" for r in reports):
        sys.exit(1)


if __name__ == "__main__":
    main()
