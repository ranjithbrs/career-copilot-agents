import datetime
import logging
from typing import Optional, List, Dict, Any
from database.connection import get_db_connection
from agents.daily_assistant.schemas import (
    DailyBriefing,
    EveningReview,
    TaskItem,
    DeadlineItem,
    PlacementItem,
)

logger = logging.getLogger(__name__)

class DailyAssistantAgent:
    """Agent 5: Synthesizes multi-agent state into daily priorities, briefings, and accountability reviews."""

    def __init__(self):
        pass

    def generate_morning_briefing(self) -> DailyBriefing:
        """Aggregate active deadlines, placement schedules, and prioritized tasks into an actionable morning brief."""
        today_str = datetime.date.today().strftime("%A, %B %d, %Y")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Fetch uncompleted deadlines
            cursor.execute(
                """
                SELECT id, title, deadline_dt, category, action_url, is_completed
                FROM deadlines
                WHERE is_completed = 0
                ORDER BY id ASC LIMIT 5
                """
            )
            deadlines = [
                DeadlineItem(
                    id=row["id"],
                    title=row["title"],
                    deadline_dt=row["deadline_dt"],
                    category=row["category"],
                    action_url=row["action_url"],
                    is_completed=bool(row["is_completed"])
                )
                for row in cursor.fetchall()
            ]

            # 2. Fetch pending placement pipeline items
            cursor.execute(
                """
                SELECT id, company_name, role, status, test_link, test_deadline
                FROM placement_pipeline
                WHERE status IN ('OA_PENDING', 'INTERVIEW_SCHEDULED')
                ORDER BY id DESC LIMIT 5
                """
            )
            placements = [
                PlacementItem(
                    id=row["id"],
                    company_name=row["company_name"],
                    role=row["role"],
                    status=row["status"],
                    test_link=row["test_link"],
                    test_deadline=row["test_deadline"]
                )
                for row in cursor.fetchall()
            ]

            # 3. Fetch P0 (Urgent) Tasks
            cursor.execute(
                """
                SELECT id, task_description, priority, due_date, is_completed
                FROM action_items
                WHERE is_completed = 0 AND priority = 'P0'
                ORDER BY id DESC
                """
            )
            p0_tasks = [
                TaskItem(
                    id=row["id"],
                    task_description=row["task_description"],
                    priority=row["priority"],
                    due_date=row["due_date"],
                    is_completed=bool(row["is_completed"])
                )
                for row in cursor.fetchall()
            ]

            # 4. Fetch P1 (Core Priority) Tasks
            cursor.execute(
                """
                SELECT id, task_description, priority, due_date, is_completed
                FROM action_items
                WHERE is_completed = 0 AND priority = 'P1'
                ORDER BY id DESC LIMIT 6
                """
            )
            p1_tasks = [
                TaskItem(
                    id=row["id"],
                    task_description=row["task_description"],
                    priority=row["priority"],
                    due_date=row["due_date"],
                    is_completed=bool(row["is_completed"])
                )
                for row in cursor.fetchall()
            ]

            # Count total pending
            cursor.execute("SELECT COUNT(*) as count FROM action_items WHERE is_completed = 0")
            total_pending = cursor.fetchone()["count"]

        # Format brief text (clean ASCII formatting for terminal & Telegram)
        summary_lines = [
            f"=== DAILY BRIEFING: {today_str.upper()} ===",
            ""
        ]

        # Critical / P0 section
        if p0_tasks:
            summary_lines.append("[!] P0 CRITICAL ACTIONS (DO FIRST):")
            for t in p0_tasks:
                due_info = f" (Due: {t.due_date})" if t.due_date else ""
                summary_lines.append(f"  * [Task #{t.id}] {t.task_description}{due_info}")
            summary_lines.append("")

        # Placement pipeline section
        if placements:
            summary_lines.append("[*] PLACEMENT & INTERVIEW PIPELINE:")
            for p in placements:
                summary_lines.append(f"  * {p.company_name} ({p.role}) -> {p.status}")
                if p.test_deadline:
                    summary_lines.append(f"    Deadline: {p.test_deadline}")
                if p.test_link:
                    summary_lines.append(f"    Link: {p.test_link}")
            summary_lines.append("")

        # Deadlines section
        if deadlines:
            summary_lines.append("[*] UPCOMING DEADLINES:")
            for d in deadlines:
                summary_lines.append(f"  * [Deadline #{d.id}] {d.title} (Cutoff: {d.deadline_dt or 'N/A'})")
                if d.action_url:
                    summary_lines.append(f"    URL: {d.action_url}")
            summary_lines.append("")

        # P1 Tasks
        if p1_tasks:
            summary_lines.append("[*] P1 HIGH PRIORITY TASKS:")
            for t in p1_tasks:
                summary_lines.append(f"  * [Task #{t.id}] {t.task_description}")
            summary_lines.append("")

        summary_lines.append(f"Total Pending Actions: {total_pending}")
        summary_lines.append("Tip: Mark tasks done with: python main.py --done-task <id>")

        formatted_summary = "\n".join(summary_lines)

        return DailyBriefing(
            date_str=today_str,
            p0_tasks=p0_tasks,
            p1_tasks=p1_tasks,
            active_deadlines=deadlines,
            placement_events=placements,
            total_pending=total_pending,
            formatted_summary=formatted_summary
        )

    def generate_evening_review(self) -> EveningReview:
        """Review tasks completed today versus pending for accountability."""
        today_str = datetime.date.today().strftime("%A, %B %d, %Y")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Completed tasks
            cursor.execute(
                """
                SELECT id, task_description, priority
                FROM action_items
                WHERE is_completed = 1
                ORDER BY id DESC LIMIT 10
                """
            )
            completed = [f"#{row['id']} [{row['priority']}] {row['task_description']}" for row in cursor.fetchall()]

            # Pending tasks
            cursor.execute(
                """
                SELECT id, task_description, priority
                FROM action_items
                WHERE is_completed = 0
                ORDER BY priority ASC, id DESC LIMIT 10
                """
            )
            pending = [f"#{row['id']} [{row['priority']}] {row['task_description']}" for row in cursor.fetchall()]

        review_lines = [
            f"=== EVENING ACCOUNTABILITY REVIEW: {today_str.upper()} ===",
            "",
            f"Tasks Completed: {len(completed)}",
            f"Tasks Still Pending: {len(pending)}",
            ""
        ]

        if completed:
            review_lines.append("[DONE] COMPLETED TODAY:")
            for c in completed:
                review_lines.append(f"  [x] {c}")
            review_lines.append("")

        if pending:
            review_lines.append("[PENDING] ROLLING OVER TO TOMORROW:")
            for p in pending:
                review_lines.append(f"  [ ] {p}")
            review_lines.append("")

        formatted_summary = "\n".join(review_lines)

        return EveningReview(
            date_str=today_str,
            completed_count=len(completed),
            pending_count=len(pending),
            completed_tasks=completed,
            pending_tasks=pending,
            formatted_summary=formatted_summary
        )

    def mark_action_item_completed(self, task_id: int) -> bool:
        """Mark an action item as completed in the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE action_items SET is_completed = 1 WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def mark_deadline_completed(self, deadline_id: int) -> bool:
        """Mark a deadline as completed in the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE deadlines SET is_completed = 1 WHERE id = ?", (deadline_id,))
            return cursor.rowcount > 0

    def add_action_item(self, task_description: str, priority: str = "P1", due_date: Optional[str] = None) -> int:
        """Manually add an action item into the central pool."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO action_items (origin_agent, task_description, priority, due_date)
                VALUES (?, ?, ?, ?)
                """,
                ("USER_MANUAL", task_description, priority.upper(), due_date)
            )
            return cursor.lastrowid
