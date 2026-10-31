import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
# Redirect to isolated test database
TEST_DB_PATH = settings.DATA_DIR / "test_hub_daemon.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from daemon import AutonomousOrchestrator

def reset_test_db():
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emails_raw")
        cursor.execute("DELETE FROM deadlines")
        cursor.execute("DELETE FROM placement_pipeline")
        cursor.execute("DELETE FROM action_items")
        cursor.execute("DELETE FROM company_dossiers")
        cursor.execute("DELETE FROM linkedin_drafts")
        cursor.execute("DELETE FROM learning_topics")
        cursor.execute("DELETE FROM learning_logs")
        cursor.execute("DELETE FROM tracked_projects")

def test_full_autonomous_sync_cycle():
    reset_test_db()
    orchestrator = AutonomousOrchestrator(use_live_email=False)

    # Run complete sync
    results = orchestrator.run_full_sync(send_telegram=False, print_output=False)

    # 1. Verify email ingestion
    assert "emails" in results
    assert results["emails"]["processed"] >= 4

    # 2. Verify study targets
    assert "study_targets" in results
    assert len(results["study_targets"]) >= 2

    # 3. Verify project audit
    assert "project_audit" in results
    assert results["project_audit"]["project_name"] == "career-copilot-agents"

    # 4. Verify briefing synthesis
    assert "briefing" in results
    briefing = results["briefing"]
    assert briefing["total_pending"] > 0
    assert "DAILY BRIEFING" in briefing["formatted_summary"]

    # 5. Verify database contains records across domains
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM emails_raw")
        assert cursor.fetchone()["count"] >= 4

        cursor.execute("SELECT COUNT(*) as count FROM action_items")
        assert cursor.fetchone()["count"] > 0

        cursor.execute("SELECT COUNT(*) as count FROM placement_pipeline")
        assert cursor.fetchone()["count"] > 0

if __name__ == "__main__":
    print("Running Autonomous Orchestrator tests manually...")
    test_full_autonomous_sync_cycle()
    print("[OK] test_full_autonomous_sync_cycle passed")

    # Clean up
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    print("ALL AUTONOMOUS DAEMON TESTS PASSED SUCCESSFULLY!")
