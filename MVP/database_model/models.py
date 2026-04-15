import os

from datetime import datetime, time
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, create_engine,BigInteger,Column
from dotenv import load_dotenv


load_dotenv()

# --- MODELS ---

class Doctor(SQLModel, table=True):
    """
    Represents a doctor in the system.
    """
    __tablename__ = "doctors"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(sa_column=Column(BigInteger(), nullable=False))
    name: str = Field(nullable=False)
    surname: str = Field(nullable=False)

    # Relationship: A doctor can have multiple patients
    patients: List["Patient"] = Relationship(back_populates="doctor")


class Patient(SQLModel, table=True):
    """
    Represents a patient assigned to a specific doctor.
    """
    __tablename__ = "patients"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(sa_column=Column(BigInteger(), nullable=False))
    # This foreign key links to the doctor's ID
    doctor_id: int = Field(foreign_key="doctors.id", nullable=False)
    name: str = Field(nullable=False)
    surname: str = Field(nullable=False)

    # Relationship: Each patient belongs to one doctor
    doctor: Optional[Doctor] = Relationship(back_populates="patients")

# --- DATABASE CONNECTION ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    """Initializes the database and creates tables."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()
    