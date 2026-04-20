import logging
import sys, os
import bot_instance
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agent import handle_message, reformat_doctor_reply
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from tools.file_utils import extract_text
from tools.kdrive_tools import upload_to_patient_folder
from sqlmodel import Session, create_engine, select
from database_model.models import MessageRelay, Patient
from datetime import datetime
import asyncio


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
        "Bonjour 👋\n\n"
        "Bienvenue.\n"
        "Je suis l'assistant du cabinet médical.\n\n"
        "Comment puis-je vous aider aujourd'hui ?"
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


async def handle_doctor_reply(update, context):
    """
    Register this as a MessageHandler on your Telegram bot.
    Intercepts the doctor's replies and forwards them to the patient.
    """
    msg = update.message
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    doctor_tg_id = update.effective_user.id
    # Only process messages that are a REPLY to another message
    if msg.text and msg.text.strip().lower() in ["oui", "yes", "o", "y"]:
        pending = bot_instance.pending_doctor_replies.get(doctor_tg_id)
        if pending:
            await context.bot.send_message(
                chat_id=pending["patient_tg_id"],
                text=f"*Réponse de votre médecin:*\n\n{pending['formatted_reply']}",
                parse_mode="Markdown",
            )
            del bot_instance.pending_doctor_replies[doctor_tg_id]
            await msg.reply_text("Votre réponse a été transmise au patient.")
            return
    if msg.text and msg.text.strip().lower() in ["non", "no", "n"]:
        if doctor_tg_id in bot_instance.pending_doctor_replies:
            del bot_instance.pending_doctor_replies[doctor_tg_id]
            await msg.reply_text("L'envoi a été annulé. Vous pouvez envoyer une nouvelle réponse.")
            return
    if not msg.reply_to_message:
        return

    replied_to_id = msg.reply_to_message.message_id

    with Session(engine) as session:
        relay = session.exec(
            select(MessageRelay).where(
                MessageRelay.message_id_in_doctor_chat == replied_to_id
            )
        ).first()

        if not relay:
            return  # Not a relayed message, ignore

        patient_tg_id = relay.patient_telegram_id
        patient = session.exec(
            select(Patient).where(Patient.telegram_id == patient_tg_id)
        ).first()
        patient_id = patient.id if patient else None

    is_valid, formatted_reply = await reformat_doctor_reply(msg.text)

    if not is_valid:
        
        bot_instance.pending_doctor_replies[doctor_tg_id] = {
            "patient_tg_id": patient_tg_id,
            "raw_reply": msg.text,
            "formatted_reply": formatted_reply or msg.text,
        }
        await msg.reply_text(
            "Votre réponse semble contenir des informations médicales inhabituelles ou potentiellement erronées.\n\n"
            f"Message qui sera envoyé:\n_{formatted_reply}_\n\n"
            "Voulez-vous toujours l'envoyer ? Répondez *oui* pour confirmer ou *non* pour annuler.",
            parse_mode="Markdown",
        )
        return

    # Forward the formatted reply to the patient
    await context.bot.send_message(
        chat_id=patient_tg_id,
        text=f"*Réponse de votre médecin:*\n\n{formatted_reply}",
        parse_mode="Markdown",
    )

    if patient_id:
        now = datetime.now()
        complaint = relay.patient_complaint or ""
        filename = f"conseil_medecin_{complaint}_{now.strftime('%Y-%m-%d_%H-%M')}.txt"
        content = f"Date: {now.strftime('%Y-%m-%d %H:%M')}\nConseil de votre médecin:\n\n{msg.text}\n"
        try:
            upload_to_patient_folder(str(patient_id), content, filename)
        except Exception as e:
            logging.warning("Failed to save doctor advice to kDrive: %s", e)

    await msg.reply_text("Votre réponse a été transmise au patient.")



def start_bot():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    # Build the application
    application = ApplicationBuilder().token(TOKEN).build()
    
    bot_instance.bot = application.bot
    bot_instance.loop = asyncio.get_event_loop()
    # Add a handler for the /start command
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    application.add_handler(
        MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, handle_doctor_reply)
    )

    # Add a handler for text messages (filtering out commands)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_telegram_message)
    application.add_handler(echo_handler)

    # Add a handler for document messages
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    

    # Start the bot
    print("Bot is polling...")
    application.run_polling()
