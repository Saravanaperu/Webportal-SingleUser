from databases import Database
from sqlalchemy import create_engine
from pathlib import Path
from app.db.base import Base

# --- Path Setup ---
# Build paths inside the project like this: BASE_DIR / 'subdir'.
# This makes the database path relative to the project root, not the current working dir.
BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "data" / "trading_portal.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


# The 'databases' library provides async support for a variety of databases.
database = Database(DATABASE_URL)

# The SQLAlchemy engine is used for synchronous operations like creating tables.
# The connect_args is necessary for SQLite to work correctly in a multi-threaded environment like FastAPI.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# The metadata object holds all the schema information of the declarative models.
metadata = Base.metadata

def create_tables():
    """
    Creates all tables in the database.
    This is a synchronous operation and should be called once on application startup.
    In a production environment, this would be handled by a migration tool like Alembic.
    """
    Base.metadata.create_all(bind=engine)
