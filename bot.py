import telebot

TOKEN = "7639044551:AAFUY8V9CzsBwIk0HZxvQxac691axmv1DY4"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"You said: {message.text}")

bot.polling(non_stop=True)
