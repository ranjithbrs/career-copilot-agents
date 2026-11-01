import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config.settings as settings
from database.connection import init_db

TEST_DB_PATH = settings.DATA_DIR / "test_hub.db"
settings.DB_PATH = TEST_DB_PATH

@pytest.fixture(autouse=True)
def ensure_test_db():
    """Ensure settings.DB_PATH is always pointing to test_hub.db for all tests."""
    settings.DB_PATH = TEST_DB_PATH
    init_db(TEST_DB_PATH)
    yield
