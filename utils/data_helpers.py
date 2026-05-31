"""Shared data-parsing and normalization helpers used across scrapers and pipeline."""
from __future__ import annotations


def parse_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(".", "").replace(",", "")
        return int(float(value))
    except Exception:
        return default


def parse_float(value, default=None):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace(",", ".")
        return float(value)
    except Exception:
        return default


def getFirstValue(value, default=None):
    if value is None:
        return default
    if not isinstance(value, list):
        return value
    if len(value) == 0:
        return default
    return value[0]


def removeInvalidValue(value):
    if value is None:
        return None
    s = str(value)
    if s.lower() in ("undefined", "null", "none", ""):
        return None
    return value


def getKey(obj, key, default=None):
    if default is None:
        default = {}
    if not isinstance(obj, dict):
        return default
    result = obj.get(key)
    return result if result else default


def normalize_tipo(tipo) -> str:
    if not tipo:
        return "Outro"

    casa = {
        "triplex", "casa", "two_story_house", "casacondominio", "home", "casas",
        "single_storey_house", "village_house", "farm",
        "allotment_land", "residential_allotment_land",
    }
    apartamento = {
        "apartamento", "apartment", "condominium", "flat", "studio", "apartamentos",
        "studiooukitchenette", "kitnet", "loft", "duplex", "penthouse",
    }

    for token in str(tipo).lower().split():
        if token in casa:
            return "Casa"
        if token in apartamento:
            return "Apartamento"

    return "Outro"
