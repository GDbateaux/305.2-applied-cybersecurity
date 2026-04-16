from database_model.models import create_db_and_tables, is_db_empty
from database_model.seed import seed
from medi_guide_bot.bot import start_bot


if __name__ == "__main__":
    create_db_and_tables()

    if is_db_empty():
        print("DB empty — seeding...")
        seed()
    else:
        print("DB already initialized — skipping seed.")

    start_bot()