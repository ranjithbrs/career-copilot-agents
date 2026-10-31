from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class DraftType(str, Enum):
    ALUMNI_REFERRAL = "ALUMNI_REFERRAL"
    RECRUITER_NOTE = "RECRUITER_NOTE"
    MILESTONE_POST = "MILESTONE_POST"

class LinkedInDraft(BaseModel):
    id: Optional[int] = None
    target_company: Optional[str] = None
    draft_type: DraftType
    recipient_name: Optional[str] = None
    content: str
    character_count: int
    is_sent: bool = False
    created_at: Optional[str] = None
