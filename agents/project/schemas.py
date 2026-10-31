from typing import List, Optional
from pydantic import BaseModel, Field

class ProjectAudit(BaseModel):
    project_name: str
    repo_path: str
    has_git: bool
    last_commit_date: Optional[str] = None
    days_since_last_commit: Optional[int] = None
    is_stalled: bool = False
    has_readme: bool = False
    has_tests: bool = False
    pending_todos: List[str] = Field(default_factory=list)
    health_score: int = Field(ge=0, le=100)
    suggested_action: str
    formatted_summary: str
