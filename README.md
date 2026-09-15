# bayanjargal_bot — Bayanaa2020 style

This folder is configured for the existing Windows Start-bot workflow.

## 1. Install
```bat
pip install -r requirements.txt
```

## 2. Configure
Open `start_bot.bat` and replace:
```bat
set "LICHESS_TOKEN=PASTE_YOUR_LICHESS_TOKEN_HERE"
```
with the token of the `bayanjargal_bot` account.

Keep the token out of GitHub.

## 3. Run
Double-click `start_bot.bat`.

The bot uses:
- `bayanaa_style_1000.json` — profile built from Bayanaa2020 games 1–1000
- `stockfish.exe` — Stockfish engine
- `bot.py` — Lichess bot logic

## Notes
This is a Stockfish + learned-move-distribution style bot, not a neural network clone.
