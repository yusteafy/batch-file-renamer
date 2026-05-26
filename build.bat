@echo off
cd /d "%~dp0"
uv run pyinstaller main.spec
pause