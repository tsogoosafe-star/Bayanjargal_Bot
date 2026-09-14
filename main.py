import os
import random
import threading
import time
import chess
import chess.pgn
import chess.engine
import berserk
from flask import Flask

# 1. 24/7 ажиллах веб сервер
app = Flask(__name__)

@app.route('/')
def home():
    return "Bayanjargal_Engine_Bot is online and ready!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Lichess холболт
TOKEN = os.environ.get("LICHESS_TOKEN")
if not TOKEN:
    print("Анхааруулга: LICHESS_TOKEN олдсонгүй!")

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)

try:
    bot_profile = client.account.get()
    BOT_USERNAME = bot_profile['username'].lower()
    print(f"Bayanjargal_Engine_Bot амжилттай холбогдлоо: {BOT_USERNAME}")
except Exception as e:
    print(f"Lichess руу нэвтрэхэд алдаа гарлаа: {e}")
    BOT_USERNAME = ""

# 3. PGN файлаас 27,000 өргийг уншиж бэлтгэх (Нээлтийн сан)
PGN_FILE = "lichess_Bayanaa2020_2026-09-14.pgn"
bayanaa_games = []

def load_games():
    global bayanaa_games
    if not os.path.exists(PGN_FILE):
        print(f"Алдаа: {PGN_FILE} файл олдсонгүй!")
        return

    print("bayanaa2020-ийн 27,000 өргийг нээлтийн санд уншиж байна...")
    count = 0
    with open(PGN_FILE, encoding="utf-8") as pgn:
        while True:
            game = chess.pgn.read_game(pgn)
            if game is None:
                break
            
            white = game.headers.get("White", "").lower()
            black = game.headers.get("Black", "").lower()
            
            if "bayanaa2020" in white or "bayanaa2020" in black:
                bayanaa_games.append(game)
                count += 1
                
    print(f"Амжилттай! нийт {count} өрөг нээлтийн санд суулаа.")

load_games()

# 4. Нээлт болон Engine хослуулсан шийдвэр гаргах логик (Rating: ~1850)
def get_bot_move(board_fen):
    current_board = chess.Board(board_fen)
    move_weights = {}
    
    # Opening Book (Сангаас ижил байрлал хайх)
    for game in bayanaa_games:
        temp_board = game.board()
        moves = list(game.mainline_moves())
        
        for move in moves:
            if temp_board.fen() == current_board.fen():
                move_uci = move.uci()
                move_weights[move_uci] = move_weights.get(move_uci, 0) + 1
                break
            temp_board.push(move)
            
    if move_weights:
        moves_list = list(move_weights.keys())
        weights_list = list(move_weights.values())
        chosen_move = random.choices(moves_list, weights=weights_list, k=1)[0]
        return chosen_move
        
    # Сангаас гарсан үед Stockfish (Elo ~1850) ашиглах
    engine_paths = ["stockfish", "/usr/games/stockfish", "/usr/bin/stockfish"]
    engine = None
    
    for path in engine_paths:
        try:
            engine = chess.engine.SimpleEngine.popen_uci(path)
            break
        except Exception:
            continue
            
    if engine:
        try:
            engine.configure({"Elo": 1850})
            result = engine.play(current_board, chess.engine.Limit(time=0.5))
            engine.quit()
            if result.move:
                return result.move.uci()
        except Exception as e:
            print(f"Engine алдаа гарлаа: {e}")
            if engine:
                engine.quit()

    legal_moves = list(current_board.legal_moves)
    if legal_moves:
        return random.choice(legal_moves).uci()
        
    return None

# 5. Тоглолтын явцыг удирдах болон чат мессеж илгээх
def play_game(game_id):
    board = chess.Board()
    print(f"Тоглолт эхэллээ: {game_id}")
    chat_sent = False
    game_ended_chat_sent = False
    
    try:
        for state in client.bots.stream_game_state(game_id):
            if state['type'] == 'gameStart':
                continue
            elif state['type'] == 'gameState':
                moves = state['moves'].split()
                board.reset()
                for m in moves:
                    board.push(chess.Move.from_uci(m))
                
                white_id = state.get('white', {}).get('id', "").lower()
                black_id = state.get('black', {}).get('id', "").lower()
                
                is_white = (white_id == BOT_USERNAME)
                is_black = (black_id == BOT_USERNAME)
                
                # Тоглолт эхлэхэд (эхний нүүдлүүдийн үеэр) мэндчилгээ илгээх
                if not chat_sent and len(moves) <= 2:
                    try:
                        client.bots.chat(game_id, 'player', "Hello! Good luck, have fun!")
                        chat_sent = True
                    except Exception as e:
                        print(f"Мэндчилгээ илгээхэд алдаа гарлаа: {e}")

                # Тоглолт дууссан эсэхийг шалгах
                if board.is_game_over():
                    if not game_ended_chat_sent:
                        try:
                            time.sleep(1)
                            client.bots.chat(game_id, 'player', "Thank you for the game, let's play again!")
                            game_ended_chat_sent = True
                        except Exception as e:
                            print(f"Төгсгөлийн чат илгээхэд алдаа гарлаа: {e}")
                    break

                my_turn = (board.turn == chess.WHITE and is_white) or (board.turn == chess.BLACK and is_black)
                
                if my_turn:
                    time.sleep(0.6)
                    move_uci = get_bot_move(board.fen())
                    if move_uci:
                        try:
                            client.bots.make_move(game_id, move_uci)
                            print(f"Нүүдэл хийлээ: {move_uci}")
                        except Exception as e:
                            print(f"Нүүдэл илгээхэд алдаа гарлаа: {e}")
            elif state['type'] == 'chat':
                pass
    except Exception as e:
        print(f"Тоглолтын стриминг алдаа ({game_id}): {e}")

if __name__ == "__main__":
    print("Bayanjargal_Engine_Bot хүсэлт хүлээж байна...")
    while True:
        try:
            for event in client.bots.stream_incoming_events():
                event_type = event.get('type')
                
                if event_type == 'challenge':
                    challenge_id = event['challenge']['id']
                    challenger = event['challenge']['challenger']['name']
                    print(f"Шинэ сорилт ирлээ: {challenger} (ID: {challenge_id})")
                    client.bots.accept_challenge(challenge_id)
                    print(f"Сорилтыг амжилттай зөвшөөрлөө!")
                    
                elif event_type == 'gameStart':
                    game_id = event['game']['id']
                    threading.Thread(target=play_game, args=(game_id,), daemon=True).start()
                    
        except Exception as e:
            print(f"Event stream алдаа гарлаа, 5 секундын дараа дахин холбогдоно: {e}")
            time.sleep(5)
