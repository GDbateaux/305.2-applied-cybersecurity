import asyncio
from venv import logger
from langchain_core.tools import tool
from sqlmodel import Session, select
from database_model.models import engine, Patient, MessageRelay
import bot_instance
from datetime import datetime
from tools.kdrive_tools import upload_to_patient_folder
from urlextract import URLExtract


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
def relay_message_to_doctor(patient_id: int, message_content: str, complaint_summary: str):
    """
    Relays a patient's medical question to their assigned doctor via Telegram.

    Args:
        patient_id (int): Unique identifier of the patient in the database.
        message_content (str): The full message written by the patient.
        complaint_summary (str): A SHORT 3-6 word summary of the patient's complaint,
            used as filename (e.g. "douleur_epaule_gauche", "fievre_persistante").
            Use lowercase, no accents, words separated by underscores.

    Returns:
        str: A confirmation message if the relay succeeds, or an error message.
    """
    extractor = URLExtract()

    if extractor.has_urls(message_content):
        return "Erreur : Liens interdits."
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

    logger.info("Relaying message from patient %s %s (TG: %s) to doctor (TG: %s)",
            patient_name, patient_surname, patient_tg_id, doctor_tg_id)
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
            patient_complaint=complaint_summary
        ))
        session.commit()

    return f"Votre message a été transmis à Dr. {doctor_name}."
