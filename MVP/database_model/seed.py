from datetime import time
from sqlmodel import Session

from models import (
    engine,
    create_db_and_tables,
    User,
    Bike,
    StockBike,
)


def seed():
    create_db_and_tables()

    with Session(engine) as session:
        # -------------------
        # USERS
        # -------------------
        users = [
            User(username="admin", password="admin123"),
            User(username="alice", password="alice123"),
            User(username="bob", password="bob123"),
            User(username="charlie", password="charlie123"),
        ]

        session.add_all(users)
        session.commit()

        # refresh IDs
        for user in users:
            session.refresh(user)

        # -------------------
        # BIKES
        # -------------------
        bikes = [
            Bike(name="Mountain Bike Pro", price=1200.0, maintenance_time=time(1, 0)),
            Bike(name="Road Bike Speed", price=1500.0, maintenance_time=time(0, 45)),
            Bike(name="City Bike Comfort", price=600.0, maintenance_time=time(0, 30)),
            Bike(name="Electric Bike E100", price=2500.0, maintenance_time=time(2, 0)),
        ]

        session.add_all(bikes)
        session.commit()

        for bike in bikes:
            session.refresh(bike)

        # -------------------
        # STOCK
        # -------------------
        stocks = [
            StockBike(bike_id=bikes[0].id, number=5),
            StockBike(bike_id=bikes[1].id, number=3),
            StockBike(bike_id=bikes[2].id, number=10),
            StockBike(bike_id=bikes[3].id, number=2),
        ]

        session.add_all(stocks)
        session.commit()

        print("Database seeded successfully!")


if __name__ == "__main__":
    seed()
