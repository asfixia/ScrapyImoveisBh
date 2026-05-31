@echo off
rem Run all scrapers then merge. Run from project root or scripts/.
cd /d "%~dp0.."

call scripts\getNetImoveis.bat
call scripts\getVivaRealImoveis.bat
call scripts\getZapImoveis.bat
python pipeline\merge.py
