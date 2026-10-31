import streamlit as st
import datetime
import json
import os
from pathlib import Path
from database.connection import init_db, get_db_connection
from agents.email_intel.agent import EmailIntelligenceAgent
from agents.daily_assistant.agent import DailyAssistantAgent
from agents.placement.agent import PlacementAgent
from agents.placement.schemas import HiringStage
from agents.linkedin.agent import LinkedInAgent
from agents.learning.agent import LearningAgent
from agents.project.agent import ProjectAgent
from daemon import AutonomousOrchestrator
import config.settings as settings

# ------------------------------------------------------------------------------
# STREAMLIT CONFIG & SECRETS SYNCHRONIZATION
# ------------------------------------------------------------------------------
if hasattr(st, "secrets"):
    for k, v in st.secrets.items():
        os.environ[k] = str(v)
        if hasattr(settings, k):
            setattr(settings, k, str(v))

st.set_page_config(
    page_title="Career Copilot AI - 6-Agent Personal OS",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema
init_db()

# Initialize agents
assistant = DailyAssistantAgent()
email_agent = EmailIntelligenceAgent()
placement_agent = PlacementAgent()
linkedin_agent = LinkedInAgent()
learning_agent = LearningAgent()
project_agent = ProjectAgent()
has_email_creds = bool(os.getenv("EMAIL_USER") and os.getenv("EMAIL_PASSWORD"))
orchestrator = AutonomousOrchestrator(use_live_email=has_email_creds)

# ------------------------------------------------------------------------------
# HIGH-END SAAS DESIGN SYSTEM (UNIFIED DARK PALETTE & GLASSMORPHISM)
# ------------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #0b0f19;
        color: #f8fafc;
    }
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Force dark background for Streamlit main block */
    .stAppViewContainer {
        background-color: #0b0f19;
    }

    /* Responsive Content Constraints (Centers and prevents distortion on ultra-wide & zoomed-out screens) */
    .block-container {
        max-width: 1440px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #0f1523 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    /* Top Header Container */
    .top-hero {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #cbd5e1 !important;
        margin-bottom: 14px;
        line-height: 1.55;
    }
    
    /* KPI Metric Cards */
    .kpi-card {
        background: #131b2e;
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 14px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.2s ease;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
    }
    .kpi-card:hover {
        border-color: rgba(255, 255, 255, 0.22);
        transform: translateY(-2px);
    }
    .kpi-stripe {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
    }
    .kpi-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .kpi-label {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #94a3b8;
    }
    .kpi-value {
        font-size: 2.4rem;
        font-weight: 800;
        line-height: 1.1;
        margin: 4px 0 6px 0;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #64748b;
    }
    
    /* Pill Badges */
    .pill {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .pill-p0 {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .pill-p1 {
        background: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .pill-p2 {
        background: rgba(6, 182, 212, 0.2);
        color: #38bdf8;
        border: 1px solid rgba(6, 182, 212, 0.4);
    }
    .pill-learning {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .pill-placement {
        background: rgba(139, 92, 246, 0.2);
        color: #a78bfa;
        border: 1px solid rgba(139, 92, 246, 0.4);
    }
    .pill-project {
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.4);
    }
    .pill-success {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    
    /* LinkedIn Modal Simulation */
    .linkedin-modal {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        position: relative;
    }
    .linkedin-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .linkedin-avatar {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: linear-gradient(135deg, #0a66c2 0%, #004182 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        color: #ffffff;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# LOCAL TIMEZONE RESOLUTION (UTC -> IST)
# ------------------------------------------------------------------------------
utc_now = datetime.datetime.now(datetime.timezone.utc)
ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
local_now = utc_now.astimezone(ist_offset)
hour = local_now.hour
greeting = "Good morning" if 5 <= hour < 12 else "Good afternoon" if 12 <= hour < 17 else "Good evening"
today_str = local_now.strftime('%A, %b %d, %Y')

# ------------------------------------------------------------------------------
# HELPER ACTIONS: DEMO SEEDER & CLEANER
# ------------------------------------------------------------------------------
def seed_sample_data():
    """Populates realistic career copilot sample data so new users see a vibrant dashboard."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Sample Placement Applications
        cursor.execute("SELECT COUNT(*) as c FROM placement_pipeline")
        if cursor.fetchone()["c"] == 0:
            cursor.execute(
                """
                INSERT INTO placement_pipeline (company_name, role, status, test_link, test_deadline, prep_notes)
                VALUES 
                ('Amazon', 'Software Development Engineer I', 'OA_PENDING', 'https://assessment.hackerrank.com/amz-sde-sample', 'Nov 5, 2026, 11:59 PM', 'Focus on 2D Grid BFS/DFS & 16 Leadership Principles'),
                ('Google', 'Software Engineer (Campus 2026)', 'INTERVIEW_SCHEDULED', 'https://meet.google.com/xyz-copilot-interview', 'Nov 12, 2026, 3:00 PM', 'Technical Phone Screen: Advanced Graphs & System Architecture'),
                ('Microsoft', 'Software Engineer', 'APPLIED', '', '', 'Referred by college alumni for Azure Core Systems')
                """
            )
        
        # 2. Sample Action Items
        cursor.execute("SELECT COUNT(*) as c FROM action_items WHERE is_completed = 0")
        if cursor.fetchone()["c"] == 0:
            cursor.execute(
                """
                INSERT INTO action_items (origin_agent, task_description, priority, due_date)
                VALUES 
                ('PLACEMENT', 'Amazon Prep: Solve 2 Grid BFS/DFS problems (Rotting Oranges, Word Search)', 'P0', 'Tonight, 9 PM'),
                ('LEARNING', 'Study [DSA]: Two Pointers & Sliding Window (Focus: Longest Substring Without Repeating Characters)', 'P1', 'Tomorrow'),
                ('LEARNING', 'Study [PYTHON]: Decorators, Closures, and Wrappers (Focus: Build custom caching & retry decorator)', 'P1', 'Nov 2, 2026'),
                ('PROJECT', 'Dev Task: career-copilot-agents: Polish README documentation and add architecture diagram', 'P1', 'Nov 3, 2026')
                """
            )

        # 3. Sample Deadlines
        cursor.execute("SELECT COUNT(*) as c FROM deadlines WHERE is_completed = 0")
        if cursor.fetchone()["c"] == 0:
            cursor.execute(
                """
                INSERT INTO deadlines (title, deadline_dt, category, action_url)
                VALUES 
                ('Amazon Online Assessment Part 1 (HackerRank)', 'Nov 5, 2026, 11:59 PM', 'ONLINE_ASSESSMENT', 'https://assessment.hackerrank.com/amz-sde-sample'),
                ('Google Technical Screening Interview', 'Nov 12, 2026, 3:00 PM', 'INTERVIEW', 'https://meet.google.com/xyz-copilot-interview')
                """
            )

# Ensure only real user practice sessions appear in learning_logs
with get_db_connection() as conn:
    cursor_cleanup = conn.cursor()
    cursor_cleanup.execute("DELETE FROM learning_logs WHERE notes LIKE '%Solved Two Sum%' OR notes LIKE '%Solved Valid Palindrome%'")

def reset_hub_data():
    """Wipes tasks, deadlines, and pipeline to start fresh."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM action_items")
        cursor.execute("DELETE FROM deadlines")
        cursor.execute("DELETE FROM placement_pipeline")
        cursor.execute("DELETE FROM emails_raw")
        cursor.execute("DELETE FROM learning_logs")

# ------------------------------------------------------------------------------
# SIDEBAR NAVIGATION & SYSTEM HEALTH
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 💼 **Career Copilot**")
    st.caption("Autonomous 6-Agent Personal Operating System")
    st.divider()

    active_email = os.getenv("EMAIL_USER") or getattr(settings, "EMAIL_USER", "")
    active_gemini = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")

    st.markdown("#### ⚡ **System Telemetry**")
    if active_email:
        st.markdown(f"📧 **Inbox:** <span class='pill pill-success'>LIVE SYNC</span><br><span style='font-size:0.8rem; color:#94a3b8;'>{active_email}</span>", unsafe_allow_html=True)
    else:
        st.markdown("📧 **Inbox:** <span class='pill pill-p0'>NOT CONFIGURED</span>", unsafe_allow_html=True)

    if active_gemini:
        st.markdown("🤖 **AI Model:** <span class='pill pill-placement'>GEMINI 2.5 FLASH</span>", unsafe_allow_html=True)
    else:
        st.markdown("🤖 **AI Model:** <span class='pill pill-p1'>HEURISTIC RADAR</span>", unsafe_allow_html=True)

    st.markdown("💾 **Hub Storage:** <span class='pill pill-learning'>SQLITE CLOUD</span>", unsafe_allow_html=True)
    st.divider()

    st.markdown("#### 🚀 **Autonomous Actions**")
    if st.button("⚡ Run Full 6-Agent Sync", use_container_width=True, type="primary"):
        with st.spinner("Executing autonomous 6-agent synchronization cycle..."):
            orchestrator.run_full_sync(send_telegram=False, print_output=False)
            st.toast("✅ All 6 agents successfully synchronized!")
            st.rerun()

    if st.button("📬 Scan Unread Gmail", use_container_width=True):
        with st.spinner("Connecting to Gmail over IMAP..."):
            try:
                res = email_agent.run_live_cycle()
                proc = res.get("processed", 0)
                placements = len(res.get("placement_updates", []))
                deadlines = len(res.get("deadlines_detected", []))
                
                if proc == 0:
                    st.toast("📥 No new unread emails in inbox.")
                elif placements > 0 or deadlines > 0:
                    st.toast(f"📥 Scanned {proc} new emails: Extracted {placements} placement updates & {deadlines} deadlines!")
                else:
                    st.toast(f"📥 Scanned {proc} emails: Filtered as non-urgent noise/newsletters.")
                st.rerun()
            except Exception as e:
                st.error(f"Gmail sync error: {e}")

    if st.button("🪄 Load Sample Career Data", use_container_width=True):
        seed_sample_data()
        st.toast("✨ Loaded realistic placement and study targets!")
        st.rerun()

    with st.expander("⚙️ Data Management"):
        if st.button("🗑️ Clear Hub Data", use_container_width=True):
            reset_hub_data()
            st.warning("Cleared all tasks, deadlines, and pipeline entries.")
            st.rerun()

    st.divider()
    st.caption(f"📅 **Date:** {today_str}")
    st.caption("🔒 All credentials securely stored in Secrets.")

# ------------------------------------------------------------------------------
# TOP HERO BANNER & KPI METRICS
# ------------------------------------------------------------------------------
briefing = assistant.generate_morning_briefing()
mastery_report = learning_agent.get_mastery_report()

with get_db_connection() as conn:
    cursor_kpi = conn.cursor()
    cursor_kpi.execute("SELECT COUNT(*) as c FROM placement_pipeline")
    total_pipeline_count = cursor_kpi.fetchone()["c"]

st.markdown(f"""
<div class="top-hero">
    <div class="hero-title">{greeting}, Ranjith! 👋</div>
    <div class="hero-subtitle">
        Your autonomous multi-agent copilot is monitoring your recruitment pipeline, tracking OA deadlines, scheduling spaced-repetition coding streaks, and auditing codebase health.
    </div>
    <div>
        <span class="pill pill-placement">6 AGENTS RUNNING</span>
        <span class="pill pill-learning">SPACED REPETITION ACTIVE</span>
        <span class="pill pill-project">GIT HYGIENE AUDITOR</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 4-Column KPI Grid
k1, k2, k3, k4 = st.columns(4)

with k1:
    p0_count = len(briefing.p0_tasks)
    p1_count = len(briefing.p1_tasks)
    tot_tasks = briefing.total_pending
    val_color = "#f87171" if p0_count > 0 else "#fbbf24"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-stripe" style="background: linear-gradient(90deg, #ef4444, #dc2626);"></div>
        <div class="kpi-header">
            <span class="kpi-label">ACTIVE PRIORITIES</span>
            <span style="font-size: 1.2rem;">🔥</span>
        </div>
        <div class="kpi-value" style="color: {val_color};">{tot_tasks}</div>
        <div class="kpi-sub">{p0_count} Critical P0 • {p1_count} High Focus</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-stripe" style="background: linear-gradient(90deg, #f59e0b, #d97706);"></div>
        <div class="kpi-header">
            <span class="kpi-label">ACTIVE DEADLINES</span>
            <span style="font-size: 1.2rem;">⏰</span>
        </div>
        <div class="kpi-value" style="color: #fbbf24;">{len(briefing.active_deadlines)}</div>
        <div class="kpi-sub">Upcoming tests & interview cutoffs</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-stripe" style="background: linear-gradient(90deg, #8b5cf6, #7c3aed);"></div>
        <div class="kpi-header">
            <span class="kpi-label">RECRUITMENT PIPELINE</span>
            <span style="font-size: 1.2rem;">🎯</span>
        </div>
        <div class="kpi-value" style="color: #a78bfa;">{total_pipeline_count}</div>
        <div class="kpi-sub">Applications actively tracked</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    solv_count = mastery_report.total_problems_solved
    solv_sub = "Log practice in 'Learning' tab" if solv_count == 0 else "Across DSA, Python, SQL"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-stripe" style="background: linear-gradient(90deg, #10b981, #059669);"></div>
        <div class="kpi-header">
            <span class="kpi-label">CODE PROBLEMS SOLVED</span>
            <span style="font-size: 1.2rem;">🧠</span>
        </div>
        <div class="kpi-value" style="color: #34d399;">{solv_count}</div>
        <div class="kpi-sub">{solv_sub}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ------------------------------------------------------------------------------
# MAIN INTERACTIVE TABS
# ------------------------------------------------------------------------------
tab_briefing, tab_placement, tab_learning, tab_linkedin, tab_project = st.tabs([
    "☀️ Command Center",
    "🎯 Placement Pipeline",
    "🧠 Learning & DSA Streak",
    "💼 LinkedIn Outreach",
    "🛠️ Project Health"
])

# ==============================================================================
# TAB 1: COMMAND CENTER (DAILY FOCUS & EISENHOWER PRIORITIZATION)
# ==============================================================================
with tab_briefing:
    left_col, right_col = st.columns([1.65, 1])

    with left_col:
        st.markdown("### 🔥 **Daily Priorities & Action Items**")

        filter_option = st.radio(
            "Filter Task Stream",
            ["All Active", "🚨 P0 Critical", "🧠 Study & Practice", "🎯 Placement & OAs", "🛠️ Project Dev"],
            horizontal=True,
            label_visibility="collapsed"
        )

        all_active = [(t, "P0") for t in briefing.p0_tasks] + [(t, "P1") for t in briefing.p1_tasks]
        
        filtered = []
        if filter_option == "All Active":
            filtered = all_active
        elif filter_option == "🚨 P0 Critical":
            filtered = [(t, "P0") for t in briefing.p0_tasks]
        elif filter_option == "🧠 Study & Practice":
            filtered = [item for item in all_active if "Study" in item[0].task_description]
        elif filter_option == "🎯 Placement & OAs":
            filtered = [item for item in all_active if "Prep" in item[0].task_description or "OA" in item[0].task_description]
        elif filter_option == "🛠️ Project Dev":
            filtered = [item for item in all_active if "Dev Task" in item[0].task_description or "project" in item[0].task_description.lower()]

        if filtered:
            for task, priority in filtered:
                p_class = "pill-p0" if priority == "P0" else "pill-p1"
                
                # Category detection and clean title trimming
                tag_label = "TASK"
                tag_class = "pill-project"
                raw_desc = task.task_description
                clean_desc = raw_desc

                if "Prep" in raw_desc or "OA" in raw_desc:
                    tag_label = "PLACEMENT"
                    tag_class = "pill-placement"
                elif "Study" in raw_desc:
                    tag_label = "LEARNING"
                    tag_class = "pill-learning"
                elif "Dev Task" in raw_desc or "career-copilot" in raw_desc:
                    tag_label = "PROJECT"
                    tag_class = "pill-project"

                # Trim redundant prefixes
                for prefix in ["Dev Task: ", "dev task: ", "Study [DSA]: ", "Study [PYTHON]: ", "Study [SQL]: ", "Study: "]:
                    if clean_desc.lower().startswith(prefix.lower()):
                        clean_desc = clean_desc[len(prefix):]
                        break

                with st.container(border=True):
                    c_info, c_action = st.columns([5.2, 1.2])
                    with c_info:
                        st.markdown(
                            f"<span class='pill {p_class}'>{priority}</span> "
                            f"<span class='pill {tag_class}'>{tag_label}</span> "
                            f"<span style='font-weight: 600; font-size: 0.95rem; color: #f8fafc;'>{clean_desc}</span>",
                            unsafe_allow_html=True
                        )
                        if task.due_date:
                            st.caption(f"⏰ **Target Cutoff:** {task.due_date}")
                    with c_action:
                        b1, b2 = st.columns([1.6, 1])
                        with b1:
                            if st.button("Done ✅", key=f"btn_done_{task.id}", use_container_width=True):
                                assistant.mark_action_item_completed(task.id)
                                st.toast(f"Marked task #{task.id} completed!")
                                st.rerun()
                        with b2:
                            if st.button("🗑️", key=f"btn_del_{task.id}", use_container_width=True):
                                assistant.delete_action_item(task.id)
                                st.toast(f"Dismissed task #{task.id}")
                                st.rerun()
        else:
            st.info("🎉 All clear! No pending tasks in this category. You're ahead of schedule today.")
            if st.button("🎲 Add Next Spaced-Repetition Study Target", key="add_quick_target"):
                learning_agent.get_daily_targets(inject_tasks=True)
                st.toast("Injected fresh study targets!")
                st.rerun()

        # Add Custom Action Item
        with st.expander("➕ **Add Custom Task to Daily Plan**"):
            with st.form("add_task_form"):
                new_desc = st.text_input("Task Objective", placeholder="e.g. Solve LeetCode #200 Number of Islands")
                c_p, c_d = st.columns(2)
                with c_p:
                    p_sel = st.selectbox("Priority Level", ["P0 (Critical)", "P1 (High Focus)", "P2 (Normal)"], index=1)
                with c_d:
                    d_sel = st.text_input("Due Date / Time", placeholder="e.g. Tonight 9 PM, Tomorrow")
                
                if st.form_submit_button("Add to Daily Focus", type="primary", use_container_width=True):
                    if new_desc:
                        p_val = p_sel.split()[0]
                        assistant.add_action_item(new_desc, priority=p_val, due_date=d_sel)
                        st.toast("Task added to your plan!")
                        st.rerun()

    with right_col:
        st.markdown("### ⏰ **Upcoming Deadlines & Tests**")
        if briefing.active_deadlines:
            for d in briefing.active_deadlines:
                with st.container(border=True):
                    st.markdown(f"#### {d.title}")
                    st.markdown(
                        f"<span class='pill pill-p1'>DUE: {d.deadline_dt or 'ASAP'}</span> "
                        f"<span class='pill pill-placement'>{d.category or 'RECRUITMENT'}</span>",
                        unsafe_allow_html=True
                    )
                    dl_b1, dl_b2 = st.columns(2)
                    with dl_b1:
                        if d.action_url:
                            st.link_button("🚀 Launch Test", d.action_url, use_container_width=True)
                        else:
                            st.caption("No direct link")
                    with dl_b2:
                        if st.button("Mark Done ✅", key=f"d_done_{d.id}", use_container_width=True):
                            assistant.mark_deadline_completed(d.id)
                            st.toast("Deadline marked completed!")
                            st.rerun()
        else:
            with st.container(border=True):
                st.markdown("#### 📅 No Active Deadlines Recorded")
                st.caption("Keep monitoring emails or quickly log an upcoming assessment below.")
                with st.popover("➕ Add Assessment / Deadline"):
                    with st.form("quick_dl_form"):
                        dl_t = st.text_input("Assessment or Interview Title", placeholder="e.g. Amazon Online Assessment")
                        dl_d = st.text_input("Cutoff Date & Time", placeholder="e.g. Nov 5, 2026, 11:59 PM")
                        dl_u = st.text_input("Assessment URL (Optional)", placeholder="https://assessment.hackerrank.com/...")
                        if st.form_submit_button("Save Deadline", type="primary", use_container_width=True):
                            if dl_t:
                                with get_db_connection() as conn:
                                    conn.cursor().execute(
                                        "INSERT INTO deadlines (title, deadline_dt, category, action_url) VALUES (?, ?, 'ONLINE_ASSESSMENT', ?)",
                                        (dl_t, dl_d, dl_u)
                                    )
                                st.toast("Saved deadline!")
                                st.rerun()

        st.write("")
        # Evening Accountability Card
        with st.container(border=True):
            st.markdown("### 🌙 **Evening Accountability Review**")
            review = assistant.generate_evening_review()
            total_tasks = review.completed_count + review.pending_count
            pct = (review.completed_count / total_tasks) if total_tasks > 0 else 0.0
            
            st.progress(pct, text=f"Daily Goal Completion: {int(pct * 100)}% ({review.completed_count}/{total_tasks})")
            
            c_comp, c_pend = st.columns(2)
            with c_comp:
                st.metric("Completed Today", f"{review.completed_count} tasks")
            with c_pend:
                st.metric("Pending Rollover", f"{review.pending_count} tasks")

            if review.completed_tasks:
                with st.expander("View Finished Tasks"):
                    for c in review.completed_tasks:
                        st.markdown(f"- ✅ <span style='color: #34d399;'>{c}</span>", unsafe_allow_html=True)
            else:
                st.caption("No tasks finished yet today. Knock out a P0 or P1 item above!")

    st.write("")
    with st.expander("📬 **Live Email Intelligence Feed (Scanned Emails)**"):
        with get_db_connection() as conn:
            c_feed = conn.cursor()
            c_feed.execute(
                """
                SELECT id, sender, subject, date_received, category, urgency, is_noise 
                FROM emails_raw 
                ORDER BY id DESC LIMIT 8
                """
            )
            ingested = c_feed.fetchall()
            if ingested:
                st.caption("How your Email Intelligence Agent classified your recent unread emails:")
                for em in ingested:
                    clean_s = em["subject"].replace("\r", " ").replace("\n", " ").strip()
                    clean_send = em["sender"].split("<")[0].replace('"', '').strip()
                    if em["is_noise"]:
                        badge = "<span class='pill pill-p0'>FILTERED NOISE</span>"
                        action_sub = "Skipped (Promotional / Commercial Newsletter) — No action required"
                    elif em["category"] in ["PLACEMENT_OA", "INTERVIEW_INVITE", "COLLEGE_NOTICE"]:
                        badge = f"<span class='pill pill-placement'>{em['category']}</span>"
                        action_sub = "Career Signal Extracted ➔ Routed to Pipeline & Action Items"
                    else:
                        badge = f"<span class='pill pill-learning'>{em['category']}</span>"
                        action_sub = f"General Email ({em['urgency']} priority)"

                    st.markdown(f"{badge} **{clean_send}**: {clean_s}", unsafe_allow_html=True)
                    st.caption(f"Status: {action_sub}")
                    st.divider()
            else:
                st.info("No emails scanned yet. Click 'Scan Unread Gmail' in the sidebar to fetch incoming emails.")

# ==============================================================================
# TAB 2: PLACEMENT PIPELINE & COMPANY INTERVIEW PREP
# ==============================================================================
with tab_placement:
    st.markdown("### 🎯 **Recruitment Pipeline Tracker**")
    pipeline = placement_agent.get_pipeline()

    # Form to add new application directly
    with st.expander("➕ **Add New Job Application / Company**"):
        with st.form("new_app_form"):
            c_co, c_ro = st.columns(2)
            with c_co:
                in_co = st.text_input("Company Name", placeholder="e.g. Amazon, Google, Uber")
            with c_ro:
                in_ro = st.text_input("Role Title", value="Software Engineer")
            
            c_st, c_dl = st.columns(2)
            with c_st:
                in_st = st.selectbox("Current Status", [s.value for s in HiringStage], index=0)
            with c_dl:
                in_dl = st.text_input("Test / Interview Deadline", placeholder="e.g. Nov 10, 2026")
            
            in_url = st.text_input("Assessment or Interview Meeting Link (Optional)", placeholder="https://...")
            in_notes = st.text_input("Notes / Strategy", placeholder="e.g. Focus on System Design and Dynamic Programming")
            
            if st.form_submit_button("Record Application", type="primary", use_container_width=True):
                if in_co:
                    placement_agent.add_pipeline_entry(
                        company_name=in_co,
                        role=in_ro,
                        status=in_st,
                        test_link=in_url,
                        test_deadline=in_dl,
                        prep_notes=in_notes
                    )
                    st.toast(f"Added {in_co} to recruitment pipeline!")
                    st.rerun()

    if pipeline:
        for p in pipeline:
            with st.container(border=True):
                col_brand, col_status, col_actions = st.columns([2.4, 1.3, 1.2])
                with col_brand:
                    # Status styling
                    s_color = "pill-p1"
                    if p.status == "OFFER":
                        s_color = "pill-success"
                    elif p.status in ["INTERVIEW_SCHEDULED", "OA_PENDING"]:
                        s_color = "pill-placement"

                    st.markdown(f"### {p.company_name}")
                    st.markdown(
                        f"**Role:** `{p.role}` | **Status:** <span class='pill {s_color}'>{p.status}</span>",
                        unsafe_allow_html=True
                    )
                    if p.test_deadline:
                        st.caption(f"⏰ **Cutoff:** {p.test_deadline}")
                    if p.test_link:
                        st.link_button("🚀 Launch Test / Portal", p.test_link)
                
                with col_status:
                    current_idx = [s.value for s in HiringStage].index(p.status) if p.status in [s.value for s in HiringStage] else 0
                    new_stage = st.selectbox("Stage", [s.value for s in HiringStage], index=current_idx, key=f"p_st_{p.id}", label_visibility="collapsed")
                    if new_stage != p.status:
                        placement_agent.advance_stage(p.id, HiringStage(new_stage))
                        st.toast(f"Updated {p.company_name} stage to {new_stage}!")
                        st.rerun()
                
                with col_actions:
                    if st.button("📖 Strategy", key=f"view_strat_{p.id}", use_container_width=True):
                        st.session_state["target_prep_company"] = p.company_name
                    if st.button("🗑️ Remove", key=f"p_del_{p.id}", use_container_width=True):
                        placement_agent.delete_pipeline_entry(p.id)
                        st.toast(f"Removed {p.company_name} from pipeline.")
                        st.rerun()
    else:
        st.info("No applications in pipeline. Click '+ Add New Job Application' above or 'Load Sample Career Data' in the sidebar!")

    st.divider()

    # --------------------------------------------------------------------------
    # COMPANY INTERVIEW STRATEGY & CHEAT-SHEETS
    # --------------------------------------------------------------------------
    st.markdown("### 📚 **Company Interview Strategy & Cheat-Sheets**")
    
    col_ctrl, col_dossier = st.columns([1, 2])
    
    with col_ctrl:
        default_co = st.session_state.get("target_prep_company", "Amazon")
        options = ["Amazon", "Microsoft", "Google", "Custom Company..."]
        init_idx = options.index(default_co) if default_co in options else 0
        
        sel_company = st.selectbox("Select Target Company", options, index=init_idx)
        c_name = sel_company
        if sel_company == "Custom Company...":
            c_name = st.text_input("Enter Company Name", placeholder="e.g. Netflix, Uber, Atlassian")
        
        inject_box = st.checkbox("Inject Prep Tasks into Command Center", value=True)
        
        if st.button("Generate Strategy Cheat-Sheet", type="primary", use_container_width=True):
            if c_name:
                with st.spinner(f"Synthesizing high-yield interview strategy for {c_name}..."):
                    dossier = placement_agent.generate_dossier(c_name, inject_tasks=inject_box)
                    st.session_state["active_dossier"] = dossier
                    st.toast(f"Generated {c_name} prep strategy!")

    with col_dossier:
        active_dos = st.session_state.get("active_dossier", placement_agent.generate_dossier("Amazon", inject_tasks=False))
        
        st.markdown(f"#### 🛡️ **{active_dos.company_name} Interview Playbook**")
        d_tab1, d_tab2, d_tab3 = st.tabs(["🧩 High-Yield DSA", "⚙️ CS Fundamentals", "🗣️ Cultural & Behavioral"])
        
        with d_tab1:
            st.markdown("**Top Algorithmic Patterns Tested:**")
            for pattern in active_dos.dsa_focus:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.04); border-left: 3px solid #8b5cf6; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                    <strong style="color: #f8fafc;">{pattern}</strong>
                </div>
                """, unsafe_allow_html=True)
        
        with d_tab2:
            st.markdown("**Core CS Fundamentals & System Architecture:**")
            for cs in active_dos.cs_fundamentals:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.04); border-left: 3px solid #0ea5e9; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                    <strong style="color: #f8fafc;">{cs}</strong>
                </div>
                """, unsafe_allow_html=True)

        with d_tab3:
            st.markdown("**Behavioral Framework & Leadership Principles:**")
            for b in active_dos.behavioral_topics:
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.04); border-left: 3px solid #10b981; padding: 10px 14px; margin-bottom: 8px; border-radius: 6px;">
                    <strong style="color: #f8fafc;">{b}</strong>
                </div>
                """, unsafe_allow_html=True)
            st.info("💡 **STAR Framework:** Structure answers as Situation ➔ Task ➔ Action ➔ Quantifiable Result.")

# ==============================================================================
# TAB 3: LEARNING & SPACED REPETITION ENGINE
# ==============================================================================
with tab_learning:
    st.markdown("### 🧠 **Spaced Repetition Skill & Practice Engine**")
    
    # Today's Targets
    st.markdown("#### 🎯 **Today's High-Yield Problem Targets**")
    targets = learning_agent.get_daily_targets(inject_tasks=False)
    
    tg_c1, tg_c2 = st.columns(2)
    for idx, t in enumerate(targets):
        col = tg_c1 if idx % 2 == 0 else tg_c2
        with col:
            with st.container(border=True):
                st.markdown(f"#### <span class='pill pill-learning'>{t.subject.value}</span> {t.topic_name}", unsafe_allow_html=True)
                st.caption(f"📌 **Status:** {t.reason}")
                st.markdown("**Curated Practice Problems:**")
                for p in t.recommended_problems:
                    st.markdown(f"- `{p}`")
                
                if st.button(f"Quick Log Problem Solved ({t.topic_name})", key=f"quick_solve_{idx}", use_container_width=True):
                    learning_agent.log_session(t.topic_name, problems_solved=1, confidence=4, notes="Solved daily target")
                    st.toast(f"Logged 1 problem for {t.topic_name}! Next review scheduled.")
                    st.rerun()

    st.divider()

    # Practice Logger & Mastery Matrix
    c_log, c_matrix = st.columns([1, 1.3])
    
    with c_log:
        st.markdown("#### 📝 **Log Completed Practice Session**")
        with st.form("practice_session_form"):
            t_choice = st.selectbox(
                "Topic Practiced",
                [
                    "Arrays & Hashing",
                    "Two Pointers & Sliding Window",
                    "Binary Search",
                    "Trees & Binary Search Trees",
                    "Graphs (BFS, DFS, TopoSort)",
                    "Dynamic Programming",
                    "Decorators, Closures, and Wrappers",
                    "Generators, Iterators, and Yield",
                    "Asyncio & Event Loops",
                    "Window Functions (ROW_NUMBER, RANK)",
                    "Common Table Expressions (CTEs)",
                    "Indexing & Query Optimization"
                ]
            )
            p_count = st.number_input("Problems Solved", min_value=1, max_value=25, value=2)
            c_rating = st.select_slider(
                "Confidence Rating",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: {
                    1: "1 - Struggled (Review Soon)",
                    2: "2 - Needed Hints",
                    3: "3 - Comfortable",
                    4: "4 - Strong",
                    5: "5 - Mastered (Extended Interval)"
                }[x]
            )
            p_notes = st.text_input("Session Notes", placeholder="e.g. Mastered cycle detection logic")
            
            if st.form_submit_button("Record Practice Session", type="primary", use_container_width=True):
                learning_agent.log_session(t_choice, problems_solved=p_count, confidence=c_rating, notes=p_notes)
                st.toast(f"Recorded session for {t_choice}!")
                st.rerun()

    with c_matrix:
        st.markdown("#### 📊 **Topic Mastery Matrix**")
        subj_filter = st.radio("Subject Filter", ["All", "DSA", "PYTHON", "SQL"], horizontal=True, label_visibility="collapsed")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if subj_filter == "All":
                cursor.execute("SELECT subject, topic_name, mastery_level, next_review_due FROM learning_topics ORDER BY subject, mastery_level DESC")
            else:
                cursor.execute("SELECT subject, topic_name, mastery_level, next_review_due FROM learning_topics WHERE subject = ? ORDER BY mastery_level DESC", (subj_filter,))
            
            topics = cursor.fetchall()
            for tp in topics:
                col_topic, col_due = st.columns([3, 1.2])
                with col_topic:
                    tier_str = f"Tier {tp['mastery_level']}/5"
                    pct = tp["mastery_level"] / 5.0
                    st.progress(pct, text=f"**{tp['topic_name']}** ({tp['subject']}) — {tier_str}")
                with col_due:
                    st.caption(f"📅 Due: `{tp['next_review_due'] or 'Today'}`")

# ==============================================================================
# TAB 4: LINKEDIN OUTREACH & NETWORKING
# ==============================================================================
with tab_linkedin:
    st.markdown("### 💼 **LinkedIn Outreach & Networking Engine**")
    
    outreach_type = st.radio(
        "Choose Outreach Template",
        ["Recruiter Connection Note (< 300 Chars)", "Alumni Referral Request", "Build in Public Milestone Post"],
        horizontal=True
    )

    if outreach_type == "Recruiter Connection Note (< 300 Chars)":
        r_col1, r_col2 = st.columns([1, 1.5])
        with r_col1:
            co_in = st.text_input("Target Company", value="Microsoft", key="in_rec_co")
            role_in = st.text_input("Role Title", value="Software Engineer", key="in_rec_ro")
            rec_in = st.text_input("Recruiter Name (Optional)", placeholder="e.g. Sarah", key="in_rec_name")
            
            if st.button("Generate Recruiter Note", type="primary", use_container_width=True):
                draft = linkedin_agent.draft_recruiter_note(co_in, role=role_in, recruiter_name=rec_in)
                st.session_state["active_linkedin_draft"] = draft
                st.toast("Drafted character-capped connection note!")

        with r_col2:
            draft = st.session_state.get("active_linkedin_draft")
            if draft and draft.draft_type.value == "RECRUITER_NOTE":
                char_pct = min(1.0, draft.character_count / 300.0)
                st.markdown(f"**Character Count:** `{draft.character_count} / 300 characters` (LinkedIn Hard Limit)")
                st.progress(char_pct)
                
                # Realistic LinkedIn Modal Simulation
                st.markdown(f"""
                <div class="linkedin-modal">
                    <div class="linkedin-header">
                        <div class="linkedin-avatar">in</div>
                        <div>
                            <div style="font-weight: 700; color: #f8fafc;">Add a note to your invitation</div>
                            <div style="font-size: 0.8rem; color: #94a3b8;">LinkedIn members are more likely to accept invitations with a personal note.</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.code(draft.content, language="markdown")
                st.caption("💡 Click the copy button in the code box above, then paste directly into LinkedIn's note modal.")

    elif outreach_type == "Alumni Referral Request":
        a_col1, a_col2 = st.columns([1, 1.5])
        with a_col1:
            a_co = st.text_input("Target Company", value="Amazon", key="in_al_co")
            a_ro = st.text_input("Role Title", value="Software Engineer", key="in_al_ro")
            a_name = st.text_input("Alumni Name", placeholder="e.g. Rahul", key="in_al_name")
            a_job = st.text_input("Job ID (Optional)", placeholder="e.g. JOB-2026-SDE", key="in_al_job")
            
            if st.button("Generate Referral Message", type="primary", use_container_width=True):
                draft = linkedin_agent.draft_alumni_referral(a_co, role=a_ro, alumni_name=a_name, job_id=a_job)
                st.session_state["active_linkedin_draft"] = draft
                st.toast("Drafted alumni referral request!")

        with a_col2:
            draft = st.session_state.get("active_linkedin_draft")
            if draft and draft.draft_type.value == "ALUMNI_REFERRAL":
                st.markdown("#### 📨 **Referral Message Draft**")
                st.code(draft.content, language="markdown")
                st.info("💡 High conversion template: highlights humility, specific role ID, and shared college background.")

    elif outreach_type == "Build in Public Milestone Post":
        m_col1, m_col2 = st.columns([1, 1.5])
        with m_col1:
            m_top = st.text_input("Milestone / Project Accomplishment", value="Built an autonomous 6-agent career copilot operating system in Python")
            if st.button("Generate Milestone Post", type="primary", use_container_width=True):
                draft = linkedin_agent.draft_achievement_post(m_top)
                st.session_state["active_linkedin_draft"] = draft
                st.toast("Generated engaging post draft!")

        with m_col2:
            draft = st.session_state.get("active_linkedin_draft")
            if draft and draft.draft_type.value == "MILESTONE_POST":
                st.markdown("#### 📢 **LinkedIn Milestone Post Draft**")
                st.code(draft.content, language="markdown")
                st.caption("💡 Ready to copy-paste into your LinkedIn feed to build tech credibility.")

# ==============================================================================
# TAB 5: PROJECT & CODEBASE HEALTH
# ==============================================================================
with tab_project:
    st.markdown("### 🛠️ **Project & Code Hygiene Auditor**")
    
    pr_col1, pr_col2 = st.columns([1, 2])
    with pr_col1:
        path_in = st.text_input("Repository Directory Path", value=".")
        if st.button("Trigger Codebase Audit", type="primary", use_container_width=True):
            audit = project_agent.audit_repository(path_in, inject_task=True)
            st.session_state["project_audit_res"] = audit
            st.toast("Repository audit completed!")
    
    with pr_col2:
        audit_res = st.session_state.get("project_audit_res", project_agent.audit_repository(".", inject_task=False))
        
        st.markdown(f"#### Repository: `{audit_res.project_name}`")
        score_pct = audit_res.health_score / 100.0
        st.progress(score_pct, text=f"Health Score: {audit_res.health_score} / 100")
        
        stat1, stat2, stat3 = st.columns(3)
        with stat1:
            st.metric("Git Repository", "Active" if audit_res.has_git else "Missing")
        with stat2:
            st.metric("Last Commit", f"{audit_res.days_since_last_commit or 0}d ago")
        with stat3:
            st.metric("Test Suites", "Present" if audit_res.has_tests else "Missing")

        st.info(f"💡 **Recommended Next Engineering Action:** {audit_res.suggested_action}")
        
        with st.expander("🔍 View Complete Codebase Audit Log"):
            st.text(audit_res.formatted_summary)
