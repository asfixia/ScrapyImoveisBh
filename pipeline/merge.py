"""Merge scraped JSON files from all sources into imoveis_unificados.json."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ImoveisScrapy.spiders.utils.data_helpers import (
    getFirstValue,
    getKey,
    normalize_tipo,
    parse_float,
    parse_int,
    removeInvalidValue,
)
from ImoveisScrapy.spiders.utils.scrape_output import OUTPUT_DIR

PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2}_\d{2}-\d{2})_(?P<site>[a-zA-Z0-9_]+)\.json$"
)

# Single central output folder — overridden by SCRAPE_OUTPUT_DIR env var.
_env_dir = os.environ.get("SCRAPE_OUTPUT_DIR", "").strip()
CENTRAL_OUTPUT_DIR: Path = Path(_env_dir) if _env_dir else OUTPUT_DIR

# ---------------------------------------------------
# Parsers
# ---------------------------------------------------

def parse_quintoandar(data):
    result = []
    for id, item in data.items():
        result.append({
            "id": parse_int(id),
            "url": item.get("url"),
            "thumb": (item.get("thumb", "") or "").replace("{description}", "a"),
            "aluguel": parse_int(item.get("aluguel")),
            "venda": parse_int(item.get("venda")),
            "iptu": 0,
            "condominio": parse_int(item.get("iptuPlusCondominium", 0)),
            "banheiros": parse_int(item.get("banheiros")),
            "quartos": parse_int(item.get("quartos")),
            "vagas": parse_int(item.get("vagas")),
            "area": parse_int(item.get("area"), -1),
            "tipo_imovel": normalize_tipo(item.get("tipo")),
            "bairro": item.get("bairro"),
            "endereco": ", ".join(filter(None, [
                item.get("estado"),
                item.get("cidade"),
                item.get("bairro"),
                item.get("rua"),
            ])),
            "lat": parse_float(item.get("lat")),
            "lon": parse_float(item.get("long")),
            "fonte": "quintoandar",
        })
    return result


def parse_vivareal(data):
    result = []
    for item in data:
        thumb = (
            [m.get("url") for m in item.get("medias", []) if m.get("type") == "IMAGE"] + [""]
        )[0].replace("action={action}&dimension={width}x{height}", "action=fit-in&dimension=870x707").replace("{description}", "a")
        urlRef = item.get("link", {}).get("href", "")
        if urlRef:
            urlRef = "https://www.vivareal.com.br" + urlRef
        pricingInfos = item.get("listing", {}).get("pricingInfos", [])
        result.append({
            "id": parse_int(item.get("listing", {}).get("id")),
            "url": urlRef,
            "thumb": thumb,
            "aluguel": parse_int(([p.get("price", 0) for p in pricingInfos if p.get("businessType") == "RENTAL"] + [0])[0]),
            "venda": parse_int(([p.get("price", 0) for p in pricingInfos if p.get("businessType") != "RENTAL"] + [0])[0]),
            "iptu": int(parse_int(([p.get("yearlyIptu", 0) for p in pricingInfos if p.get("yearlyIptu", 0)] + [0])[0]) / 12),
            "condominio": parse_int(([p.get("monthlyCondoFee", 0) for p in pricingInfos if p.get("monthlyCondoFee", 0)] + [0])[0]),
            "banheiros": parse_int(item.get("listing", {}).get("bathrooms", [0])[0]),
            "quartos": parse_int(item.get("listing", {}).get("bedrooms", [0])[0]),
            "vagas": parse_int(getFirstValue(item.get("listing", {}).get("parkingSpaces")) or 0),
            "area": parse_int(getFirstValue(item.get("listing", {}).get("totalAreas")) or getFirstValue(item.get("listing", {}).get("usableAreas")) or 0),
            "tipo_imovel": normalize_tipo(item.get("listing", {}).get("unitTypes", [None])[0]),
            "bairro": item.get("listing", {}).get("address", {}).get("neighborhood", ""),
            "endereco": ", ".join(filter(None, [
                item.get("listing", {}).get("address", {}).get("stateAcronym", ""),
                item.get("listing", {}).get("address", {}).get("city", ""),
                item.get("listing", {}).get("address", {}).get("neighborhood", ""),
                item.get("listing", {}).get("address", {}).get("street", ""),
            ])),
            "lat": parse_float(item.get("listing", {}).get("address", {}).get("point", {}).get("lat") or item.get("listing", {}).get("address", {}).get("point", {}).get("approximateLat")),
            "lon": parse_float(item.get("listing", {}).get("address", {}).get("point", {}).get("lon") or item.get("listing", {}).get("address", {}).get("point", {}).get("approximateLon")),
            "fonte": "vivareal",
        })
    return result


def parse_netimoveis(data):
    result = []
    for item in data:
        fullJson = json.loads(item.get("fulljson", "{}"))
        result.append({
            "id": parse_int(item.get("id")),
            "url": item.get("url"),
            "thumb": fullJson.get("nomeArquivoThumb", "").replace("{description}", "a"),
            "aluguel": parse_int(item.get("aluguel")),
            "venda": parse_int(item.get("venda")),
            "iptu": parse_int(fullJson.get("valorIPTU")),
            "condominio": parse_int(item.get("condominio")),
            "banheiros": parse_int(item.get("banheiros")),
            "quartos": parse_int(item.get("quartos")),
            "vagas": parse_int(item.get("vagas")),
            "area": parse_int(item.get("area"), -1),
            "tipo_imovel": normalize_tipo(fullJson.get("tipoImovel1")),
            "bairro": fullJson.get("nomeBairro", ""),
            "endereco": ", ".join(filter(None, [
                fullJson.get("nomeEstado", ""),
                fullJson.get("nomeCidade", ""),
                fullJson.get("nomeBairro", ""),
                fullJson.get("logradouroPublico", ""),
            ])),
            "lat": parse_float(item.get("lat")),
            "lon": parse_float(item.get("long")),
            "fonte": "netimoveis",
        })
    return result


def parse_zapimoveis(data):
    result = []
    for url, item in data.items():
        offers = getKey(getKey(item, "jsonGeneralData"), "offers")
        result.append({
            "id": parse_int(item.get("id")),
            "url": url,
            "thumb": (getFirstValue(getKey(item, "jsonGeneralData").get("image", [])) or "").replace("{description}", "a"),
            "aluguel": parse_int(offers.get("potentialAction", {}).get("priceSpecification", {}).get("price") if offers.get("potentialAction", {}).get("@type", "") == "RentAction" else 0),
            "venda": parse_int(offers.get("potentialAction", {}).get("priceSpecification", {}).get("price") if offers.get("potentialAction", {}).get("@type", "") == "BuyAction" else 0),
            "iptu": parse_int(item.get("iptu")),
            "condominio": parse_int(item.get("condominio")),
            "banheiros": parse_int(item.get("banheiros")),
            "quartos": parse_int(item.get("quartos")),
            "vagas": parse_int(item.get("vagas")),
            "area": parse_int(item.get("area"), -1),
            "tipo_imovel": normalize_tipo(item.get("tipoImovel")),
            "bairro": item.get("bairro"),
            "endereco": ", ".join(filter(None, [
                removeInvalidValue(getKey(item, "jsonPointData").get("address", {}).get("stateAcronym", "")),
                removeInvalidValue(getKey(item, "jsonPointData").get("address", {}).get("city", "")),
                removeInvalidValue(getKey(item, "jsonPointData").get("address", {}).get("neighborhood", "")),
                removeInvalidValue(getKey(item, "jsonPointData").get("address", {}).get("street", "")),
                removeInvalidValue(getKey(item, "jsonPointData").get("address", {}).get("streetNumber", "")),
            ])),
            "lat": parse_float(item.get("lat")),
            "lon": parse_float(item.get("lon")),
            "fonte": "zapimoveis",
        })
    return result


# ---------------------------------------------------
# Find latest file for each site in the central output dir
# ---------------------------------------------------

def _find_latest_files(output_dir: Path) -> dict[str, dict]:
    site_latest: dict[str, dict] = {}
    if not output_dir.exists():
        return site_latest
    for file in output_dir.glob("*.json"):
        match = PATTERN.match(file.name)
        if not match:
            continue
        site = match.group("site").lower()
        dt = datetime.strptime(match.group("date"), "%Y-%m-%d_%H-%M")
        if site not in site_latest or dt > site_latest[site]["date"]:
            site_latest[site] = {"date": dt, "file": file}
    return site_latest


if __name__ == "__main__":
    site_latest = _find_latest_files(CENTRAL_OUTPUT_DIR)

    print("Latest files:")
    for site, info in site_latest.items():
        print(f"  {site} -> {info['file']}")

    site_jsons: dict[str, object] = {}
    for site, info in site_latest.items():
        with open(info["file"], "r", encoding="utf-8") as f:
            site_jsons[site] = json.load(f)

    merged = []

    if "quintoandar" in site_jsons:
        merged.extend(parse_quintoandar(site_jsons["quintoandar"]))

    if "vivareal" in site_jsons:
        merged.extend(parse_vivareal(site_jsons["vivareal"]))

    if "netimoveis" in site_jsons:
        merged.extend(parse_netimoveis(site_jsons["netimoveis"]))

    # Combine aluguel + venda ZAP; also accept legacy combined file.
    zap_data: dict = {}
    for zap_key in ("zapimoveis", "zapimoveis_aluguel", "zapimoveis_venda"):
        if zap_key in site_jsons:
            zap_data.update(site_jsons[zap_key])
    if zap_data:
        merged.extend(parse_zapimoveis(zap_data))

    if "casamineira" in site_jsons:
        raw = site_jsons["casamineira"]
        merged.extend(raw if isinstance(raw, list) else [])

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
            shutil.copy(output_file_minified, dest)
            print(f"Copied to {dest}")
        except Exception as e:
            print(f"Error copying to {dest}: {e}")
