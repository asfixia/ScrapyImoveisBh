@echo off
cd /d "%~dp0"
call setEnvironment.bat
if exist "..\venv\Scripts\activate.bat" call "..\venv\Scripts\activate.bat"

cd /d "%~dp0.."
python -m scrapy crawl NetImoveis
