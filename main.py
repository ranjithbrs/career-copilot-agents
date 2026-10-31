import sys
import argparse
from database.connection import init_db, get_db_connection
from agents.email_intel.agent import EmailIntelligenceAgent
from agents.daily_assistant.agent import DailyAssistantAgent
from agents.daily_assistant.telegram_bot import TelegramNotifier
from agents.placement.agent import PlacementAgent
from agents.placement.schemas import HiringStage
from agents.linkedin.agent import LinkedInAgent
from agents.learning.agent import LearningAgent
from agents.project.agent import ProjectAgent

def print_banner():
    print("""
============================================================
  CAREER COPILOT: MULTI-AGENT PRODUCTIVITY & CAREER OS
============================================================
""")

def view_dashboard():
    """Print current database state across emails, deadlines, and placement pipeline."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        print("\n--- [EMAILS] RECENT PROCESSED EMAILS ---")
        cursor.execute("SELECT id, sender, category, urgency, is_noise, created_at FROM emails_raw ORDER BY id DESC LIMIT 5")
        emails = cursor.fetchall()
        if not emails:
            print("No emails processed yet.")
        else:
            for e in emails:
                noise_tag = "[SPAM/NOISE]" if e["is_noise"] else "[SIGNAL]"
                print(f"#{e['id']} | {noise_tag} [{e['urgency']}] ({e['category']}) from: {e['sender']}")

        print("\n--- [DEADLINES] ACTIVE DEADLINES ---")
        cursor.execute("SELECT id, title, deadline_dt, category, is_completed FROM deadlines ORDER BY id DESC LIMIT 5")
        deadlines = cursor.fetchall()
        if not deadlines:
            print("No deadlines tracked.")
        else:
            for d in deadlines:
                status = "[DONE]" if d["is_completed"] else "[PENDING]"
                print(f"#{d['id']} | {status} | Due: {d['deadline_dt']} | {d['title']}")

        print("\n--- [PLACEMENT] PIPELINE ---")
        cursor.execute("SELECT id, company_name, role, status, test_deadline, test_link FROM placement_pipeline ORDER BY id DESC")
        placements = cursor.fetchall()
        if not placements:
            print("No placement events recorded.")
        else:
            for p in placements:
                print(f"#{p['id']} | {p['company_name']} ({p['role']}) -> Status: {p['status']} | Deadline: {p['test_deadline'] or 'N/A'}")
                if p['test_link']:
                    print(f"      Link: {p['test_link']}")

        print("\n--- [ACTION ITEMS] HIGH PRIORITY (P0 / P1) ---")
        cursor.execute("SELECT id, task_description, priority, is_completed FROM action_items WHERE priority IN ('P0', 'P1') ORDER BY priority ASC, id DESC")
        tasks = cursor.fetchall()
        if not tasks:
            print("No urgent action items.")
        else:
            for t in tasks:
                status = "[DONE]" if t["is_completed"] else "[PENDING]"
                print(f"{status} [{t['priority']}] #{t['id']} {t['task_description']}")

def main():
    parser = argparse.ArgumentParser(description="Career Copilot Multi-Agent System")
    parser.add_argument("--mode", choices=["mock", "live", "dashboard", "briefing", "evening"], default="briefing",
                        help="Execution mode: mock (ingest mock emails), live (ingest IMAP), dashboard, briefing, or evening")
    parser.add_argument("--reset", action="store_true", help="Reset local database before execution")
    parser.add_argument("--done-task", type=int, help="Mark an action item ID as completed")
    parser.add_argument("--done-deadline", type=int, help="Mark a deadline ID as completed")
    parser.add_argument("--add-task", type=str, help="Add a custom action item")
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "P3"], default="P1", help="Priority for new custom task")
    parser.add_argument("--telegram", action="store_true", help="Dispatch morning briefing to Telegram bot")

    # Phase 3: Placement & LinkedIn Agent options
    parser.add_argument("--prep-company", type=str, help="Generate tailored interview prep dossier for a company")
    parser.add_argument("--advance-stage", type=str, help="Advance hiring stage for a company (e.g. Amazon)")
    parser.add_argument("--stage", choices=[s.value for s in HiringStage], help="Target stage for --advance-stage")
    parser.add_argument("--draft-outreach", type=str, help="Draft LinkedIn outreach for a target company")
    parser.add_argument("--type", choices=["alumni", "recruiter"], default="alumni", help="Outreach message type")
    parser.add_argument("--name", type=str, help="Name of recipient (alumni or recruiter)")
    parser.add_argument("--job-id", type=str, help="Optional job requisition ID for referral request")
    parser.add_argument("--draft-post", type=str, help="Draft a 'Build in Public' milestone post on LinkedIn")
    parser.add_argument("--view-drafts", action="store_true", help="View recently generated LinkedIn drafts")

    # Phase 4: Learning & Project Agent options
    parser.add_argument("--daily-study", action="store_true", help="Generate today's recommended study targets (injected into morning brief)")
    parser.add_argument("--log-study", type=str, help="Log a completed study session for a topic")
    parser.add_argument("--problems", type=int, default=1, help="Number of problems solved (default: 1)")
    parser.add_argument("--confidence", type=int, choices=[1, 2, 3, 4, 5], default=3, help="Confidence score: 1 (Hard) to 5 (Mastered)")
    parser.add_argument("--notes", type=str, default="", help="Notes from the study session")
    parser.add_argument("--learning-stats", action="store_true", help="View skill mastery heatmap & spaced repetition schedule")
    parser.add_argument("--audit-project", nargs="?", const=".", type=str, help="Audit a project repository (defaults to current repo)")

    # Phase 5: Autonomous Orchestrator & Daemon
    parser.add_argument("--sync-all", action="store_true", help="Run a full synchronous 6-agent cycle (ingest, study, audit, briefing)")
    parser.add_argument("--daemon", action="store_true", help="Launch background scheduler daemon for periodic polling & timed briefings")
    parser.add_argument("--poll-interval", type=int, default=900, help="Poll interval in seconds for background daemon (default: 900s / 15m)")
    parser.add_argument("--live", action="store_true", help="Use live IMAP inbox instead of mock emails for sync/daemon")

    args = parser.parse_args()
    print_banner()

    if args.reset:
        from config.settings import DB_PATH
        if DB_PATH.exists():
            DB_PATH.unlink()
            print("[*] Local database reset.")

    init_db()

    # Autonomous Orchestrator Handlers (Phase 5)
    if args.sync_all:
        from daemon import AutonomousOrchestrator
        orchestrator = AutonomousOrchestrator(use_live_email=args.live)
        orchestrator.run_full_sync(send_telegram=args.telegram, print_output=True)
        return

    if args.daemon:
        from daemon import AutonomousOrchestrator
        orchestrator = AutonomousOrchestrator(use_live_email=args.live)
        orchestrator.run_daemon_loop(poll_interval_seconds=args.poll_interval, send_telegram=args.telegram)
        return

    assistant = DailyAssistantAgent()
    email_agent = EmailIntelligenceAgent()
    notifier = TelegramNotifier()
    placement_agent = PlacementAgent()
    linkedin_agent = LinkedInAgent()
    learning_agent = LearningAgent()
    project_agent = ProjectAgent()

    # Placement Agent Commands
    if args.prep_company:
        dossier = placement_agent.generate_dossier(args.prep_company, inject_tasks=True)
        print(dossier.full_dossier_text)
        print(f"\n[OK] Dossier created and {len(dossier.actionable_prep_tasks)} prep tasks injected into Daily Assistant.")
        return

    if args.advance_stage:
        if not args.stage:
            print("[!] Please provide target --stage (e.g. --stage OA_SUBMITTED, INTERVIEW_SCHEDULED, OFFER)")
            return
        success = placement_agent.advance_stage(args.advance_stage, HiringStage(args.stage))
        if success:
            print(f"[OK] {args.advance_stage} advanced to stage: {args.stage}")
        else:
            print(f"[!] Could not find company matching '{args.advance_stage}' in placement pipeline.")
        return

    # LinkedIn Agent Commands
    if args.draft_outreach:
        if args.type == "recruiter":
            draft = linkedin_agent.draft_recruiter_note(
                company=args.draft_outreach,
                recruiter_name=args.name
            )
            print("\n=== LINKEDIN RECRUITER CONNECTION NOTE (< 300 Chars) ===")
            print(draft.content)
            print(f"\nCharacter Count: {draft.character_count}/300 (Within limit)")
        else:
            draft = linkedin_agent.draft_alumni_referral(
                company=args.draft_outreach,
                alumni_name=args.name,
                job_id=args.job_id
            )
            print("\n=== LINKEDIN ALUMNI REFERRAL REQUEST ===")
            print(draft.content)
            print(f"\nCharacter Count: {draft.character_count}")
        print(f"[OK] Saved to drafts (ID #{draft.id}). Ready to copy.")
        return

    if args.draft_post:
        draft = linkedin_agent.draft_achievement_post(topic=args.draft_post)
        print("\n=== LINKEDIN MILESTONE POST DRAFT ===")
        print(draft.content)
        print(f"\n[OK] Saved to drafts (ID #{draft.id}). Ready to copy.")
        return

    if args.view_drafts:
        drafts = linkedin_agent.list_drafts(limit=5)
        if not drafts:
            print("No LinkedIn drafts saved yet.")
        else:
            print("--- [LINKEDIN] RECENT DRAFTS ---")
            for d in drafts:
                co_str = f" ({d.target_company})" if d.target_company else ""
                print(f"#{d.id} | [{d.draft_type.value}]{co_str} -> {d.character_count} chars")
                print(f"Content Preview: {d.content[:80]}...\n")
        return

    # Learning Agent Commands
    if args.daily_study:
        targets = learning_agent.get_daily_targets(inject_tasks=True)
        print("=== TODAY'S RECOMMENDED STUDY TARGETS (SPACED REPETITION) ===")
        for idx, t in enumerate(targets, 1):
            print(f"\n{idx}. [{t.subject.value}] {t.topic_name} ({t.reason})")
            if t.recommended_problems:
                for p in t.recommended_problems:
                    print(f"   * {p}")
        print("\n[OK] Study targets injected into Daily Assistant morning briefing.")
        return

    if args.log_study:
        learning_agent.log_session(
            topic_name=args.log_study,
            problems_solved=args.problems,
            confidence=args.confidence,
            notes=args.notes
        )
        print(f"[OK] Logged session for '{args.log_study}' (Problems: {args.problems}, Confidence: {args.confidence}/5).")
        print("     Spaced repetition schedule updated.")
        return

    if args.learning_stats:
        summary = learning_agent.get_mastery_report()
        print(summary.formatted_report)
        return

    # Project Agent Commands
    if args.audit_project:
        audit = project_agent.audit_repository(repo_path=args.audit_project, inject_task=True)
        print(audit.formatted_summary)
        print(f"\n[OK] Project audit saved and engineering action item injected into Daily Assistant.")
        return

    # Handle single action completions
    if args.done_task:
        success = assistant.mark_action_item_completed(args.done_task)
        if success:
            print(f"[OK] Task #{args.done_task} marked as COMPLETED.")
        else:
            print(f"[!] Task #{args.done_task} not found.")
        return

    if args.done_deadline:
        success = assistant.mark_deadline_completed(args.done_deadline)
        if success:
            print(f"[OK] Deadline #{args.done_deadline} marked as COMPLETED.")
        else:
            print(f"[!] Deadline #{args.done_deadline} not found.")
        return

    if args.add_task:
        task_id = assistant.add_action_item(args.add_task, priority=args.priority)
        print(f"[OK] Created Task #{task_id} [{args.priority}]: {args.add_task}")
        return

    # Dispatch Modes
    if args.mode == "briefing":
        briefing = assistant.generate_morning_briefing()
        print(briefing.formatted_summary)

        if args.telegram:
            if notifier.is_configured():
                print("\n[*] Sending briefing to Telegram...")
                sent = notifier.send_morning_briefing()
                if sent:
                    print("[OK] Delivered to Telegram.")
                else:
                    print("[!] Failed to deliver to Telegram.")
            else:
                print("\n[!] Telegram credentials (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) not set in .env.")

    elif args.mode == "evening":
        review = assistant.generate_evening_review()
        print(review.formatted_summary)

    elif args.mode == "mock":
        print("[*] Running Email Intelligence Agent in MOCK mode...")
        results = email_agent.run_mock_cycle()
        print("\nProcessing Results:")
        print(f"  Total Ingested:      {results['total_ingested']}")
        print(f"  Skipped Duplicates:  {results['skipped_duplicates']}")
        print(f"  Newly Processed:     {results['processed']}")
        print(f"  Critical Alerts:     {len(results['critical_alerts'])}")
        print(f"  Deadlines Added:     {len(results['deadlines_detected'])}")
        print(f"  Placement Updates:   {len(results['placement_updates'])}")
        view_dashboard()

    elif args.mode == "live":
        print("[*] Connecting to Live IMAP inbox...")
        try:
            results = email_agent.run_live_cycle()
            print(f"Processed {results['processed']} new emails.")
            view_dashboard()
        except Exception as e:
            print(f"[ERROR] Error during live email processing: {e}")

    elif args.mode == "dashboard":
        view_dashboard()

if __name__ == "__main__":
    main()
