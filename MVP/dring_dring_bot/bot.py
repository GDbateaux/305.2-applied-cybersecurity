import logging
import os
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
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echoes the user message."""
    user_text = update.message.text
    await update.message.reply_text(f"You said: {user_text}")

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    # Build the application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add a handler for the /start command
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    # Add a handler for text messages (filtering out commands)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    application.add_handler(echo_handler)
    
    # Start the bot
    print("Bot is polling...")
    application.run_polling()