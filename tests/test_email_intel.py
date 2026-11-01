import os
import sys
import sqlite3
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
# Redirect to isolated test database
TEST_DB_PATH = settings.DATA_DIR / "test_hub.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from agents.email_intel.agent import EmailIntelligenceAgent
from agents.email_intel.schemas import RawEmail, EmailCategory, UrgencyLevel
from agents.email_intel.ingester import MockEmailIngester

def reset_test_db():
    """Ensure test database starts completely clean."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emails_raw")
        cursor.execute("DELETE FROM deadlines")
        cursor.execute("DELETE FROM placement_pipeline")
        cursor.execute("DELETE FROM action_items")

def test_database_initialization():
    """Verify that all required tables are properly created in SQLite."""
    reset_test_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]
        
        assert "emails_raw" in tables
        assert "deadlines" in tables
        assert "placement_pipeline" in tables
        assert "action_items" in tables

def test_mock_email_processing_and_routing():
    """Verify that simulated emails are properly parsed, classified, and routed to tables."""
    reset_test_db()
    agent = EmailIntelligenceAgent()
    
    # Run cycle with mock emails
    results = agent.run_mock_cycle()
    assert results["processed"] >= 4
    
    # Verify Amazon OA was recorded in placement_pipeline
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM placement_pipeline WHERE company_name LIKE '%Amazon%'")
        amazon_entry = cursor.fetchone()
        assert amazon_entry is not None
        assert "hackerrank" in amazon_entry["test_link"].lower()
        assert amazon_entry["status"] == "OA_PENDING"

        # Verify Spam was marked as is_noise
        cursor.execute("SELECT is_noise FROM emails_raw WHERE message_id = 'mock_004_marketing_newsletter'")
        spam_entry = cursor.fetchone()
        assert spam_entry is not None
        assert spam_entry["is_noise"] == 1

        # Verify Deadlines table has entries
        cursor.execute("SELECT COUNT(*) as count FROM deadlines")
        deadline_count = cursor.fetchone()["count"]
        assert deadline_count > 0

        # Verify Action items table has P0/P1 tasks
        cursor.execute("SELECT COUNT(*) as count FROM action_items WHERE priority IN ('P0', 'P1')")
        urgent_tasks_count = cursor.fetchone()["count"]
        assert urgent_tasks_count > 0

def test_deduplication():
    """Verify that re-processing the same emails does not duplicate records in the database."""
    init_db()
    agent = EmailIntelligenceAgent()

    # First run processes or skips existing
    results1 = agent.run_mock_cycle()

    # Second run MUST skip all
    results2 = agent.run_mock_cycle()
    assert results2["processed"] == 0
    assert results2["skipped_duplicates"] >= 4

if __name__ == "__main__":
    print("Running tests manually...")
    test_database_initialization()
    print("[OK] test_database_initialization passed")
    test_mock_email_processing_and_routing()
    print("[OK] test_mock_email_processing_and_routing passed")
    test_deduplication()
    print("[OK] test_deduplication passed")
    
    # Clean up test database
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
            
    print("ALL TESTS PASSED SUCCESSFULLY!")
