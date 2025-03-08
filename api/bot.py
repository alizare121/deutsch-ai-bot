import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from http.server import BaseHTTPRequestHandler
import requests
import asyncio
import logging
import google.generativeai as genai
from gtts import gTTS
import speech_recognition as sr
import tempfile

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your own tokens
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# Configure Google Generative AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# User data storage (in-memory for serverless environment)
user_data = {}

async def start(update: Update, context):
    await update.message.reply_text("سلام! من یک ربات هوش مصنوعی هستم که می‌تواند به سوالات شما در مورد زبان آلمانی پاسخ دهد. لطفاً سوال خود را بپرسید.")

async def help_command(update: Update, context):
    await update.message.reply_text("من می‌توانم به سوالات شما در مورد زبان آلمانی پاسخ دهم. فقط کافیست سوال خود را بپرسید.")

async def translate_text(text, source_lang, target_lang):
    try:
        prompt = f"Translate the following text from {source_lang} to {target_lang}: {text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return None

async def text_to_speech(text, lang='de'):
    try:
        tts = gTTS(text=text, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            tts.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        logger.error(f"Text-to-speech error: {str(e)}")
        return None

async def learn(update: Update, context):
    user_id = update.effective_user.id
    prompt = "Generate a random German word with its English translation and a simple example sentence in German."
    response = model.generate_content(prompt)
    word_info = response.text.split('\n')
    german_word = word_info[0].split(': ')[1]
    english_translation = word_info[1].split(': ')[1]
    example_sentence = word_info[2].split(': ')[1]
    
    farsi_translation = await translate_text(english_translation, "en", "fa")
    user_data[user_id]["words_learned"] += 1
    
    audio_file = await text_to_speech(german_word)
    if audio_file:
        await update.message.reply_voice(voice=open(audio_file, "rb"))
        os.unlink(audio_file)
    
    await update.message.reply_text(f"کلمه جدید: {german_word}\nترجمه انگلیسی: {english_translation}\nترجمه فارسی: {farsi_translation}\nمثال: {example_sentence}\n\nبرای تمرین تلفظ، روی فایل صوتی کلیک کنید.")

async def practice(update: Update, context):
    user_id = update.effective_user.id
    prompt = "Generate a simple German sentence for language practice."
    response = model.generate_content(prompt)
    german_sentence = response.text
    
    await update.message.reply_text(f"لطفاً این جمله را ترجمه کنید:\n\n{german_sentence}")
    
    context.user_data['practice_sentence'] = german_sentence

async def check_translation(update: Update, context):
    user_translation = update.message.text
    original_sentence = context.user_data.get('practice_sentence')
    
    if original_sentence:
        prompt = f"Compare the following German sentence:\n'{original_sentence}'\nwith this translation attempt:\n'{user_translation}'\nProvide feedback in Farsi on the accuracy and any corrections needed."
        response = model.generate_content(prompt)
        feedback = response.text
        
        await update.message.reply_text(feedback)
        del context.user_data['practice_sentence']
    else:
        await update.message.reply_text("لطفاً ابتدا از دستور /practice استفاده کنید تا یک جمله برای تمرین دریافت کنید.")

async def stats(update: Update, context):
    user_id = update.effective_user.id
    user_stats = user_data.get(user_id, {"level": 1, "words_learned": 0})
    await update.message.reply_text(f"آمار یادگیری شما:\nسطح: {user_stats['level']}\nتعداد کلمات یاد گرفته شده: {user_stats['words_learned']}")

async def handle_voice(update: Update, context):
    voice = update.message.voice
    if voice:
        file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as voice_file:
            await file.download_to_drive(voice_file.name)
        
        r = sr.Recognizer()
        with sr.AudioFile(voice_file.name) as source:
            audio = r.record(source)
        
        try:
            text = r.recognize_google(audio, language="de-DE")
            translation = await translate_text(text, "de", "fa")
            
            prompt = f"Provide feedback in Farsi on the pronunciation and grammar of this German sentence: '{text}'"
            feedback_response = model.generate_content(prompt)
            feedback = feedback_response.text
            
            await update.message.reply_text(f"متن تشخیص داده شده: {text}\nترجمه: {translation}\n\nبازخورد: {feedback}")
        except sr.UnknownValueError:
            await update.message.reply_text("متأسفانه نتوانستم صدا را تشخیص دهم. لطفاً دوباره تلاش کنید.")
        except sr.RequestError as e:
            await update.message.reply_text("خطا در ارتباط با سرویس تشخیص گفتار. لطفاً بعداً دوباره تلاش کنید.")
        
        os.unlink(voice_file.name)

async def handle_message(update: Update, context):
    user_message = update.message.text
    prompt = f"""
    You are a helpful AI assistant specializing in German language education. 
    Respond to the following query about the German language. 
    If the query is in Farsi, respond in Farsi. If it's in English or German, respond in the same language as the query.
    Always provide accurate and helpful information about German language, grammar, vocabulary, or culture.

    Query: {user_message}
    """
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        await update.message.reply_text("متأسفانه در پردازش پیام شما مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")

async def setup_application():
    """Set up PTB application"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("learn", learn))
    application.add_handler(CommandHandler("practice", practice))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application

async def process_update(json_data):
    """Process update from Telegram"""
    application = await setup_application()
    await application.initialize()
    
    try:
        update = Update.de_json(json_data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
    finally:
        await application.shutdown()

class handler(BaseHTTPRequestHandler):
    """Handler for Vercel serverless function"""
    def do_POST(self):
        """Handle POST request"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        json_data = json.loads(post_data)
        
        asyncio.run(process_update(json_data))
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write("success".encode())

    def do_GET(self):
        """Handle GET request"""
        self.send_response(200)
        self.end_headers()
        self.wfile.write("Bot is running!".encode())

# Set webhook on startup
VERCEL_URL = os.environ.get('VERCEL_URL')
if VERCEL_URL:
    logger.info(f"Setting webhook to: https://{VERCEL_URL}/api/bot")
    webhook_url = f"https://{VERCEL_URL}/api/bot"
    response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
    logger.info(f"Webhook set response: {response.text}")
else:
    logger.warning("VERCEL_URL is not set. Webhook not updated.")