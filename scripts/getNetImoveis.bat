cd /d "%~dp0"
call setEnvironment.bat
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

echo to confirm one property details, run:
echo scrapy parse --spider=NetImoveis -c parse_detail "https://www.netimoveis.com/imovel/locacao-apartamento-3-quartos-minas-gerais-belo-horizonte-oeste-nova-suissa/1153135/"

cd ImoveisScrapy
scrapy crawl NetImoveis -o ./../netimoveis.json

cd %~dp0
