# backend/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Check for PostgreSQL connection string
POSTGRES_URL = os.getenv("POSTGRES_URL")

if POSTGRES_URL:
    # Use PostgreSQL (Vercel Postgres or external)
    SQLALCHEMY_DATABASE_URL = POSTGRES_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # Fallback to SQLite (ephemeral filesystem on Vercel)
    # Note: Data will be lost on cold start (function instance recreation)
    BASE_DIR = Path(__file__).resolve().parent
    DB_PATH = BASE_DIR / "data" / "db" / "irkg.db"
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
