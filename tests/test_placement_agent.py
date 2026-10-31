import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
# Redirect to isolated test database
TEST_DB_PATH = settings.DATA_DIR / "test_hub_placement.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from agents.placement.agent import PlacementAgent
from agents.placement.schemas import HiringStage

def reset_test_db():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
    init_db()

def test_company_dossier_generation_and_task_injection():
    reset_test_db()
    agent = PlacementAgent()

    # Generate Amazon dossier
    dossier = agent.generate_dossier("Amazon", role="SDE Intern", inject_tasks=True)
    assert dossier.company_name == "Amazon"
    assert len(dossier.dsa_focus) > 0
    assert len(dossier.cs_fundamentals) > 0
    assert len(dossier.behavioral_topics) > 0
    assert len(dossier.actionable_prep_tasks) > 0
    assert "DOSSIER: AMAZON" in dossier.full_dossier_text

    # Verify dossier was saved to database
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_dossiers WHERE company_name = 'Amazon'")
        row = cursor.fetchone()
        assert row is not None

        # Verify prep tasks were injected into action_items table
        cursor.execute("SELECT COUNT(*) as count FROM action_items WHERE origin_agent = 'PLACEMENT'")
        task_count = cursor.fetchone()["count"]
        assert task_count >= len(dossier.actionable_prep_tasks)

def test_pipeline_stage_advancement():
    reset_test_db()
    agent = PlacementAgent()

    # Seed a pipeline entry
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO placement_pipeline (company_name, role, status)
            VALUES ('Microsoft', 'Software Engineer', 'OA_PENDING')
            """
        )
        placement_id = cursor.lastrowid

    # Advance stage to INTERVIEW_SCHEDULED
    success = agent.advance_stage(placement_id, HiringStage.INTERVIEW_SCHEDULED)
    assert success is True

    # Verify updated
    pipeline = agent.get_pipeline()
    assert len(pipeline) == 1
    assert pipeline[0].status == "INTERVIEW_SCHEDULED"

if __name__ == "__main__":
    print("Running Placement Agent tests manually...")
    test_company_dossier_generation_and_task_injection()
    print("[OK] test_company_dossier_generation_and_task_injection passed")
    test_pipeline_stage_advancement()
    print("[OK] test_pipeline_stage_advancement passed")

    # Clean up
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    print("ALL PLACEMENT AGENT TESTS PASSED SUCCESSFULLY!")
