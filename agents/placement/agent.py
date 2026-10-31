import json
import logging
from typing import List, Optional, Dict, Any, Union
from database.connection import get_db_connection
from agents.placement.schemas import HiringStage, CompanyDossier, PipelineRecord
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

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
