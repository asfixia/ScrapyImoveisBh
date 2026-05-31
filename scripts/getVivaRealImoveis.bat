cd /d "%~dp0"
call setEnvironment.bat
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

cd ImoveisScrapy
set PATH=F:\Danilo\Programacao\python\ImoveisScrapy\ImoveisScrapy\exe\;C:\Program Files\Mozilla Firefox\;%PATH%

scrapy crawl VivaReal -o ./../vivareal.json

cd %~dp0