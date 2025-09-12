from databases import Database
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from pathlib import Path
from .base import Base

# --- Path Setup ---
# Build paths inside the project like this: BASE_DIR / 'subdir'.
# This makes the database path relative to the project root, not the current working dir.
BASE_DIR = Path(__file__).resolve().parents[3]
data_dir = BASE_DIR / "data"
data_dir.mkdir(exist_ok=True)  # Ensure data directory exists
DB_PATH = data_dir / "trading_portal.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"


# The 'databases' library provides async support for a variety of databases.
database = Database(DATABASE_URL)

# The SQLAlchemy engine with connection pooling for better performance
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)

# The metadata object holds all the schema information of the declarative models.
metadata = Base.metadata

def create_tables():
    """
    Creates all tables in the database.
    This is a synchronous operation and should be called once on application startup.
    In a production environment, this would be handled by a migration tool like Alembic.
    """
    try:
        Base.metadata.create_all(bind=engine)
        from ..core.logging import logger
        logger.info("Database tables created successfully")
    except Exception as e:
        from ..core.logging import logger
        logger.error(f"Error creating database tables: {e}")
        raise
