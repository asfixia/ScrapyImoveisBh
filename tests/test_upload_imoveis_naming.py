from pathlib import Path

from pipeline.upload_to_db import snapshot_suffix_from_path, snapshot_table_fqn


def test_snapshot_suffix_from_quintoandar_filename() -> None:
    path = Path("2026-05-04_00-31_quintoandar.json")
    assert snapshot_suffix_from_path(path, "quintoandar") == "2026_05_04_00_31"


def test_snapshot_suffix_from_zapimoveis_filename() -> None:
    path = Path("2026-05-06_14-18_zapimoveis.json")
    assert snapshot_suffix_from_path(path, "zapimoveis") == "2026_05_06_14_18"


def test_snapshot_table_fqn() -> None:
    path = Path("2026-05-04_01-01_vivareal.json")
    assert (
        snapshot_table_fqn("vivareal", path)
        == "b_dados.vivareal_imoveis_2026_05_04_01_01"
    )


def test_snapshot_table_fqn_casamineira() -> None:
    path = Path("2026-05-21_01-21_casamineira.json")
    assert (
        snapshot_table_fqn("casamineira", path)
        == "b_dados.casamineira_imoveis_2026_05_21_01_21"
    )
