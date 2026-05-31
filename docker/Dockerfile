FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    SCRAPE_OUTPUT_DIR=/data \
    CHROME_PATH=/usr/bin/chromium \
    CHROMIUM_PATH=/usr/bin/chromium \
    BOTASAURUS_CHROME_PATH=/usr/bin/chromium

WORKDIR /app

# System deps: pgrep (main_update_data.py), Chromium (Botasaurus), libs for Scrapy/lxml
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        procps \
        chromium \
        chromium-driver \
        fonts-liberation \
        libnss3 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcups2 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libxss1 \
        libasound2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main_update_data.py scrapy.cfg ./
COPY pipeline ./pipeline
COPY ImoveisScrapy ./ImoveisScrapy
COPY docker ./docker

RUN chmod +x /app/docker/entrypoint.sh /app/docker/run-crawler.sh

VOLUME ["/data", "/app/logs"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
