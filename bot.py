"""
Bayanaa Father-Style Lichess Bot

Install:
    pip install -r requirements.txt

Environment:
    LICHESS_TOKEN=your_bot_token

Files:
    bayanaa_style.json  (created by build_style.py)
    stockfish executable available in PATH or STOCKFISH_PATH

Run:
    python bot.py
"""

import os
import json
import time
import random
import threading
from pathlib import Path
from collections import Counter

import chess
import chess.engine
import berserk
from flask import Flask

MODEL_FILE = Path(os.getenv("STYLE_MODEL", "bayanaa_style_1000.json"))
TARGET_ELO = int(os.getenv("TARGET_ELO", "1900"))
STYLE_WEIGHT = float(os.getenv("STYLE_WEIGHT", "0.72"))
BOOK_WEIGHT = float(os.getenv("BOOK_WEIGHT", "1.0"))
THINK_TIME = float(os.getenv("THINK_TIME", "0.65"))
MULTIPV = int(os.getenv("MULTIPV", "8"))
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", str(Path(__file__).with_name("stockfish.exe")))

# -------------------- health server --------------------

app = Flask(__name__)

@app.get("/")
def home():
    return "Bayanaa Father-Style Bot is online."

def run_web():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# -------------------- model --------------------

if not MODEL_FILE.exists():
    raise FileNotFoundError(
        f"{MODEL_FILE} not found. Run: "
        f"python build_style.py your_games.pgn"
    )

MODEL = json.loads(MODEL_FILE.read_text(encoding="utf-8"))
BOOK = MODEL.get("book", {})
STYLE = MODEL.get("style", {})
PHASE_STYLE = MODEL.get("phase_style", {})

def pos_key(board):
    return " ".join(board.fen().split()[:4])

def phase(board):
    pieces = len(board.piece_map())
    if pieces >= 26:
        return "opening"
    if pieces >= 12:
        return "middlegame"
    return "endgame"

def safe_ratio(value, total):
    return value / total if total else 0.0

def feature_vector(board, move):
    san = board.san(move)
    mover = board.piece_at(move.from_square)
    captured = board.piece_at(move.to_square)
    p = phase(board)
    return {
        "piece": chess.piece_name(mover.piece_type) if mover else "unknown",
        "capture": bool(board.is_capture(move)),
        "promotion": bool(move.promotion),
        "castle": board.is_castling(move),
        "check": "+" in san or "#" in san,
        "san": san,
        "from_file": chess.square_file(move.from_square),
        "to_file": chess.square_file(move.to_square),
        "from_rank": chess.square_rank(move.from_square),
        "to_rank": chess.square_rank(move.to_square),
        "captured_piece": chess.piece_name(captured.piece_type) if captured else None,
        "phase": p,
    }

def style_score(board, move):
    """
    Score how much a candidate resembles the learned move distribution.
    Exact position memory dominates. General style is a softer fallback.
    """
    key = pos_key(board)
    uci = move.uci()
    exact = BOOK.get(key, {})
    exact_total = sum(exact.values())
    exact_prob = safe_ratio(exact.get(uci, 0), exact_total)

    feat = feature_vector(board, move)
    pstyle = PHASE_STYLE.get(feat["phase"], {})
    score = 0.0

    # Exact-position imitation is strongest.
    score += 7.0 * exact_prob

    # General tendencies learned from the PGN.
    total_moves = max(1, pstyle.get("moves_seen", MODEL.get("moves_seen", 1)))
    for k, v in feat.items():
        if isinstance(v, bool) and v:
            score += 0.35 * safe_ratio(pstyle.get(k, 0), total_moves)
        elif isinstance(v, str) and v:
            score += 0.20 * safe_ratio(pstyle.get(f"{k}:{v}", 0), total_moves)

    # Encourage moves seen in the same position, but do not force them.
    if uci in exact:
        score += 2.0 * safe_ratio(exact[uci], max(exact_total, 1))

    return score

# -------------------- engine --------------------

ENGINE = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
try:
    ENGINE.configure({
        "UCI_LimitStrength": True,
        "UCI_Elo": max(1350, min(2200, TARGET_ELO)),
    })
except Exception as e:
    print("Could not set UCI Elo; continuing:", e)

ENGINE_LOCK = threading.Lock()

def choose_move(board):
    legal = list(board.legal_moves)
    if not legal:
        return None

    # Opening / exact memory: imitate the father's actual choices.
    exact = BOOK.get(pos_key(board), {})
    if exact:
        candidates = [(m, exact.get(m.uci(), 0)) for m in legal if m.uci() in exact]
        if candidates:
            # Keep some variety, but strongly favor the most common move.
            moves, weights = zip(*candidates)
            return random.choices(moves, weights=weights, k=1)[0]

    # Outside the book: ask Stockfish for several good moves, then rank
    # them by a blend of engine quality and learned father-style similarity.
    with ENGINE_LOCK:
        infos = ENGINE.analyse(
            board,
            chess.engine.Limit(time=THINK_TIME),
            multipv=min(MULTIPV, len(legal)),
        )

    if not isinstance(infos, list):
        infos = [infos]

    scored = []
    for info in infos:
        move = info["pv"][0]
        score = info["score"].pov(board.turn).score(mate_score=100000)
        normalized_engine = max(-1000, min(1000, score)) / 1000.0
        s_score = style_score(board, move)
        final = normalized_engine + STYLE_WEIGHT * s_score
        scored.append((final, move, score, s_score))

    scored.sort(reverse=True, key=lambda x: x[0])

    # Small temperature gives natural variation without random blunders.
    top = scored[:min(3, len(scored))]
    weights = [max(0.01, 1.0 / (i + 1)) for i in range(len(top))]
    chosen = random.choices(top, weights=weights, k=1)[0]

    print("Candidates:")
    for final, move, eng, sty in scored[:5]:
        print(f"  {move.uci()} engine={eng} style={sty:.4f} final={final:.4f}")
    print("Chosen:", chosen[1].uci())

    return chosen[1]

# -------------------- lichess --------------------

TOKEN = os.getenv("LICHESS_TOKEN")
if not TOKEN:
    raise RuntimeError("Set LICHESS_TOKEN in your environment.")

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)
BOT_USERNAME = client.account.get()["username"].lower()
print(f"Connected as {BOT_USERNAME}")

def play_game(game_id):
    board = chess.Board()
    greeted = False
    finished = False
    is_white = None
    is_black = None

    try:
        for state in client.bots.stream_game_state(game_id):
            kind = state.get("type")

            if kind == "gameFull":
                white = state.get("white", {}).get("id", "").lower()
                black = state.get("black", {}).get("id", "").lower()
                is_white = white == BOT_USERNAME
                is_black = black == BOT_USERNAME
                initial = state.get("state", {})
                moves = initial.get("moves", "").split()
                board.reset()
                for uci in moves:
                    board.push_uci(uci)

            elif kind == "gameState":
                moves = state.get("moves", "").split()
                board.reset()
                for uci in moves:
                    board.push_uci(uci)

            else:
                continue

            if not greeted and len(list(board.move_stack)) <= 2:
                try:
                    client.bots.chat(game_id, "player",
                                     "Hello! Good luck, have fun!")
                except Exception as e:
                    print("Greeting error:", e)
                greeted = True

            if board.is_game_over():
                if not finished:
                    try:
                        client.bots.chat(
                            game_id, "player",
                            "Thank you for the game. Let's play again!"
                        )
                    except Exception as e:
                        print("End chat error:", e)
                    finished = True
                break

            my_turn = (
                (board.turn == chess.WHITE and is_white) or
                (board.turn == chess.BLACK and is_black)
            )
            if my_turn:
                time.sleep(0.35)
                move = choose_move(board)
                if move:
                    uci = move.uci()
                    sent = False
                    for attempt in range(1, 4):
                        try:
                            client.bots.make_move(game_id, uci)
                            print("Played:", uci)
                            sent = True
                            break
                        except Exception as e:
                            print(f"Move error (attempt {attempt}/3):", e)
                            if attempt < 3:
                                time.sleep(1.5 * attempt)
                    if not sent:
                        print("Could not send move after 3 attempts:", uci)

    except Exception as e:
        print(f"Game stream error {game_id}:", e)

def event_loop():
    while True:
        try:
            for event in client.bots.stream_incoming_events():
                kind = event.get("type")
                if kind == "challenge":
                    challenge = event["challenge"]
                    cid = challenge["id"]
                    try:
                        client.bots.accept_challenge(cid)
                        print("Accepted challenge:", cid)
                    except Exception as e:
                        print("Challenge error:", e)
                elif kind == "gameStart":
                    gid = event["game"]["id"]
                    threading.Thread(
                        target=play_game, args=(gid,), daemon=True
                    ).start()
        except Exception as e:
            print("Event stream error:", e)
            time.sleep(5)

threading.Thread(target=event_loop, daemon=True).start()

if __name__ == "__main__":
    # Flask is already running in the background.
    while True:
        time.sleep(3600)
