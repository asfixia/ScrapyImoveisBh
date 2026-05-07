"""Absent-value checks, numbers, dates, coordinates, and generic nested Mapping access."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Literal, TypeVar

from zap_parser.constants import ZAP_AMENITY_LABELS

T = TypeVar("T")

_RE_BRL_NUMBER = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+)")


def value_is_absent(value: object) -> bool:
    """True for None, empty sequences, and ZAP/Next sentinels on strings (not False/0)."""
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return False
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return True
        return value_is_absent(value[0])
    if isinstance(value, str):
        s = value.strip()
        if not s or s in ("$undefined", "undefined", "null", "None"):
            return True
        return False
    return False


def nested_get(obj: object, *path: str, default: T | None = None) -> object | T | None:
    """Walk Mapping keys; any step that is absent-by-ZAP-rules yields ``default``."""
    cur: object = obj
    for key in path:
        if not isinstance(cur, Mapping):
            return default
        cur = cur.get(key)
        if value_is_absent(cur):
            return default
    return cur


def strip_accents_lower(s: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", (s or "").lower().strip())
        if unicodedata.category(c) != "Mn"
    )


def clean_str(value: object) -> str | None:
    """Normalize optional string fields: sentinels and empties → None."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return None
        return clean_str(value[0])
    s = str(value).strip()
    if not s or s in ("$undefined", "undefined", "null", "None"):
        return None
    return s


def normalize_street_number(val: object) -> str:
    s = clean_str(val)
    return s if s else ""


def parse_first_int(text: str | None) -> int | None:
    if not text:
        return None
    m = _RE_BRL_NUMBER.search(text)
    if not m:
        return None
    return int(m.group(1).replace(".", ""))


def parse_int_digits(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def valid_lat_lon(lat: float, lon: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lon <= 180


def coerce_lat_lon(lat: object, lon: object) -> tuple[float, float] | None:
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None
    la, lo = float(lat), float(lon)
    if valid_lat_lon(la, lo):
        return la, lo
    return None


def zap_iso_to_datestr(s: str | None) -> str | None:
    """UTC calendar date ``YYYY-MM-DD`` from ZAP ISO timestamps."""
    if not s or not isinstance(s, str):
        return None
    t = s.strip()
    if not t:
        return None
    try:
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def timedelta_from_pt_ha_unit(n: int, unit: str) -> timedelta | None:
    if n < 0:
        return None
    u = strip_accents_lower(unit)
    if u.startswith("segund"):
        return timedelta(seconds=n)
    if u.startswith("minut"):
        return timedelta(minutes=n)
    if u.startswith("hor"):
        return timedelta(hours=n)
    if u.startswith("dia"):
        return timedelta(days=n)
    if u.startswith("seman"):
        return timedelta(weeks=n)
    if u.startswith("mes"):
        return timedelta(days=30 * n)
    if u.startswith("ano"):
        return timedelta(days=365 * n)
    return None


def datestr_from_zap_ha_relative_phrase(plain: str, kind: str) -> str | None:
    label = (kind or "").strip().lower()
    if label not in ("publicado", "atualizado"):
        return None
    m = re.search(
        rf"{label}\s+há\s+(\d+)\s+"
        r"(segundos?|minutos?|horas?|dias?|semanas?|mês|meses|anos?)",
        plain,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    n = int(m.group(1))
    td = timedelta_from_pt_ha_unit(n, m.group(2))
    if td is None:
        return None
    d = (datetime.now(timezone.utc) - td).date()
    return d.isoformat()


def detail_rsc_value_to_datestr(s: str | None) -> str | None:
    if not s or not isinstance(s, str):
        return None
    t = s.strip()
    if len(t) >= 10 and t[4] == "-" and t[7] == "-":
        return t[:10]
    return zap_iso_to_datestr(t)


def coerce_zap_detail_calendar_date(
    raw: object, *, phrase_kind: Literal["publicado", "atualizado"]
) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                return date.fromisoformat(s[:10])
            except ValueError:
                pass
        for conv in (zap_iso_to_datestr, detail_rsc_value_to_datestr):
            ds = conv(s)
            if ds:
                try:
                    return date.fromisoformat(ds)
                except ValueError:
                    pass
        ds = datestr_from_zap_ha_relative_phrase(s, phrase_kind)
        if ds:
            try:
                return date.fromisoformat(ds)
            except ValueError:
                pass
    return None


def zap_amenity_code_to_label(code: str) -> str:
    c = (code or "").strip()
    if not c:
        return ""
    return ZAP_AMENITY_LABELS.get(c, c.replace("_", " ").title())


def decode_json_string_fragment(raw: str) -> str:
    if not raw:
        return ""
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return raw.replace("\\/", "/")


def format_endereco_zap(
    street: str | None,
    numero: str | None,
    bairro: str | None,
    cidade: str | None,
    estado: str | None,
) -> str | None:
    s = (street or "").strip()
    n = (numero or "").strip() if numero else ""
    left = ", ".join(p for p in [s, n] if p)
    nei = (bairro or "").strip()
    city = (cidade or "").strip()
    uf = (estado or "").strip()
    mid = f"{left} - {nei}" if nei else left
    tail = ", ".join(p for p in [city] if p)
    if uf and tail:
        return f"{mid} - {tail} - {uf}"
    if uf:
        return f"{mid} - {uf}" if mid else uf
    if tail:
        return f"{mid} - {tail}" if mid else tail
    return mid or None


# Back-compat alias used by older imports
zap_value_is_absent = value_is_absent
zap_nested_get = nested_get
