import streamlit as st
import datetime
import json
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
from config.settings import EMAIL_USER, GEMINI_API_KEY

# Page setup
st.set_page_config(
    page_title="Career Copilot AI",
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
orchestrator = AutonomousOrchestrator()

# Custom Header Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #888888;
        font-size: 1.05rem;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #1a1c24;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #2e3440;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("💼 Career Copilot")
    st.caption("Autonomous 6-Agent Personal OS")
    
    st.divider()
    
    # Status badges
    st.markdown("**System Health**")
    st.markdown(f"📧 **Inbox:** `{EMAIL_USER or 'Not Configured'}`")
    st.markdown(f"🤖 **AI Engine:** `{'Gemini Active' if GEMINI_API_KEY else 'Heuristic Mode'}`")
    st.markdown(f"💾 **Database:** `SQLite (Local Hub)`")
    
    st.divider()
    
    # Quick Global Actions
    st.markdown("### ⚡ Fast Actions")
    if st.button("🚀 Run Full 6-Agent Sync", use_container_width=True, type="primary"):
        with st.spinner("Running synchronized 6-agent cycle..."):
            orchestrator.run_full_sync(send_telegram=False, print_output=False)
            st.success("Synchronized all agents!")
            st.rerun()

    if st.button("📬 Scan Live Gmail", use_container_width=True):
        with st.spinner("Fetching unread emails from Gmail..."):
            try:
                res = email_agent.run_live_cycle()
                st.success(f"Processed {res.get('processed', 0)} new emails!")
                st.rerun()
            except Exception as e:
                st.error(f"Scan failed: {e}")

    st.divider()
    st.caption(f"Local System Date: {datetime.date.today().strftime('%B %d, %Y')}")

# Main Header
st.markdown('<p class="main-header">🎯 Career & Productivity Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Multi-agent executive copilot coordinating placements, deadlines, DSA streaks, and projects.</p>', unsafe_allow_html=True)

# Main Navigation Tabs
tab_briefing, tab_placement, tab_learning, tab_linkedin, tab_project = st.tabs([
    "☀️ Morning Briefing",
    "🎯 Placement Pipeline",
    "🧠 Learning & DSA Streak",
    "💼 LinkedIn Outreach",
    "🛠️ Project & Git Health"
])

# ==============================================================================
# TAB 1: MORNING BRIEFING & TASKS
# ==============================================================================
with tab_briefing:
    briefing = assistant.generate_morning_briefing()
    
    # Metric KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🚨 Critical P0 Tasks", len(briefing.p0_tasks))
    with col2:
        st.metric("⏰ Active Deadlines", len(briefing.active_deadlines))
    with col3:
        st.metric("🎯 Placement Pipeline", len(briefing.placement_events))
    with col4:
        st.metric("📋 Total Pending", briefing.total_pending)
        
    st.divider()

    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.subheader("🔥 Priorities (Eisenhower Matrix)")
        
        # P0 Tasks
        if briefing.p0_tasks:
            st.markdown("#### [!] P0 Critical Actions (Do First)")
            for t in briefing.p0_tasks:
                c1, c2 = st.columns([4, 1])
                with c1:
                    due = f" *(Due: {t.due_date})*" if t.due_date else ""
                    st.markdown(f"**#{t.id}** {t.task_description}{due}")
                with c2:
                    if st.button("Complete", key=f"p0_done_{t.id}", use_container_width=True):
                        assistant.mark_action_item_completed(t.id)
                        st.rerun()
            st.write("")

        # P1 Tasks
        if briefing.p1_tasks:
            st.markdown("#### [*] P1 High Priority Focus")
            for t in briefing.p1_tasks:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**#{t.id}** {t.task_description}")
                with c2:
                    if st.button("Complete", key=f"p1_done_{t.id}", use_container_width=True):
                        assistant.mark_action_item_completed(t.id)
                        st.rerun()
                        
        if not briefing.p0_tasks and not briefing.p1_tasks:
            st.info("🎉 All urgent and core priority tasks are complete!")

        # Add Custom Task Form
        with st.expander("➕ Add Custom Task"):
            with st.form("add_task_form"):
                new_desc = st.text_input("Task Description")
                prio = st.selectbox("Priority", ["P0", "P1", "P2", "P3"], index=1)
                due = st.text_input("Due Date (Optional)", placeholder="e.g. Tonight, Nov 5")
                submitted = st.form_submit_button("Add Task")
                if submitted and new_desc:
                    assistant.add_action_item(new_desc, priority=prio, due_date=due)
                    st.success("Task added!")
                    st.rerun()

    with right_col:
        st.subheader("⏰ Upcoming Deadlines")
        if briefing.active_deadlines:
            for d in briefing.active_deadlines:
                with st.container(border=True):
                    st.markdown(f"**{d.title}**")
                    st.caption(f"Cutoff: {d.deadline_dt or 'ASAP'} | Category: {d.category}")
                    if d.action_url:
                        st.link_button("🔗 Open Action Link", d.action_url)
                    if st.button("Mark Completed", key=f"dead_{d.id}"):
                        assistant.mark_deadline_completed(d.id)
                        st.rerun()
        else:
            st.info("No active deadlines recorded.")

        # Evening Review Expander
        with st.expander("🌙 Evening Accountability Review"):
            review = assistant.generate_evening_review()
            st.markdown(f"**Completed Today:** {review.completed_count} tasks")
            st.markdown(f"**Rolling Over:** {review.pending_count} tasks")
            if review.completed_tasks:
                st.write("**Completed:**")
                for c in review.completed_tasks:
                    st.markdown(f"- {c}")

# ==============================================================================
# TAB 2: PLACEMENT PIPELINE & COMPANY PREP
# ==============================================================================
with tab_placement:
    st.subheader("🎯 Active Recruitment Funnel")
    
    pipeline = placement_agent.get_pipeline()
    if pipeline:
        for p in pipeline:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"### {p.company_name}")
                    st.markdown(f"**Role:** {p.role} | **Status:** `{p.status}`")
                    if p.test_deadline:
                        st.caption(f"Deadline: {p.test_deadline}")
                    if p.test_link:
                        st.link_button("🔗 Launch Assessment / Meeting", p.test_link)
                with col2:
                    new_stage = st.selectbox(
                        "Update Hiring Stage",
                        [s.value for s in HiringStage],
                        index=[s.value for s in HiringStage].index(p.status) if p.status in [s.value for s in HiringStage] else 0,
                        key=f"stage_select_{p.id}"
                    )
                    if st.button("Update Stage", key=f"update_stage_btn_{p.id}"):
                        placement_agent.advance_stage(p.id, HiringStage(new_stage))
                        st.success(f"Updated {p.company_name} status to {new_stage}!")
                        st.rerun()
                with col3:
                    if st.button("📖 View Prep Dossier", key=f"prep_btn_{p.id}", use_container_width=True):
                        st.session_state["selected_prep_company"] = p.company_name
    else:
        st.info("No companies currently in the placement pipeline.")

    st.divider()

    # Company Prep Dossier Generator
    st.subheader("📚 Company-Specific Interview & OA Dossier")
    prep_col1, prep_col2 = st.columns([1, 2])
    with prep_col1:
        selected_company = st.selectbox(
            "Select Target Company",
            ["Amazon", "Microsoft", "Google", "Custom Company..."]
        )
        custom_company_name = ""
        if selected_company == "Custom Company...":
            custom_company_name = st.text_input("Enter Company Name")

        target_co = custom_company_name if selected_company == "Custom Company..." else selected_company
        target_role = st.text_input("Target Role", value="Software Engineer")
        inject_tasks = st.checkbox("Inject Prep Tasks into Morning Briefing", value=True)

        if st.button("Generate Prep Dossier", type="primary", use_container_width=True):
            if target_co:
                with st.spinner(f"Generating interview strategy for {target_co}..."):
                    dossier = placement_agent.generate_dossier(target_co, role=target_role, inject_tasks=inject_tasks)
                    st.session_state["active_dossier"] = dossier.full_dossier_text

    with prep_col2:
        if "active_dossier" in st.session_state:
            st.text_area("Generated Cheat-Sheet", st.session_state["active_dossier"], height=380)
        else:
            # Default preview
            d = placement_agent.generate_dossier("Amazon", inject_tasks=False)
            st.text_area("Example Strategy (Amazon)", d.full_dossier_text, height=380)

# ==============================================================================
# TAB 3: LEARNING & SPACED REPETITION
# ==============================================================================
with tab_learning:
    st.subheader("🧠 Daily Skill Mastery & Spaced Repetition")
    
    # Daily Study Targets
    st.markdown("#### 🎯 Today's Recommended Study Focus")
    targets = learning_agent.get_daily_targets(inject_tasks=False)
    t_col1, t_col2 = st.columns(2)
    for idx, t in enumerate(targets):
        col = t_col1 if idx % 2 == 0 else t_col2
        with col:
            with st.container(border=True):
                st.markdown(f"**[{t.subject.value}] {t.topic_name}**")
                st.caption(f"Reason: {t.reason}")
                st.markdown("**Recommended Practice:**")
                for p in t.recommended_problems:
                    st.markdown(f"- `{p}`")

    st.divider()

    # Log Practice Session Form
    log_col, stats_col = st.columns([1, 1.2])

    with log_col:
        st.markdown("#### 📝 Log Completed Study Session")
        with st.form("log_study_form"):
            topic = st.selectbox(
                "Topic",
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
            problems = st.number_input("Problems / Exercises Solved", min_value=1, max_value=20, value=2)
            confidence = st.slider("Confidence Rating (1 = Difficult, 5 = Mastered)", 1, 5, 3)
            notes = st.text_input("Quick Notes (Optional)", placeholder="e.g. Mastered topological sort with indegree array")
            
            if st.form_submit_button("Record Practice Session", type="primary", use_container_width=True):
                learning_agent.log_session(topic, problems_solved=problems, confidence=confidence, notes=notes)
                st.success(f"Logged {problems} problems for {topic}! Spaced repetition updated.")
                st.rerun()

    with stats_col:
        st.markdown("#### 📊 Topic Mastery Breakdown")
        summary = learning_agent.get_mastery_report()
        st.code(summary.formatted_report, language="text")

# ==============================================================================
# TAB 4: LINKEDIN OUTREACH HUB
# ==============================================================================
with tab_linkedin:
    st.subheader("💼 LinkedIn Outreach & Networking Hub")
    
    outreach_type = st.radio("Choose Action", ["Recruiter Connection Note (< 300 Chars)", "Alumni Referral Request", "Build in Public Milestone Post"], horizontal=True)

    if outreach_type == "Recruiter Connection Note (< 300 Chars)":
        c1, c2 = st.columns([1, 1.5])
        with c1:
            co = st.text_input("Target Company", value="Microsoft", key="rec_co")
            role = st.text_input("Role", value="Software Engineer", key="rec_role")
            name = st.text_input("Recruiter Name (Optional)", placeholder="e.g. Sarah", key="rec_name")
            if st.button("Draft Recruiter Note", type="primary"):
                draft = linkedin_agent.draft_recruiter_note(co, role=role, recruiter_name=name)
                st.session_state["current_draft"] = draft
        with c2:
            if "current_draft" in st.session_state and st.session_state["current_draft"].draft_type.value == "RECRUITER_NOTE":
                d = st.session_state["current_draft"]
                st.markdown(f"**Character Count:** `{d.character_count}/300` ✅ (Under limit)")
                st.text_area("Ready to Copy:", d.content, height=150)
                st.info("💡 Copy and paste directly into your LinkedIn connection request note!")

    elif outreach_type == "Alumni Referral Request":
        c1, c2 = st.columns([1, 1.5])
        with c1:
            co = st.text_input("Target Company", value="Amazon", key="alumni_co")
            role = st.text_input("Role", value="Software Engineer", key="alumni_role")
            name = st.text_input("Alumni Name", placeholder="e.g. Rahul", key="alumni_name")
            job_id = st.text_input("Job Requisition ID (Optional)", placeholder="e.g. JOB-2026-SDE", key="alumni_job")
            if st.button("Draft Referral Request", type="primary"):
                draft = linkedin_agent.draft_alumni_referral(co, role=role, alumni_name=name, job_id=job_id)
                st.session_state["current_draft"] = draft
        with c2:
            if "current_draft" in st.session_state and st.session_state["current_draft"].draft_type.value == "ALUMNI_REFERRAL":
                d = st.session_state["current_draft"]
                st.text_area("Ready to Copy:", d.content, height=250)

    elif outreach_type == "Build in Public Milestone Post":
        c1, c2 = st.columns([1, 1.5])
        with c1:
            topic = st.text_input("Milestone / Topic", value="Built an autonomous 6-agent career copilot in Python")
            if st.button("Draft LinkedIn Post", type="primary"):
                draft = linkedin_agent.draft_achievement_post(topic)
                st.session_state["current_draft"] = draft
        with c2:
            if "current_draft" in st.session_state and st.session_state["current_draft"].draft_type.value == "MILESTONE_POST":
                d = st.session_state["current_draft"]
                st.text_area("Ready to Copy:", d.content, height=250)

    st.divider()
    st.markdown("#### 📜 Saved Drafts History")
    drafts = linkedin_agent.list_drafts(limit=5)
    if drafts:
        for d in drafts:
            with st.expander(f"[{d.draft_type.value}] {d.target_company or 'Post'} - {d.character_count} chars"):
                st.code(d.content, language="markdown")
    else:
        st.info("No drafts saved yet.")

# ==============================================================================
# TAB 5: PROJECT & GIT HEALTH
# ==============================================================================
with tab_project:
    st.subheader("🛠️ Codebase & Repository Health Auditor")
    
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        repo_input = st.text_input("Repository Directory", value=".")
        if st.button("Run Audit", type="primary", use_container_width=True):
            audit = project_agent.audit_repository(repo_path=repo_input, inject_task=True)
            st.session_state["project_audit_data"] = audit
            st.success("Audit complete!")
    
    with p_col2:
        audit_data = st.session_state.get("project_audit_data", project_agent.audit_repository(repo_path=".", inject_task=False))
        st.markdown(f"### Project: `{audit_data.project_name}`")
        st.progress(audit_data.health_score / 100, text=f"Health Score: {audit_data.health_score}/100")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Git Initialized", "Yes" if audit_data.has_git else "No")
        with c2:
            st.metric("Stall Status", "STALLED" if audit_data.is_stalled else "ACTIVE")
        with c3:
            st.metric("Tests Present", "Yes" if audit_data.has_tests else "No")

        st.info(f"💡 Recommended Action: {audit_data.suggested_action}")
        with st.expander("View Full Audit Log"):
            st.text(audit_data.formatted_summary)
