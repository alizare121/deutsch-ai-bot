import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your own tokens
TELEGRAM_TOKEN = '7701481008:AAF8W6oNdogMyh3aWNj6d96SfAR-8lYyM40'
OPENAI_API_KEY = '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'

# Set up OpenAI API
openai.api_key = OPENAI_API_KEY

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"سلام {user.mention_html()}! من یک ربات آموزش زبان آلمانی هستم. چطور می‌توانم به شما کمک کنم؟"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("برای شروع یادگیری، لطفاً سوال خود را به زبان فارسی بپرسید.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user message and respond using ChatGPT."""
    user_message = update.message.text

    # Prepare the prompt for ChatGPT
    prompt = f"You are a German language tutor. The user is learning German and asks in Persian: '{user_message}'. Provide a helpful response in Persian, potentially including German phrases or words where appropriate."

    try:
        # Get response from ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful German language tutor."},
                {"role": "user", "content": prompt}
            ]
        )

        # Send the response back to the user
        await update.message.reply_text(response.choices[0].message['content'])
    except Exception as e:
        logger.error(f"Error in ChatGPT API call: {str(e)}")
        await update.message.reply_text("متأسفم، مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - handle the message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()