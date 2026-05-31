@echo off
REM One-time setup: create .venv and install Scrapy + dependencies
cd /d "%~dp0"

call setEnvironment.bat

if exist ".venv\Scripts\activate.bat" (
    echo Virtual environment already exists at .venv
    echo To reinstall dependencies, run: activate_venv.bat then pip install -r requirements.txt
    exit /b 0
)

echo Creating virtual environment in .venv ...
"%PYTHON_EXE%" -m venv .venv
if errorlevel 1 (
    echo Failed to create venv.
    exit /b 1
)

echo Activating venv and installing requirements...
call .venv\Scripts\activate.bat

REM Install lxml from pre-built wheel only (no build; avoids libxml2/VS on Windows)
echo Installing lxml from wheel...
pip install lxml --only-binary lxml
if errorlevel 1 (
    echo.
    echo lxml has no pre-built wheel for this Python version on Windows.
    echo Use Python 3.12 or 3.13: in setEnvironment.bat set PYTHON_HOME to that path,
    echo delete the .venv folder, then run create_venv.bat again.
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo pip install failed.
    exit /b 1
)

REM Playwright browser for NetImoveis spider (JS-rendered listing page)
echo Installing Playwright Chromium...
.venv\Scripts\playwright.exe install chromium
if errorlevel 1 (
    echo Playwright install failed. You can run later: .venv\Scripts\playwright.exe install chromium
) else (
    echo Playwright Chromium installed.
)

echo.
echo Done. Use activate_venv.bat to activate the venv, then run getVivaRealImoveis.bat, getNetImoveis.bat etc.
