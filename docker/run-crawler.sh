#!/bin/sh
set -e

SCRAPE_OUTPUT_DIR="${SCRAPE_OUTPUT_DIR:-/data}"
export SCRAPE_OUTPUT_DIR
mkdir -p "$SCRAPE_OUTPUT_DIR"

usage() {
  echo "Usage: $0 <crawler>"
  echo "  netimoveis | vivareal | quintoandar | casamineira | zap"
  exit 1
}

[ -n "$1" ] || usage

cd /app

case "$1" in
  netimoveis)
    exec python -m scrapy crawl NetImoveis
    ;;
  vivareal)
    exec python -m scrapy crawl VivaReal
    ;;
  quintoandar)
    exec python -m scrapy crawl QuintoAndar
    ;;
  casamineira)
    exec python -m scrapy crawl CasaMineira
    ;;
  zap)
    exec python ImoveisScrapy/spiders/zapimoveis_scrapy.py
    ;;
  *)
    echo "Unknown crawler: $1"
    usage
    ;;
esac
