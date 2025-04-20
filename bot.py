import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import requests
import time
import pyfiglet
from quart import Quart, request, jsonify

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Color codes
Z = '\033[1;31m'  # Red
F = '\033[2;32m'  # Green
C = '\033[2;35m'  # Purple

# Display logo
logo = pyfiglet.figlet_format('KMZ BOT')
print(Z + logo)

# Initialize Quart app
app = Quart(__name__)

# Telegram Bot Token from environment
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("No BOT_TOKEN environment variable set!")

# ========== HANDLER FUNCTIONS ==========

async def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message"""
    user = update.effective_user
    await update.message.reply_text(
        f'Hi {user.first_name}! Welcome to KMZ Checker Bot\n\n'
        'Send me a combo file (text file with CC details) to start checking.'
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send help message"""
    await update.message.reply_text(
        'Help: Send me a combo file (text file) with CC details in format:\n'
        'cardnumber|mm|yy|cvc'
    )

async def handle_document(update: Update, context: CallbackContext) -> None:
    """Handle received combo file"""
    # Check if already processing
    if context.user_data.get('checking_in_progress', False):
        await update.message.reply_text("Already checking cards. Please wait for the current process to finish.")
        return
        
    try:
        # Set processing flag
        context.user_data['checking_in_progress'] = True
        
        file = await update.message.document.get_file()
        await file.download_to_drive('combo.txt')
        
        if 'token' not in context.user_data:
            await update.message.reply_text('Please send your Telegram bot token:')
            context.user_data['checking_in_progress'] = False
            return
            
        if 'chat_id' not in context.user_data:
            await update.message.reply_text('Please send your Telegram chat ID:')
            context.user_data['checking_in_progress'] = False
            return
        
        # Process the combo in a separate task to avoid webhook timeout
        asyncio.create_task(process_combo_wrapper(update, context, 'combo.txt'))
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        context.user_data['checking_in_progress'] = False
        await update.message.reply_text("Error processing your file. Please try again.")

async def process_combo_wrapper(update: Update, context: CallbackContext, combo_file: str):
    """Wrapper to properly handle combo processing with cleanup"""
    try:
        await process_combo(update, context, combo_file)
    except Exception as e:
        logger.error(f"Error in process_combo_wrapper: {e}")
        await update.message.reply_text(f"An error occurred: {str(e)}")
    finally:
        # Always clear the processing flag
        context.user_data['checking_in_progress'] = False
        logger.info("Processing completed, flag cleared")

# [Rest of your existing process_combo, send_telegram_alert, and handle_text functions remain the same]
# ========== APPLICATION SETUP ==========

def setup_application():
    """Initialize and configure the Telegram application"""
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    return application

# Initialize the application
application = setup_application()

# Webhook setup
def set_webhook():
    """Set up the webhook URL"""
    try:
        webhook_url = f"https://your-app-url.herokuapp.com/{TOKEN}"
        response = requests.get(
            f'https://api.telegram.org/bot{TOKEN}/setWebhook',
            params={'url': webhook_url}
        )
        if response.status_code == 200:
            logger.info("Webhook set successfully!")
        else:
            logger.error(f"Failed to set webhook: {response.text}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

@app.route(f'/{TOKEN}', methods=['POST'])
async def webhook():
    """Handle incoming updates from Telegram"""
    try:
        json_data = await request.get_json()
        update = Update.de_json(json_data, application.bot)
        
        async with application:
            await application.process_update(update)
            
        return '', 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return jsonify({"status": "error"}), 500
        
@app.route('/')
async def index():
    """Basic health check endpoint"""
    return 'KMZ Bot is running!'

async def run_app():
    """Run both Quart app and Telegram bot"""
    set_webhook()
    await app.run_task(host='0.0.0.0', port=8000)

if __name__ == '__main__':
    import asyncio
    asyncio.run(run_app())
