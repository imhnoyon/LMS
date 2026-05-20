# components/quick_actions.py
# Renders the right panel: Quick Action buttons and their sub-forms,
# plus the AI-generated output display area.

import streamlit as st
from services.ai_service import (
    suggest_course_structure,
    generate_lesson_draft,
    create_quiz_questions,
    improve_content,
    generate_learning_objectives,
)
from utils.helpers import get_all_lectures, display_ai_response


# ── Action definitions ──────────────────────────────────────────────────────
QUICK_ACTIONS = [
    {
        "key": "suggest_structure",
        "label": "Suggest Course Structure",
        "icon": "🏗️",
        "description": "Get an AI-recommended module and lecture outline",
    },
    {
        "key": "lesson_draft",
        "label": "Generate Lesson Draft",
        "icon": "📝",
        "description": "Create a full lesson draft for any lecture",
    },
    {
        "key": "quiz_questions",
        "label": "Create Quiz Questions",
        "icon": "❓",
        "description": "Generate multiple-choice questions for any topic",
    },
    {
        "key": "improve_content",
        "label": "Improve Content",
        "icon": "✨",
        "description": "Rewrite content to be clearer and more engaging",
    },
    {
        "key": "learning_objectives",
        "label": "Learning Objectives",
        "icon": "🎯",
        "description": "Write SMART objectives using Bloom's Taxonomy",
    },
]


def _run_action(key: str, course: dict) -> None:
    """
    Render the sub-form for the selected quick action and handle submission.
    All forms use st.form to avoid re-runs on every widget interaction.
    """

    # ── Suggest Course Structure ────────────────────────────────────────────
    if key == "suggest_structure":
        st.info(
            "This will analyse the current course metadata and suggest an improved, "
            "comprehensive module structure."
        )
        if st.button("🚀 Generate Structure", type="primary", use_container_width=True):
            with st.spinner("Generating course structure…"):
                try:
                    result = suggest_course_structure(course)
                    st.session_state.last_action_result = result
                    st.session_state.last_action_label = "Suggested Course Structure"
                except Exception as e:
                    st.error(str(e))

    # ── Generate Lesson Draft ───────────────────────────────────────────────
    elif key == "lesson_draft":
        lectures = get_all_lectures(course)
        if not lectures:
            st.warning("No lectures found in this course.")
            return

        lecture_options = {
            f"[{l.get('section_name', '')}] {l.get('name', '')}": l for l in lectures
        }

        with st.form("lesson_draft_form"):
            selected_label = st.selectbox(
                "Select a lecture to draft",
                options=list(lecture_options.keys()),
            )
            submitted = st.form_submit_button(
                "📝 Generate Lesson Draft", type="primary", use_container_width=True
            )

        if submitted:
            selected_lecture = lecture_options[selected_label]
            with st.spinner(f"Drafting lesson for '{selected_lecture.get('name', '')}'…"):
                try:
                    result = generate_lesson_draft(
                        course=course,
                        lecture_name=selected_lecture.get("name", ""),
                        lecture_notes=selected_lecture.get("lecture_notes", ""),
                    )
                    st.session_state.last_action_result = result
                    st.session_state.last_action_label = (
                        f"Lesson Draft: {selected_lecture.get('name', '')}"
                    )
                except Exception as e:
                    st.error(str(e))

    # ── Create Quiz Questions ───────────────────────────────────────────────
    elif key == "quiz_questions":
        sections = course.get("sections") or []
        topics = [s.get("name", "") for s in sections]
        # Also add course-level outcomes as topic options
        outcomes = [o.get("text", "") for o in (course.get("outcomes") or [])]
        all_topics = topics + outcomes

        with st.form("quiz_form"):
            topic = st.selectbox(
                "Select topic / section",
                options=all_topics if all_topics else ["General course content"],
            )
            num_q = st.slider("Number of questions", min_value=3, max_value=10, value=5)
            submitted = st.form_submit_button(
                "❓ Generate Questions", type="primary", use_container_width=True
            )

        if submitted:
            with st.spinner(f"Creating {num_q} quiz questions on '{topic}'…"):
                try:
                    result = create_quiz_questions(course, topic, num_q)
                    st.session_state.last_action_result = result
                    st.session_state.last_action_label = f"Quiz: {topic}"
                except Exception as e:
                    st.error(str(e))

    # ── Improve Content ─────────────────────────────────────────────────────
    elif key == "improve_content":
        improvement_goals = [
            "Make it more engaging and student-friendly",
            "Simplify for beginners",
            "Add more depth and technical detail",
            "Improve clarity and conciseness",
            "Make it more actionable with examples",
        ]

        with st.form("improve_content_form"):
            content_to_improve = st.text_area(
                "Paste the content you want to improve",
                height=150,
                placeholder="Paste a lecture description, lesson notes, or any course content here…",
            )
            goal = st.selectbox("Improvement goal", options=improvement_goals)
            custom_goal = st.text_input(
                "Or type a custom goal (overrides dropdown if filled)",
                placeholder="e.g. Rewrite for a professional audience",
            )
            submitted = st.form_submit_button(
                "✨ Improve Content", type="primary", use_container_width=True
            )

        if submitted:
            if not content_to_improve.strip():
                st.warning("Please paste some content to improve.")
                return
            effective_goal = custom_goal.strip() if custom_goal.strip() else goal
            with st.spinner("Improving content…"):
                try:
                    result = improve_content(course, content_to_improve, effective_goal)
                    st.session_state.last_action_result = result
                    st.session_state.last_action_label = f"Improved Content ({effective_goal})"
                except Exception as e:
                    st.error(str(e))

    # ── Learning Objectives ─────────────────────────────────────────────────
    elif key == "learning_objectives":
        sections = course.get("sections") or []
        section_options = ["Entire Course"] + [s.get("name", "") for s in sections]

        with st.form("objectives_form"):
            scope = st.selectbox(
                "Generate objectives for",
                options=section_options,
            )
            submitted = st.form_submit_button(
                "🎯 Generate Objectives", type="primary", use_container_width=True
            )

        if submitted:
            section_name = "" if scope == "Entire Course" else scope
            with st.spinner(f"Writing learning objectives for '{scope}'…"):
                try:
                    result = generate_learning_objectives(course, section_name)
                    st.session_state.last_action_result = result
                    st.session_state.last_action_label = f"Learning Objectives: {scope}"
                except Exception as e:
                    st.error(str(e))


def render_quick_actions(course: dict) -> None:
    """
    Render the Quick Actions panel with buttons, sub-forms, and result display.

    Args:
        course: The currently selected course dict.
    """
    st.markdown("### ⚡ Quick Actions")
    st.caption("Common tasks to get started")

    # Initialise active action key in session state
    if "active_action" not in st.session_state:
        st.session_state.active_action = None

    # ── Action buttons ──────────────────────────────────────────────────────
    for action in QUICK_ACTIONS:
        col_btn, col_desc = st.columns([2, 3])
        with col_btn:
            is_active = st.session_state.active_action == action["key"]
            if st.button(
                f"{action['icon']} {action['label']}",
                key=f"btn_{action['key']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if is_active:
                    # Toggle off
                    st.session_state.active_action = None
                    st.session_state.last_action_result = None
                else:
                    st.session_state.active_action = action["key"]
                    st.session_state.last_action_result = None
                st.rerun()
        with col_desc:
            st.caption(action["description"])

    # ── Active action sub-form ──────────────────────────────────────────────
    if st.session_state.active_action:
        st.markdown("---")
        active = next(
            (a for a in QUICK_ACTIONS if a["key"] == st.session_state.active_action),
            None,
        )
        if active:
            st.markdown(f"**{active['icon']} {active['label']}**")
            _run_action(st.session_state.active_action, course)

    # ── Result display ──────────────────────────────────────────────────────
    if st.session_state.last_action_result:
        st.markdown("---")
        st.markdown(f"#### 📄 {st.session_state.last_action_label}")

        display_ai_response(st.session_state.last_action_result)

        # Download button
        st.download_button(
            label="⬇️ Download as .txt",
            data=st.session_state.last_action_result,
            file_name=f"{st.session_state.last_action_label.replace(' ', '_').lower()}.txt",
            mime="text/plain",
            use_container_width=True,
        )
