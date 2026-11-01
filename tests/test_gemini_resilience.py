import sys
import unittest.mock as mock
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.settings as settings
TEST_DB_PATH = settings.DATA_DIR / "test_hub.db"
settings.DB_PATH = TEST_DB_PATH

from database.connection import init_db, get_db_connection
from agents.email_intel.schemas import RawEmail, EmailCategory, UrgencyLevel
from agents.email_intel.extractor import EmailExtractor
from agents.placement.agent import PlacementAgent

def setup_module():
    init_db(TEST_DB_PATH)
    with get_db_connection(TEST_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mock_interviews")
        cursor.execute("DELETE FROM company_dossiers")
        cursor.execute("DELETE FROM action_items")

def teardown_module():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

def test_email_extractor_gemini_rate_limit_429():
    """Verify EmailExtractor gracefully degrades to heuristic extraction on HTTP 429 Rate Limit."""
    sample_email = RawEmail(
        message_id="msg_test_429",
        sender="jobs@amazon.com",
        subject="Amazon Online Assessment Part 1 - HackerRank",
        date="2026-11-01",
        body="Dear Candidate, your Amazon Online Assessment is active. Link: https://hackerrank.com/test-amazon. Deadline: 48 hours."
    )

    extractor = EmailExtractor(api_key="mock_key", model_name="gemini-2.5-flash")
    
    # Mock client generate_content raising 429 Rate Limit
    mock_client = mock.MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 ResourceExhausted: Quota exceeded for quota metric 'Queries' and limit 'QUOTA_FOR_CORE_CALLS'")
    extractor.client = mock_client

    parsed = extractor.extract(sample_email)
    assert parsed is not None
    assert parsed.category == EmailCategory.PLACEMENT_OA
    assert parsed.urgency in (UrgencyLevel.CRITICAL, UrgencyLevel.HIGH)
    assert parsed.company_or_sender.lower() == "amazon"
    assert any("hackerrank.com" in u for u in parsed.important_urls)
    assert not parsed.is_noise

def test_email_extractor_gemini_service_unavailable_503():
    """Verify EmailExtractor gracefully degrades to heuristics on HTTP 503 Service Unavailable."""
    sample_email = RawEmail(
        message_id="msg_test_503",
        sender="interviews@google.com",
        subject="Google Technical Screening Interview Schedule",
        date="2026-11-01",
        body="Your Google technical interview round is scheduled for Friday. Please confirm."
    )

    extractor = EmailExtractor(api_key="mock_key")
    mock_client = mock.MagicMock()
    mock_client.models.generate_content.side_effect = Exception("503 Service Unavailable: The model is currently overloaded. Please try again.")
    extractor.client = mock_client

    parsed = extractor.extract(sample_email)
    assert parsed is not None
    assert parsed.category == EmailCategory.INTERVIEW_INVITE
    assert parsed.company_or_sender.lower() == "google"
    assert parsed.urgency == UrgencyLevel.CRITICAL

def test_email_extractor_gemini_timeout():
    """Verify EmailExtractor gracefully degrades to heuristics on network TimeoutError."""
    sample_email = RawEmail(
        message_id="msg_test_timeout",
        sender="noreply@medium.com",
        subject="Medium Daily Digest: 5 Python Tips",
        date="2026-11-01",
        body="Here are top stories for today. Unsubscribe anytime."
    )

    extractor = EmailExtractor(api_key="mock_key")
    mock_client = mock.MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Connection to generativelanguage.googleapis.com timed out.")
    extractor.client = mock_client

    parsed = extractor.extract(sample_email)
    assert parsed is not None
    assert parsed.is_noise is True
    assert parsed.category == EmailCategory.NEWSLETTER_SPAM

def test_email_extractor_gemini_malformed_json():
    """Verify EmailExtractor falls back to heuristics when Gemini returns non-JSON / corrupt output."""
    sample_email = RawEmail(
        message_id="msg_test_bad_json",
        sender="recruitment@microsoft.com",
        subject="Microsoft Coding Assessment Due Date",
        date="2026-11-01",
        body="Please complete your Microsoft test by Sunday."
    )

    extractor = EmailExtractor(api_key="mock_key")
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.text = "Error: Invalid JSON response <<EOF...>>"
    mock_client.models.generate_content.return_value = mock_response
    extractor.client = mock_client

    parsed = extractor.extract(sample_email)
    assert parsed is not None
    assert parsed.category in (EmailCategory.PLACEMENT_OA, EmailCategory.DEADLINE_ALERT)
    assert parsed.company_or_sender.lower() == "microsoft"

def test_placement_agent_dossier_gemini_failure():
    """Verify PlacementAgent returns standard baseline dossier when Gemini API fails."""
    agent = PlacementAgent()
    
    with mock.patch("agents.placement.agent.GEMINI_API_KEY", "mock_key"):
        with mock.patch("google.genai.Client") as mock_client_cls:
            mock_client = mock.MagicMock()
            mock_client.models.generate_content.side_effect = Exception("429 Rate Limit Exceeded")
            mock_client_cls.return_value = mock_client

            dossier = agent.generate_dossier("UnknownStartup", role="Backend Engineer", inject_tasks=False)
            assert dossier is not None
            assert dossier.company_name == "UnknownStartup"
            assert len(dossier.dsa_focus) > 0
            assert len(dossier.cs_fundamentals) > 0
            assert len(dossier.actionable_prep_tasks) > 0

def test_placement_agent_star_grading_resilience():
    """Verify grade_behavioral_answer falls back to deterministic STAR rubric engine on API failure."""
    agent = PlacementAgent()
    answer = "When working on our microservices project, the goal was to reduce API response latency. I designed an asynchronous Redis caching layer in Python and refactored SQL queries, which reduced response time by 45% across 50,000 requests."

    with mock.patch("agents.placement.agent.GEMINI_API_KEY", "mock_key"):
        with mock.patch("google.genai.Client") as mock_client_cls:
            mock_client = mock.MagicMock()
            mock_client.models.generate_content.side_effect = Exception("500 Internal Server Error")
            mock_client_cls.return_value = mock_client

            result = agent.grade_behavioral_answer("Amazon", "Tell me about a difficult technical challenge.", answer)
            assert result is not None
            assert 1 <= result["score"] <= 10
            assert "star_breakdown" in result
            assert result["star_breakdown"]["situation"] != ""
            assert result["star_breakdown"]["action"] != ""
            assert result["star_breakdown"]["result"] != ""
            assert len(result["strengths"]) > 0
            assert len(result["improved_rewrite"]) > 0

            # Verify saved to database
            with get_db_connection(TEST_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT score, star_feedback FROM mock_interviews WHERE company_name = 'Amazon'")
                row = cursor.fetchone()
                assert row is not None
                assert row["score"] == result["score"]
