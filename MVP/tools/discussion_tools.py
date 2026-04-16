import os
from sqlmodel import Session, select, create_engine
from database_model.models import MessageRelay,Patient
from langchain_core.tools import tool
from telegram.ext import ContextTypes

@tool
async def relay_message_to_doctor(patient_telegram_id: int, content: str, context: ContextTypes.DEFAULT_TYPE):
    """
    Relays a medical question to the patient's assigned doctor.
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        # 1. Find the doctor linked to this patient
        statement = select(Patient).where(Patient.telegram_id == patient_telegram_id)
        patient = session.exec(statement).first()
        
        if not patient or not patient.doctor:
            return "Error: No assigned doctor found for this patient."

        doctor_telegram_id = patient.doctor.telegram_id

        # 2. Send message to the doctor
        text_for_doctor = (
            f"📥 **Message from Patient: {patient.name} {patient.surname}**\n"
            f"------------------\n"
            f"{content}\n"
            f"------------------\n"
            f"💡 *Tip: Reply directly to this message to answer.*"
        )
        
        sent_msg = await context.bot.send_message(
            chat_id=doctor_telegram_id, 
            text=text_for_doctor,
            parse_mode="Markdown"
        )

        # 3. Save the relay mapping so we can route the reply later
        relay_entry = MessageRelay(
            message_id_in_doctor_chat=sent_msg.message_id,
            patient_telegram_id=patient_telegram_id
        )
        session.add(relay_entry)
        session.commit()

        return "Message sent to your doctor. They will reply as soon as possible."
    

    