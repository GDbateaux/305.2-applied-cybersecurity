import logging
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agent import handle_message
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from tools.file_utils import extract_text

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
USER_FILES_CACHE = os.path.join(os.path.dirname(__file__), '..', 'user_files_cache')

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
    telegram_id = update.effective_user.id

    # To make the bot "typing..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Agent call
    response = await handle_message(text=user_text, telegram_id=telegram_id)

    await update.message.reply_text(response)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    telegram_id = update.effective_user.id

    if doc.file_size > MAX_FILE_SIZE_BYTES:
        await update.message.reply_text("File is too large. Max : 20 MB.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    os.makedirs(USER_FILES_CACHE, exist_ok=True)
    tg_file = await doc.get_file()
    path = os.path.join(USER_FILES_CACHE, doc.file_name)
    await tg_file.download_to_drive(path)

    file_text = extract_text(path)
    user_message = f"[File attached : {doc.file_name}]\n\n{file_text[:8000]}"
    if update.message.caption:
        user_message += f"\n\n{update.message.caption}"

    response = await handle_message(text=user_message, telegram_id=telegram_id)
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

    # Add a handler for document messages
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Start the bot
    print("Bot is polling...")
    application.run_polling()
