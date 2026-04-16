import os
from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Session, create_engine, select
from sqlalchemy import BigInteger, Column
from dotenv import load_dotenv

load_dotenv()

# --- MODELS ---

class Doctor(SQLModel, table=True):
    __tablename__ = "doctors"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(sa_column=Column(BigInteger(), nullable=False))
    name: str = Field(nullable=False)
    surname: str = Field(nullable=False)

    patients: List["Patient"] = Relationship(back_populates="doctor")


class Patient(SQLModel, table=True):
    __tablename__ = "patients"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(sa_column=Column(BigInteger(), nullable=False))
    doctor_id: int = Field(foreign_key="doctors.id", nullable=False)
    name: str = Field(nullable=False)
    surname: str = Field(nullable=False)

    doctor: Optional[Doctor] = Relationship(back_populates="patients")


class MessageRelay(SQLModel, table=True):
    __tablename__ = "message_relays"

    message_id_in_doctor_chat: int = Field(
        sa_column=Column(BigInteger(), primary_key=True)
    )
    patient_telegram_id: int = Field(sa_column=Column(BigInteger(), nullable=False))
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- DATABASE ---

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def create_db_and_tables():
    """Crée les tables si elles n'existent pas (idempotent)."""
    SQLModel.metadata.create_all(engine)


def is_db_empty() -> bool:
    """Retourne True si aucun docteur n'existe encore."""
    with Session(engine) as session:
        return session.exec(select(Doctor)).first() is None


if __name__ == "__main__":
    create_db_and_tables()