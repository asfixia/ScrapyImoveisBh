from pathlib import Path

from pipeline.upload_to_db import (
    build_db_row,
    json_filename_from_table_name,
    json_path_from_table_name,
    snapshot_suffix_from_path,
    snapshot_table_fqn,
    table_fqn_from_json_path,
    table_name_from_json_filename,
    table_name_from_json_path,
)


def test_table_name_from_quintoandar_filename() -> None:
    path = Path("2026-06-20_21-14_quintoandar.json")
    assert table_name_from_json_path(path) == "quintoandar_2026_06_20_21_14"


def test_table_name_from_json_filename_string() -> None:
    assert (
        table_name_from_json_filename("2026-06-01_02-25_quintoandar.json")
        == "quintoandar_2026_06_01_02_25"
    )


def test_json_filename_from_table_name() -> None:
    assert (
        json_filename_from_table_name("quintoandar_2026_06_01_02_25")
        == "2026-06-01_02-25_quintoandar.json"
    )


def test_table_name_json_filename_round_trip() -> None:
    original = "2026-06-21_07-05_zapimoveis.json"
    table = table_name_from_json_filename(original)
    assert json_filename_from_table_name(table) == original


def test_json_path_from_table_name() -> None:
    root = Path("/data")
    assert json_path_from_table_name("vivareal_2026_05_04_01_01", root) == (
        root / "2026-05-04_01-01_vivareal.json"
    )


def test_table_fqn_from_zapimoveis_filename() -> None:
    path = Path("2026-06-21_07-05_zapimoveis.json")
    assert table_fqn_from_json_path(path) == "b_dados.zapimoveis_2026_06_21_07_05"


def test_build_db_row_uid_and_fonte() -> None:
    merged = {
        "id": 895366613,
        "url": "https://example.com",
        "thumb": "",
        "aluguel": 0,
        "venda": 2200000,
        "iptu": 0,
        "condominio": 225,
        "banheiros": 3,
        "quartos": 3,
        "vagas": 6,
        "area": 370,
        "bairro": "Jardim Canada",
        "tipo_imovel": "Casa",
        "endereco": "Rua X",
        "lat": -20.0,
        "lon": -43.9,
        "fonte": "quintoandar",
    }
    raw = {"id": 895366613, "extra": "field"}
    row = build_db_row(merged, raw)
    assert row["uid"] == "895366613_quintoandar"
    assert row["fonte"] == "quintoandar"
    assert row["lon"] == -43.9
    assert "long" not in row


# Legacy snapshot helpers (older table naming).
def test_snapshot_suffix_from_quintoandar_filename() -> None:
    path = Path("2026-05-04_00-31_quintoandar.json")
    assert snapshot_suffix_from_path(path, "quintoandar") == "2026_05_04_00_31"


def test_snapshot_table_fqn() -> None:
    path = Path("2026-05-04_01-01_vivareal.json")
    assert (
        snapshot_table_fqn("vivareal", path)
        == "b_dados.vivareal_imoveis_2026_05_04_01_01"
    )
