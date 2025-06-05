import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional, List
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine, select

from app.models.models import Keyword, LandingPage, TrafficMetric, PageCategory, KeywordStatus

# Configure logging
logger = logging.getLogger(__name__)

# Get database directory using pathlib for better path handling
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_DIR = PROJECT_ROOT / "data"

# Ensure database directory exists with proper permissions
try:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Database directory ensured at: {DB_DIR}")
except PermissionError as e:
    logger.error(f"Permission error creating database directory: {e}")
    # Try alternative location in user home
    DB_DIR = Path.home() / ".step1_scraper" / "data"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    logger.warning(f"Using alternative database location: {DB_DIR}")

# Database URL (SQLite for MVP) - use absolute path to avoid issues
DB_PATH = DB_DIR / "database.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

logger.info(f"Database URL: {DATABASE_URL}")

# Create SQLAlchemy engine with better settings
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # Set to True for debugging SQL queries
    connect_args={
        "check_same_thread": False,  # Needed for SQLite
        "timeout": 30  # Increase timeout to prevent locking issues
    },
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,  # Connection pool size
    max_overflow=10  # Maximum overflow connections
)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Create a new database session and handle closing and rollbacks on exceptions.
    
    Usage:
        with get_session() as session:
            # Use session here
            session.add(some_object)
            session.commit()
    """
    session = Session(engine)
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_db_and_tables() -> None:
    """Create database and tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_pending_keywords(limit: Optional[int] = None) -> List[Keyword]:
    """Get a list of pending keywords to process."""
    with get_session() as session:
        query = select(Keyword).where(Keyword.status == KeywordStatus.PENDING)
        if limit:
            query = query.limit(limit)
        return session.exec(query).all()


def update_keyword_status(keyword_id: int, status: str) -> bool:
    """Update the status of a keyword.
    
    Args:
        keyword_id: ID of the keyword to update
        status: Status string ('pending', 'processing', 'completed', 'failed')
        
    Returns:
        bool: True if update was successful, False otherwise
        
    Raises:
        ValueError: If the status value is invalid
        RuntimeError: If database error occurs during update
    """
    # Convert string status to enum if needed
    status_value = status
    if isinstance(status, str):
        try:
            status_value = KeywordStatus(status)
        except ValueError:
            valid_statuses = [s.value for s in KeywordStatus]
            error_msg = f"Invalid status value: {status}. Must be one of {valid_statuses}"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
    try:
        with get_session() as session:
            keyword = session.get(Keyword, keyword_id)
            if not keyword:
                error_msg = f"Keyword with ID {keyword_id} not found"
                logging.warning(error_msg)
                return False
                
            # Update the keyword status
            keyword.status = status_value
            keyword.updated_at = __import__('datetime').datetime.utcnow()
            session.add(keyword)
            session.commit()
            logging.info(f"Updated keyword {keyword_id} status to {status}")
            return True
                
    except Exception as e:
        error_msg = f"Database error updating keyword status: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg) from e


if __name__ == "__main__":
    # When run as a script, create the database and tables
    create_db_and_tables()
    print(f"Database created at {os.path.join(DB_DIR, 'database.db')}")
    print("Tables created: Keyword, LandingPage, TrafficMetric, PageCategory")
