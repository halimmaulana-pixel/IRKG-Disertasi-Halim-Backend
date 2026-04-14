"""
Initialize an empty database schema (no data rows).
Usage:
  python -m services.init_empty_db
"""
from database import engine
from models import Base


def run():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[DB] Empty schema initialized.")


if __name__ == "__main__":
    run()
