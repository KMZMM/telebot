from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Welcome to my Telegram bot.')

if __name__ == '__main__':
    app = ApplicationBuilder().token('7639044551:AAFUY8V9CzsBwIk0HZxvQxac691axmv1DY4').build()
    
    app.add_handler(CommandHandler('start', start))
    
    app.run_polling()

