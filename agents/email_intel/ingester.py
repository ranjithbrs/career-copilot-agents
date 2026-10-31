import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Generator
from agents.email_intel.schemas import RawEmail
from config.settings import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD

logger = logging.getLogger(__name__)

def decode_mime_words(s: str) -> str:
    """Decode encoded email header words into standard unicode."""
    if not s:
        return ""
    decoded_fragments = decode_header(s)
    result = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            result.append(fragment.decode(encoding or "utf-8", errors="replace"))
        else:
            result.append(str(fragment))
    return "".join(result)

class IMAPEmailIngester:
    """Fetches real unread emails from IMAP inbox (Gmail, Outlook, University mail)."""
    def __init__(self, host=EMAIL_HOST, port=EMAIL_PORT, user=EMAIL_USER, password=EMAIL_PASSWORD):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def is_configured(self) -> bool:
        return bool(self.user and self.password)

    def fetch_unread(self, limit: int = 15) -> List[RawEmail]:
        if not self.is_configured():
            logger.warning("Email credentials not provided in .env. Skipping live IMAP fetch.")
            return []

        raw_emails = []
        try:
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(self.user, self.password)
            mail.select("INBOX")

            # Strictly search for UNSEEN (unread) emails only
            status, search_data = mail.search(None, "UNSEEN")
            if status != "OK" or not search_data[0]:
                mail.close()
                mail.logout()
                return []

            email_ids = search_data[0].split()
            target_ids = email_ids[-limit:]

            for e_id in reversed(target_ids):
                # Use BODY.PEEK[] so fetch doesn't prematurely clear flags before processing completes
                status, msg_data = mail.fetch(e_id, "(BODY.PEEK[])")
                if status != "OK" or not msg_data or not msg_data[0]:
                    status, msg_data = mail.fetch(e_id, "(RFC822)")
                if status != "OK" or not msg_data:
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = decode_mime_words(msg.get("Subject", "No Subject"))
                        sender = decode_mime_words(msg.get("From", "Unknown Sender"))
                        date = decode_mime_words(msg.get("Date", ""))
                        message_id = msg.get("Message-ID", f"id_{e_id.decode()}")

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode(errors="replace")
                                        break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="replace")

                        raw_emails.append(RawEmail(
                            message_id=message_id,
                            sender=sender,
                            subject=subject,
                            date=date,
                            body=body.strip()
                        ))

            mail.close()
            mail.logout()
        except Exception as e:
            logger.error(f"Error fetching emails over IMAP: {e}")

        return raw_emails


class MockEmailIngester:
    """Supplies realistic sample test emails for instant testing without email credentials."""
    @staticmethod
    def get_sample_emails() -> List[RawEmail]:
        return [
            RawEmail(
                message_id="mock_001_amazon_oa",
                sender="recruitment-no-reply@amazon.jobs",
                subject="Action Required: Amazon SDE 2026 Online Assessment (OA) Link",
                date="2026-10-30 14:00:00",
                body=(
                    "Dear Candidate,\n\n"
                    "Congratulations on passing our resume screening for the Software Development Engineer (SDE) position.\n"
                    "Your Online Assessment (OA1 - Coding & Work Simulation) is now active.\n\n"
                    "Instructions:\n"
                    "- Duration: 90 Minutes (2 Data Structures & Algorithms coding challenges + system design work styles)\n"
                    "- Assessment Link: https://amazon.hackerrank.com/tests/sde-intern-2026-eval\n"
                    "- Deadline: Complete the assessment before November 04, 2026 by 11:59 PM IST.\n\n"
                    "Please ensure you are in a quiet room with a functioning webcam.\n"
                    "Amazon Student Programs Team"
                )
            ),
            RawEmail(
                message_id="mock_002_microsoft_interview",
                sender="university-recruiting@microsoft.com",
                subject="Interview Schedule: Microsoft Technical Round 1 - SDE",
                date="2026-10-30 15:30:00",
                body=(
                    "Hello,\n\n"
                    "We are pleased to invite you to Microsoft Technical Round 1.\n"
                    "Date & Time: November 03, 2026 at 2:00 PM IST.\n"
                    "Platform: Microsoft Teams (Meeting link: https://teams.microsoft.com/l/meetup-join/msft-round1)\n\n"
                    "Please confirm your slot within 24 hours by replying to this email.\n"
                    "Best regards,\nMicrosoft Talent Acquisition"
                )
            ),
            RawEmail(
                message_id="mock_003_college_placement",
                sender="placement-cell@university.edu",
                subject="URGENT: Registration Closes Tonight for Google Campus Recruitment Drive",
                date="2026-10-30 16:45:00",
                body=(
                    "Attention Final Year B.Tech Students,\n\n"
                    "Google has announced their On-Campus hiring drive for 2026 graduates.\n"
                    "Eligible branches: CSE, IT, ECE with CGPA >= 7.5.\n"
                    "Registration Portal: https://university.edu/placements/drives/google-2026\n"
                    "Hard Deadline: Today, October 30, 2026 by 11:59 PM IST. Late submissions will NOT be accepted under any circumstances.\n\n"
                    "Placement Officer"
                )
            ),
            RawEmail(
                message_id="mock_004_marketing_newsletter",
                sender="newsletter@marketing-deals.com",
                subject="🔥 70% Off on all UI/UX Masterclasses this Weekend Only!",
                date="2026-10-30 11:00:00",
                body=(
                    "Don't miss our biggest flash sale of the season! Click here to view the best deals on design courses.\n"
                    "Unsubscribe here: https://marketing-deals.com/unsubscribe\n"
                    "Privacy policy and terms of service apply."
                )
            ),
        ]
