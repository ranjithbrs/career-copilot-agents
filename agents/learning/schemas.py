from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class SubjectType(str, Enum):
    DSA = "DSA"
    PYTHON = "PYTHON"
    SQL = "SQL"

class TopicRecord(BaseModel):
    id: Optional[int] = None
    subject: SubjectType
    topic_name: str
    mastery_level: int = 1
    last_reviewed_at: Optional[str] = None
    next_review_due: Optional[str] = None
    review_count: int = 0

class StudyTarget(BaseModel):
    subject: SubjectType
    topic_name: str
    recommended_problems: List[str] = Field(default_factory=list)
    reason: str

class LearningSummary(BaseModel):
    total_topics: int
    mastered_topics: int
    in_progress_topics: int
    overdue_topics: int
    total_problems_solved: int
    formatted_report: str
