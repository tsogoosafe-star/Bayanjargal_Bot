import os
import threading
from flask import Flask
import berserk
import chess

# Render-ийг 24/7 унтуулахгүй ажиллуулах веб сервер
app = Flask(__name__)

@app.route('/')
def home():
    return "Bayanjargal_Bot is online and ready!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Веб серверийг арын ард ажиллуулах
threading.Thread(target=run_flask, daemon=True).start()

# Lichess холболт
TOKEN = os.environ.get("LICHESS_TOKEN")
if not TOKEN:
    print("LICHESS_TOKEN олдсонгүй!")

session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)

print("Bayanjargal_Bot амжилттай холбогдлоо.")

# Дуудлага болон тоглолт хүлээн авах
for event in client.bots.stream_incoming_events():
    if event['type'] == 'challenge':
        challenge_id = event['challenge']['id']
        client.bots.accept_challenge(challenge_id)
        print(f"Тоглох сорилтыг хүлээж авлаа: {challenge_id}")
    elif event['type'] == 'gameStart':
        game_id = event['game']['id']
        print(f"Тоглолт эхэллээ: {game_id}")
