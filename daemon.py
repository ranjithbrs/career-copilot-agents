import time
import datetime
import logging
from typing import Dict, Any, Optional
from database.connection import init_db
from agents.email_intel.agent import EmailIntelligenceAgent
from agents.daily_assistant.agent import DailyAssistantAgent
from agents.daily_assistant.telegram_bot import TelegramNotifier
from agents.placement.agent import PlacementAgent
from agents.learning.agent import LearningAgent
from agents.project.agent import ProjectAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AutonomousDaemon")

import time
import datetime
import logging
from typing import Dict, Any, Optional, List
from database.connection import init_db, get_db_connection
from agents.email_intel.agent import EmailIntelligenceAgent
from agents.daily_assistant.agent import DailyAssistantAgent
from agents.daily_assistant.telegram_bot import TelegramNotifier
from agents.placement.agent import PlacementAgent
from agents.learning.agent import LearningAgent
from agents.project.agent import ProjectAgent
from agents.linkedin.agent import LinkedInAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AutonomousDaemon")

class AutonomousOrchestrator:
    """Phase 5: Autonomous background service coordinating all 6 agents on continuous schedules."""

    def __init__(self, use_live_email: bool = False):
        init_db()
        self.use_live_email = use_live_email
        self.email_agent = EmailIntelligenceAgent()
        self.assistant = DailyAssistantAgent()
        self.placement_agent = PlacementAgent()
        self.learning_agent = LearningAgent()
        self.project_agent = ProjectAgent()
        self.linkedin_agent = LinkedInAgent()
        self.notifier = TelegramNotifier()

        self.last_morning_date: Optional[str] = None
        self.last_evening_date: Optional[str] = None

    def run_full_sync(self, send_telegram: bool = False, print_output: bool = True) -> Dict[str, Any]:
        """
        Executes a complete coordinated sync cycle across all 6 agents:
        1. Ingest & classify emails (Agent 1: Email Intelligence)
        2. Alert immediately on critical OAs/interviews
        3. Auto-generate dossiers & prep tasks for new placements (Agent 2: Placement)
        4. Refresh daily learning targets via spaced repetition (Agent 3: Learning & DSA)
        5. Audit project codebase health & hygiene (Agent 4: Project Health)
        6. Coordinate recruiter outreach drafts for applications (Agent 5: LinkedIn Outreach)
        7. Synthesize Eisenhower-prioritized Daily Briefing (Agent 6: Daily Assistant)
        """
        results: Dict[str, Any] = {"errors": []}

        if print_output:
            print("\n" + "=" * 60)
            print("  AUTONOMOUS ORCHESTRATOR: FULL 6-AGENT SYNC CYCLE")
            print("=" * 60)

        # 1. Ingest Emails (Agent 1)
        if print_output:
            print("[1/6] Ingesting and analyzing emails...")
        try:
            if self.use_live_email:
                try:
                    email_results = self.email_agent.run_live_cycle()
                except Exception as e:
                    logger.warning(f"Live email fetch failed ({e}). Falling back to mock email radar.")
                    email_results = self.email_agent.run_mock_cycle()
            else:
                email_results = self.email_agent.run_mock_cycle()
        except Exception as e:
            logger.error(f"Email intelligence agent cycle failed: {e}")
            email_results = {"total_ingested": 0, "processed": 0, "critical_alerts": [], "placement_updates": [], "error": str(e)}
            results["errors"].append(f"EmailIntelligenceAgent: {e}")
        results["emails"] = email_results

        # 2. Critical Alert Dispatch
        critical_alerts = email_results.get("critical_alerts", [])
        if critical_alerts:
            if print_output:
                print(f"[!] Detected {len(critical_alerts)} CRITICAL placement/deadline alerts!")
            for alert in critical_alerts:
                try:
                    title = f"{alert.get('company', 'Urgent Alert')}: {alert.get('subject', 'Notice')}"
                    details = f"Deadline: {alert.get('deadline', 'Urgent')}\nActions:\n" + "\n".join([f"• {a}" for a in alert.get("actions", [])])
                    if self.notifier.is_configured():
                        self.notifier.send_critical_alert(title, details)
                except Exception as e:
                    logger.warning(f"Failed to dispatch critical alert: {e}")
                    results["errors"].append(f"AlertDispatch: {e}")

        # 3. Placement Agent Coordination (Agent 2)
        if print_output:
            print("[2/6] Coordinating Placement Pipeline & generating dossiers...")
        placement_updates = email_results.get("placement_updates", [])
        dossier_count = 0
        for update in placement_updates:
            co = update.get("company")
            if co and co != "Campus Placement":
                try:
                    self.placement_agent.generate_dossier(co, inject_tasks=True)
                    dossier_count += 1
                except Exception as e:
                    logger.warning(f"Could not generate dossier for {co}: {e}")
                    results["errors"].append(f"PlacementDossier ({co}): {e}")
        results["dossiers_generated"] = dossier_count

        # 4. Refresh Learning Targets (Agent 3)
        if print_output:
            print("[3/6] Updating spaced repetition and scheduling daily study targets...")
        try:
            targets = self.learning_agent.get_daily_targets(inject_tasks=True)
            results["study_targets"] = [t.model_dump() for t in targets]
        except Exception as e:
            logger.error(f"Learning agent cycle failed: {e}")
            results["study_targets"] = []
            results["errors"].append(f"LearningAgent: {e}")

        # 5. Audit Project Repository (Agent 4)
        if print_output:
            print("[4/6] Auditing repository health and commit activity...")
        try:
            audit = self.project_agent.audit_repository(".", inject_task=True)
            results["project_audit"] = audit.model_dump()
        except Exception as e:
            logger.error(f"Project health audit failed: {e}")
            results["project_audit"] = {}
            results["errors"].append(f"ProjectAgent: {e}")

        # 6. Coordinate LinkedIn Outreach Drafts (Agent 5)
        if print_output:
            print("[5/6] Generating personalized LinkedIn outreach drafts for active pipeline...")
        try:
            outreach_drafts = self.generate_outreach_recommendations()
            results["outreach_drafts"] = outreach_drafts
        except Exception as e:
            logger.warning(f"LinkedIn outreach coordination failed: {e}")
            results["outreach_drafts"] = []
            results["errors"].append(f"LinkedInAgent: {e}")

        # 7. Generate Morning Briefing (Agent 6)
        if print_output:
            print("[6/6] Synthesizing Eisenhower-prioritized Daily Briefing...")
        try:
            briefing = self.assistant.generate_morning_briefing()
            results["briefing"] = briefing.model_dump()
            briefing_text = briefing.formatted_summary
        except Exception as e:
            logger.error(f"Daily assistant briefing generation failed: {e}")
            results["briefing"] = {}
            results["errors"].append(f"DailyAssistantAgent: {e}")
            briefing_text = "Briefing generation encountered an issue; check errors list."

        # 8. Optional Telegram Dispatch
        if send_telegram and self.notifier.is_configured():
            try:
                if print_output:
                    print("Delivering Morning Briefing to Telegram...")
                sent = self.notifier.send_morning_briefing()
                results["telegram_sent"] = sent
            except Exception as e:
                logger.warning(f"Telegram delivery failed: {e}")
                results["telegram_sent"] = False
                results["errors"].append(f"TelegramNotifier: {e}")
        else:
            if print_output:
                print("Telegram delivery skipped (not enabled or credentials not set).")
            results["telegram_sent"] = False

        if print_output:
            print("\n" + briefing_text)
            print("\n[OK] Full 6-agent sync completed successfully.")

        return results

    def generate_outreach_recommendations(self) -> List[Dict[str, Any]]:
        """Coordinates Placement -> LinkedIn by ensuring outreach notes exist for tracked companies."""
        drafts: List[Dict[str, Any]] = []
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT company_name FROM placement_pipeline WHERE status IN ('APPLIED', 'OA_PENDING') LIMIT 3")
            companies = [r["company_name"] for r in cursor.fetchall()]

        for co in companies:
            try:
                # Check if draft already exists
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM linkedin_drafts WHERE LOWER(target_company) = LOWER(?)", (co,))
                    if not cursor.fetchone():
                        draft = self.linkedin_agent.draft_recruiter_note(co)
                        drafts.append(draft.model_dump())
            except Exception as e:
                logger.warning(f"Could not generate outreach note for {co}: {e}")
        return drafts

    def run_daemon_loop(self, poll_interval_seconds: int = 900, send_telegram: bool = True) -> None:
        """
        Continuously runs in the background:
        - Polls emails every `poll_interval_seconds` (default: 15 mins)
        - Dispatches morning briefing at 08:00 AM
        - Dispatches evening review at 09:00 PM (21:00)
        """
        print("\n" + "=" * 60)
        print("  CAREER COPILOT AUTONOMOUS DAEMON RUNNING")
        print("=" * 60)
        print(f"[*] Email polling interval: Every {poll_interval_seconds} seconds")
        print(f"[*] Telegram alerts:        {'ENABLED' if self.notifier.is_configured() else 'DISABLED (set .env)'}")
        print("[*] Press Ctrl+C anytime to stop.\n")

        try:
            while True:
                now = datetime.datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                current_hour = now.hour

                # 1. Morning Briefing Trigger (At or after 08:00 AM once per day)
                if current_hour >= 8 and self.last_morning_date != today_str:
                    logger.info("Triggering Scheduled Morning Briefing Routine...")
                    self.run_full_sync(send_telegram=send_telegram, print_output=False)
                    if self.notifier.is_configured() and send_telegram:
                        self.notifier.send_morning_briefing()
                    self.last_morning_date = today_str
                    logger.info("Morning Briefing delivered.")

                # 2. Evening Review Trigger (At or after 09:00 PM once per day)
                if current_hour >= 21 and self.last_evening_date != today_str:
                    logger.info("Triggering Scheduled Evening Accountability Review...")
                    review = self.assistant.generate_evening_review()
                    if self.notifier.is_configured() and send_telegram:
                        self.notifier.send_message(f"🌙 *EVENING ACCOUNTABILITY REVIEW*\n\n{review.formatted_summary}")
                    self.last_evening_date = today_str
                    logger.info("Evening Review delivered.")

                # 3. Regular Email Ingestion Check
                logger.info("Checking for new incoming career signals & deadlines...")
                try:
                    if self.use_live_email:
                        res = self.email_agent.run_live_cycle()
                    else:
                        res = self.email_agent.run_mock_cycle()

                    if res.get("processed", 0) > 0:
                        logger.info(f"Processed {res['processed']} new emails.")
                        # Immediate alert for critical notices
                        for alert in res.get("critical_alerts", []):
                            logger.warning(f"CRITICAL ALERT: {alert['subject']}")
                            if self.notifier.is_configured() and send_telegram:
                                title = f"{alert.get('company', 'Urgent')}: {alert['subject']}"
                                self.notifier.send_critical_alert(title, f"Deadline: {alert.get('deadline', 'ASAP')}")
                except Exception as e:
                    logger.error(f"Error during scheduled email poll: {e}")

                time.sleep(poll_interval_seconds)

        except KeyboardInterrupt:
            print("\n[*] Daemon stopped gracefully by user.")
