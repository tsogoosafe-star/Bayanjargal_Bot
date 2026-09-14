"""
Build Bayanaa's chess style model from a PGN database.

Usage:
    python build_style.py lichess_Bayanaa2020_2026-09-14.pgn
"""

import sys, json, math, collections, os
from pathlib import Path
import chess
import chess.pgn

MODEL_PATH = Path("bayanaa_style.json")
MAX_BOOK_PLY = 24
MIN_POSITION_COUNT = 1

def pos_key(board: chess.Board) -> str:
    # Keep the position identity, but ignore move counters.
    return " ".join(board.fen().split()[:4])

def phase(board: chess.Board) -> str:
    pieces = len(board.piece_map())
    if pieces >= 26:
        return "opening"
    if pieces >= 12:
        return "middlegame"
    return "endgame"

def move_features(board, move):
    mover = board.piece_at(move.from_square)
    captured = board.piece_at(move.to_square)
    san = board.san(move)
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
        "phase": phase(board),
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python build_style.py <games.pgn>")
        raise SystemExit(2)

    pgn_path = Path(sys.argv[1])
    if not pgn_path.exists():
        raise FileNotFoundError(pgn_path)

    book = collections.defaultdict(collections.Counter)
    style = collections.Counter()
    phase_style = collections.defaultdict(collections.Counter)
    opening_first_moves = collections.Counter()
    result_by_phase = collections.defaultdict(collections.Counter)
    games = 0
    moves_seen = 0
    player_names = collections.Counter()

    with pgn_path.open("r", encoding="utf-8", errors="replace") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            games += 1
            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")
            player_names[white] += 1
            player_names[black] += 1

            # Learn only Bayanaa's moves. The username can be overridden
            # with BAYANAA_USERNAME, but defaults to Bayanaa2020.
            target = os.getenv("BAYANAA_USERNAME", "Bayanaa2020").lower()
            target_is_white = target in white.lower()
            target_is_black = target in black.lower()
            if not (target_is_white or target_is_black):
                continue

            board = game.board()
            ply = 0
            for move in game.mainline_moves():
                is_target_turn = (
                    (board.turn == chess.WHITE and target_is_white) or
                    (board.turn == chess.BLACK and target_is_black)
                )
                if is_target_turn:
                    feat = move_features(board, move)
                    key = pos_key(board)
                    uci = move.uci()
                    book[key][uci] += 1
                    moves_seen += 1

                    if ply == 0:
                        opening_first_moves[uci] += 1

                    for k, v in feat.items():
                        if isinstance(v, bool) and v:
                            style[k] += 1
                            phase_style[feat["phase"]][k] += 1
                        elif isinstance(v, str) and v:
                            style[f"{k}:{v}"] += 1
                            phase_style[feat["phase"]][f"{k}:{v}"] += 1

                board.push(move)
                ply += 1

            result_by_phase["all"][game.headers.get("Result", "*")] += 1

    model = {
        "version": 1,
        "source_file": str(pgn_path),
        "games": games,
        "moves_seen": moves_seen,
        "book": {k: dict(v) for k, v in book.items()},
        "style": dict(style),
        "phase_style": {k: dict(v) for k, v in phase_style.items()},
        "opening_first_moves": dict(opening_first_moves),
        "results": {k: dict(v) for k, v in result_by_phase.items()},
        "top_names": player_names.most_common(10),
    }

    MODEL_PATH.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    print(f"Built model: {MODEL_PATH}")
    print(f"Games: {games:,}")
    print(f"Moves: {moves_seen:,}")
    print(f"Unique positions: {len(book):,}")
    print("Top first moves:", opening_first_moves.most_common(10))

if __name__ == "__main__":
    main()
