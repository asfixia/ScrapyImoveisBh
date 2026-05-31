"""ZAP map viewport and listing metadata models."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date
import math

from scrapers.zap.parser.normalizers import clean_str, coerce_zap_detail_calendar_date


def _format_endereco_line(parts: tuple[str | None, ...]) -> str:
    acc = ""
    for v in parts:
        if v:
            acc = f"{acc}, {v}" if acc else str(v)
    return acc


@dataclass(frozen=True, slots=True)
class ZapMapViewport:
    """ZAP ``viewport`` query: ``maxX,maxY|minX,minY`` (high corner before ``|``)."""

    maxX: float
    maxY: float
    minX: float
    minY: float

    @classmethod
    def from_string(cls, viewport_str: str) -> ZapMapViewport:
        parts = re.split(r"[,;|]", viewport_str)
        if len(parts) != 4:
            raise ValueError(
                f"ZapMapViewport.from_string: expected 4 numbers, got {len(parts)} segment(s)"
            )
        a, b, c, d = (float(x) for x in parts)
        return cls(a, b, c, d)

    def as_query_string(self) -> str:
        return f"{self.maxX},{self.maxY}|{self.minX},{self.minY}"

    def _best_grid(self, divide_grid_size_by):
        aspect = self.get_width() / self.get_height()
        best_nx, best_ny = 1, divide_grid_size_by
        best_error = float("inf")

        for nx in range(1, divide_grid_size_by + 1):
            if divide_grid_size_by % nx != 0:
                continue

            ny = divide_grid_size_by // nx
            ratio = nx / ny
            error = abs(ratio - aspect)

            if error < best_error:
                best_error = error
                best_nx, best_ny = nx, ny

        return best_nx, best_ny

    def get_width(self) -> float:
        return self.maxX - self.minX
    
    def get_height(self) -> float:
        return self.maxY - self.minY

    def split_grid(self, divide_grid_size_by: int) -> list[ZapMapViewport]:
        if divide_grid_size_by < 1:
            raise ValueError("divide_grid_size_by must be >= 1")
        divide_grid_size_by = math.ceil(divide_grid_size_by)
        nx, ny = self._best_grid(divide_grid_size_by)
        dx = self.get_width() / nx
        dy = self.get_height() / ny

        rectangles = []
        for i in range(nx):
            for j in range(ny):
                x0 = self.minX + i * dx
                x1 = self.minX + (i + 1) * dx if i < nx - 1 else self.maxX
                y0 = self.minY + j * dy
                y1 = self.minY + (j + 1) * dy if j < ny - 1 else self.maxY
                rectangles.append(ZapMapViewport(x1, y1, x0, y0))
        return rectangles

        #if divide_grid_size_by < 1:
        #    raise ValueError("divide_grid_size_by must be >= 1")
        #n = divide_grid_size_by
        #grid_size_x = (self.maxX - self.minX) / n
        #grid_size_y = (self.maxY - self.minY) / n
        #last = n - 1
        #out: list[ZapMapViewport] = []
        #for i in range(n):
        #    for j in range(n):
        #        lo_x = self.minX + i * grid_size_x
        #        lo_y = self.minY + j * grid_size_y
        #        hi_x = self.maxX if i == last else self.minX + (i + 1) * grid_size_x
        #        hi_y = self.maxY if j == last else self.minY + (j + 1) * grid_size_y
        #        out.append(ZapMapViewport(hi_x, hi_y, lo_x, lo_y))
        #return out


@dataclass(slots=True)
class ZapDetailPageMetadata:
    """Listing fields for list cards and detail enrichment."""

    aluguel: int | None
    amenidades: list[str] | None
    andares: int | None
    area: int | None
    atualizadoHa: date | None
    bairro: str | None
    banheiros: int | None
    cidade: str | None
    compra: int | None
    condominio: int | None
    detailsUrl: str | None
    enderecoNumero: str | None
    enderecoRua: str | None
    estado: str | None
    externalId: str | None
    fotos: list[str] | None
    geoSource: str | None
    id: str | None
    iptu: int | None
    isAbsoluteLocation: bool | None
    jsonDetailsData: dict | None
    jsonGeneralData: dict | None
    jsonPointData: dict | None
    lat: float | None
    locationId: str | None
    lon: float | None
    publicadoHa: date | None
    quartos: int | None
    tipoImovel: str | None
    vagas: int | None
    fullJsonData: dict | None

    @staticmethod
    def replace_undefined_str(value: object) -> str | None:
        return clean_str(value)

    def set_location_id(self, value: object) -> None:
        object.__setattr__(
            self,
            "locationId",
            ZapDetailPageMetadata.replace_undefined_str(value),
        )

    @property
    def endereco(self) -> str:
        return _format_endereco_line(
            (self.enderecoRua, self.enderecoNumero, self.bairro, self.cidade, self.estado)
        )

    def merge(self, other: ZapDetailPageMetadata | None) -> ZapDetailPageMetadata:
        """Field-wise coalesce: keep ``self`` when not ``None``; else ``other``. ``other`` may be ``None``."""
        if other is None:
            return self
        merged: dict[str, object] = {}
        for f in fields(self):
            name = f.name
            a = getattr(self, name)
            b = getattr(other, name)
            merged[name] = a if a is not None else b
        return ZapDetailPageMetadata(**merged)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "publicadoHa",
            coerce_zap_detail_calendar_date(self.publicadoHa, phrase_kind="publicado"),
        )
        object.__setattr__(
            self,
            "atualizadoHa",
            coerce_zap_detail_calendar_date(self.atualizadoHa, phrase_kind="atualizado"),
        )
        object.__setattr__(
            self,
            "locationId",
            ZapDetailPageMetadata.replace_undefined_str(self.locationId),
        )

    def hasMissingDetails(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, date):
                out[f.name] = v.isoformat()
            else:
                out[f.name] = v
        return out

    @classmethod
    def field_names(cls) -> frozenset[str]:
        return frozenset(f.name for f in fields(cls))

    @classmethod
    def from_mapping(cls, data: Mapping[str, object], *, strict: bool = True) -> ZapDetailPageMetadata:
        allowed = cls.field_names()
        keys = frozenset(data.keys())
        if strict:
            unknown = keys - allowed
            if unknown:
                raise TypeError(
                    "ZapDetailPageMetadata: unknown field(s) "
                    f"{sorted(unknown)}; allowed {sorted(allowed)}"
                )
        missing = allowed - keys
        if missing:
            raise TypeError(
                "ZapDetailPageMetadata: missing field(s) " f"{sorted(missing)}"
            )
        return cls(**{name: data[name] for name in allowed})
