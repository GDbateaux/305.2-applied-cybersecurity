from datetime import time
from sqlmodel import Session

from models import (
    engine,
    create_db_and_tables,
    Doctor,
    Patient,
)


def seed():
    # 1. Create the tables if they don't exist
    create_db_and_tables()

    with Session(engine) as session:
        # -------------------
        # DOCTORS
        # -------------------
        # Using realistic 9-digit Telegram IDs
        doctors = [
            Doctor(telegram_id=111222333, name="Gregory", surname="House"),
            Doctor(telegram_id=444555666, name="Meredith", surname="Grey"),
            Doctor(telegram_id=8794985042, name="Robin", surname="Bütikofer"),
        ]

        session.add_all(doctors)
        session.commit()

        # Refresh to get the auto-generated database IDs
        for doctor in doctors:
            session.refresh(doctor)

        # -------------------
        # PATIENTS
        # -------------------
        # Assigning specific patients to our doctors using the primary keys (id)
        patients = [
            # Patients for Dr. House
            Patient(telegram_id=123456789, name="John", surname="Doe", doctor_id=doctors[0].id),
            Patient(telegram_id=987654321, name="Jane", surname="Smith", doctor_id=doctors[0].id),
            
            # Patients for Dr. Grey
            Patient(telegram_id=555444333, name="Arthur", surname="Morgan", doctor_id=doctors[1].id),
            
            # Patient for Dr. Murphy
            Patient(telegram_id=5035260982, name="Simon", surname="Masserey", doctor_id=doctors[2].id),
        ]

        session.add_all(patients)
        session.commit()

        print("Healthcare database seeded successfully!")


if __name__ == "__main__":
    seed()
