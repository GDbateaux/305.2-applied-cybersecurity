import os

from sqlmodel import Session, create_engine, select
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

def create_new_patient(session: Session, telegram_id: int, doctor_id: int, name: str, surname: str):
    """
    Creates a new patient after verifying that the Telegram ID is unique 
    across both the Doctors and Patients tables.
    """

    # 1. Check if the Telegram ID already exists in the Doctors table
    doctor_check = session.exec(
        select(Doctor).where(Doctor.telegram_id == telegram_id)
    ).first()

    if doctor_check:
        print(f"Validation Error: Telegram ID {telegram_id} is already registered as a Doctor.")
        return None

    # 2. Check if the Telegram ID already exists in the Patients table
    patient_check = session.exec(
        select(Patient).where(Patient.telegram_id == telegram_id)
    ).first()

    if patient_check:
        print(f"Validation Error: Telegram ID {telegram_id} is already registered as a Patient.")
        return None

    # 3. If both checks pass, create the new Patient
    try:
        new_patient = Patient(
            telegram_id=telegram_id,
            doctor_id=doctor_id,
            name=name,
            surname=surname
        )
        
        session.add(new_patient)
        session.commit()
        session.refresh(new_patient)
        
        print(f"Patient {name} {surname} successfully created with ID {new_patient.id}.")
        return new_patient

    except Exception as e:
        session.rollback()
        print(f"Database Error: Could not create patient. {e}")
        return None
    
if __name__ == "__main__":
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        # Example: Get patients for a doctor
        doctor_telegram_id = 8794985042
        patients = get_patients_by_doctor_telegram(session, doctor_telegram_id)
        print(f"Patients for Doctor with Telegram ID {doctor_telegram_id}:")
        for patient in patients:
            print(f"- {patient.name} {patient.surname} (Telegram ID: {patient.telegram_id})")

        # Example: Get doctor for a patient
        patient_telegram_id = 123456789
        doctor = get_doctor_by_patient_telegram(session, patient_telegram_id)
        if doctor:
            print(f"Doctor for Patient with Telegram ID {patient_telegram_id}: {doctor.name} {doctor.surname} (Telegram ID: {doctor.telegram_id})")

        # Example: Create a new patient
        new_patient = create_new_patient(
            session,
            telegram_id=555666777,
            doctor_id=1, 
            name="Alice",
            surname="Johnson"
        )