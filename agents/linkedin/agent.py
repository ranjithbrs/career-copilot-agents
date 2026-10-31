import logging
from typing import List, Optional
from database.connection import get_db_connection
from agents.linkedin.schemas import DraftType, LinkedInDraft
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

class LinkedInAgent:
    """Agent 6: Generates personalized recruiter connection notes, alumni referral requests, and build-in-public posts."""

    def __init__(self):
        pass

    def draft_recruiter_note(self, company: str, role: str = "Software Engineer", recruiter_name: Optional[str] = None) -> LinkedInDraft:
        """
        Draft a high-converting connection note strictly under LinkedIn's 300-character limit.
        """
        greeting = f"Hi {recruiter_name}," if recruiter_name else "Hi,"
        template = (
            f"{greeting} I've been following {company}'s engineering work and recently applied for the "
            f"{role} role. With hands-on experience in Python, systems, and algorithms, I'd love to connect "
            f"and follow your updates. Thank you!"
        )
        # Ensure under 300 characters
        if len(template) > 295:
            template = (
                f"{greeting} Applied for {company}'s {role} opening. With strong Python, DSA, and systems experience, "
                f"I'd love to connect and follow your updates!"
            )

        draft = LinkedInDraft(
            target_company=company,
            draft_type=DraftType.RECRUITER_NOTE,
            recipient_name=recruiter_name,
            content=template,
            character_count=len(template)
        )
        draft.id = self._save_draft(draft)
        return draft

    def draft_alumni_referral(
        self,
        company: str,
        role: str = "Software Engineer",
        alumni_name: Optional[str] = None,
        job_id: Optional[str] = None,
        college_name: str = "our university"
    ) -> LinkedInDraft:
        """
        Draft a warm, respectful, and direct referral request for college alumni.
        """
        greeting = f"Dear {alumni_name}," if alumni_name else "Hello,"
        job_ref = f" (Job ID: {job_id})" if job_id else ""
        content = (
            f"{greeting}\n\n"
            f"Hope you are doing well! I'm a fellow student/alumnus from {college_name}. "
            f"I came across the {role} position at {company}{job_ref} and would love to apply.\n\n"
            f"I have built projects in Python/distributed systems and regularly practice DSA (solving medium-to-hard "
            f"problems across graphs, DP, and trees). Given your experience at {company}, I would be incredibly grateful "
            f"if you could review my resume for a potential referral.\n\n"
            f"I have my resume and portfolio ready to share whenever convenient. Thank you so much for your time!\n\n"
            f"Best regards,\n[Your Name]"
        )

        draft = LinkedInDraft(
            target_company=company,
            draft_type=DraftType.ALUMNI_REFERRAL,
            recipient_name=alumni_name,
            content=content,
            character_count=len(content)
        )
        draft.id = self._save_draft(draft)
        return draft

    def draft_achievement_post(
        self,
        topic: str,
        highlights: Optional[List[str]] = None,
        tech_stack: Optional[str] = "Python, SQLite, Multi-Agent Systems"
    ) -> LinkedInDraft:
        """
        Draft an engaging, professional 'Build in Public' milestone post.
        """
        bullets = ""
        if highlights:
            bullets = "\n" + "\n".join([f"- {h}" for h in highlights]) + "\n"
        else:
            bullets = (
                "\n- Architected an autonomous multi-agent coordination loop\n"
                "- Extracted real-time signals from raw career notifications\n"
                "- Implemented persistent SQLite state synchronization\n"
            )

        content = (
            f"Excited to share a recent milestone: {topic}! 🚀\n\n"
            f"Over the past few weeks, I focused on turning manual productivity workflows into an automated engine. "
            f"Here is what I built and learned:\n"
            f"{bullets}\n"
            f"🛠 Tech Stack: {tech_stack}\n\n"
            f"Building end-to-end systems from first principles has been an incredible learning experience. "
            f"Would love to hear feedback or thoughts from fellow engineers!\n\n"
            f"#SoftwareEngineering #Python #Productivity #SystemDesign #OpenSource #ContinuousLearning"
        )

        draft = LinkedInDraft(
            target_company=None,
            draft_type=DraftType.MILESTONE_POST,
            recipient_name=None,
            content=content,
            character_count=len(content)
        )
        draft.id = self._save_draft(draft)
        return draft

    def _save_draft(self, draft: LinkedInDraft) -> int:
        """Persist draft into linkedin_drafts table."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO linkedin_drafts (target_company, draft_type, recipient_name, content, character_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    draft.target_company,
                    draft.draft_type.value,
                    draft.recipient_name,
                    draft.content,
                    draft.character_count
                )
            )
            return cursor.lastrowid

    def list_drafts(self, limit: int = 5) -> List[LinkedInDraft]:
        """Retrieve recent drafts from the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, target_company, draft_type, recipient_name, content, character_count, is_sent, created_at
                FROM linkedin_drafts
                ORDER BY id DESC LIMIT ?
                """,
                (limit,)
            )
            return [
                LinkedInDraft(
                    id=row["id"],
                    target_company=row["target_company"],
                    draft_type=DraftType(row["draft_type"]),
                    recipient_name=row["recipient_name"],
                    content=row["content"],
                    character_count=row["character_count"],
                    is_sent=bool(row["is_sent"]),
                    created_at=str(row["created_at"])
                )
                for row in cursor.fetchall()
            ]
