import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
# Redirect to isolated test database
TEST_DB_PATH = settings.DATA_DIR / "test_hub_learning.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from agents.learning.agent import LearningAgent

def reset_test_db():
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM learning_topics")
        cursor.execute("DELETE FROM learning_logs")
        cursor.execute("DELETE FROM action_items")

def test_curriculum_seeding_and_daily_targets():
    reset_test_db()
    agent = LearningAgent()

    # Verify topics seeded
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM learning_topics")
        count = cursor.fetchone()["count"]
        assert count > 5

    # Get daily targets
    targets = agent.get_daily_targets(inject_tasks=True)
    assert len(targets) >= 2
    assert any(t.subject.value == "DSA" for t in targets)
    assert any(t.subject.value in ("PYTHON", "SQL") for t in targets)

    # Verify task injected into action_items
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM action_items WHERE origin_agent = 'LEARNING'")
        task_count = cursor.fetchone()["count"]
        assert task_count >= 2

def test_log_study_session_and_spaced_repetition():
    reset_test_db()
    agent = LearningAgent()

    # Log high confidence session
    agent.log_session(topic_name="Arrays & Hashing", problems_solved=3, confidence=5, notes="Mastered Top-K")

    # Verify log recorded
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM learning_logs WHERE topic_name LIKE '%Arrays%'")
        log = cursor.fetchone()
        assert log is not None
        assert log["problems_solved"] == 3
        assert log["confidence_rating"] == 5

        # Verify mastery level increased
        cursor.execute("SELECT mastery_level, review_count FROM learning_topics WHERE topic_name LIKE '%Arrays%'")
        topic = cursor.fetchone()
        assert topic["mastery_level"] >= 2
        assert topic["review_count"] == 1

def test_mastery_report_generation():
    reset_test_db()
    agent = LearningAgent()
    agent.log_session("Decorators", problems_solved=2, confidence=4)

    summary = agent.get_mastery_report()
    assert summary.total_topics > 5
    assert summary.total_problems_solved >= 2
    assert "SKILL & LEARNING MASTERY REPORT" in summary.formatted_report

if __name__ == "__main__":
    print("Running Learning Agent tests manually...")
    test_curriculum_seeding_and_daily_targets()
    print("[OK] test_curriculum_seeding_and_daily_targets passed")
    test_log_study_session_and_spaced_repetition()
    print("[OK] test_log_study_session_and_spaced_repetition passed")
    test_mastery_report_generation()
    print("[OK] test_mastery_report_generation passed")

    # Clean up
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    print("ALL LEARNING AGENT TESTS PASSED SUCCESSFULLY!")
