from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class HiringStage(str, Enum):
    APPLIED = "APPLIED"
    OA_PENDING = "OA_PENDING"
    OA_SUBMITTED = "OA_SUBMITTED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    TECHNICAL_ROUND_1 = "TECHNICAL_ROUND_1"
    TECHNICAL_ROUND_2 = "TECHNICAL_ROUND_2"
    HR_ROUND = "HR_ROUND"
    OFFER = "OFFER"
    REJECTED = "REJECTED"

class CompanyDossier(BaseModel):
    company_name: str
    role: str = "Software Engineer"
    dsa_focus: List[str] = Field(default_factory=list, description="Top high-yield DSA patterns for this company")
    cs_fundamentals: List[str] = Field(default_factory=list, description="Key OS, DBMS, Networks, or OOP concepts asked")
    behavioral_topics: List[str] = Field(default_factory=list, description="Company values / behavioral themes (e.g. Amazon LPs)")
    actionable_prep_tasks: List[str] = Field(default_factory=list, description="Specific practice tasks to assign to the user")
    full_dossier_text: str = Field(description="Formatted cheat sheet for the company")

class PipelineRecord(BaseModel):
    id: int
    company_name: str
    role: str
    status: str
    test_link: Optional[str] = None
    test_deadline: Optional[str] = None
    prep_notes: Optional[str] = None
    updated_at: str
