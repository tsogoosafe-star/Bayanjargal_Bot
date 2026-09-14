# Bayanaa Father-Style Chess Bot

## 1. Install

```bash
pip install -r requirements.txt
```

Install Stockfish and make sure `stockfish` is in PATH, or set:

```bash
export STOCKFISH_PATH=/path/to/stockfish
```

## 2. Build the style model

Put the PGN next to the scripts:

```bash
python build_style.py lichess_Bayanaa2020_2026-09-14.pgn
```

This creates:

```text
bayanaa_style.json
```

## 3. Run the bot

Set the Lichess bot token:

Linux/macOS:
```bash
export LICHESS_TOKEN="YOUR_TOKEN"
python bot.py
```

Windows PowerShell:
```powershell
$env:LICHESS_TOKEN="YOUR_TOKEN"
python bot.py
```

## Tuning

Default target:
```text
TARGET_ELO=1900
```

Useful environment variables:

- `TARGET_ELO=1850` to `1930`
- `THINK_TIME=0.65`
- `MULTIPV=8`
- `STYLE_WEIGHT=0.72`
- `STOCKFISH_PATH=/path/to/stockfish`

## Important

The builder learns only moves belonging to BAYANAA_USERNAME (default: Bayanaa2020). Override with BAYANAA_USERNAME=your_username.
The engine Elo is only a strength limit; actual Lichess rating must be measured through games.
