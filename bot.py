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

# ========== HANDLER FUNCTIONS (DEFINE THESE FIRST) ==========

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
    try:
        file = await update.message.document.get_file()
        await file.download_to_drive('combo.txt')
        
        if 'token' not in context.user_data:
            await update.message.reply_text('Please send your Telegram bot token:')
            return
        if 'chat_id' not in context.user_data:
            await update.message.reply_text('Please send your Telegram chat ID:')
            return
        
        await process_combo(update, context, 'combo.txt')
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await update.message.reply_text("Error processing your file. Please try again.")

# ========== OTHER FUNCTIONS ==========

async def process_combo(update: Update, context: CallbackContext, combo_file: str):
    """Process the combo file"""
    try:
        await update.message.reply_text('Starting to check cards...')
        
        token = context.user_data['token']
        chat_id = context.user_data['chat_id']
        
        with open(combo_file, 'r') as file:
            for i, line in enumerate(file, 1):
                try:
                    if not line.strip():
                        continue
                        
                    n, mm, yy, cvc = line.strip().split('|')[:4]
                    yy = yy[-2:]
                    cvc = cvc.strip()

                    # Process card here (removed sensitive processing code)
                    # Replace with your actual processing logic
                    await simulate_card_processing(update, i, line, token, chat_id)
                    
                except ValueError:
                    await update.message.reply_text(f'[ {i} ] Invalid format: {line.strip()}')
                except Exception as e:
                    logger.error(f"Error processing line {i}: {e}")
                    await update.message.reply_text(f'Error processing line {i}: {str(e)}')

    except Exception as e:
        logger.error(f"Error in process_combo: {e}")
        await update.message.reply_text("Error processing combo file.")

async def simulate_card_processing(update, line_num, card_data, token, chat_id):
    """Simulate card processing with delay"""
    time.sleep(2)  # Simulate processing delay
    
    # Simulate different outcomes
    if int(card_data.split('|')[0][-1]) % 3 == 0:
        msg = f'''✘ Succeeded ✅
✘ CC ➠ {card_data}
✘ Result ➠ Approved
━━━━━━━━━━━━━━━━━  
✘ By ➠ KMZ BOT'''
        await update.message.reply_text(msg)
        await send_telegram_alert(token, chat_id, msg)
    else:
        await update.message.reply_text(f'[ {line_num} ] {card_data} ➠➠ Declined ❌')

async def send_telegram_alert(token: str, chat_id: str, message: str):
    """Send alert to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message
        }
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {e}")

async def handle_text(update: Update, context: CallbackContext) -> None:
    """Handle text messages"""
    text = update.message.text.strip()
    
    if 'token' not in context.user_data:
        context.user_data['token'] = text
        await update.message.reply_text('Token saved. Now please send your chat ID:')
        return
    
    if 'chat_id' not in context.user_data:
        context.user_data['chat_id'] = text
        await update.message.reply_text('Chat ID saved. Now please send your combo file (as document):')

# ========== APPLICATION SETUP ==========

# Initialize Telegram application
# Telegram bot application - OLD VERSION (problematic)
application = Application.builder().token(TOKEN).build()

# Change to this NEW VERSION:
def setup_application():
    """Initialize and configure the Telegram application"""
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    return application

# Initialize the application properly
application = setup_application()

# Webhook setup
def set_webhook():
    """Set up the webhook URL"""
    try:
        webhook_url = f"https://telebot-ep9a.onrender.com/{TOKEN}"
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
        
        # Initialize update processing
        async with application:
            await application.initialize()
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
