from databases import Database
from sqlalchemy import create_engine
from app.db.base import Base

# The database URL should point to the data volume in the Docker container.
DATABASE_URL = "sqlite:////app/data/trading_portal.db"

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
