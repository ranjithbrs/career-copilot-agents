import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
# Redirect to isolated test database
TEST_DB_PATH = settings.DATA_DIR / "test_hub.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from agents.linkedin.agent import LinkedInAgent
from agents.linkedin.schemas import DraftType

def reset_test_db():
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM linkedin_drafts")

def test_recruiter_note_generation():
    reset_test_db()
    agent = LinkedInAgent()

    draft = agent.draft_recruiter_note("Google", role="SDE Intern", recruiter_name="Sarah")
    assert draft.target_company == "Google"
    assert draft.draft_type == DraftType.RECRUITER_NOTE
    # Strict LinkedIn character limit check
    assert draft.character_count <= 300
    assert "Sarah" in draft.content

def test_alumni_referral_generation():
    reset_test_db()
    agent = LinkedInAgent()

    draft = agent.draft_alumni_referral(
        company="Amazon",
        role="Software Development Engineer",
        alumni_name="Rahul",
        job_id="JOB-123456"
    )
    assert draft.target_company == "Amazon"
    assert draft.draft_type == DraftType.ALUMNI_REFERRAL
    assert "Rahul" in draft.content
    assert "JOB-123456" in draft.content

def test_milestone_post_generation():
    reset_test_db()
    agent = LinkedInAgent()

    draft = agent.draft_achievement_post(
        topic="Built a 6-Agent Career Copilot in Python",
        highlights=[
            "Automated email intelligence with Pydantic and SQLite",
            "Designed company prep cheat sheets",
            "Added Telegram push notifications"
        ]
    )
    assert draft.draft_type == DraftType.MILESTONE_POST
    assert "Career Copilot" in draft.content
    assert "#SoftwareEngineering" in draft.content

def test_draft_persistence_and_retrieval():
    reset_test_db()
    agent = LinkedInAgent()

    agent.draft_recruiter_note("Meta")
    agent.draft_alumni_referral("Apple")
    
    drafts = agent.list_drafts(limit=5)
    assert len(drafts) == 2
    assert drafts[0].target_company in ("Meta", "Apple")

if __name__ == "__main__":
    print("Running LinkedIn Agent tests manually...")
    test_recruiter_note_generation()
    print("[OK] test_recruiter_note_generation passed")
    test_alumni_referral_generation()
    print("[OK] test_alumni_referral_generation passed")
    test_milestone_post_generation()
    print("[OK] test_milestone_post_generation passed")
    test_draft_persistence_and_retrieval()
    print("[OK] test_draft_persistence_and_retrieval passed")

    # Clean up
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    print("ALL LINKEDIN AGENT TESTS PASSED SUCCESSFULLY!")
