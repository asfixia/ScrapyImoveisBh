import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent

PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2}_\d{2}-\d{2})_(?P<site>[a-zA-Z0-9_]+)\.json$"
)

# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def parse_int(value, default=0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace(".", "").replace(",", "")

        return int(float(value))
    except:
        return default

def removeInvalidValue(value):
    if value is None or "undefined" in value.lower() or value == "null" or value == "None" or value == "":
        return None
    return value

def getFirstValue(value, default=None):
    if value is None:
        return default
    if not isinstance(value, list):
        return value
    if len(value) == 0:
        return default
    return value[0]

def parse_float(value, default=None):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace(",", ".")

        return float(value)
    except:
        return default


def normalize_tipo(tipo):
    if not tipo:
        return "Outro"
    
    casa = {
        'triplex','casa','two_story_house','casacondominio','home',
        'single_storey_house','village_house','farm',
        'allotment_land','residential_allotment_land'
    }

    apartamento = {
        'apartamento','apartment','condominium','flat','studio',
        'studiooukitchenette','kitnet','loft','duplex','penthouse'
    }

    for curTipo in str(tipo).lower().split(" "):
        if curTipo in casa:
            return "Casa"

        if curTipo in apartamento:
            return "Apartamento"

    return "Outro"

# ---------------------------------------------------
# Parsers
# ---------------------------------------------------

def parse_quintoandar(data):
    result = []

    for id, item in data.items():
        full_json = item

        result.append({
            "id": parse_int(id),
            "url": item.get("url"),
            "thumb": item.get("thumb"),
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
        thumb = ([media.get("url") for media in item.get("medias", []) if media.get("type") == "IMAGE"] + [""])[0]
        urlRef = (item.get("link", {}).get("href", ""))
        if urlRef:
            urlRef = "https://www.vivareal.com.br" + urlRef
        pricingInfos = item.get("listing", {}).get("pricingInfos", [])

        result.append({
            "id": parse_int(item.get("listing", {}).get("id")),
            "url": urlRef,
            "thumb": thumb,
            "aluguel": parse_int(([price.get("price", 0) for price in pricingInfos if price.get("businessType") == "RENTAL"] + [0])[0]),
            "venda": parse_int(([price.get("price", 0) for price in pricingInfos if price.get("businessType") != "RENTAL"] + [0])[0]),
            "iptu": int(parse_int(([price.get("yearlyIptu", 0) for price in pricingInfos if price.get("yearlyIptu", 0) != 0] + [0])[0]) / 12),
            "condominio": parse_int(([price.get("monthlyCondoFee", 0) for price in pricingInfos if price.get("monthlyCondoFee", 0) != 0] + [0])[0]),
            "banheiros": parse_int(item.get("listing", {}).get("bathrooms", [0])[0]),
            "quartos": parse_int(item.get("listing", {}).get("bedrooms", [0])[0]),
            "vagas": parse_int(getFirstValue(item.get("listing", {}).get("parkingSpaces", None)) or 0),
            "area": parse_int(getFirstValue(item.get("listing", {}).get("totalAreas", None)) or getFirstValue(item.get("listing", {}).get("usableAreas", None)) or 0),
            "tipo_imovel": normalize_tipo(item.get("listing", {}).get("unitTypes", [None])[0]),
            "bairro": item.get("listing", {}).get("address", {}).get("neighborhood", ""),
            "endereco": ", ".join(filter(None, [
                item.get("listing", {}).get("address", {}).get("stateAcronym", ""),
                item.get("listing", {}).get("address", {}).get("city", ""),
                item.get("listing", {}).get("address", {}).get("neighborhood", ""),
                item.get("listing", {}).get("address", {}).get("street", ""),
            ])),
            "lat": parse_float(item.get("listing", {}).get("address", {}).get("point", {}).get("lat", 0)),
            "lon": parse_float(item.get("listing", {}).get("address", {}).get("point", {}).get("lon", 0)),
            "fonte": "vivareal"
        })

    return result


def parse_netimoveis(data):
    result = []

    for item in data:
        fullJson = json.loads(item.get("fulljson", "{}"))

        result.append({
            "id": parse_int(item.get("id")),
            "url": item.get("url"),
            "thumb": fullJson.get("nomeArquivoThumb", ""),
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
            "fonte": "netimoveis"
        })

    return result
    

def parse_zapimoveis(data):
    result = []

    for url, item in data.items():
        offers = item.get("jsonGeneralData", {}).get("offers", {})

        result.append({
            "id": parse_int(item.get("id")),
            "url": url,
            "thumb": getFirstValue(item.get("jsonGeneralData", {}).get("image", [])) or "",
            "aluguel": parse_int(offers.get("potentialAction", {}).get("priceSpecification", {}).get("price", None) if offers.get("potentialAction", {}).get("@type", "") == "RentAction" else 0),
            "venda": parse_int(offers.get("potentialAction", {}).get("priceSpecification", {}).get("price", None) if offers.get("potentialAction", {}).get("@type", "") == "BuyAction" else 0),
            "iptu": parse_int(item.get("iptu")),
            "condominio": parse_int(item.get("condominio")),
            "banheiros": parse_int(item.get("banheiros")),
            "quartos": parse_int(item.get("quartos")),
            "vagas": parse_int(item.get("vagas")),
            "area": parse_int(item.get("area"), -1),
            "tipo_imovel": normalize_tipo(item.get("tipoImovel")),
            "bairro": item.get("bairro"),
            "endereco": ", ".join(filter(None, [
                removeInvalidValue(item.get("jsonPointData", {}).get("address", {}).get("stateAcronym", "")),
                removeInvalidValue(item.get("jsonPointData", {}).get("address", {}).get("city", "")),
                removeInvalidValue(item.get("jsonPointData", {}).get("address", {}).get("neighborhood", "")),
                removeInvalidValue(item.get("jsonPointData", {}).get("address", {}).get("street", "")),
                removeInvalidValue(item.get("jsonPointData", {}).get("address", {}).get("streetNumber", "")),
            ])),
            "lat": parse_float(item.get("lat")),
            "lon": parse_float(item.get("lon")),
            "fonte": "zapimoveis"
        })

    return result

# ---------------------------------------------------
# Find latest file for each site
# ---------------------------------------------------

site_latest = {}

for file in PROJECT_ROOT.glob("*.json"):
    match = PATTERN.match(file.name)

    if not match:
        continue

    site = match.group("site").lower()

    dt = datetime.strptime(
        match.group("date"),
        "%Y-%m-%d_%H-%M"
    )

    if site not in site_latest or dt > site_latest[site]["date"]:
        site_latest[site] = {
            "date": dt,
            "file": file
        }

print("Latest files:")
for site, info in site_latest.items():
    print(site, "->", info["file"].name)

# ---------------------------------------------------
# Load JSONs
# ---------------------------------------------------

site_jsons = {}

for site, info in site_latest.items():
    with open(info["file"], "r", encoding="utf-8") as curFile:
        site_jsons[site] = json.load(curFile)


# ---------------------------------------------------
# Merge all
# ---------------------------------------------------

merged = []

if "quintoandar" in site_jsons:
    merged.extend(parse_quintoandar(site_jsons["quintoandar"]))

if "vivareal" in site_jsons:
    merged.extend(parse_vivareal(site_jsons["vivareal"]))

if "netimoveis" in site_jsons:
    merged.extend(parse_netimoveis(site_jsons["netimoveis"]))

if "zapimoveis" in site_jsons:
    merged.extend(parse_zapimoveis(site_jsons["zapimoveis"]))

print(f"\nMerged properties: {len(merged)}")

# ---------------------------------------------------
# Save merged
# ---------------------------------------------------

output_file = PROJECT_ROOT / "imoveis_unificados.json"
with open(output_file, "w", encoding="utf-8") as curFile:
    json.dump(merged, curFile, ensure_ascii=False, indent=2)
print(f"Saved: {output_file}")


output_file_minified = PROJECT_ROOT / "imoveis_unificados_minified.json"
with open(output_file_minified, "w", encoding="utf-8") as curFile:
    json.dump(merged, curFile, ensure_ascii=False, separators=(",", ":"))
print(f"Saved: {output_file_minified}")


