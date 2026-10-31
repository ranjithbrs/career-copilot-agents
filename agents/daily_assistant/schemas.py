from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TaskItem(BaseModel):
    id: int
    task_description: str
    priority: str
    due_date: Optional[str] = None
    is_completed: bool = False

class DeadlineItem(BaseModel):
    id: int
    title: str
    deadline_dt: Optional[str] = None
    category: Optional[str] = None
    action_url: Optional[str] = None
    is_completed: bool = False

class PlacementItem(BaseModel):
    id: int
    company_name: str
    role: str
    status: str
    test_link: Optional[str] = None
    test_deadline: Optional[str] = None

class DailyBriefing(BaseModel):
    date_str: str
    p0_tasks: List[TaskItem] = Field(default_factory=list)
    p1_tasks: List[TaskItem] = Field(default_factory=list)
    active_deadlines: List[DeadlineItem] = Field(default_factory=list)
    placement_events: List[PlacementItem] = Field(default_factory=list)
    total_pending: int = 0
    formatted_summary: str = ""

class EveningReview(BaseModel):
    date_str: str
    completed_count: int = 0
    pending_count: int = 0
    completed_tasks: List[str] = Field(default_factory=list)
    pending_tasks: List[str] = Field(default_factory=list)
    formatted_summary: str = ""
