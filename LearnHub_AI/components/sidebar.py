# components/sidebar.py
# Renders the left sidebar: data source toggle, course selector,
# and course metadata overview.

import streamlit as st
from services.course_api import fetch_all_courses, fetch_course_by_id
from utils.helpers import get_level_badge, format_price, init_session_state


def render_sidebar() -> None:
    """Render the full sidebar and handle course selection logic."""
    init_session_state()

    with st.sidebar:
        st.image(
            "https://via.placeholder.com/280x60/1a1a2e/FFFFFF?text=AI+Teaching+Assistant",
            width="stretch",
        )
        st.markdown("---")

        # ── Data source toggle ──────────────────────────────────────────────
        st.markdown("#### ⚙️ Data Source")
        use_dummy = st.toggle(
            "Use dummy data (no API needed)",
            value=st.session_state.use_dummy_data,
            help="Disable to fetch live data from the Django REST API.",
        )
        if use_dummy != st.session_state.use_dummy_data:
            st.session_state.use_dummy_data = use_dummy
            st.session_state.selected_course = None
            st.rerun()

        st.markdown("---")

        # ── Course loader ───────────────────────────────────────────────────
        st.markdown("#### 📚 Select a Course")
        courses, error = fetch_all_courses(use_dummy=st.session_state.use_dummy_data)

        if error:
            st.error(f"**API Error:** {error}")
            st.info("Enable **dummy data** above to test without the Django server.")
            return

        if not courses:
            st.warning("No courses found.")
            return

        course_options = {f"[{c['id']}] {c['title']}": c["id"] for c in courses}
        selected_label = st.selectbox(
            "Course",
            options=list(course_options.keys()),
            label_visibility="collapsed",
        )

        selected_id = course_options[selected_label]

        # Only re-fetch if the selection changed
        if (
            st.session_state.selected_course is None
            or st.session_state.selected_course.get("id") != selected_id
        ):
            course, err = fetch_course_by_id(
                selected_id, use_dummy=st.session_state.use_dummy_data
            )
            if err:
                st.error(err)
                return
            st.session_state.selected_course = course
            st.session_state.chat_history = []   # Reset chat on course change
            st.session_state.last_action_result = None

        course = st.session_state.selected_course
        if not course:
            return

        # ── Course metadata card ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📋 Course Info")

        thumbnail = (course.get("advance_info") or {}).get("thumbnail")
        if thumbnail and thumbnail.startswith("http"):
            st.image(thumbnail, width="stretch")

        st.markdown(f"**{course['title']}**")
        st.caption(course.get("subtitle", ""))

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(get_level_badge(course.get("level", "")))
        with col2:
            st.markdown(f"🌐 `{course.get('language', 'en').upper()}`")

        st.markdown(
            format_price(
                course.get("price", "0"),
                course.get("discount_price"),
            )
        )

        st.markdown("---")
        st.markdown("**📊 Stats**")
        m1, m2, m3 = st.columns(3)
        m1.metric("Modules", course.get("modules", 0))
        m2.metric("Lectures", course.get("lectures", 0))
        m3.metric("Quizzes", course.get("quizes", 0))

        st.markdown("---")
        st.markdown("**👨‍🏫 Instructor**")
        instructor = course.get("instructor") or {}
        avatar = instructor.get("avatar", "")
        if avatar and avatar.startswith("http"):
            st.image(avatar, width=60)
        st.markdown(f"**{instructor.get('name', 'N/A')}**")
        st.caption(instructor.get("get_biography", ""))

        st.markdown("---")
        st.markdown("**🎯 Learning Outcomes**")
        for outcome in sorted(course.get("outcomes") or [], key=lambda x: x.get("order", 0)):
            st.markdown(f"✅ {outcome.get('text', '')}")

        st.markdown("**📌 Requirements**")
        for req in sorted(course.get("requirements") or [], key=lambda x: x.get("order", 0)):
            st.markdown(f"• {req.get('text', '')}")
