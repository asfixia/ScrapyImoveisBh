# ScrapyImoveisBh

Scrapers for real-estate listings in Belo Horizonte and region. Each crawler runs independently and writes a JSON file named with a timestamp and the site name.

## Crawlers

| Site | How to run (local) | Output file suffix |
|------|--------------------|--------------------|
| Net Imóveis | `scrapy crawl NetImoveis` | `_netimoveis.json` |
| Viva Real | `scrapy crawl VivaReal` | `_vivareal.json` |
| Quinto Andar | `scrapy crawl QuintoAndar` | `_quintoandar.json` |
| Casa Mineira | `scrapy crawl CasaMineira` | `_casamineira.json` |
| ZAP Imóveis | `python zap_botasaurus_client.py` | `_zapimoveis.json` |

Example output files:

```text
2026-05-13_01-48_casamineira.json
2026-05-09_23-08_netimoveis.json
2026-05-11_02-59_quintoandar.json
```

By default, files are written to the **current working directory**. Set `SCRAPE_OUTPUT_DIR` to change that (used by Docker and optional locally).

---

## Requirements

- Python **3.12+** recommended
- Dependencies: `requirements.txt` (Scrapy, Botasaurus, requests, BeautifulSoup, etc.)

---

## Windows setup

1. Configure Python in `setEnvironment.bat` if needed.
2. Create the virtual environment and install packages:

   ```bat
   create_venv.bat
   ```

3. Activate the venv (opens a new cmd with venv active):

   ```bat
   activate_venv.bat
   ```

4. Run crawlers from the project root, or use **VS Code** launch configs in `.vscode/launch.json` (Scrapy netimoveis, vivareal, quintoandar, casamineira, zap).

---

## Linux / macOS setup

Install Python 3 and the venv module if needed:

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

From the project root:

```bash
chmod +x create_venv.sh activate_venv.sh
./create_venv.sh

source ./activate_venv.sh
```

Reinstall from scratch:

```bash
rm -rf .venv && ./create_venv.sh
```

Use a specific Python:

```bash
PYTHON=python3.12 ./create_venv.sh
```

### Run crawlers (venv active)

```bash
scrapy crawl NetImoveis
scrapy crawl VivaReal
scrapy crawl QuintoAndar
scrapy crawl CasaMineira
python zap_botasaurus_client.py
```

### Optional: write JSON to `./output`

```bash
export SCRAPE_OUTPUT_DIR="$(pwd)/output"
mkdir -p "$SCRAPE_OUTPUT_DIR"
scrapy crawl NetImoveis
```

---

## Docker

Each crawler is a separate Compose service. JSON files are saved under **`./output`** on the host.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose plugin) running.

```bash
# Build image once
docker compose build

# Run one crawler
docker compose run --rm netimoveis
docker compose run --rm vivareal
docker compose run --rm quintoandar
docker compose run --rm casamineira
docker compose run --rm zap
```

Run several in sequence:

```bash
docker compose run --rm netimoveis && \
docker compose run --rm vivareal && \
docker compose run --rm quintoandar && \
docker compose run --rm casamineira && \
docker compose run --rm zap
```

Results appear in `output/`, for example:

```text
output/2026-05-20_14-30_netimoveis.json
```

---

## VS Code debugging

Use the predefined configurations in `.vscode/launch.json`:

- **Scrapy netimoveis** / **vivareal** / **quintoandar** / **casamineira** — `scrapy crawl …`
- **Scrapy zapimoveis** — runs `zap_botasaurus_client.py`
- **Upload zap_imoveis to db** — `upload_zap_to_db.py` (needs PostgreSQL)

Docker is best for repeatable runs and scheduling; **launch.json** is best for breakpoints and local debugging.

---

## Project layout (main parts)

```text
ImoveisScrapy/spiders/     Scrapy spiders
zap_botasaurus_client.py   ZAP (Botasaurus)
quintoandar_botasaurus_client.py
zap_parser/                ZAP HTML/JSON parsing
scrape_output.py           Shared output path helper
requirements.txt
create_venv.sh / create_venv.bat
docker-compose.yml
output/                    JSON output (Docker + optional local)
```

---

## Upload to database

After scraping, load JSON into PostgreSQL with `upload_zap_to_db.py` (see launch config **Upload zap_imoveis to db** for example arguments).
