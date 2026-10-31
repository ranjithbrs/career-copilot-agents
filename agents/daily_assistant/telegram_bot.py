import logging
import requests
from typing import Optional, Dict, Any
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from agents.daily_assistant.agent import DailyAssistantAgent

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Delivers instant mobile push notifications and briefings via Telegram Bot API."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
        """Send message via Telegram API."""
        if not self.is_configured():
            logger.warning("Telegram Bot Token or Chat ID not configured in .env.")
            return False

        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_morning_briefing(self) -> bool:
        """Generate morning briefing from DailyAssistantAgent and dispatch to Telegram."""
        assistant = DailyAssistantAgent()
        briefing = assistant.generate_morning_briefing()
        
        # Markdown formatted text
        text = f"🌅 *CAREER COPILOT MORNING BRIEF*\n"
        text += f"📅 _{briefing.date_str}_\n\n"

        if briefing.p0_tasks:
            text += "🚨 *P0 CRITICAL TASKS (DO FIRST):*\n"
            for t in briefing.p0_tasks:
                text += f"• `{t.id}` {t.task_description}\n"
            text += "\n"

        if briefing.placement_events:
            text += "🎯 *PLACEMENT & INTERVIEWS:*\n"
            for p in briefing.placement_events:
                text += f"• *{p.company_name}* ({p.role}) - `{p.status}`\n"
                if p.test_deadline:
                    text += f"  ⏰ Due: _{p.test_deadline}_\n"
                if p.test_link:
                    text += f"  🔗 [Test Link]({p.test_link})\n"
            text += "\n"

        if briefing.active_deadlines:
            text += "⏰ *UPCOMING DEADLINES:*\n"
            for d in briefing.active_deadlines:
                text += f"• `{d.id}` {d.title} (Due: _{d.deadline_dt or 'ASAP'}_\n"
            text += "\n"

        text += f"📋 *Total Pending Tasks:* `{briefing.total_pending}`\n"
        text += "_Reply with /done <id> to complete a task._"

        return self.send_message(text)

    def send_critical_alert(self, title: str, details: str, link: Optional[str] = None) -> bool:
        """Send urgent high-priority notification for OAs or interviews."""
        text = f"🚨 *CRITICAL ALERT: {title}*\n\n{details}\n"
        if link:
            text += f"\n🔗 [Open Link]({link})"
        return self.send_message(text)
