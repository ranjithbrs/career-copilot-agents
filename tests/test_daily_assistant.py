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
from agents.daily_assistant.agent import DailyAssistantAgent

def reset_test_db():
    """Ensure test database starts completely clean."""
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
    init_db()

def test_morning_briefing_generation():
    reset_test_db()
    # Seed mock email intelligence
    email_agent = EmailIntelligenceAgent()
    email_agent.run_mock_cycle()

    assistant = DailyAssistantAgent()
    briefing = assistant.generate_morning_briefing()

    assert briefing.total_pending > 0
    assert len(briefing.p0_tasks) > 0 or len(briefing.p1_tasks) > 0
    assert len(briefing.placement_events) > 0
    assert len(briefing.active_deadlines) > 0
    assert "DAILY BRIEFING" in briefing.formatted_summary

def test_task_completion_and_evening_review():
    reset_test_db()
    email_agent = EmailIntelligenceAgent()
    email_agent.run_mock_cycle()

    assistant = DailyAssistantAgent()

    # Get first task
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM action_items LIMIT 1")
        task_id = cursor.fetchone()["id"]

    # Mark as completed
    assert assistant.mark_action_item_completed(task_id) is True

    # Check evening review
    review = assistant.generate_evening_review()
    assert review.completed_count >= 1
    assert "EVENING ACCOUNTABILITY REVIEW" in review.formatted_summary

def test_add_custom_task():
    reset_test_db()
    assistant = DailyAssistantAgent()
    task_id = assistant.add_action_item("Practice 2 LeetCode Medium Graphs", priority="P0", due_date="Tonight")
    assert task_id > 0

    briefing = assistant.generate_morning_briefing()
    assert any("LeetCode Medium" in t.task_description for t in briefing.p0_tasks)

if __name__ == "__main__":
    print("Running Daily Assistant tests manually...")
    test_morning_briefing_generation()
    print("[OK] test_morning_briefing_generation passed")
    test_task_completion_and_evening_review()
    print("[OK] test_task_completion_and_evening_review passed")
    test_add_custom_task()
    print("[OK] test_add_custom_task passed")

    # Clean up test database
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    print("ALL DAILY ASSISTANT TESTS PASSED SUCCESSFULLY!")
