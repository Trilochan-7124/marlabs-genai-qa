@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" -m evaluator.evaluator %*
exit /b %errorlevel%