# 📘 Personal Study Planner Agent

[![CI](https://github.com/minmon6767/study-planner-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/minmon6767/study-planner-agent/actions/workflows/ci.yml)

**Track 2 — AI Agent** · Summer of CodeFest 2.0 · GSDC Innovation Club x iNSiGHTS, VIT Bhopal
**Author:** Privil · [github.com/minmon6767](https://github.com/minmon6767)

An agent that turns a scattered timetable, assignment deadlines, and study
goals into a **transparent, editable weekly study plan** — and re-plans
itself as deadlines shift and progress comes in.

> Problem statement: students receive syllabi, deadlines, attendance
> pressure, and exam dates in many different places, which makes planning
> feel overwhelming. This agent ingests a timetable, assignments, and goal
> preferences, then produces a clear plan with reminders, progress
> tracking, and a way to accept, edit, or reject its suggestions.

## Why this isn't "just a chatbot"

- **Transparent** — every scheduled block carries a plain-English `reason`
  (deadline pressure, priority, or a standing weekly goal). Nothing is a
  black box.
- **Controllable** — every block can be **accepted**, **edited**, or
  **rejected** in the UI. Re-planning respects those decisions instead of
  silently overwriting them.
- **Grounded, not generative-by-default** — the actual scheduling logic in
  `planner/scheduler.py` is 100% deterministic, rule-based, and unit
  tested. An LLM (Claude) is *optional* and only used to narrate an
  already-decided plan in plain English — never to invent the schedule.
  With zero API key configured, the agent still fully works via a
  rule-based narrative fallback.

## How it works

```
 timetable.json ─┐
 assignments  ───┼──▶  planner.scheduler.generate_weekly_plan()  ──▶  weekly plan (with reasons)
 goals        ───┘                     │
                                        ▼
                              user accepts / edits / rejects
                                        │
                                        ▼
                       planner.scheduler.replan()  ──▶  updated plan
                                        │
                        ┌───────────────┼────────────────┐
                        ▼                                ▼
              planner.llm.generate_narrative()   planner.ics_export.blocks_to_ics()
              (Claude, or rule-based fallback)    (downloadable calendar reminders)
```

**Urgency scoring** (fully deterministic, see `compute_urgency`):

```
hours_needed_per_day = remaining_hours / days_left
urgency_score = hours_needed_per_day * (1 + priority / 5)
```

A small assignment due tomorrow can outrank a large one due in three
weeks — matching how a sensible human planner actually prioritizes.

## Project layout

```
study-planner-agent/
├── app.py                   # Streamlit UI (the demo entry point)
├── planner/
│   ├── models.py             # dataclasses: TimetableSlot, Assignment, Goal, PlanBlock
│   ├── scheduler.py           # the agent: urgency scoring, slot allocation, replanning
│   ├── llm.py                  # optional Claude narrative layer + rule-based fallback
│   ├── storage.py               # JSON load/save for planner state
│   └── ics_export.py             # exports the plan as a .ics calendar file
├── data/sample_input.json    # ready-to-load demo data
├── tests/                    # pytest suite for the scheduling logic
└── .github/workflows/ci.yml  # runs the test suite on every push/PR
```

## Running it

```bash
git clone https://github.com/minmon6767/study-planner-agent.git
cd study-planner-agent
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
streamlit run app.py
```

Then in the sidebar, click **"Load sample data"** to populate a demo
timetable, four assignments, and two standing goals, and click
**"Generate weekly plan."**


Without this, the app still runs end-to-end — the "Plan summary" panel
just uses a deterministic templated summary instead of a Claude-generated
one. The scheduling itself is identical either way.

## Running the tests

```bash
pytest -v
```

The suite covers: urgency scoring, no-double-booking across the week,
deadline-respecting allocation, goal-time allocation, and that `replan()`
locks in accepted blocks and drops completed assignments correctly.

## Judging-criteria fit

| Criterion | How this meets it |
|---|---|
| **Planning quality** | Deadline + priority-aware urgency scoring; respects a configurable study window, session length, and break time; never double-books against the fixed timetable. |
| **Transparency of reasoning** | Every block ships a human-readable `reason`; the "Plan summary" panel states which source (Claude vs. fallback) generated the narration. |
| **Genuinely useful, not decorative** | Accept/edit/reject controls actually change future re-plans; `.ics` export turns the plan into real calendar reminders; progress hours feed back into urgency on the next re-plan. |

## Roadmap

- Multi-week rolling plans instead of a fixed 7-day window
- Attendance-risk input (auto-boost priority for low-attendance subjects)
- Native calendar sync (Google Calendar API) instead of `.ics` download
- Per-subject historical accuracy tracking (estimated vs. actual hours)

## License

MIT — see [LICENSE](LICENSE).
