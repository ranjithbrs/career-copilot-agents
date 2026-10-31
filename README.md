# Career Copilot Multi-Agent System

An interconnected 6-agent personal career and productivity operating system designed for students, developers, and job seekers.

---

## 💡 What is this Project in 30 Seconds? (In Plain English)

Searching for jobs, tracking placement applications, preparing for technical interviews, and managing project deadlines can quickly get overwhelming when scattered across inboxes, spreadsheets, and sticky notes.

**Career Copilot Multi-Agent System** solves this by acting as your personal 24/7 AI career management team. Six smart AI assistants coordinate seamlessly in the background:
- 📩 **Email Radar Agent**: Scans incoming messages, immediately identifying interview invites, assessment links, and recruiter updates so nothing falls through the cracks.
- 🎯 **Placement Tracker Agent**: Automatically organizes every job application into a visual funnel (*Applied ➡️ Interviewing ➡️ Offered*).
- 📚 **Study & Skill Agent**: Tracks topics you are studying and recommends targeted revision before tests.
- 💼 **Project Progress Agent**: Logs development milestones, tasks, and GitHub commits.
- ⏰ **Daily Briefing Assistant**: Prepares a clear morning summary of today's highest-priority action items.
- 🤝 **Networking Agent**: Drafts polite, professional follow-up messages for recruiters and connections.

Everything connects directly to a clean, interactive **Streamlit web dashboard** running locally in your browser!

---

## 🏗️ Project Architecture

```
career-copilot-agents/
├── .env.example             # Configuration template (Gemini API, IMAP, Telegram)
├── requirements.txt         # Dependencies
├── main.py                  # Master CLI runner
├── config/
│   └── settings.py          # Centralized environment and path settings
├── database/
│   ├── connection.py        # SQLite context managers and connection pool
│   └── models.py            # SQLite table schemas (Shared Memory)
├── data/
│   └── hub.db               # SQLite database file (auto-generated)
├── agents/
│   ├── email_intel/         # Agent 1: Email Intelligence Radar
│   │   ├── schemas.py       # Pydantic data models
│   │   ├── extractor.py     # LLM (Gemini) + Heuristic Fallback Extractor
│   │   ├── ingester.py      # IMAP mail client & Mock sample generator
│   │   └── agent.py         # Main Email Intelligence Agent orchestration
│   ├── placement/           # Agent 2: (Coming in Phase 3)
│   ├── learning/            # Agent 3: (Coming in Phase 4)
│   ├── project/             # Agent 4: (Coming in Phase 4)
│   ├── daily_assistant/     # Agent 5: (Coming in Phase 2)
│   └── linkedin/            # Agent 6: (Coming in Phase 3)
└── tests/
    └── test_email_intel.py  # End-to-end automated unit test suite
```

---

## 🚀 Quickstart & Commands

### 1. Launch Visual Web Dashboard (Streamlit)
Launch the interactive browser dashboard with visual placement funnel, study logger, and daily priorities:
```powershell
.venv\Scripts\streamlit.exe run app.py
```
*Opens automatically at:* `http://localhost:8501`

### 2. Unified 6-Agent Single-Shot Sync (Phase 5)
Run the entire coordinated pipeline across all 6 agents with a single command:
```powershell
python main.py --sync-all
```
To also dispatch the generated briefing to Telegram:
```powershell
python main.py --sync-all --telegram
```

### 2. Autonomous Background Daemon (Hands-Free Mode)
Runs continuously in the background, polling for critical emails, scheduling daily study targets, triggering morning briefings at 08:00 AM, and triggering evening reviews at 09:00 PM:
```powershell
# Run with default 15-minute polling interval
python main.py --daemon

# Run with custom polling interval (e.g. 5 minutes / 300 seconds)
python main.py --daemon --poll-interval 300 --telegram
```

### 3. View Daily Morning Briefing (Agent 5)
```powershell
python main.py --mode briefing
```
To also dispatch this to Telegram:
```powershell
python main.py --mode briefing --telegram
```

### 2. View Evening Accountability Review (Agent 5)
```powershell
python main.py --mode evening
```

### 3. Placement Agent: Company Prep & Stage Tracking (Agent 2)
```powershell
# Generate tailored interview/OA prep dossier (e.g. Amazon, Microsoft, Google, etc.)
python main.py --prep-company "Amazon"

# Advance hiring stage for an application
python main.py --advance-stage "Microsoft" --stage TECHNICAL_ROUND_1
```

### 4. LinkedIn Agent: Outreach & Milestone Posts (Agent 6)
```powershell
# Draft recruiter connection note (< 300 characters for LinkedIn free note limit)
python main.py --draft-outreach "Microsoft" --type recruiter --name "Alex"

# Draft alumni referral request
python main.py --draft-outreach "Amazon" --type alumni --name "Rahul" --job-id "JOB-2026-SDE"

# Draft a "Build in Public" LinkedIn post
python main.py --draft-post "Built an autonomous 6-agent career copilot in Python"

# View recent drafts
python main.py --view-drafts
```

### 5. Learning Agent: Spaced Repetition & DSA/Python/SQL (Agent 3)
```powershell
# Get today's recommended study targets (auto-injected into morning briefing)
python main.py --daily-study

# Log a study session (e.g. solved 3 problems on Dynamic Programming with high confidence)
python main.py --log-study "Dynamic Programming" --problems 3 --confidence 4

# View your skill mastery heatmap, problems solved, and revision schedule
python main.py --learning-stats
```

### 6. Project Agent: GitHub Health & Codebase Auditor (Agent 4)
```powershell
# Audit a project repository for commit freshness, README quality, and code TODOs
python main.py --audit-project "."

# Audit any external repository path
python main.py --audit-project "C:\path\to\your\other-repo"
```

### 7. Complete Tasks & Deadlines Interactively
```powershell
# Mark an action item as completed
python main.py --done-task 3

# Mark a deadline as completed
python main.py --done-deadline 1

# Manually add a custom task
python main.py --add-task "Practice 2 LeetCode Graph problems" --priority P0
```

### 4. Run Email Intelligence Agent (Agent 1)
```powershell
# Ingest mock test emails
python main.py --mode mock

# Reset local database and run mock mode fresh
python main.py --mode mock --reset

# Ingest live emails via IMAP
python main.py --mode live

# Inspect raw database tables
python main.py --mode dashboard
```

### 11. Run Automated Tests
```powershell
# Run individual agent tests
python tests/test_email_intel.py
python tests/test_daily_assistant.py
python tests/test_placement_agent.py
python tests/test_linkedin_agent.py
python tests/test_learning_agent.py
python tests/test_project_agent.py
python tests/test_daemon.py
```

---

## 📱 Setting up Telegram Push Notifications (Optional)

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, choose a name and username, and copy your API Token.
3. Message your new bot once, then find your Chat ID (e.g. by forwarding a message to `@userinfobot`).
4. Add them to your `.env` file:
   ```ini
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuvWxyz
   TELEGRAM_CHAT_ID=987654321
   ```
5. Test delivery:
   ```powershell
   python main.py --mode briefing --telegram
   ```

---

## 📬 Connecting to Real Gmail / Webmail (Live Mode)

1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Configure your credentials in `.env`:
   * **`GEMINI_API_KEY`**: Your Google Gemini API Key (for high-accuracy entity extraction).
   * **`EMAIL_USER`**: Your email address (e.g. `yourname@gmail.com`).
   * **`EMAIL_PASSWORD`**: 
     * For **Gmail**: Enable 2-Step Verification, visit [Google App Passwords](https://myaccount.google.com/apppasswords), generate an App Password, and paste the 16-character code here.
     * For **Outlook / University mail**: Use your IMAP app password or account credentials.
3. Run Live Ingestion:
   ```powershell
   python main.py --mode live
   ```
