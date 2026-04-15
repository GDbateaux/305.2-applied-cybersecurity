import os

from datetime import datetime, time
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, create_engine
from dotenv import load_dotenv


load_dotenv()

# --- MODELS (Tables) ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    orders: List["Order"] = Relationship(back_populates="user")

class Bike(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    maintenance_time: time
    
    # Relationships
    orders: List["Order"] = Relationship(back_populates="bike")
    stock: Optional["StockBike"] = Relationship(back_populates="bike")

class Discount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: float
    starts_at: datetime
    ends_at: datetime
    active: bool = Field(default=False)
    
    # Relationships
    orders: List["Order"] = Relationship(back_populates="discount")

class StockBike(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bike_id: int = Field(foreign_key="bike.id")
    number: int = Field(default=0)
    
    # Relationships
    bike: Bike = Relationship(back_populates="stock")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    bike_id: int = Field(foreign_key="bike.id")
    discount_id: Optional[int] = Field(default=None, foreign_key="discount.id")
    total_price: float
    is_validated: bool = Field(default=False)
    order_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    user: User = Relationship(back_populates="orders")
    bike: Bike = Relationship(back_populates="orders")
    discount: Optional[Discount] = Relationship(back_populates="orders")

# --- DATABASE CONNECTION ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    """Initializes the database and creates tables."""
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()
    