import argparse
import json
from pathlib import Path

import psycopg


SQL_EXPORT_QUERY = """
SELECT jsonb_agg(to_jsonb(q))::text AS result
FROM (
	SELECT *
	FROM b_dados.imoveis_unificados
) as q;
"""


def export_query_to_json(dsn: str, output_path: str) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_EXPORT_QUERY)
            row = cur.fetchone()

    result_text = row[0] if row else None
    payload = json.loads(result_text) if result_text else []

    #if len(payload) != 74086:
    #    return None

    with target.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=None)

    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run ZAP export query and save result to JSON file."
    )
    parser.add_argument("--dsn", required=True, help="PostgreSQL DSN connection string.")
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file path (e.g. ./zap_export.json).",
    )
    args = parser.parse_args()

    output_file = export_query_to_json(args.dsn, args.output)
    print(f"Exported query result to {output_file}")


if __name__ == "__main__":
    main()
