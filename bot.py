import telebot
import os
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

WEBHOOK_URL = f"https://telebot-ep9a.onrender.com/{TOKEN}"
  # Change this later

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, f"You said: {message.text}")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.data.decode('utf-8'))
    bot.process_new_updates([update])
    return '', 200

@app.route('/')
def index():
    return 'Bot is running!'

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
