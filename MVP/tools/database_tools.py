from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from database_model.models import Doctor, Patient

def get_patients_by_doctor_telegram(session: Session, doctor_telegram_id: int):
    """
    Finds a doctor by their Telegram ID, then returns all their patients.
    """
    # 1. Find the doctor record matching the Telegram ID
    statement = select(Doctor).where(Doctor.telegram_id == doctor_telegram_id)
    doctor = session.exec(statement).first()
    
    if not doctor:
        print(f"Error: No doctor found with Telegram ID {doctor_telegram_id}")
        return []

    # 2. Return the list of patients via the relationship
    return doctor.patients

def get_doctor_by_patient_telegram(session: Session, patient_telegram_id: int):
    """
    Finds a patient by their Telegram ID, then returns their assigned doctor.
    """
    # 1. Find the patient and eager-load the doctor relationship
    statement = (
        select(Patient)
        .where(Patient.telegram_id == patient_telegram_id)
        .options(joinedload(Patient.doctor))
    )
    
    patient = session.exec(statement).first()

    if not patient:
        print(f"Error: No patient found with Telegram ID {patient_telegram_id}")
        return None

    # 2. Return the doctor object linked to this patient
    return patient.doctor