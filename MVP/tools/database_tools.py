import os

from sqlmodel import Session, create_engine, select
from sqlalchemy.orm import joinedload
from database_model.models import Doctor, Patient
from langchain_core.tools import tool

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
    
def get_patient_by_telegram_id(session: Session, telegram_id: int):
    """
    Finds and returns a Patient object based on their Telegram ID.
    Returns None if no patient matches the ID.
    """
    # Create the query to filter by the telegram_id column
    statement = select(Patient).where(Patient.telegram_id == telegram_id)
    
    # Execute and get the first result
    patient = session.exec(statement).first()
    
    if not patient:
        print(f"Lookup: No patient found for Telegram ID {telegram_id}")
    
    return patient

def get_doctor_by_telegram_id(session: Session, telegram_id: int):
    """
    Finds and returns a Doctor object based on their Telegram ID.
    Returns None if no doctor matches the ID.
    """
    # Create the query to filter by the telegram_id column
    statement = select(Doctor).where(Doctor.telegram_id == telegram_id)
    
    # Execute and get the first result
    doctor = session.exec(statement).first()
    
    if not doctor:
        print(f"Lookup: No doctor found for Telegram ID {telegram_id}")
    
    return doctor

def build_database_tools(engine, id: int):
    @tool
    def get_patient_list() -> str:
        """Returns the list of patients assigned to the current doctor with their names and IDs."""
        with Session(engine) as session:
            statement = select(Doctor).where(Doctor.id == id)
            doctor = session.exec(statement).first()
            if not doctor or not doctor.patients:
                return "No patients found for this doctor."
            return "\n".join(
                f"- {p.name} {p.surname} (patient_id: {p.id})"
                for p in doctor.patients
            )

    @tool
    def get_patient_id_by_name(name: str) -> str:
        """Finds a patient's ID from their first or last name.
        Use this when the doctor mentions a patient by name to get their patient_id.
        Parameter: name (first name, last name, or both)."""
        with Session(engine) as session:
            statement = select(Doctor).where(Doctor.id == id)
            doctor = session.exec(statement).first()
            if not doctor:
                return "Doctor not found."
            matches = [
                p for p in doctor.patients
                if name.lower() in p.name.lower() or name.lower() in p.surname.lower()
            ]
            if not matches:
                return f"No patient found matching '{name}'."
            return "\n".join(
                f"- {p.name} {p.surname} → patient_id: {p.id}"
                for p in matches
            )

    @tool
    def get_treating_doctor() -> str:
        """Returns the name of the treating doctor assigned to the current patient."""
        with Session(engine) as session:
            statement = (
                select(Patient)
                .where(Patient.id == id)
                .options(joinedload(Patient.doctor))
            )
            patient = session.exec(statement).first()
            if not patient or not patient.doctor:
                return "No treating doctor found."
            d = patient.doctor
            return f"Your treating doctor is Dr. {d.name} {d.surname}."
    
    @tool
    def get_doctor_list() -> str:
        """Returns a list of all doctors in the system with their names and IDs."""
        with Session(engine) as session:
            doctors = session.exec(select(Doctor)).all()
            if not doctors:
                return "No doctors found in the system."
            return "\n".join(
                f"- Dr. {d.name} {d.surname} (doctor_id: {d.id})"
                for d in doctors
            )

    return [get_patient_list, get_patient_id_by_name, get_treating_doctor, get_doctor_list]

@tool
def create_patient(telegram_id: int, doctor_id: int, name: str, surname: str) -> str:
    """Creates a new patient with the provided details.
    Parameters: telegram_id (unique Telegram ID), doctor_id (ID of the treating doctor), name (first name), surname (last name)."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        patient = get_patient_by_telegram_id(session, telegram_id)
        doctor = get_doctor_by_telegram_id(session, telegram_id)
        if patient:
            return f"Validation Error: Telegram ID {telegram_id} is already registered as a Patient."
        if doctor:
            return f"Validation Error: Telegram ID {telegram_id} is already registered as a Doctor."
        # Create new patient
        try:
            create_new_patient(session, telegram_id, doctor_id, name, surname)
            return f"Patient {name} {surname} successfully created with Telegram ID {telegram_id}."
        except Exception as e:
            session.rollback()
            return f"Database Error: Could not create patient. {e}"
        
@tool
def get_doctor_list() -> str:
    """Returns a list of all doctors in the system with their names and IDs."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        doctors = session.exec(select(Doctor)).all()
        if not doctors:
            return "No doctors found in the system."
        return "\n".join(
            f"- Dr. {d.name} {d.surname} (doctor_id: {d.id})"
            for d in doctors
        )

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