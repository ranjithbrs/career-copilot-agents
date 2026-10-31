"""
Database schema definitions for the Central Hub SQLite database.
Shared across all 6 agents.
"""

INIT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS emails_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    sender TEXT NOT NULL,
    subject TEXT NOT NULL,
    date_received TEXT,
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    is_noise INTEGER NOT NULL DEFAULT 0,
    parsed_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER,
    title TEXT NOT NULL,
    deadline_dt TEXT,
    category TEXT,
    action_url TEXT,
    is_completed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(email_id) REFERENCES emails_raw(id)
);

CREATE TABLE IF NOT EXISTS placement_pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER,
    company_name TEXT NOT NULL,
    role TEXT DEFAULT 'Software Engineer',
    status TEXT NOT NULL, -- 'APPLIED', 'OA_PENDING', 'INTERVIEW_SCHEDULED', 'OFFER', 'REJECTED'
    test_link TEXT,
    test_deadline TEXT,
    prep_notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(email_id) REFERENCES emails_raw(id)
);

CREATE TABLE IF NOT EXISTS action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_agent TEXT NOT NULL, -- 'EMAIL_INTEL', 'PLACEMENT', 'LEARNING', 'PROJECT'
    task_description TEXT NOT NULL,
    priority TEXT DEFAULT 'P1', -- 'P0', 'P1', 'P2', 'P3'
    due_date TEXT,
    is_completed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_dossiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'Software Engineer',
    dsa_focus TEXT,
    cs_fundamentals TEXT,
    behavioral_topics TEXT,
    full_dossier_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS linkedin_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_company TEXT,
    draft_type TEXT NOT NULL, -- 'ALUMNI_REFERRAL', 'RECRUITER_NOTE', 'MILESTONE_POST'
    recipient_name TEXT,
    content TEXT NOT NULL,
    character_count INTEGER NOT NULL,
    is_sent INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL, -- 'DSA', 'PYTHON', 'SQL'
    topic_name TEXT UNIQUE NOT NULL,
    mastery_level INTEGER DEFAULT 1, -- 1 (Novice) to 5 (Mastered)
    last_reviewed_at TEXT,
    next_review_due TEXT,
    review_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS learning_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name TEXT NOT NULL,
    problems_solved INTEGER DEFAULT 1,
    confidence_rating INTEGER DEFAULT 3, -- 1 to 5
    notes TEXT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracked_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT UNIQUE NOT NULL,
    repo_path TEXT NOT NULL,
    last_commit_date TEXT,
    is_stalled INTEGER DEFAULT 0,
    pending_todos_count INTEGER DEFAULT 0,
    health_score INTEGER DEFAULT 0,
    audit_summary TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails_raw(message_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_due ON deadlines(deadline_dt);
CREATE INDEX IF NOT EXISTS idx_action_items_priority ON action_items(priority, is_completed);
CREATE INDEX IF NOT EXISTS idx_dossiers_company ON company_dossiers(company_name);
CREATE INDEX IF NOT EXISTS idx_linkedin_drafts_company ON linkedin_drafts(target_company);
CREATE INDEX IF NOT EXISTS idx_learning_due ON learning_topics(next_review_due);
"""
