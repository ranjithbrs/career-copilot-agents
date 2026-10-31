import json
import re
import logging
from typing import List, Optional, Dict, Any, Union
from database.connection import get_db_connection
from agents.placement.schemas import HiringStage, CompanyDossier, PipelineRecord
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

CURATED_INTERVIEW_QUESTIONS = {
    "amazon": [
        "Tell me about a time you showed Customer Obsession by going beyond your assigned duties.",
        "Describe a situation where you had to make a technical decision with incomplete information (Bias for Action).",
        "Give an example of a tough problem you faced and how you took Ownership to resolve it without escalating."
    ],
    "google": [
        "Tell me about a time you worked on an ambiguous project with no clear specifications.",
        "Describe a time you navigated technical conflict or disagreement with a peer or senior engineer.",
        "Give an example of how you used data or profiling to diagnose and fix a complex performance bottleneck."
    ],
    "microsoft": [
        "Tell me about a time you failed or made a technical mistake, and what you learned from it (Growth Mindset).",
        "Describe a project where you collaborated with a cross-functional team to deliver an impactful feature.",
        "How do you stay up-to-date with emerging technologies and apply them to your daily work?"
    ],
    "general": [
        "Tell me about yourself and your most challenging engineering project.",
        "Describe a time when you were under a tight deadline and had to prioritize features.",
        "Tell me about a time you improved a system or codebase that you didn't originally write."
    ]
}

CURATED_PREP_DATA = {
    "amazon": {
        "dsa_focus": [
            "BFS/DFS on 2D Grids (e.g., Number of Islands, Rotting Oranges)",
            "Sliding Window & Two Pointers (e.g., Longest Substring Without Repeating Characters)",
            "Dynamic Programming (e.g., 0/1 Knapsack variants, Coin Change)",
            "Heaps / Priority Queues (e.g., Top K Frequent Elements, Median from Data Stream)"
        ],
        "cs_fundamentals": [
            "OOP Design Patterns (Factory, Singleton, Strategy)",
            "RDBMS ACID properties and B+ Tree indexing",
            "Multi-threading, Race Conditions, and Mutex locks"
        ],
        "behavioral_topics": [
            "16 Amazon Leadership Principles (Customer Obsession, Ownership, Bias for Action, Deliver Results)",
            "Prepare STAR stories (Situation, Task, Action, Result) with quantifiable impact metrics"
        ],
        "actionable_prep_tasks": [
            "Amazon Prep: Solve 2 Grid BFS/DFS problems (Rotting Oranges, Word Search)",
            "Amazon Prep: Practice 1 Top-K Heap problem",
            "Amazon Prep: Prepare 3 STAR stories for Customer Obsession & Ownership"
        ]
    },
    "microsoft": {
        "dsa_focus": [
            "Binary Trees & BSTs (LCA, Diameter, Level Order Traversal)",
            "Linked Lists (Reverse in K-groups, Cycle detection)",
            "String Parsing and Two-Pointer logic"
        ],
        "cs_fundamentals": [
            "Operating Systems: Concurrency, Deadlocks, Mutex vs Semaphore",
            "Virtual Memory, Paging, and Page Faults",
            "Database Normalization and Foreign Key constraints"
        ],
        "behavioral_topics": [
            "Growth Mindset and Adaptability",
            "Handling technical failure or constructive feedback",
            "Cross-functional collaboration and empathy"
        ],
        "actionable_prep_tasks": [
            "Microsoft Prep: Solve LCA of Binary Tree & Zigzag Level Order",
            "Microsoft Prep: Review OS Concurrency & Deadlock prevention",
            "Microsoft Prep: Prepare a story about learning from a technical mistake"
        ]
    },
    "google": {
        "dsa_focus": [
            "Advanced Graphs (Dijkstra, Topological Sort, Strongly Connected Components)",
            "Trie / Prefix Trees and String matching",
            "Intervals and Greedy Algorithms",
            "Bit Manipulation and Math-based problems"
        ],
        "cs_fundamentals": [
            "Distributed Systems: Consistent Hashing, CAP Theorem, Load Balancing",
            "Memory management, Cache Locality (L1/L2), and Stack vs Heap",
            "Linux system calls and Network Sockets (TCP/UDP handshake)"
        ],
        "behavioral_topics": [
            "Googleyness: Navigating Ambiguity and thriving without rigid specs",
            "Intellectual humility and open discourse",
            "Bias for doing the right thing for the user"
        ],
        "actionable_prep_tasks": [
            "Google Prep: Solve Course Schedule (Topological Sort)",
            "Google Prep: Implement a complete Trie with Insert/Search/StartsWith",
            "Google Prep: Review Consistent Hashing and CAP Theorem"
        ]
    }
}

class PlacementAgent:
    """Agent 2: Manages the hiring pipeline and prepares company-specific interview dossiers."""

    def __init__(self):
        pass

    def get_pipeline(self) -> List[PipelineRecord]:
        """Fetch all current entries in the placement pipeline."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, company_name, role, status, test_link, test_deadline, prep_notes, updated_at
                FROM placement_pipeline
                ORDER BY id DESC
                """
            )
            return [
                PipelineRecord(
                    id=row["id"],
                    company_name=row["company_name"],
                    role=row["role"],
                    status=row["status"],
                    test_link=row["test_link"],
                    test_deadline=row["test_deadline"],
                    prep_notes=row["prep_notes"],
                    updated_at=str(row["updated_at"])
                )
                for row in cursor.fetchall()
            ]

    def advance_stage(self, identifier: Union[int, str], new_stage: HiringStage) -> bool:
        """Update the hiring status for a company by ID or name."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if isinstance(identifier, int):
                cursor.execute(
                    "UPDATE placement_pipeline SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_stage.value, identifier)
                )
            else:
                cursor.execute(
                    "UPDATE placement_pipeline SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE company_name LIKE ?",
                    (new_stage.value, f"%{identifier}%")
                )
            return cursor.rowcount > 0

    def add_pipeline_entry(
        self,
        company_name: str,
        role: str = "Software Engineer",
        status: str = "APPLIED",
        test_link: Optional[str] = None,
        test_deadline: Optional[str] = None,
        prep_notes: Optional[str] = None
    ) -> int:
        """Add a new company application into the placement pipeline."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO placement_pipeline (company_name, role, status, test_link, test_deadline, prep_notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (company_name, role, status, test_link, test_deadline, prep_notes)
            )
            return cursor.lastrowid

    def delete_pipeline_entry(self, entry_id: int) -> bool:
        """Remove a company from the pipeline."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM placement_pipeline WHERE id = ?", (entry_id,))
            return cursor.rowcount > 0

    def generate_dossier(self, company_name: str, role: str = "Software Engineer", inject_tasks: bool = True) -> CompanyDossier:
        """Generate a tailored interview prep dossier for a company and inject prep tasks into action_items."""
        co_key = company_name.strip().lower()

        # Check curated knowledge base first
        if co_key in CURATED_PREP_DATA:
            data = CURATED_PREP_DATA[co_key]
            dossier = self._build_dossier_from_dict(company_name, role, data)
        else:
            # Fallback to LLM if configured or default template
            dossier = self._generate_with_llm_or_default(company_name, role)

        # Store in company_dossiers table
        self._save_dossier(dossier)

        # Inject prep tasks into central action_items
        if inject_tasks and dossier.actionable_prep_tasks:
            self._inject_action_items(dossier)

        return dossier

    def _build_dossier_from_dict(self, company_name: str, role: str, data: Dict[str, Any]) -> CompanyDossier:
        lines = [
            f"============================================================",
            f"  INTERVIEW & OA PREP DOSSIER: {company_name.upper()} ({role.upper()})",
            f"============================================================",
            "",
            "[*] HIGH-YIELD DSA PATTERNS:",
        ]
        for p in data["dsa_focus"]:
            lines.append(f"  * {p}")

        lines.append("\n[*] CORE CS FUNDAMENTALS:")
        for cs in data["cs_fundamentals"]:
            lines.append(f"  * {cs}")

        lines.append("\n[*] BEHAVIORAL & VALUES:")
        for b in data["behavioral_topics"]:
            lines.append(f"  * {b}")

        lines.append("\n[*] TARGET PREPARATION CHECKLIST:")
        for t in data["actionable_prep_tasks"]:
            lines.append(f"  [ ] {t}")

        full_text = "\n".join(lines)

        return CompanyDossier(
            company_name=company_name,
            role=role,
            dsa_focus=data["dsa_focus"],
            cs_fundamentals=data["cs_fundamentals"],
            behavioral_topics=data["behavioral_topics"],
            actionable_prep_tasks=data["actionable_prep_tasks"],
            full_dossier_text=full_text
        )

    def _generate_with_llm_or_default(self, company_name: str, role: str) -> CompanyDossier:
        """Generate tailored strategy via Gemini if key is available, else standard SWE baseline."""
        if GEMINI_API_KEY:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=GEMINI_API_KEY)
                prompt = f"""
Generate an interview preparation strategy for {company_name} for the role of {role}.
Return structured JSON with:
- dsa_focus: list of 3-4 top data structures / algorithms patterns commonly asked
- cs_fundamentals: list of 2-3 essential OS/DBMS/OOP topics
- behavioral_topics: list of 2 company culture or behavioral expectations
- actionable_prep_tasks: list of 3 concrete practice tasks for this week
"""
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                parsed_json = json.loads(response.text)
                return self._build_dossier_from_dict(company_name, role, parsed_json)
            except Exception as e:
                logger.warning(f"Could not generate via LLM ({e}). Using standard SWE baseline.")

        # Default high-yield baseline for tech companies
        default_data = {
            "dsa_focus": [
                "Arrays, Hash Maps, and Two Pointers",
                "Binary Search on Answer Spaces",
                "Breadth-First Search (BFS) on Graphs",
                "Dynamic Programming: 1D Memoization"
            ],
            "cs_fundamentals": [
                "SQL Joins, Group By, Aggregations, and Indexing",
                "OS: Process vs Thread, Deadlock conditions",
                "OOP: Polymorphism, Inheritance, Encapsulation with real-world examples"
            ],
            "behavioral_topics": [
                "STAR method stories on overcoming technical obstacles",
                "Demonstrating fast learning ability and passion for software engineering"
            ],
            "actionable_prep_tasks": [
                f"{company_name} Prep: Solve 2 Two-Pointer / Sliding Window problems",
                f"{company_name} Prep: Review SQL Aggregations and Window Functions",
                f"{company_name} Prep: Rehearse a 2-minute elevator pitch and resume walkthrough"
            ]
        }
        return self._build_dossier_from_dict(company_name, role, default_data)

    def _save_dossier(self, dossier: CompanyDossier) -> None:
        """Persist dossier into company_dossiers table."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO company_dossiers (company_name, role, dsa_focus, cs_fundamentals, behavioral_topics, full_dossier_text)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_name) DO UPDATE SET
                    role = excluded.role,
                    dsa_focus = excluded.dsa_focus,
                    cs_fundamentals = excluded.cs_fundamentals,
                    behavioral_topics = excluded.behavioral_topics,
                    full_dossier_text = excluded.full_dossier_text,
                    created_at = CURRENT_TIMESTAMP
                """,
                (
                    dossier.company_name,
                    dossier.role,
                    json.dumps(dossier.dsa_focus),
                    json.dumps(dossier.cs_fundamentals),
                    json.dumps(dossier.behavioral_topics),
                    dossier.full_dossier_text
                )
            )

    def _inject_action_items(self, dossier: CompanyDossier) -> None:
        """Inject company prep tasks into action_items so they appear in morning briefing."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for task in dossier.actionable_prep_tasks:
                # Avoid inserting duplicate task text
                cursor.execute(
                    "SELECT 1 FROM action_items WHERE task_description = ? AND is_completed = 0",
                    (task,)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO action_items (origin_agent, task_description, priority)
                        VALUES (?, ?, ?)
                        """,
                        ("PLACEMENT", task, "P0")
                    )

    def grade_behavioral_answer(self, company_name: str, question: str, user_answer: str) -> Dict[str, Any]:
        """
        Evaluate candidate's behavioral answer using STAR rubric (Situation, Task, Action, Result)
        and company leadership principles.
        """
        if GEMINI_API_KEY:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=GEMINI_API_KEY)
                prompt = f"""
Company: {company_name}
Question: {question}
Candidate's Answer: {user_answer}

Grade this behavioral answer strictly for a Software Engineer role.
Return JSON with:
- score: Integer from 1 to 10
- star_breakdown: Dict with keys 'situation', 'task', 'action', 'result' each containing a 1-sentence assessment
- strengths: List of 2 key strengths
- areas_for_improvement: List of 2 concrete weaknesses (e.g. missing metrics, too vague on personal actions)
- improved_rewrite: A polished 4-paragraph STAR response demonstrating high ownership and quantifiable impact.
"""
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                data = json.loads(response.text)
                score = data.get("score", 7)
                feedback = json.dumps({
                    "star_breakdown": data.get("star_breakdown", {}),
                    "strengths": data.get("strengths", []),
                    "areas_for_improvement": data.get("areas_for_improvement", [])
                })
                improved = data.get("improved_rewrite", "")
                self._save_mock_interview(company_name, question, user_answer, score, feedback, improved)
                return {
                    "score": score,
                    "star_breakdown": data.get("star_breakdown", {}),
                    "strengths": data.get("strengths", []),
                    "areas_for_improvement": data.get("areas_for_improvement", []),
                    "improved_rewrite": improved
                }
            except Exception as e:
                logger.warning(f"Gemini STAR grading fallback: {e}")

        # Rule-based STAR Rubric Engine
        lower_ans = user_answer.lower()
        has_situation = any(w in lower_ans for w in ["when", "during", "while", "project", "working on", "at my", "in my"])
        has_task = any(w in lower_ans for w in ["goal", "task", "objective", "challenge", "problem was", "needed to"])
        has_action = any(w in lower_ans for w in ["i built", "i designed", "i created", "i implemented", "i analyzed", "i decided", "my approach"])
        has_metrics = bool(re.search(r"(\d+%\b|\d+x\b|\d+ ms|\d+ days|\d+ users|\$|\bmetrics\b)", lower_ans))

        score = 5
        if has_situation: score += 1
        if has_task: score += 1
        if has_action: score += 1
        if has_metrics: score += 2
        score = min(10, max(3, score))

        star_breakdown = {
            "situation": "Clear project context established." if has_situation else "Context is vague; mention the specific company, team, or project timeline.",
            "task": "Problem or objective clearly identified." if has_task else "Specify the exact engineering bottleneck or obstacle you were assigned to solve.",
            "action": "Strong individual agency ('I implemented/designed')." if has_action else "Focus on what YOU personally coded and decided, not what 'we' did.",
            "result": "Quantifiable impact and metrics included." if has_metrics else "Missing quantitative metrics (e.g., reduced latency by 30%, saved 5 hours/week)."
        }

        strengths = []
        if has_action: strengths.append("Emphasized personal ownership and engineering initiative")
        if has_situation: strengths.append("Provided real-world technical scenario context")
        if not strengths: strengths.append("Direct answer to the prompt")

        improvements = []
        if not has_metrics: improvements.append("Quantify the final result with numbers (%, seconds, users, throughput)")
        if not has_action: improvements.append("Use first-person active verbs ('I architected', 'I refactored') instead of passive voice")
        if not improvements: improvements.append("Tie your outcome directly to the company's core values")

        improved_rewrite = f"""**Situation:** During my software engineering project at {company_name.capitalize() if company_name.lower() != 'general' else 'my team'}, we had to address an urgent reliability requirement.

**Task:** My objective was to eliminate bottlenecks and ensure the system scaled under heavy load before launch.

**Action:** I designed and implemented an asynchronous pipeline in Python, replaced linear lookup scans with hash indexes, and wrote comprehensive unit tests with automated regression coverage.

**Result:** Successfully decreased latency by 45%, eliminated deadlocks, and delivered the feature 2 days ahead of deadline with zero regression defects."""

        feedback_json = json.dumps({
            "star_breakdown": star_breakdown,
            "strengths": strengths,
            "areas_for_improvement": improvements
        })

        self._save_mock_interview(company_name, question, user_answer, score, feedback_json, improved_rewrite)

        return {
            "score": score,
            "star_breakdown": star_breakdown,
            "strengths": strengths,
            "areas_for_improvement": improvements,
            "improved_rewrite": improved_rewrite
        }

    def _save_mock_interview(self, company: str, question: str, answer: str, score: int, feedback: str, improved: str) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO mock_interviews (company_name, question, user_answer, score, star_feedback, improved_answer)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (company, question, answer, score, feedback, improved)
            )
