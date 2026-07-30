"""Personal Study Planner Agent — Streamlit prototype.

Run:
    streamlit run app.py

The agent ingests a timetable, assignments, and standing goals, then
produces a transparent weekly plan (every block explains *why* it's
scheduled). The user can accept, edit, or reject each block; re-planning
respects those decisions and adapts to progress updates.
"""

from __future__ import annotations

import json
from datetime import date

import streamlit as st

from planner.ics_export import blocks_to_ics
from planner.llm import generate_narrative
from planner.models import Assignment, Goal, PlanBlock, PlannerInput, TaskStatus, TimetableSlot
from planner.scheduler import generate_weekly_plan, plan_summary, replan
from planner.storage import load_sample_input

st.set_page_config(page_title="Study Planner Agent", page_icon="📘", layout="wide")

STATUS_COLORS = {
    TaskStatus.PENDING: "#F9E795",
    TaskStatus.ACCEPTED: "#8FD19E",
    TaskStatus.EDITED: "#8FC1E3",
    TaskStatus.REJECTED: "#E39494",
    TaskStatus.DONE: "#B7B7B7",
    TaskStatus.PARTIAL: "#D8B9E3",
}

if "planner_input" not in st.session_state:
    st.session_state.planner_input = PlannerInput()
if "plan" not in st.session_state:
    st.session_state.plan: list[PlanBlock] = []
if "today" not in st.session_state:
    st.session_state.today = date.today()

st.title("📘 Personal Study Planner Agent")
st.caption(
    "Track 2 — AI Agent | Ingests your timetable, assignments, and goals; produces a "
    "transparent weekly plan; adapts as deadlines and progress change."
)

with st.sidebar:
    st.header("1 · Load your data")
    use_sample = st.button("Load sample data", use_container_width=True)
    uploaded = st.file_uploader("...or upload a planner JSON", type=["json"])

    if use_sample:
        st.session_state.planner_input = load_sample_input("data/sample_input.json")
        st.session_state.plan = []
        st.success("Sample data loaded.")

    if uploaded is not None:
        from planner.storage import planner_input_from_dict

        st.session_state.planner_input = planner_input_from_dict(json.load(uploaded))
        st.session_state.plan = []
        st.success("Uploaded data loaded.")

    st.divider()
    st.header("2 · Planning window")
    pi = st.session_state.planner_input
    pi.study_window_start = st.text_input("Study window start (HH:MM)", pi.study_window_start)
    pi.study_window_end = st.text_input("Study window end (HH:MM)", pi.study_window_end)
    pi.max_session_minutes = st.slider("Max session length (min)", 30, 180, pi.max_session_minutes, step=15)
    pi.min_session_minutes = st.slider("Min session length (min)", 15, 60, pi.min_session_minutes, step=5)

    st.divider()
    st.header("3 · Add an assignment")
    with st.form("add_assignment", clear_on_submit=True):
        name = st.text_input("Assignment name")
        subject = st.text_input("Subject")
        deadline = st.date_input("Deadline")
        est_hours = st.number_input("Estimated hours", min_value=0.5, value=3.0, step=0.5)
        priority = st.slider("Priority", 1, 5, 3)
        if st.form_submit_button("Add assignment") and name and subject:
            st.session_state.planner_input.assignments.append(
                Assignment(name=name, subject=subject, deadline=deadline.isoformat(), estimated_hours=est_hours, priority=priority)
            )
            st.success(f"Added '{name}'.")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Timetable (fixed commitments)")
    if pi.timetable:
        st.dataframe(
            [{"Day": s.day, "Start": s.start, "End": s.end, "Label": s.label} for s in pi.timetable],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No timetable loaded yet — load sample data or upload a JSON file.")

with col_right:
    st.subheader("Assignments & goals")
    if pi.assignments:
        st.dataframe(
            [
                {
                    "Task": a.name,
                    "Subject": a.subject,
                    "Deadline": a.deadline,
                    "Est. hrs": a.estimated_hours,
                    "Done hrs": a.progress_hours,
                    "Priority": a.priority,
                }
                for a in pi.assignments
            ],
            hide_index=True,
            use_container_width=True,
        )
    if pi.goals:
        st.caption("Standing weekly goals: " + ", ".join(f"{g.subject} ≥ {g.target_hours_per_week}h" for g in pi.goals))

st.divider()

gen_col, replan_col, _ = st.columns([1, 1, 3])
if gen_col.button("🧠 Generate weekly plan", type="primary", use_container_width=True):
    st.session_state.plan = generate_weekly_plan(st.session_state.planner_input, today=st.session_state.today)

if replan_col.button("🔁 Re-plan (respecting my decisions)", use_container_width=True):
    st.session_state.plan = replan(st.session_state.planner_input, st.session_state.plan, today=st.session_state.today)

plan: list[PlanBlock] = st.session_state.plan

if plan:
    st.subheader("Weekly plan")
    st.caption("Every block shows *why* the agent scheduled it. Accept, edit, or reject each one.")

    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        day_blocks = [b for b in plan if b.day == day]
        if not day_blocks:
            continue
        st.markdown(f"**{day}**")
        for i, b in enumerate(day_blocks):
            idx = plan.index(b)
            c1, c2, c3 = st.columns([3, 5, 2])
            with c1:
                st.markdown(
                    f"<div style='padding:6px 10px;border-radius:6px;background:{STATUS_COLORS[b.status]}22;"
                    f"border-left:4px solid {STATUS_COLORS[b.status]}'>"
                    f"<b>{b.start}–{b.end}</b><br>{b.subject}: {b.task_name}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.caption(b.reason)
            with c3:
                choice = st.selectbox(
                    "Status",
                    options=[s.value for s in TaskStatus],
                    index=[s.value for s in TaskStatus].index(b.status.value),
                    key=f"status_{idx}",
                    label_visibility="collapsed",
                )
                plan[idx].status = TaskStatus(choice)

    st.divider()
    summary = plan_summary(plan)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total planned hours", f"{summary['total_hours']:.1f}h")
    m2.metric("Subjects covered", len(summary["by_subject"]))
    m3.metric("Accepted / edited blocks", int(summary["by_status"].get("accepted", 0) + summary["by_status"].get("edited", 0)))

    with st.expander("📊 Hours by subject"):
        st.bar_chart(summary["by_subject"])

    st.subheader("🗣️ Plan summary")
    narrative, source = generate_narrative(plan)
    st.info(narrative)
    st.caption(f"Narrative source: {'Claude API' if source == 'claude' else 'rule-based fallback (no ANTHROPIC_API_KEY set)'}")

    ics_text = blocks_to_ics(plan, today=st.session_state.today)
    st.download_button("📅 Download plan as .ics (calendar reminders)", ics_text, file_name="study_plan.ics", mime="text/calendar")
else:
    st.info("Load data in the sidebar, then click **Generate weekly plan**.")
