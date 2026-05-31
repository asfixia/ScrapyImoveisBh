@echo off
REM Install lxml from PyPI pre-built wheel only (no build). Use if create_venv failed on lxml.
cd /d "%~dp0"

call setEnvironment.bat
if not exist ".venv\Scripts\activate.bat" (
    echo Run create_venv.bat first to create the venv.
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Installing lxml from wheel only...
pip install lxml --only-binary lxml --force-reinstall
if errorlevel 1 (
    echo.
    echo No pre-built lxml wheel for this Python on Windows.
    echo Use Python 3.12 or 3.13: set PYTHON_HOME in setEnvironment.bat,
    echo remove .venv, then run create_venv.bat again.
    exit /b 1
)
echo lxml installed from wheel.
