import sys
import threading
import sqlite3
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
TEST_DB_PATH = settings.DATA_DIR / "test_hub.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection

def setup_module():
    """Ensure clean test database."""
    init_db(TEST_DB_PATH)
    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emails_raw")
        cursor.execute("DELETE FROM deadlines")
        cursor.execute("DELETE FROM placement_pipeline")
        cursor.execute("DELETE FROM action_items")
        cursor.execute("DELETE FROM focus_sessions")
        cursor.execute("DELETE FROM mock_interviews")

def teardown_module():
    """Clean up test database file."""
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

def test_wal_mode_and_pragmas():
    """Verify that SQLite is running with Write-Ahead Logging (WAL) and busy timeout enabled."""
    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.lower() == "wal", f"Expected WAL mode, got {journal_mode}"

        cursor.execute("PRAGMA busy_timeout;")
        busy_timeout = cursor.fetchone()[0]
        assert busy_timeout >= 5000, f"Expected busy_timeout >= 5000ms, got {busy_timeout}"

def test_schema_tables_exist():
    """Verify all 10 core tables and schemas exist."""
    required_tables = {
        "emails_raw",
        "deadlines",
        "placement_pipeline",
        "action_items",
        "company_dossiers",
        "linkedin_drafts",
        "learning_topics",
        "learning_logs",
        "tracked_projects",
        "focus_sessions",
        "mock_interviews"
    }
    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        for table in required_tables:
            assert table in tables, f"Missing required table: {table}"

def test_transaction_commit_and_persistence_across_connections():
    """Verify data committed in one connection is immediately readable in a separate connection."""
    # Write in connection 1
    with get_db_connection(TEST_DB_PATH) as conn1:
        cursor1 = conn1.cursor()
        cursor1.execute(
            "INSERT INTO action_items (origin_agent, task_description, priority) VALUES (?, ?, ?)",
            ("TEST_AGENT", "Verify persistence across connections", "P0")
        )
        inserted_id = cursor1.lastrowid

    # Read in connection 2
    with get_db_connection(TEST_DB_PATH) as conn2:
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT id, origin_agent, task_description, priority FROM action_items WHERE id = ?", (inserted_id,))
        row = cursor2.fetchone()
        assert row is not None
        assert row["origin_agent"] == "TEST_AGENT"
        assert row["task_description"] == "Verify persistence across connections"
        assert row["priority"] == "P0"

def test_transaction_rollback_on_exception():
    """Verify that an unhandled exception inside get_db_connection automatically rolls back changes."""
    initial_count = 0
    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM action_items")
        initial_count = cursor.fetchone()["count"]

    try:
        with get_db_connection(TEST_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO action_items (origin_agent, task_description, priority) VALUES (?, ?, ?)",
                ("FAIL_AGENT", "This should rollback", "P3")
            )
            # Intentionally simulate an error before exiting context
            raise RuntimeError("Simulated crash during transaction")
    except RuntimeError:
        pass

    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM action_items")
        after_count = cursor.fetchone()["count"]
        assert after_count == initial_count, "Transaction was not rolled back after exception!"

def test_concurrent_multi_thread_reads_and_writes():
    """Verify that concurrent threads simulating background agents read and write without database lock errors."""
    errors = []
    num_threads = 6
    ops_per_thread = 20

    def worker(worker_id: int):
        try:
            for i in range(ops_per_thread):
                with get_db_connection(TEST_DB_PATH) as conn:
                    cursor = conn.cursor()
                    # Write operation
                    cursor.execute(
                        """
                        INSERT INTO focus_sessions (task_description, session_type, duration_minutes)
                        VALUES (?, ?, ?)
                        """,
                        (f"Worker {worker_id} Task {i}", "DEEP_WORK", 25)
                    )
                    # Read operation
                    cursor.execute("SELECT COUNT(*) FROM focus_sessions")
                    _ = cursor.fetchone()[0]
        except Exception as e:
            errors.append((worker_id, e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Encountered concurrency errors during multi-agent test: {errors}"

    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM focus_sessions")
        total_sessions = cursor.fetchone()["count"]
        assert total_sessions == num_threads * ops_per_thread
