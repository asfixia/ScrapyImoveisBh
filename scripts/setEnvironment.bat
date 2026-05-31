@echo off
REM Set Python 3.13 environment variables

set "PYTHON_HOME=E:\Danilo\Programacao\python313"
set "PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;%PYTHON_HOME%\DLLs;%PATH%"

REM Optional: explicit paths for scripts that might use them
set "PYTHON_EXE=%PYTHON_HOME%\python.exe"
set "PIP_EXE=%PYTHON_HOME%\Scripts\pip.exe"

REM MinGW for building C/C++ extensions (e.g. lxml) instead of MSVC
set "MINGW_HOME=C:\MinGW"
set "PATH=%MINGW_HOME%\bin;%PATH%"
set "CC=%MINGW_HOME%\bin\gcc.exe"
set "CXX=%MINGW_HOME%\bin\mingw32-c++.exe"

REM Node.js for MCP (Playwright), npx, etc.
set "NODE_HOME=E:\Danilo\Programas\NodeJs\node-v20.20.0-win-x64"
set "PATH=%NODE_HOME%;%NODE_HOME%\node_modules\npm\bin;%PATH%"
set "NODE_EXE=%NODE_HOME%\node.exe"
set "NPM_EXE=%NODE_HOME%\npm.cmd"
set "NPX_EXE=%NODE_HOME%\npx.cmd"

echo Python environment set.
echo PYTHON_HOME=%PYTHON_HOME%
echo PYTHON_EXE=%PYTHON_EXE%
echo CC=%CC%
echo CXX=%CXX%
echo NODE_HOME=%NODE_HOME%
echo NODE_EXE=%NODE_EXE%
