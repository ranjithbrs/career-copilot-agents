import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
# Redirect to isolated test database
TEST_DB_PATH = settings.DATA_DIR / "test_hub_project.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from agents.project.agent import ProjectAgent

def reset_test_db():
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tracked_projects")
        cursor.execute("DELETE FROM action_items")

def test_project_audit_current_repo():
    reset_test_db()
    agent = ProjectAgent()

    # Audit current career-copilot-agents repo
    current_dir = Path(__file__).resolve().parent.parent
    audit = agent.audit_repository(repo_path=str(current_dir), inject_task=True)

    assert audit.project_name == "career-copilot-agents"
    assert audit.has_readme is True
    assert audit.has_tests is True
    assert audit.health_score >= 50
    assert "PROJECT AUDIT: CAREER-COPILOT-AGENTS" in audit.formatted_summary

    # Verify task injected into action_items
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM action_items WHERE origin_agent = 'PROJECT'")
        assert cursor.fetchone()["count"] >= 1

        # Verify saved to tracked_projects table
        cursor.execute("SELECT * FROM tracked_projects WHERE project_name = 'career-copilot-agents'")
        assert cursor.fetchone() is not None

if __name__ == "__main__":
    print("Running Project Agent tests manually...")
    test_project_audit_current_repo()
    print("[OK] test_project_audit_current_repo passed")

    # Clean up
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    print("ALL PROJECT AGENT TESTS PASSED SUCCESSFULLY!")
