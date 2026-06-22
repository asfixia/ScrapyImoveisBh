"""Load scraped JSON snapshot files into Postgres (one table per file).

Each ``output/YYYY-MM-DD_HH-MM_<site>.json`` file maps to a Postgres table named
``<site>_YYYY_MM_DD_HH_MM`` (site first — valid unquoted identifier).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence, get_args

import psycopg
from psycopg.types.json import Json

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ImoveisScrapy.spiders.utils.scrape_latest import SCRAPE_JSON_PATTERN
from ImoveisScrapy.spiders.utils.scrape_output import OUTPUT_DIR
from pipeline.merge import _to_merged

# CLI / env
ENV_DSN = "IMOVEIS_UPLOAD_DSN"
ENV_OUTPUT_DIR = "SCRAPE_OUTPUT_DIR"
ENV_TRUNCATE_BEFORE = "IMOVEIS_UPLOAD_TRUNCATE_BEFORE"
ENV_SCHEMA = "IMOVEIS_UPLOAD_SCHEMA"

_TRUTHY_ENV = frozenset({"1", "true", "yes", "on"})
BATCH_SIZE = 500
DEFAULT_SCHEMA = "b_dados"

_EXCLUDED_JSON_SITES = frozenset({"imoveis_unificados", "imoveis_unificados_minified"})

ProviderStr = Literal[
    "quintoandar", "vivareal", "netimoveis", "zapimoveis", "casamineira"
]

_UPLOAD_COLUMNS: tuple[str, ...] = (
    "uid",
    "internal_id",
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


def _env_str(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY_ENV


def output_directory() -> Path:
    raw = os.environ.get(ENV_OUTPUT_DIR, "").strip()
    return Path(raw) if raw else OUTPUT_DIR


def _sanitize_pg_identifier(value: str) -> str:
    value = value.replace("-", "_").lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        raise ValueError(f"Could not derive a Postgres-safe identifier from {value!r}")
    return value[:63]


def site_from_json_path(path: Path) -> ProviderStr:
    match = SCRAPE_JSON_PATTERN.match(path.name)
    if not match:
        raise ValueError(f"Unrecognized scrape JSON filename: {path.name}")
    site = match.group("site").lower()
    if site not in get_args(ProviderStr):
        raise ValueError(f"Unknown site in filename {path.name!r}: {site!r}")
    return site  # type: ignore[return-value]


def table_name_from_json_filename(name: str) -> str:
    """``2026-06-01_02-25_quintoandar.json`` → ``quintoandar_2026_06_01_02_25``."""
    match = SCRAPE_JSON_PATTERN.match(Path(name).name)
    if not match:
        raise ValueError(f"Unrecognized scrape JSON filename: {name}")
    site = match.group("site").lower()
    if site not in get_args(ProviderStr):
        raise ValueError(f"Unknown site in filename {name!r}: {site!r}")
    stamp = match.group("date").replace("-", "_")
    return _sanitize_pg_identifier(f"{site}_{stamp}")


def json_filename_from_table_name(table_name: str) -> str:
    """``quintoandar_2026_06_01_02_25`` → ``2026-06-01_02-25_quintoandar.json``."""
    _TABLE_STAMP_PATTERN = re.compile(
        rf"^(?P<site>{'|'.join(get_args(ProviderStr))})_"
        r"(?P<y>\d{4})_(?P<m>\d{2})_(?P<d>\d{2})_(?P<h>\d{2})_(?P<min>\d{2})$"
    )
    normalized = _sanitize_pg_identifier(table_name)
    match = _TABLE_STAMP_PATTERN.match(normalized)
    if not match:
        raise ValueError(f"Unrecognized snapshot table name: {table_name!r}")
    date_part = (
        f"{match.group('y')}-{match.group('m')}-{match.group('d')}_"
        f"{match.group('h')}-{match.group('min')}"
    )
    return f"{date_part}_{match.group('site')}.json"


def table_name_from_json_path(path: Path) -> str:
    """Postgres table name for a scrape JSON file (site prefix, then timestamp)."""
    return table_name_from_json_filename(path.name)


def json_path_from_table_name(
    table_name: str,
    directory: Path | None = None,
) -> Path:
    """Resolve the scrape JSON path for a snapshot table name."""
    root = directory if directory is not None else output_directory()
    return root / json_filename_from_table_name(table_name)


def table_fqn_from_json_path(path: Path, schema: str = DEFAULT_SCHEMA) -> str:
    return f"{schema}.{table_name_from_json_path(path)}"


# Backward-compatible helpers (tests / launch configs).
def snapshot_suffix_from_path(path: Path, provider: ProviderStr) -> str:
    stem = path.stem.lower()
    for token in (f"_{provider}", "_zap"):
        if stem.endswith(token):
            stem = stem[: -len(token)]
            break
    return _sanitize_pg_identifier(stem.strip("_"))


def snapshot_table_fqn(provider: ProviderStr, json_path: str | Path) -> str:
    path = Path(json_path)
    suffix = snapshot_suffix_from_path(path, provider)
    base = {
        "quintoandar": "quintoandar_imoveis",
        "netimoveis": "netimoveis_imoveis",
        "vivareal": "vivareal_imoveis",
        "zapimoveis": "zap_imoveis",
        "casamineira": "casamineira_imoveis",
    }[provider]
    return f"{DEFAULT_SCHEMA}.{base}_{suffix}"


def list_scrape_json_files(directory: Path | None = None) -> list[Path]:
    """All timestamped scrape JSON files in *directory* (newest name order)."""
    root = directory if directory is not None else output_directory()
    if not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.glob("*.json"):
        match = SCRAPE_JSON_PATTERN.match(path.name)
        if not match:
            continue
        site = match.group("site").lower()
        if site in _EXCLUDED_JSON_SITES:
            continue
        if site.startswith("_upload_merge_"):
            continue
        if site not in get_args(ProviderStr):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.name)


def iter_db_rows_from_file(path: Path) -> Iterable[dict[str, Any]]:
    """Yield DB rows one at a time (no full merged/list buffer)."""
    fonte = site_from_json_path(path)
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
        yield build_db_row_from_raw(raw, effective_fonte)


def build_db_row_from_raw(raw: dict[str, Any], fonte: str) -> dict[str, Any]:
    """Build one upload row; ``merged`` is not kept after return."""
    return build_db_row(_to_merged(raw, fonte), raw)


def build_db_row(merged: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    listing_id = int(merged.get("id") or 0)
    fonte = str(merged.get("fonte") or "")
    if not listing_id or not fonte:
        raise ValueError(f"Row missing id or fonte: id={listing_id!r} fonte={fonte!r}")

    lon = merged.get("lon")

    return {
        "uid": f"{listing_id}_{fonte}",
        "internal_id": str(uuid.uuid4()),
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
        "lon": lon,
        "fonte": fonte,
        "full_item_json": Json(raw),
    }


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
    print(f"\n{table_fqn}) Inserting rows in batches of {batch_size}")
    for row in rows:
        batch.append(row)
        total += 1
        if len(batch) >= batch_size:
            cur.executemany(sql, batch)
            batch.clear()
        if total % 1000 == 0:
            print(f"\n{table_fqn}) Inserted -> {total} rows")
    if batch:
        cur.executemany(sql, batch)
        print(f"\n{table_fqn}) Inserted -> {total} rows")
    print(f"\n{table_fqn}) Finished inserting")
    return total


def _ensure_schema(cur: psycopg.Cursor, schema: str) -> None:
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


def _table_exists(cur: psycopg.Cursor, schema: str, table_name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        )
        """,
        (schema, table_name),
    )
    row = cur.fetchone()
    return bool(row and row[0])


def _ddl_create_snapshot_table(table_fqn: str) -> str:
    cols = ",\n        ".join(
        [
            "uid             TEXT PRIMARY KEY",
            "internal_id     UUID NOT NULL",
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


def _ddl_create_snapshot_indexes(table_fqn: str) -> list[str]:
    idx = table_fqn.replace(".", "_")
    return [
        f"CREATE INDEX {idx}_internal_id ON {table_fqn} (internal_id)",
        f"CREATE INDEX {idx}_fonte_id ON {table_fqn} (fonte, id)",
    ]


def _insert_sql(table_fqn: str) -> str:
    col_list = ", ".join(_UPLOAD_COLUMNS)
    val_list = ", ".join(f"%({c})s" for c in _UPLOAD_COLUMNS)
    return f"INSERT INTO {table_fqn} ({col_list}) VALUES ({val_list})"


@dataclass
class UploadReport:
    json_path: Path
    table_fqn: str
    table_existed: bool
    status: str
    rows_inserted: int = 0
    error: str | None = None


def upload_json_file(
    json_path: Path,
    dsn: str,
    *,
    schema: str = DEFAULT_SCHEMA,
    truncate_before: bool = False,
) -> UploadReport:
    table_fqn = table_fqn_from_json_path(json_path, schema)
    schema_name, table_name = table_fqn.split(".", 1)

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                _ensure_schema(cur, schema_name)
                existed = _table_exists(cur, schema_name, table_name)

            if existed and not truncate_before:
                return UploadReport(
                    json_path=json_path,
                    table_fqn=table_fqn,
                    table_existed=True,
                    status="skipped_exists",
                )

            with conn.transaction():
                with conn.cursor() as cur:
                    creating_table = not existed
                    if existed and truncate_before:
                        print(f"\nDropping table: {table_fqn}")
                        cur.execute(f"DROP TABLE {table_fqn}")
                        creating_table = True
                    if creating_table:
                        print(f"\nCreating table: {table_fqn}")
                        cur.execute(_ddl_create_snapshot_table(table_fqn))

                    print(f"\nInserting   {json_path.name} -> {table_fqn}")
                    row_count = _insert_rows_batched(cur, table_fqn, iter_db_rows_from_file(json_path))

                    if creating_table:
                        print(f"Creating indexes on {table_fqn}")
                        for stmt in _ddl_create_snapshot_indexes(table_fqn):
                            cur.execute(stmt)

        status = "reloaded" if existed and truncate_before else "created"
        return UploadReport(
            json_path=json_path,
            table_fqn=table_fqn,
            table_existed=existed,
            status=status,
            rows_inserted=row_count,
        )
    except Exception as exc:
        return UploadReport(
            json_path=json_path,
            table_fqn=table_fqn,
            table_existed=False,
            status="error",
            error=str(exc),
        )


def print_upload_report(reports: Sequence[UploadReport]) -> None:
    print("\n" + "=" * 72)
    print("UPLOAD REPORT")
    print("=" * 72)
    created = skipped = errors = 0
    total_rows = 0

    for report in reports:
        existed_label = "yes" if report.table_existed else "no"
        line = (
            f"{report.json_path.name}\n"
            f"  table:          {report.table_fqn}\n"
            f"  table_existed:  {existed_label}\n"
            f"  status:         {report.status}\n"
            f"  rows_inserted:  {report.rows_inserted}"
        )
        if report.error:
            line += f"\n  error:          {report.error}"
            errors += 1
        elif report.status == "skipped_exists":
            skipped += 1
        else:
            created += 1
            total_rows += report.rows_inserted
        print(line)
        print("-" * 72)

    print(
        f"Summary: {len(reports)} file(s) | "
        f"loaded={created} | skipped={skipped} | errors={errors} | "
        f"rows_inserted={total_rows}"
    )
    print("=" * 72 + "\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Upload all scrape JSON files from the output folder into Postgres. "
            "One table per file (name = file stem). No merge step."
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
        "--truncate-before",
        action="store_true",
        default=_env_bool(ENV_TRUNCATE_BEFORE),
        help="Drop and reload tables that already exist",
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

    if args.files:
        json_files = [Path(p) for p in args.files]
    else:
        json_files = list_scrape_json_files(args.output_dir)

    if not json_files:
        parser.error(f"No scrape JSON files found in {args.output_dir}")

    print(f"Output dir: {args.output_dir}")
    print(f"Schema:     {args.schema}")
    print(f"Files:      {len(json_files)}")

    reports: list[UploadReport] = []
    for path in json_files:
        print(f"\nDealing with {path.name}")
        report = upload_json_file(path, args.dsn, schema=args.schema, truncate_before=args.truncate_before)
        reports.append(report)
        if report.error:
            print(f"  ERROR: {report.error}")
        elif report.status == "skipped_exists":
            print(f"  skipped (table already exists): {report.table_fqn}")
        else:
            print(f"  {report.status}: {report.rows_inserted} row(s) -> {report.table_fqn}")

    print_upload_report(reports)

    if any(r.status == "error" for r in reports):
        sys.exit(1)


if __name__ == "__main__":
    main()
