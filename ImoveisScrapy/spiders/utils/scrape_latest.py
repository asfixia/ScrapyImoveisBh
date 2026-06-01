"""Find the newest timestamped JSON export per scraper site."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from ImoveisScrapy.spiders.utils.scrape_output import output_dir

SCRAPE_JSON_PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2}_\d{2}-\d{2})_(?P<site>[a-zA-Z0-9_]+)\.json$"
)

# Not per-site scraper snapshots (merge outputs, upload temp files, etc.).
_EXCLUDED_SITES = frozenset({"imoveis_unificados", "imoveis_unificados_minified"})


class ScrapeLatestFiles:
    """Index timestamped scrape JSON files and resolve the newest file per site."""

    @staticmethod
    def scrape_output_dir() -> Path:
        return output_dir()

    @classmethod
    def find_latest_by_site(cls, directory: Path | None = None) -> dict[str, Path]:
        """Return ``site -> path`` for the newest export file per site in *directory*."""
        root = directory if directory is not None else cls.scrape_output_dir()
        site_latest: dict[str, tuple[datetime, Path]] = {}
        if not root.is_dir():
            return {}
        for file in root.glob("*.json"):
            match = SCRAPE_JSON_PATTERN.match(file.name)
            if not match:
                continue
            site = match.group("site").lower()
            if site in _EXCLUDED_SITES or site.startswith("_upload_merge_"):
                continue
            dt = datetime.strptime(match.group("date"), "%Y-%m-%d_%H-%M")
            prev = site_latest.get(site)
            if prev is None or dt > prev[0]:
                site_latest[site] = (dt, file)
        return {site: path for site, (_, path) in site_latest.items()}

    @classmethod
    def latest_for_site(cls, site: str, directory: Path | None = None) -> Path | None:
        return cls.find_latest_by_site(directory).get(site.lower())

    @classmethod
    def latest_for_provider(cls, provider: str, directory: Path | None = None) -> Path | None:
        """Resolve the newest JSON path for an upload/merge provider name."""
        provider = provider.lower()
        latest = cls.find_latest_by_site(directory)
        if provider != "zapimoveis":
            return latest.get(provider)
        if "zapimoveis" in latest:
            return latest["zapimoveis"]
        aluguel = latest.get("zapimoveis_aluguel")
        venda = latest.get("zapimoveis_venda")
        if aluguel and venda:
            return cls._merge_zap_exports(aluguel, venda, directory or cls.scrape_output_dir())
        return aluguel or venda

    @staticmethod
    def _merge_zap_exports(aluguel: Path, venda: Path, directory: Path) -> Path:
        merged: dict = {}
        for path in (aluguel, venda):
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                merged.update(payload)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        out_path = directory / f"{stamp}_zapimoveis.json"
        out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path
