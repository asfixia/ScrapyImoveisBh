@echo off
REM Activate the project venv (use this before running scrapy or other scripts)
cd /d "%~dp0"

call setEnvironment.bat

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Run create_venv.bat first.
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Venv activated. Python: 
python --version
echo.
cmd /k
