from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class UrgencyLevel(str, Enum):
    CRITICAL = "CRITICAL"    # e.g. OA expires within 24h, interview tomorrow
    HIGH = "HIGH"            # e.g. OA link valid for 3-5 days, assignment due this week
    MEDIUM = "MEDIUM"        # e.g. Application acknowledgment, normal notice
    LOW = "LOW"              # e.g. Info newsletter, general notification

class EmailCategory(str, Enum):
    PLACEMENT_OA = "PLACEMENT_OA"
    INTERVIEW_INVITE = "INTERVIEW_INVITE"
    JOB_APPLICATION = "JOB_APPLICATION"
    DEADLINE_ALERT = "DEADLINE_ALERT"
    COLLEGE_NOTICE = "COLLEGE_NOTICE"
    NEWSLETTER_SPAM = "NEWSLETTER_SPAM"
    GENERAL = "GENERAL"

class RawEmail(BaseModel):
    message_id: str
    sender: str
    subject: str
    date: str
    body: str

class ParsedEmail(BaseModel):
    category: EmailCategory = Field(description="Category of the email")
    urgency: UrgencyLevel = Field(description="Urgency priority")
    company_or_sender: Optional[str] = Field(default=None, description="Company name or college authority")
    subject_summary: str = Field(description="One-sentence clear summary of the email purpose")
    deadline_date: Optional[str] = Field(default=None, description="Exact deadline date/time extracted if present (e.g. 2026-11-05 18:00 IST)")
    action_items: List[str] = Field(default_factory=list, description="List of immediate concrete tasks required from the user")
    important_urls: List[str] = Field(default_factory=list, description="Links to assessments, forms, or portals")
    is_noise: bool = Field(default=False, description="True if marketing, promotional, or irrelevant spam")
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0, description="Extraction confidence")
