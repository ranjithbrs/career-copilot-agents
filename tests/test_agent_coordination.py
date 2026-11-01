import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
TEST_DB_PATH = settings.DATA_DIR / "test_hub.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from agents.email_intel.agent import EmailIntelligenceAgent
from agents.placement.agent import PlacementAgent
from agents.learning.agent import LearningAgent
from agents.project.agent import ProjectAgent
from agents.linkedin.agent import LinkedInAgent
from agents.daily_assistant.agent import DailyAssistantAgent
from daemon import AutonomousOrchestrator

def setup_module():
    init_db(TEST_DB_PATH)
    reset_db()

def reset_db():
    with get_db_connection(TEST_DB_PATH) as conn:
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
        cursor.execute("DELETE FROM focus_sessions")
        cursor.execute("DELETE FROM mock_interviews")

def teardown_module():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

def test_agent_1_email_intelligence_independent():
    """Agent 1 works independently to ingest, classify, and store emails."""
    reset_db()
    agent = EmailIntelligenceAgent()
    res = agent.run_mock_cycle()
    assert res["processed"] >= 4
    assert len(res["critical_alerts"]) >= 1
    
    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM emails_raw")
        assert cursor.fetchone()["cnt"] >= 4

def test_agent_2_placement_independent():
    """Agent 2 works independently to manage pipeline, generate dossiers, and grade answers."""
    reset_db()
    agent = PlacementAgent()
    entry_id = agent.add_pipeline_entry("Uber", "Backend Engineer", "APPLIED")
    assert entry_id > 0

    dossier = agent.generate_dossier("Uber", inject_tasks=True)
    assert dossier.company_name == "Uber"
    assert len(dossier.dsa_focus) > 0

    eval_result = agent.grade_behavioral_answer("Uber", "Tell me about yourself.", "When working at my university project, my goal was...")
    assert 1 <= eval_result["score"] <= 10

def test_agent_3_learning_independent():
    """Agent 3 works independently to seed curriculum, schedule SM-2 targets, and log progress."""
    reset_db()
    agent = LearningAgent()
    targets = agent.get_daily_targets(inject_tasks=True)
    assert len(targets) >= 2

    # Log study session
    agent.log_session(topic_name="Arrays & Hashing", problems_solved=2, confidence=4, notes="Solved BFS problems")
    summary = agent.get_mastery_report()
    assert summary.total_problems_solved >= 2

def test_agent_4_project_independent():
    """Agent 4 works independently to audit git status and code hygiene."""
    reset_db()
    agent = ProjectAgent()
    current_dir = Path(__file__).resolve().parent.parent
    audit = agent.audit_repository(str(current_dir), inject_task=True)
    assert audit.project_name == "career-copilot-agents"
    assert audit.health_score > 0
    assert audit.has_git is True
    assert audit.has_readme is True

def test_agent_5_linkedin_independent():
    """Agent 5 works independently to draft recruiter notes and alumni outreach."""
    reset_db()
    agent = LinkedInAgent()
    draft = agent.draft_recruiter_note("Amazon", "SDE 1", "Sarah")
    assert draft.character_count <= 300
    assert "Amazon" in draft.content

    alumni_draft = agent.draft_alumni_referral("Google", "SWE", "Alex", "REQ-101")
    assert "Google" in alumni_draft.content

def test_agent_6_daily_assistant_independent():
    """Agent 6 works independently to compile briefings, evening reviews, and track action items."""
    reset_db()
    assistant = DailyAssistantAgent()
    # Add a custom task
    task_id = assistant.add_action_item("Solve LeetCode #200", priority="P0", due_date="Tonight 9 PM")
    assert task_id > 0

    briefing = assistant.generate_morning_briefing()
    assert briefing.total_pending >= 1
    assert "DAILY BRIEFING" in briefing.formatted_summary

    # Complete task and review
    assistant.mark_action_item_completed(task_id)
    review = assistant.generate_evening_review()
    assert review.completed_count >= 1

def test_six_agents_coordination_together():
    """Test full multi-agent workflow: Email -> Placement -> LinkedIn -> Learning -> Project -> Briefing."""
    reset_db()
    orchestrator = AutonomousOrchestrator(use_live_email=False)
    
    # Run full coordinated sync
    results = orchestrator.run_full_sync(send_telegram=False, print_output=False)
    
    # 1. Email Agent produced outputs
    assert results["emails"]["processed"] >= 4
    
    # 2. Placement dossiers were generated for identified companies
    assert "dossiers_generated" in results
    assert results["dossiers_generated"] >= 1
    
    # 3. Learning targets scheduled
    assert len(results["study_targets"]) >= 2
    
    # 4. Project audit completed
    assert results["project_audit"]["project_name"] == "career-copilot-agents"
    
    # 5. LinkedIn drafts generated for pipeline companies
    assert len(results["outreach_drafts"]) >= 1
    
    # 6. Daily Briefing synthesized
    briefing = results["briefing"]
    assert briefing["total_pending"] > 0
    assert len(results["errors"]) == 0

def test_coordination_error_resilience():
    """Verify that if one agent fails during orchestrator sync, the other agents still run and complete."""
    reset_db()
    orchestrator = AutonomousOrchestrator(use_live_email=False)

    # Intentionally corrupt learning agent to simulate a crash
    original_get_targets = orchestrator.learning_agent.get_daily_targets
    orchestrator.learning_agent.get_daily_targets = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Simulated Learning Agent Fault"))

    try:
        results = orchestrator.run_full_sync(send_telegram=False, print_output=False)
        # Verify orchestrator did not crash
        assert results is not None
        assert "emails" in results
        assert "project_audit" in results
        assert "briefing" in results
        # Verify the error was trapped and recorded
        assert any("LearningAgent" in err for err in results["errors"])
    finally:
        orchestrator.learning_agent.get_daily_targets = original_get_targets
