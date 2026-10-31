import json
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from agents.email_intel.schemas import RawEmail, ParsedEmail, EmailCategory, UrgencyLevel
from agents.email_intel.extractor import EmailExtractor
from agents.email_intel.ingester import IMAPEmailIngester, MockEmailIngester

logger = logging.getLogger(__name__)

class EmailIntelligenceAgent:
    """Agent 1: Ingests emails, extracts structured career signals, stores in central DB."""

    def __init__(self, extractor: Optional[EmailExtractor] = None):
        self.extractor = extractor or EmailExtractor()

    def is_already_processed(self, message_id: str) -> bool:
        """Check if message_id exists in SQLite emails_raw."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM emails_raw WHERE message_id = ?", (message_id,))
            return cursor.fetchone() is not None

    def process_emails(self, emails: List[RawEmail]) -> Dict[str, Any]:
        """Main processing loop for a batch of incoming emails."""
        results = {
            "total_ingested": len(emails),
            "skipped_duplicates": 0,
            "processed": 0,
            "critical_alerts": [],
            "deadlines_detected": [],
            "placement_updates": []
        }

        for raw in emails:
            if self.is_already_processed(raw.message_id):
                results["skipped_duplicates"] += 1
                continue

            # Extract intelligence
            parsed = self.extractor.extract(raw)

            # Save to Central Hub Database
            email_row_id = self._save_raw_email(raw, parsed)

            # Route to domain tables
            self._route_intelligence(email_row_id, raw, parsed, results)

            results["processed"] += 1

        return results

    def _save_raw_email(self, raw: RawEmail, parsed: ParsedEmail) -> int:
        """Persist parsed email to emails_raw table."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO emails_raw (message_id, sender, subject, date_received, category, urgency, is_noise, parsed_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw.message_id,
                    raw.sender,
                    raw.subject,
                    raw.date,
                    parsed.category.value,
                    parsed.urgency.value,
                    1 if parsed.is_noise else 0,
                    parsed.model_dump_json()
                )
            )
            return cursor.lastrowid

    def _route_intelligence(self, email_id: int, raw: RawEmail, parsed: ParsedEmail, results: Dict[str, Any]) -> None:
        """Distribute extracted signals to Placement, Deadlines, and Action Items."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Critical Alert Tracker
            if parsed.urgency == UrgencyLevel.CRITICAL:
                results["critical_alerts"].append({
                    "subject": parsed.subject_summary,
                    "company": parsed.company_or_sender,
                    "deadline": parsed.deadline_date,
                    "actions": parsed.action_items
                })

            # 2. Deadlines table
            if parsed.deadline_date or parsed.urgency in (UrgencyLevel.CRITICAL, UrgencyLevel.HIGH):
                action_url = parsed.important_urls[0] if parsed.important_urls else None
                cursor.execute(
                    """
                    INSERT INTO deadlines (email_id, title, deadline_dt, category, action_url)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (email_id, parsed.subject_summary, parsed.deadline_date or "Urgent / ASAP", parsed.category.value, action_url)
                )
                results["deadlines_detected"].append({
                    "title": parsed.subject_summary,
                    "deadline": parsed.deadline_date
                })

            # 3. Placement Pipeline table
            if parsed.category in (EmailCategory.PLACEMENT_OA, EmailCategory.INTERVIEW_INVITE, EmailCategory.JOB_APPLICATION, EmailCategory.COLLEGE_NOTICE):
                status_map = {
                    EmailCategory.PLACEMENT_OA: "OA_PENDING",
                    EmailCategory.INTERVIEW_INVITE: "INTERVIEW_SCHEDULED",
                    EmailCategory.JOB_APPLICATION: "APPLIED",
                    EmailCategory.COLLEGE_NOTICE: "APPLIED"
                }
                status = status_map.get(parsed.category, "APPLIED")
                test_link = parsed.important_urls[0] if parsed.important_urls else None
                
                cursor.execute(
                    """
                    INSERT INTO placement_pipeline (email_id, company_name, role, status, test_link, test_deadline, prep_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email_id,
                        parsed.company_or_sender or "Campus Placement",
                        "Software Engineer",
                        status,
                        test_link,
                        parsed.deadline_date,
                        f"Action: {', '.join(parsed.action_items)}" if parsed.action_items else "Campus placement notice"
                    )
                )
                results["placement_updates"].append({
                    "company": parsed.company_or_sender or "Campus Placement",
                    "status": status,
                    "deadline": parsed.deadline_date
                })

            # 4. Action items
            priority_map = {
                UrgencyLevel.CRITICAL: "P0",
                UrgencyLevel.HIGH: "P1",
                UrgencyLevel.MEDIUM: "P2",
                UrgencyLevel.LOW: "P3"
            }
            priority = priority_map.get(parsed.urgency, "P2")

            for item in parsed.action_items:
                cursor.execute("SELECT 1 FROM action_items WHERE task_description = ? AND is_completed = 0", (item,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO action_items (origin_agent, task_description, priority, due_date)
                        VALUES (?, ?, ?, ?)
                        """,
                        ("EMAIL_INTEL", item, priority, parsed.deadline_date)
                    )

    def run_mock_cycle(self) -> Dict[str, Any]:
        """Convenience method to run a test cycle using sample emails."""
        sample_emails = MockEmailIngester.get_sample_emails()
        return self.process_emails(sample_emails)

    def run_live_cycle(self, limit: int = 15) -> Dict[str, Any]:
        """Fetch real emails via IMAP and process them."""
        ingester = IMAPEmailIngester()
        if not ingester.is_configured():
            raise ValueError("IMAP email credentials are not set in .env. Use run_mock_cycle() or configure EMAIL_USER and EMAIL_PASSWORD.")
        emails = ingester.fetch_unread(limit=limit)
        return self.process_emails(emails)

    def reprocess_stored_emails(self) -> Dict[str, Any]:
        """Re-evaluates previously stored emails with the enhanced extractor to capture missed placement signals."""
        results = {"reprocessed": 0, "promoted_placements": 0, "promoted_deadlines": 0}
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, message_id, sender, subject, date_received FROM emails_raw ORDER BY id ASC")
            rows = cursor.fetchall()

            for r in rows:
                raw = RawEmail(
                    message_id=r["message_id"],
                    sender=r["sender"],
                    subject=r["subject"],
                    date=r["date_received"],
                    body=r["subject"]
                )
                parsed = self.extractor.extract(raw)
                
                # Check if this qualifies as a placement or campus signal
                if parsed.category in (EmailCategory.PLACEMENT_OA, EmailCategory.INTERVIEW_INVITE, EmailCategory.JOB_APPLICATION, EmailCategory.COLLEGE_NOTICE):
                    cursor.execute("SELECT 1 FROM placement_pipeline WHERE email_id = ?", (r["id"],))
                    if not cursor.fetchone():
                        status = "INTERVIEW_SCHEDULED" if parsed.category == EmailCategory.INTERVIEW_INVITE else "OA_PENDING" if parsed.category == EmailCategory.PLACEMENT_OA else "APPLIED"
                        cursor.execute(
                            """
                            INSERT INTO placement_pipeline (email_id, company_name, role, status, test_link, test_deadline, prep_notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                r["id"],
                                parsed.company_or_sender or "Campus Placement",
                                "Software Engineer",
                                status,
                                parsed.important_urls[0] if parsed.important_urls else None,
                                parsed.deadline_date,
                                f"Extracted from {r['subject']}"
                            )
                        )
                        results["promoted_placements"] += 1

                # Update emails_raw row
                cursor.execute(
                    "UPDATE emails_raw SET category = ?, urgency = ?, is_noise = ? WHERE id = ?",
                    (parsed.category.value, parsed.urgency.value, 1 if parsed.is_noise else 0, r["id"])
                )
                results["reprocessed"] += 1

        return results
