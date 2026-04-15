from sqlmodel import Session, select
from database_model.models import Bike, StockBike, Order, engine
from datetime import datetime

def get_available_bikes(session: Session):
    """
    Fetch all bikes that have at least one unit remaining in stock.
    
    Args:
        session (Session): The active SQLModel database session.
        
    Returns:
        list[dict]: A list of dictionaries containing the ID, name, and price of available bikes.
    """
    # Create a query to select Bikes joined with their Stock information
    # Filter only those where the stock count is greater than zero
    statement = select(Bike).join(StockBike).where(StockBike.number > 0)
    
    # Execute the query and retrieve all matching records
    results = session.exec(statement).all()

    # Format the result set into a list of clean dictionaries
    return [
        {"id": result.id, "name": result.name, "price": result.price}
        for result in results
    ]
    
def add_order_bike(session: Session, user_id: int, bike_id: int):
    """
    Handles the bike ordering process by verifying stock, calculating price,
    recording the order, and updating inventory in a single transaction.

    Args:
        session (Session): The active database session.
        user_id (int): ID of the user placing the order.
        bike_id (int): ID of the bike being ordered.

    Returns:
        Order: The newly created order object, or None if the process fails.
    """

    # 1. Check if the bike is in stock
    stock_statement = select(StockBike).where(StockBike.bike_id == bike_id)
    stock_item = session.exec(stock_statement).first()

    if not stock_item or stock_item.number <= 0:
        print(f"Error: Bike ID {bike_id} is out of stock.")
        return None

    # 2. Retrieve bike details for pricing
    bike = session.get(Bike, bike_id)
    if not bike:
        print(f"Error: Bike ID {bike_id} not found.")
        return None

    # 3. Instantiate the new order
    new_order = Order(
        user_id=user_id,
        bike_id=bike_id,
        discount_id=None,
        total_price=bike.price,
        is_validated=False,
        order_at=datetime.now()
    )
    
    # 4. Update the stock count
    stock_item.number -= 1
    
    # 5. Save changes
    session.add(new_order)
    session.add(stock_item)
    session.commit()
    
    # Refresh to get the generated order ID
    session.refresh(new_order)
    print(f"Order #{new_order.id} placed successfully at CHF{bike.price:.2f}!")
    return new_order

def get_bike_price(session: Session, bike_id: int) -> float:
    """
    Retrieve the unit price of a specific bike from the database.

    Args:
        session (Session): The active SQLModel database session.
        bike_id (int): The unique identifier of the bike.

    Returns:
        float: The price of the bike if found.

    Raises:
        ValueError: If no bike matches the provided bike_id.
    """
    # Attempt to fetch the bike record by its primary key
    bike = session.get(Bike, bike_id)

    # If the bike exists, return its price attribute
    if bike:
        return bike.price
    # If the record is missing, raise an error to prevent further logic errors
    else:
        raise ValueError("Bike does not exist.")

with Session(engine) as session:
    bikes = get_available_bikes(session)
    add_order_bike(session, user_id=1, bike_id=1)
    bike_price = get_bike_price(session, 1)
    print(bikes)
    print(bike_price)
