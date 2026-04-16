import asyncio
from langchain_core.tools import tool
from sqlmodel import Session, select
from database_model.models import engine, Patient, MessageRelay
import bot_instance


# ── Thread-safe Telegram message sender ─────────────────────────────────────
def _send(bot: any, chat_id: int, text: str):
    """
    Sends a Telegram message from any thread, whether or not
    an asyncio event loop is already running.
    """
    try:
        if bot_instance.loop is None:
         raise RuntimeError("Bot loop not initialized.")
        
        coro = bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        future = asyncio.run_coroutine_threadsafe(coro, bot_instance.loop)
        return future.result(timeout=10)
    except RuntimeError:
        # No loop in this thread → spin up a temporary one
        return asyncio.run(
            bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        )
    
# ── LangChain Tool: patient → doctor ────────────────────────────────────────
@tool
def relay_message_to_doctor(patient_id: int, message_content: str):
    """(Patients only) Relays a medical question to your assigned doctor."""

    # 1. Fetch data from DB
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if not patient or not patient.doctor:
            return "Erreur : aucun médecin n'est associé à votre profil."

        doctor_tg_id  = patient.doctor.telegram_id
        patient_tg_id = patient.telegram_id
        doctor_name   = patient.doctor.surname
        patient_name  = patient.name
        patient_surname = patient.surname

    # 2. Forward the message to the doctor
    try:
        sent_msg = _send(
            bot_instance.bot,
            chat_id=doctor_tg_id,
            text=(
                f"*Message de votre patient {patient_name} {patient_surname}:*\n\n"
                f"{message_content}\n\n"
                f"_Répondez directement à ce message et votre réponse "
                f"sera automatiquement transmise au patient._"
            ),
        )
    except Exception as e:
        return f"Technical error while sending message: {e}"

    # 3. Save the relay in DB (to route the doctor's reply back)
    with Session(engine) as session:
        session.add(MessageRelay(
            message_id_in_doctor_chat=sent_msg.message_id,
            patient_telegram_id=patient_tg_id,
        ))
        session.commit()

    return f"Votre message a été transmis à Dr. {doctor_name}."


# ── Telegram Handler: doctor's reply → patient ───────────────────────────────
async def handle_doctor_reply(update, context):
    """
    Register this as a MessageHandler on your Telegram bot.
    Intercepts the doctor's replies and forwards them to the patient.
    """
    msg = update.message

    # Only process messages that are a REPLY to another message
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

    # Forward the doctor's reply to the patient
    await context.bot.send_message(
        chat_id=patient_tg_id,
        text=(
            f"*Réponse de votre médecin:*\n\n"
            f"{msg.text}"
        ),
        parse_mode="Markdown",
    )

    # Confirm to the doctor that their reply was delivered
    await msg.reply_text("Votre réponse a été transmise au patient.")