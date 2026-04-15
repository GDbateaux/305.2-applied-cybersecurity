import logging
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agent import handle_message
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Enable logging to see errors in the console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Function to handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a greeting message when the command /start is issued."""
    await update.message.reply_text(
        "Hello! I am your Python bot. How can I help you today?"
    )

# Function to handle regular text messages
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles regular text messages."""
    user_text = update.message.text
    user_id = update.effective_user.id

    # To make the bot "typing..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Agent call
    response = await handle_message(text=user_text, user_id=user_id)

    await update.message.reply_text(response)

def start_bot():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    # Build the application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add a handler for the /start command
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    # Add a handler for text messages (filtering out commands)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_telegram_message)
    application.add_handler(echo_handler)
    
    # Start the bot
    print("Bot is polling...")
    application.run_polling()
