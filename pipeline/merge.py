"""Merge scraped JSON files from all sources into imoveis_unificados.json."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ImoveisScrapy.spiders.utils.models import ImoveisScrapyItem
from ImoveisScrapy.spiders.utils.scrape_latest import ScrapeLatestFiles
from ImoveisScrapy.spiders.utils.scrape_output import OUTPUT_DIR

# Single central output folder — overridden by SCRAPE_OUTPUT_DIR env var.
_env_dir = os.environ.get("SCRAPE_OUTPUT_DIR", "").strip()
CENTRAL_OUTPUT_DIR: Path = Path(_env_dir) if _env_dir else OUTPUT_DIR



def _to_merged(item: dict, fonte: str) -> dict:
    """Extract standard fields from a spider's to_dict() output, add fonte, drop payload."""
    out = {k: item.get(k) for k in ImoveisScrapyItem.merge_field_names() if k != "long"}
    out["lon"] = item.get("lon")
    out['thumb'] = out['thumb'].replace("action={action}&dimension={width}x{height}", "action=fit-in&dimension=614x297")
    out["fonte"] = fonte
    return out


def parse_quintoandar(data: dict[str, dict]) -> list[dict]:
    return [_to_merged(item, "quintoandar") for item in data.values()]


def parse_vivareal(data: dict[str, dict]) -> list[dict]:
    return [_to_merged(item, "vivareal") for item in data.values()]


def parse_netimoveis(data: dict[str, dict]) -> list[dict]:
    return [_to_merged(item, "netimoveis") for item in data.values()]


def parse_casamineira(data: dict[str, dict]) -> list[dict]:
    return [_to_merged(item, "casamineira") for item in data.values()]


def parse_zapimoveis(data: dict[str, dict]) -> list[dict]:
    return [_to_merged(item, "zapimoveis") for item in data.values()]


# ---------------------------------------------------
# Merge
# ---------------------------------------------------

if __name__ == "__main__":
    site_latest_paths = ScrapeLatestFiles.find_latest_by_site(CENTRAL_OUTPUT_DIR)

    print("Latest files:")
    for site, path in sorted(site_latest_paths.items()):
        print(f"  {site} -> {path}")

    site_jsons: dict[str, object] = {}
    for site, path in site_latest_paths.items():
        with path.open("r", encoding="utf-8") as f:
            site_jsons[site] = json.load(f)

    merged = []

    if "quintoandar" in site_jsons:
        merged.extend(parse_quintoandar(site_jsons["quintoandar"]))

    if "vivareal" in site_jsons:
        merged.extend(parse_vivareal(site_jsons["vivareal"]))

    if "netimoveis" in site_jsons:
        merged.extend(parse_netimoveis(site_jsons["netimoveis"]))

    if "zapimoveis" in site_jsons:
        merged.extend(parse_zapimoveis(site_jsons["zapimoveis"]))

    if "casamineira" in site_jsons:
        merged.extend(parse_casamineira(site_jsons["casamineira"]))

    print(f"\nMerged properties: {len(merged)}")

    CENTRAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = CENTRAL_OUTPUT_DIR / "imoveis_unificados.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"Saved: {output_file}")

    output_file_minified = CENTRAL_OUTPUT_DIR / "imoveis_unificados_minified.json"
    with open(output_file_minified, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Saved: {output_file_minified}")

    merged_destinations = os.getenv(
        "MERGED_FILE_MINIFIED",
        r"\\recalcards.com\web_html\fitrabit\data\imoveis_unificados.json,/var/www/html/fitrabit/data/imoveis_unificados.json",
    )
    for dest_str in re.split(r"[,|;]", merged_destinations):
        dest_str = dest_str.strip()
        if not dest_str:
            continue
        dest = Path(dest_str)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(output_file_minified, str(dest).replace(".json", "_minified.json"))
            shutil.copy(output_file, dest)
            print(f"Copied to {dest}")
        except Exception as e:
            print(f"Error copying to {dest}: {e}")
