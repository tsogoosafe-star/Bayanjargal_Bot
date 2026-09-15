@echo off
cd /d "%~dp0"

REM Paste your Lichess bot token after the equals sign below.
set "LICHESS_TOKEN=PASTE_YOUR_LICHESS_TOKEN_HERE"
set "STYLE_MODEL=bayanaa_style_1000.json"
set "STOCKFISH_PATH=%~dp0stockfish.exe"

python bot.py
pause
