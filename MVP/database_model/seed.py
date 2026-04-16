import os
from sqlmodel import Session
from dotenv import load_dotenv
from database_model.models import engine, Doctor, Patient

load_dotenv()


def seed():
    doctors = [
        Doctor(
            telegram_id=int(os.getenv("DOCTOR_1_TELEGRAM_ID")),
            name="Gregory", surname="House"
        ),
        Doctor(
            telegram_id=int(os.getenv("DOCTOR_2_TELEGRAM_ID")),
            name="Meredith", surname="Grey"
        ),
        Doctor(
            telegram_id=int(os.getenv("DOCTOR_3_TELEGRAM_ID")),
            name="Robin", surname="Bütikofer"
        ),
    ]

    with Session(engine) as session:
        session.add_all(doctors)
        session.commit()
        for doctor in doctors:
            session.refresh(doctor)

        patients = [
            Patient(telegram_id=int(os.getenv("PATIENT_1_TELEGRAM_ID")), name="John", surname="Doe", doctor_id=doctors[0].id),
            Patient(telegram_id=int(os.getenv("PATIENT_2_TELEGRAM_ID")), name="Jane", surname="Smith", doctor_id=doctors[0].id),
            Patient(telegram_id=int(os.getenv("PATIENT_3_TELEGRAM_ID")), name="Arthur", surname="Morgan", doctor_id=doctors[1].id),
            Patient(telegram_id=int(os.getenv("PATIENT_4_TELEGRAM_ID")), name="Simon", surname="Masserey", doctor_id=doctors[2].id),
        ]

        session.add_all(patients)
        session.commit()
        print("Healthcare database seeded successfully!")


if __name__ == "__main__":
    seed()