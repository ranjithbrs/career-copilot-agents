import datetime
import logging
from typing import List, Optional, Dict, Any
from database.connection import get_db_connection
from agents.learning.schemas import SubjectType, TopicRecord, StudyTarget, LearningSummary
from agents.learning.curriculum import CURRICULUM

logger = logging.getLogger(__name__)

class LearningAgent:
    """Agent 3: Manages continuous technical skill development across DSA, Python, and SQL with spaced repetition."""

    def __init__(self):
        self._ensure_curriculum_seeded()

    def _ensure_curriculum_seeded(self) -> None:
        """Seed default curriculum topics into the database if table is empty."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM learning_topics")
            if cursor.fetchone()["count"] == 0:
                for subject, topics in CURRICULUM.items():
                    for t in topics:
                        cursor.execute(
                            """
                            INSERT INTO learning_topics (subject, topic_name, mastery_level, next_review_due)
                            VALUES (?, ?, 1, DATE('now'))
                            """,
                            (subject, t["topic"])
                        )

    def get_daily_targets(self, inject_tasks: bool = True) -> List[StudyTarget]:
        """
        Identify high-yield study targets for today using spaced repetition (overdue or lowest mastery).
        Picks 1 DSA target + 1 Python or SQL target.
        """
        targets = []
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Select top overdue or lowest mastery DSA topic
            cursor.execute(
                """
                SELECT topic_name, mastery_level, last_reviewed_at, next_review_due
                FROM learning_topics
                WHERE subject = 'DSA'
                ORDER BY (next_review_due <= DATE('now')) DESC, mastery_level ASC, review_count ASC
                LIMIT 1
                """
            )
            dsa_row = cursor.fetchone()
            if dsa_row:
                probs = self._get_problems_for_topic("DSA", dsa_row["topic_name"])
                targets.append(StudyTarget(
                    subject=SubjectType.DSA,
                    topic_name=dsa_row["topic_name"],
                    recommended_problems=probs,
                    reason="Due for spaced repetition" if dsa_row["next_review_due"] else "Foundational mastery"
                ))

            # 2. Select top overdue Python or SQL topic
            cursor.execute(
                """
                SELECT subject, topic_name, mastery_level, next_review_due
                FROM learning_topics
                WHERE subject IN ('PYTHON', 'SQL')
                ORDER BY (next_review_due <= DATE('now')) DESC, mastery_level ASC, review_count ASC
                LIMIT 1
                """
            )
            eng_row = cursor.fetchone()
            if eng_row:
                probs = self._get_problems_for_topic(eng_row["subject"], eng_row["topic_name"])
                targets.append(StudyTarget(
                    subject=SubjectType(eng_row["subject"]),
                    topic_name=eng_row["topic_name"],
                    recommended_problems=probs,
                    reason="Due for spaced repetition" if eng_row["next_review_due"] else "Foundational mastery"
                ))

        # Injects targets into Daily Assistant action_items
        if inject_tasks:
            self._inject_targets_to_daily_assistant(targets)

        return targets

    def _get_problems_for_topic(self, subject: str, topic_name: str) -> List[str]:
        if subject in CURRICULUM:
            for item in CURRICULUM[subject]:
                if item["topic"].lower() == topic_name.lower():
                    return item["problems"]
        return [f"Practice 2 medium problems on {topic_name}"]

    def _inject_targets_to_daily_assistant(self, targets: List[StudyTarget]) -> None:
        """Inject target tasks into action_items so they show in morning briefing."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for t in targets:
                prob_preview = f" (Focus: {t.recommended_problems[0]})" if t.recommended_problems else ""
                desc = f"Study [{t.subject.value}]: {t.topic_name}{prob_preview}"
                cursor.execute(
                    "SELECT 1 FROM action_items WHERE task_description = ? AND is_completed = 0",
                    (desc,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO action_items (origin_agent, task_description, priority)
                        VALUES (?, ?, ?)
                        """,
                        ("LEARNING", desc, "P1")
                    )

    def log_session(self, topic_name: str, problems_solved: int = 1, confidence: int = 3, notes: str = "") -> None:
        """
        Record a completed practice session and update spaced repetition schedule.
        Confidence: 1 (Very Difficult) to 5 (Mastered).
        """
        confidence = max(1, min(5, confidence))
        
        # Calculate next review date based on confidence
        intervals = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}
        days_ahead = intervals.get(confidence, 3)
        next_due = (datetime.date.today() + datetime.timedelta(days=days_ahead)).isoformat()
        now_str = datetime.date.today().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Record log
            cursor.execute(
                """
                INSERT INTO learning_logs (topic_name, problems_solved, confidence_rating, notes)
                VALUES (?, ?, ?, ?)
                """,
                (topic_name, problems_solved, confidence, notes)
            )

            # Update or insert topic
            cursor.execute(
                """
                UPDATE learning_topics
                SET last_reviewed_at = ?,
                    next_review_due = ?,
                    review_count = review_count + 1,
                    mastery_level = CASE 
                        WHEN ? >= 4 AND mastery_level < 5 THEN mastery_level + 1
                        WHEN ? <= 2 AND mastery_level > 1 THEN mastery_level - 1
                        ELSE mastery_level
                    END
                WHERE topic_name LIKE ?
                """,
                (now_str, next_due, confidence, confidence, f"%{topic_name}%")
            )

    def get_mastery_report(self) -> LearningSummary:
        """Generate a structured summary of skill mastery and review schedules."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM learning_topics")
            total = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM learning_topics WHERE mastery_level >= 4")
            mastered = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM learning_topics WHERE mastery_level BETWEEN 2 AND 3")
            in_prog = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM learning_topics WHERE next_review_due <= DATE('now')")
            overdue = cursor.fetchone()["count"]

            cursor.execute("SELECT COALESCE(SUM(problems_solved), 0) as total FROM learning_logs")
            total_solved = cursor.fetchone()["total"]

            # Topic breakdown
            cursor.execute("SELECT subject, topic_name, mastery_level, next_review_due FROM learning_topics ORDER BY subject, mastery_level DESC")
            all_topics = cursor.fetchall()

        report_lines = [
            "============================================================",
            "  SKILL & LEARNING MASTERY REPORT (DSA, PYTHON, SQL)",
            "============================================================",
            f"Total Curricula Topics: {total}",
            f"Mastered (Tier 4-5):    {mastered}",
            f"In Progress (Tier 2-3): {in_prog}",
            f"Due for Revision:       {overdue}",
            f"Total Problems Solved:  {total_solved}",
            "",
            "[*] TOPIC BREAKDOWN:"
        ]

        curr_subj = None
        for t in all_topics:
            if t["subject"] != curr_subj:
                curr_subj = t["subject"]
                report_lines.append(f"\n  -- {curr_subj} --")
            stars = "*" * t["mastery_level"] + "." * (5 - t["mastery_level"])
            due = f"Due: {t['next_review_due']}" if t["next_review_due"] else "Not started"
            report_lines.append(f"  [{stars}] {t['topic_name']} ({due})")

        return LearningSummary(
            total_topics=total,
            mastered_topics=mastered,
            in_progress_topics=in_prog,
            overdue_topics=overdue,
            total_problems_solved=total_solved,
            formatted_report="\n".join(report_lines)
        )
