cd /d "%~dp0"
call setEnvironment.bat
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

rem cd ImoveisScrapy
rem scrapy crawl ZapImoveis -o ./../zapimoveis.json


python zap_botasaurus_client.py 
