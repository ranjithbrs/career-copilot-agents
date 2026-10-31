import re
import json
import logging
from typing import Optional
from agents.email_intel.schemas import RawEmail, ParsedEmail, EmailCategory, UrgencyLevel
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are an expert Executive Email Intelligence Agent.
Analyze the given email and extract actionable structured intelligence.

Categorize into:
- PLACEMENT_OA: Coding assessments, tests, OA invitations (HackerRank, Mettl, CodeSignal, SHL, etc.)
- INTERVIEW_INVITE: Interview calls, technical rounds, HR discussion schedules
- JOB_APPLICATION: Application confirmations, status updates, rejection/selection notices
- DEADLINE_ALERT: Urgent academic, project, or registration deadlines
- COLLEGE_NOTICE: College administration, fee, exam, or placement cell general circulars
- NEWSLETTER_SPAM: Promotional, commercial, digest newsletters
- GENERAL: Other normal emails

Assess Urgency:
- CRITICAL: Assessment link or interview scheduled within 24-48 hours.
- HIGH: Action required within 3-7 days.
- MEDIUM: Informational update, no immediate ticking clock.
- LOW: Newsletters, receipts, spam.

Extract all relevant deadlines, action items, and important links (e.g. test links).
"""

class EmailExtractor:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = model_name or GEMINI_MODEL
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini Client initialized for Email Extractor.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini Client: {e}. Falling back to rule-based engine.")

    def extract(self, email: RawEmail) -> ParsedEmail:
        """Extract structured data from raw email using LLM if available, otherwise heuristics."""
        if self.client:
            try:
                return self._extract_with_gemini(email)
            except Exception as e:
                logger.warning(f"Gemini extraction failed ({e}), falling back to heuristic extractor.")
        
        return self._extract_with_heuristics(email)

    def _extract_with_gemini(self, email: RawEmail) -> ParsedEmail:
        from google.genai import types

        prompt = f"""
Sender: {email.sender}
Subject: {email.subject}
Date: {email.date}
Body:
{email.body[:3500]}
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ParsedEmail,
                temperature=0.1
            ),
        )
        return ParsedEmail.model_validate_json(response.text)

    def _extract_with_heuristics(self, email: RawEmail) -> ParsedEmail:
        """Fast offline rule-based heuristic parser for testing and resilience."""
        sender_lower = email.sender.lower()
        content = f"{email.subject} {email.body}".lower()

        # 0. Intercept known publication, social, and newsletter senders immediately
        if any(d in sender_lower for d in ["medium.com", "quora.com", "substack.com", "reddit.com", "twitter.com", "x.com", "youtube.com", "spotify.com", "cloudplatform-noreply@google.com"]):
            clean_s = email.subject.replace("\r", " ").replace("\n", " ").strip()[:100]
            send_name = "Medium" if "medium.com" in sender_lower else "Newsletter"
            return ParsedEmail(
                category=EmailCategory.NEWSLETTER_SPAM,
                urgency=UrgencyLevel.LOW,
                company_or_sender=send_name,
                subject_summary=clean_s,
                deadline_date=None,
                action_items=[],
                important_urls=[],
                is_noise=True,
                confidence_score=0.95
            )

        # Comprehensive career and hiring signals (strictly protected from spam filter)
        career_keywords = [
            "interview", "assessment", "placement", "shortlist", "hiring", "hire", "unstop",
            "job opening", "job application", "campus drive", "recruitment drive", "coding test",
            "online test", "hackerrank", "mettl", "codesignal", "test link", "assessment link",
            "superset", "hirepro", "cocubes", "myanatomy", "cuvette", "naukri", "wellfound",
            "internshala", "infosys", "tcs", "wipro", "cognizant", "accenture", "technical screening"
        ]

        has_career_signal = any(kw in content for kw in career_keywords)

        # 1. Check for spam / noise (NEVER classify as noise if career signal exists)
        noise_signals = ["unsubscribe", "view in browser", "privacy policy", "promotions", "newsletter", "sale", "discount", "deal of the day"]
        is_noise = any(signal in content for signal in noise_signals) and not has_career_signal
        
        # 2. Extract links (filter out images, tracking pixels, css, fonts)
        urls = re.findall(r"https?://[^\s'\"<>]+", email.body)
        important_urls = [
            u for u in urls 
            if not any(x in u.lower() for x in [
                "unsubscribe", "privacy", "twitter", "linkedin.com/feed", "facebook", 
                ".png", ".jpg", ".jpeg", ".svg", ".gif", ".css", "fonts.googleapis", "cloudfront.net"
            ])
        ]

        # 3. Detect Category & Urgency
        category = EmailCategory.GENERAL
        urgency = UrgencyLevel.LOW

        is_campus_platform = any(p in email.sender.lower() for p in [
            "unstop", "hirepro", "superset", "cocubes", "myanatomy", "hackerrank", "hackerearth", 
            "codesignal", "mettl", "internshala", "cuvette", "naukri", "wellfound"
        ])
        has_placement_kw = any(kw in content for kw in [
            "placement journey", "placement drive", "campus recruitment", "campus hiring", 
            "hiring challenge", "online test", "coding assessment", "hackerrank", "mettl", 
            "codesignal", "test link", "assessment link", "internship opportunity", "job opportunity",
            "shortlisted candidates", "shortlist", "interview call", "is hiring", "hiring for"
        ])

        if any(kw in content for kw in ["coding test", "online assessment", "hackerrank", "mettl", "codesignal", "test link", "assessment link"]):
            category = EmailCategory.PLACEMENT_OA
            urgency = UrgencyLevel.CRITICAL if any(kw in content for kw in ["today", "tomorrow", "24 hours", "expires soon"]) else UrgencyLevel.HIGH
        elif any(kw in content for kw in ["interview schedule", "technical round", "hr interview", "interview call", "technical screening"]):
            category = EmailCategory.INTERVIEW_INVITE
            urgency = UrgencyLevel.CRITICAL
        elif any(kw in content for kw in ["deadline", "due date", "last date to apply", "closes on", "submission"]):
            category = EmailCategory.DEADLINE_ALERT
            urgency = UrgencyLevel.HIGH
        elif is_campus_platform or has_placement_kw or any(kw in content for kw in ["placement", "recruitment", "hiring", "job opening"]):
            category = EmailCategory.COLLEGE_NOTICE
            urgency = UrgencyLevel.HIGH
        elif any(kw in content for kw in ["outskill", "workshop", "webinar", "course", "bootcamp"]):
            category = EmailCategory.GENERAL
            urgency = UrgencyLevel.MEDIUM
        elif is_noise:
            category = EmailCategory.NEWSLETTER_SPAM
            urgency = UrgencyLevel.LOW

        # 4. Extract Company / Organization
        company = None
        known_companies = [
            "infosys", "tcs", "wipro", "cognizant", "accenture", "amazon", "google", 
            "microsoft", "meta", "apple", "netflix", "uber", "swiggy", "zomato", 
            "flipkart", "atlassian", "oracle", "cisco", "ibm", "deloitte", "ey", "pwc", "kpmg", "outskill"
        ]
        for comp in known_companies:
            if re.search(rf"\b{comp}\b", email.subject, re.IGNORECASE) or re.search(rf"\b{comp}\b", email.sender, re.IGNORECASE):
                company = comp.upper() if len(comp) <= 4 or comp in ["infosys", "tcs", "wipro"] else comp.capitalize()
                break

        if not company:
            match_co = re.search(r"(at|from|with|for)\s+([A-Z][a-zA-Z0-9&]+)", email.subject)
            if match_co:
                company = match_co.group(2)
            elif is_campus_platform:
                domain_match = re.search(r"@([a-zA-Z0-9.-]+)", email.sender)
                company = domain_match.group(1).split(".")[0].capitalize() if domain_match else "Campus Placement"
            else:
                domain_match = re.search(r"@([a-zA-Z0-9.-]+)", email.sender)
                if domain_match:
                    company = domain_match.group(1).split(".")[0].capitalize()

        # 5. Extract Deadline mention
        deadline_match = re.search(r"(deadline|due|expires|before|by)[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]+ \d{1,2}(?:, \d{4})?)", content)
        deadline_date = deadline_match.group(2) if deadline_match else None

        # 6. Action items
        action_items = []
        if category == EmailCategory.PLACEMENT_OA:
            action_items.append(f"Complete online coding assessment for {company or 'company'} before deadline")
            if important_urls:
                action_items.append(f"Access test link: {important_urls[0]}")
        elif category == EmailCategory.INTERVIEW_INVITE:
            action_items.append(f"Confirm interview slot with {company or 'recruiter'}")
            action_items.append("Review company interview topics and resume")
        elif category == EmailCategory.COLLEGE_NOTICE:
            clean_s = email.subject.replace("\r", " ").replace("\n", " ").strip()[:65]
            action_items.append(f"Review placement notice: {clean_s}")
            if important_urls:
                action_items.append(f"Check portal link: {important_urls[0]}")
        elif category == EmailCategory.DEADLINE_ALERT:
            action_items.append(f"Complete submission before {deadline_date or 'due date'}")

        return ParsedEmail(
            category=category,
            urgency=urgency,
            company_or_sender=company,
            subject_summary=email.subject.replace("\r", " ").replace("\n", " ").strip()[:100],
            deadline_date=deadline_date,
            action_items=action_items,
            important_urls=important_urls[:3],
            is_noise=is_noise,
            confidence_score=0.8
        )
