import os
import re
import datetime
import subprocess
import logging
from pathlib import Path
from typing import List, Optional
from database.connection import get_db_connection
from agents.project.schemas import ProjectAudit

logger = logging.getLogger(__name__)

class ProjectAgent:
    """Agent 4: Tracks GitHub / local code projects, detects stalled development, audits health, and scans for TODOs."""

    def __init__(self):
        pass

    def audit_repository(self, repo_path: str = ".", inject_task: bool = True) -> ProjectAudit:
        """Run an automated health and freshness audit on a local project repository."""
        target = Path(repo_path).resolve()
        project_name = target.name

        # 1. Check Git & Last Commit
        has_git = (target / ".git").exists()
        last_commit_date, days_since_commit = self._get_last_commit_info(target)
        is_stalled = False
        if days_since_commit is not None and days_since_commit > 7:
            is_stalled = True
        elif not has_git:
            is_stalled = True

        # 2. Check Documentation (README.md)
        readme_file = target / "README.md"
        has_readme = False
        if readme_file.exists() and readme_file.stat().st_size > 150:
            has_readme = True

        # 3. Check Test Suite
        test_dir = target / "tests"
        has_tests = test_dir.exists() and any(test_dir.glob("test_*.py"))

        # 4. Scan Codebase for TODOs & FIXMEs
        pending_todos = self._scan_todos(target)

        # 5. Calculate Health Score (0-100)
        score = 0
        if has_git:
            score += 20
        if days_since_commit is not None and days_since_commit <= 7:
            score += 25
        elif days_since_commit is not None and days_since_commit <= 14:
            score += 15
        if has_readme:
            score += 25
        if has_tests:
            score += 20
        if len(pending_todos) <= 3:
            score += 10
        elif len(pending_todos) <= 8:
            score += 5

        # 6. Formulate High-Impact Action
        if not has_readme:
            suggested_action = f"{project_name}: Create comprehensive README.md with setup instructions"
        elif not has_tests:
            suggested_action = f"{project_name}: Set up basic unit tests in tests/ directory"
        elif is_stalled:
            suggested_action = f"{project_name}: Commit pending changes or push new feature to break {days_since_commit}-day commit stall"
        elif pending_todos:
            suggested_action = f"{project_name}: Resolve open task: {pending_todos[0]}"
        else:
            suggested_action = f"{project_name}: Optimize performance and polish documentation for portfolio review"

        # Format Summary
        summary_lines = [
            "============================================================",
            f"  PROJECT AUDIT: {project_name.upper()} (Health Score: {score}/100)",
            "============================================================",
            f"Repository Path:   {target}",
            f"Git Initialized:   {'Yes' if has_git else 'No'}",
            f"Last Commit:       {last_commit_date or 'No commits found'} ({days_since_commit if days_since_commit is not None else 'N/A'} days ago)",
            f"Stall Alert:       {'[STALLED > 7 DAYS]' if is_stalled else '[ACTIVE]'}",
            f"Documentation:     {'[OK] Comprehensive README' if has_readme else '[MISSING / TOO SHORT]'}",
            f"Automated Tests:   {'[OK] Tests Present' if has_tests else '[MISSING]'}",
            f"Open Code TODOs:   {len(pending_todos)} found",
            "",
            "[*] HIGH PRIORITY ENGINEERING ACTION:",
            f"  -> {suggested_action}"
        ]

        if pending_todos:
            summary_lines.append("\n[*] OPEN TODOS DETECTED IN CODEBASE:")
            for todo in pending_todos[:5]:
                summary_lines.append(f"  * {todo}")

        formatted_summary = "\n".join(summary_lines)

        audit = ProjectAudit(
            project_name=project_name,
            repo_path=str(target),
            has_git=has_git,
            last_commit_date=last_commit_date,
            days_since_last_commit=days_since_commit,
            is_stalled=is_stalled,
            has_readme=has_readme,
            has_tests=has_tests,
            pending_todos=pending_todos[:10],
            health_score=score,
            suggested_action=suggested_action,
            formatted_summary=formatted_summary
        )

        self._save_audit(audit)

        if inject_task:
            self._inject_dev_task(suggested_action)

        return audit

    def _get_last_commit_info(self, target: Path):
        """Extract last commit date and calculate days elapsed."""
        if not (target / ".git").exists():
            return None, None

        try:
            output = subprocess.check_output(
                ["git", "log", "-1", "--format=%cd", "--date=short"],
                cwd=target,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            if output:
                commit_dt = datetime.datetime.strptime(output, "%Y-%m-%d").date()
                days_ago = (datetime.date.today() - commit_dt).days
                return output, days_ago
        except Exception:
            pass

        return None, None

    def _scan_todos(self, target: Path) -> List[str]:
        """Scan codebase files for TODO, FIXME, BUG tags."""
        todos = []
        ignore_dirs = {".git", "__pycache__", "venv", ".venv", "env", "data", "node_modules", ".idea"}
        extensions = {".py", ".js", ".ts", ".html", ".css", ".sql", ".sh"}

        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                p = Path(root) / file
                if p.suffix in extensions and p.stat().st_size < 500_000:
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as f:
                            for idx, line in enumerate(f, 1):
                                match = re.search(r"(?:#|//|<!--)\s*(TODO|FIXME|BUG)[:\s]+(.+)", line, re.IGNORECASE)
                                if match:
                                    todos.append(f"{p.name}:{idx} [{match.group(1).upper()}] {match.group(2).strip()[:80]}")
                    except Exception:
                        continue
        return todos

    def _save_audit(self, audit: ProjectAudit) -> None:
        """Persist audit record in tracked_projects table."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tracked_projects (project_name, repo_path, last_commit_date, is_stalled, pending_todos_count, health_score, audit_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_name) DO UPDATE SET
                    repo_path = excluded.repo_path,
                    last_commit_date = excluded.last_commit_date,
                    is_stalled = excluded.is_stalled,
                    pending_todos_count = excluded.pending_todos_count,
                    health_score = excluded.health_score,
                    audit_summary = excluded.audit_summary,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    audit.project_name,
                    audit.repo_path,
                    audit.last_commit_date,
                    1 if audit.is_stalled else 0,
                    len(audit.pending_todos),
                    audit.health_score,
                    audit.formatted_summary
                )
            )

    def _inject_dev_task(self, action_text: str) -> None:
        """Inject engineering task into action_items for Daily Assistant."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            desc = f"Dev Task: {action_text}"
            cursor.execute(
                "SELECT 1 FROM action_items WHERE task_description = ? AND is_completed = 0",
                (desc,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO action_items (origin_agent, task_description, priority)
                    VALUES (?, ?, ?)
                    """,
                    ("PROJECT", desc, "P1")
                )
