import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import config.settings as settings
from database.models import INIT_SCHEMA_SQL

def init_db(db_path: Optional[Path | str] = None) -> None:
    """Initialize database tables and indexes if they do not exist."""
    target = Path(db_path) if db_path else settings.DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as conn:
        cursor = conn.cursor()
        cursor.executescript(INIT_SCHEMA_SQL)
        conn.commit()

@contextmanager
def get_db_connection(db_path: Optional[Path | str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connection with row factory enabled."""
    target = Path(db_path) if db_path else settings.DB_PATH
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
