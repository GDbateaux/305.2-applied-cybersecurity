import os
from sqlmodel import Session
from dotenv import load_dotenv
from database_model.models import engine, Doctor, Patient

load_dotenv()


def seed():
    doctors = [
        Doctor(
            telegram_id=int(os.getenv("DOCTOR_1_TELEGRAM_ID")),
            name="Robin", surname="Bütikofer"
        ),
    ]

    with Session(engine) as session:
        session.add_all(doctors)
        session.commit()
        for doctor in doctors:
            session.refresh(doctor)

        patients = [
            Patient(telegram_id=int(os.getenv("PATIENT_1_TELEGRAM_ID")), name="Simon", surname="Masserey", doctor_id=doctors[0].id),
        ]

        session.add_all(patients)
        session.commit()
        print("Healthcare database seeded successfully!")


if __name__ == "__main__":
    seed()