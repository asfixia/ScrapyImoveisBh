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


def test_scrapy_date_from_json_path() -> None:
    from pipeline.upload_to_db import scrapy_date_from_json_path

    assert (
        scrapy_date_from_json_path(Path("2026-06-01_02-25_quintoandar.json"))
        == "2026-06-01_02-25"
    )


def test_parse_scrapy_date() -> None:
    from datetime import datetime

    from pipeline.upload_to_db import parse_scrapy_date, scrapy_date_to_stamp

    dt = datetime(2026, 6, 1, 2, 25)
    assert parse_scrapy_date("2026-06-01_02-25") == dt
    assert scrapy_date_to_stamp(dt) == "2026-06-01_02-25"


def test_source_key_from_json_path() -> None:
    from pipeline.upload_imoveis_stamped import source_key_from_json_path

    path = Path("2026-06-01_02-25_quintoandar.json")
    assert source_key_from_json_path(path) == ("2026-06-01_02-25", "quintoandar")

    path2 = Path("2026-06-01_02-25_zapimoveis.json")
    assert source_key_from_json_path(path2) == ("2026-06-01_02-25", "zapimoveis")
    assert source_key_from_json_path(path) != source_key_from_json_path(path2)


def test_build_stamped_row() -> None:
    from datetime import datetime

    from pipeline.upload_imoveis_stamped import build_stamped_row, build_stamped_uid

    merged = {
        "id": 1,
        "url": "u",
        "thumb": "",
        "aluguel": 0,
        "venda": 0,
        "iptu": 0,
        "condominio": 0,
        "banheiros": 0,
        "quartos": 0,
        "vagas": 0,
        "area": 0,
        "bairro": "",
        "tipo_imovel": "",
        "endereco": "",
        "lat": 0.0,
        "lon": 0.0,
        "fonte": "quintoandar",
    }
    scrapy_date_stamp = "2026-06-01_02-25"
    row = build_stamped_row(merged, {"id": 1}, scrapy_date_stamp)
    assert row["scrapy_date"] == datetime(2026, 6, 1, 2, 25)
    assert row["uid"] == build_stamped_uid(1, "quintoandar", scrapy_date_stamp)
    assert row["uid"] == "1_quintoandar_2026-06-01_02-25"


def test_stamped_table_fqn() -> None:
    from pipeline.upload_imoveis_stamped import stamped_table_fqn

    assert stamped_table_fqn() == "b_dados.imoveis_stamped"


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
