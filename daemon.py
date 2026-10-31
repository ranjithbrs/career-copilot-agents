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
        self.notifier = TelegramNotifier()

        self.last_morning_date: Optional[str] = None
        self.last_evening_date: Optional[str] = None

    def run_full_sync(self, send_telegram: bool = False, print_output: bool = True) -> Dict[str, Any]:
        """
        Executes a complete coordinated sync cycle across all 6 agents:
        1. Ingest & classify emails
        2. Alert immediately on critical OAs/interviews
        3. Refresh daily learning targets (spaced repetition)
        4. Audit project codebase health
        5. Generate and optionally deliver Daily Morning Briefing
        """
        results = {}

        if print_output:
            print("\n" + "=" * 60)
            print("  AUTONOMOUS ORCHESTRATOR: FULL 6-AGENT SYNC CYCLE")
            print("=" * 60)

        # 1. Ingest Emails
        if print_output:
            print("[1/5] Ingesting and analyzing emails...")
        try:
            if self.use_live_email:
                email_results = self.email_agent.run_live_cycle()
            else:
                email_results = self.email_agent.run_mock_cycle()
        except Exception as e:
            logger.warning(f"Live email fetch failed ({e}). Falling back to mock email radar.")
            email_results = self.email_agent.run_mock_cycle()
        results["emails"] = email_results

        # 2. Critical Alert Dispatch
        critical_alerts = email_results.get("critical_alerts", [])
        if critical_alerts:
            if print_output:
                print(f"[!] Detected {len(critical_alerts)} CRITICAL placement/deadline alerts!")
            for alert in critical_alerts:
                title = f"{alert.get('company', 'Urgent Alert')}: {alert.get('subject', 'Notice')}"
                details = f"Deadline: {alert.get('deadline', 'Urgent')}\nActions:\n" + "\n".join([f"• {a}" for a in alert.get("actions", [])])
                if self.notifier.is_configured():
                    self.notifier.send_critical_alert(title, details)

        # 3. Refresh Learning Targets
        if print_output:
            print("[2/5] Updating spaced repetition and scheduling daily study targets...")
        targets = self.learning_agent.get_daily_targets(inject_tasks=True)
        results["study_targets"] = [t.model_dump() for t in targets]

        # 4. Audit Project Repository
        if print_output:
            print("[3/5] Auditing repository health and commit activity...")
        audit = self.project_agent.audit_repository(".", inject_task=True)
        results["project_audit"] = audit.model_dump()

        # 5. Generate Morning Briefing
        if print_output:
            print("[4/5] Synthesizing Eisenhower-prioritized Daily Briefing...")
        briefing = self.assistant.generate_morning_briefing()
        results["briefing"] = briefing.model_dump()

        # 6. Telegram Dispatch
        if send_telegram and self.notifier.is_configured():
            if print_output:
                print("[5/5] Delivering Morning Briefing to Telegram...")
            sent = self.notifier.send_morning_briefing()
            results["telegram_sent"] = sent
        else:
            if print_output:
                print("[5/5] Telegram delivery skipped (not enabled or credentials not set).")
            results["telegram_sent"] = False

        if print_output:
            print("\n" + briefing.formatted_summary)
            print("\n[OK] Full 6-agent sync completed successfully.")

        return results

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
