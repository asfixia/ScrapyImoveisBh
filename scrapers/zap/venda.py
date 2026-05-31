"""ZAP Imóveis — venda scraper entry point."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as a script
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from botasaurus.request import Request, request

from scrapers.zap.client import _scrape_zap_transaction
from scrapers.zap.parser import TRANSACAO_VENDA
from utils.scrape_output import output_json_path

LOG = logging.getLogger(__name__)


@request(max_retry=5)
def zap_venda(request_obj: Request, data=None):
    """Botasaurus @request: scrape ZAP venda listings for BH and write JSON output."""
    imv_data = _scrape_zap_transaction(request_obj, TRANSACAO_VENDA)
    imv_data_json = {url: imv.to_dict() for url, imv in imv_data.items()}

    out_path = output_json_path("zapimoveis_venda")
    out_path.write_text(
        json.dumps(imv_data_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LOG.info("[ZAP venda] wrote %s listing(s) to %s", len(imv_data_json), out_path)
    return imv_data_json


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    zap_venda()
