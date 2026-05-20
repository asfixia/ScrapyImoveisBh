FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SCRAPE_OUTPUT_DIR=/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrape_output.py scrape_output.py
COPY scrapy.cfg .
COPY zap_parser ./zap_parser
COPY zap_botasaurus_client.py quintoandar_botasaurus_client.py ./
COPY docker ./docker
COPY ImoveisScrapy ./ImoveisScrapy

RUN chmod +x /app/docker/run-crawler.sh

ENTRYPOINT ["/app/docker/run-crawler.sh"]
CMD ["netimoveis"]
