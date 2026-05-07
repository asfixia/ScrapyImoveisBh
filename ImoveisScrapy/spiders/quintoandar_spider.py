# -*- coding: utf-8 -*-
import scrapy
import json
from pathlib import Path
from datetime import datetime
from logging import getLogger
LOG = getLogger(__name__)

from quintoandar_botasaurus_client import quintoandar_get_items


class QuintoAndarSpider(scrapy.Spider):
    name = "QuintoAndar"
    allowed_domains = ["www.quintoandar.com.br", "apigw.prod.quintoandar.com.br"]
    custom_settings = {"ROBOTSTXT_OBEY": False}

    def start_requests(self):
        all_imv_data = quintoandar_get_items()
        for imv_data in all_imv_data.values():
            yield imv_data
