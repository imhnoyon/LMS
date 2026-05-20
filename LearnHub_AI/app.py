# app.py
# Entry point for the AI Teaching Assistant Streamlit application.
# Run with: streamlit run app.py [-- --course_id=33]
#
# For Django integration, pass the course ID as a query parameter:
#   http://localhost:8501/?course_id=33
# Django can embed this via an iframe:
#   <iframe src="http://localhost:8501/?course_id=33" />

import streamlit as st
from dotenv import load_dotenv

from components.sidebar import render_sidebar
from components.chat_panel import render_chat_panel
from components.quick_actions import render_quick_actions
from utils.helpers import init_session_state

load_dotenv()

# ── Page configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Teaching Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tighten sidebar padding */
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }

    /* Chat message bubbles */
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 8px;
    }

    /* Action result container */
    .stContainer {
        border-radius: 8px;
    }

    /* Divider spacing */
    hr {
        margin: 0.5rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """Main application entry point."""
    init_session_state()

    # ── Django integration: read course_id from URL query params ────────────
    query_params = st.query_params
    url_course_id = query_params.get("course_id")

    if url_course_id and st.session_state.selected_course is None:
        try:
            from services.course_api import fetch_course_by_id
            course_id = int(url_course_id)
            course, err = fetch_course_by_id(
                course_id,
                use_dummy=st.session_state.use_dummy_data,
            )
            if course:
                st.session_state.selected_course = course
            elif err:
                st.sidebar.error(f"URL course load failed: {err}")
        except (ValueError, TypeError):
            st.sidebar.warning(f"Invalid course_id in URL: `{url_course_id}`")

    # ── Sidebar ─────────────────────────────────────────────────────────────
    render_sidebar()

    # ── Main area ───────────────────────────────────────────────────────────
    course = st.session_state.selected_course

    if not course:
        st.markdown("## 🤖 AI Teaching Assistant")
        st.info("← Select a course from the sidebar to get started.")
        return

    # Page header
    st.markdown(f"## 🤖 AI Teaching Assistant")
    st.markdown(
        f"**Course:** {course.get('title') or 'N/A'}  |  "
        f"**Topic:** {course.get('topic') or 'N/A'}  |  "
        f"**Level:** {(course.get('level') or 'N/A').title()}"
    )
    st.markdown("---")

    # Two-column layout: Chat (left) | Quick Actions (right)
    chat_col, actions_col = st.columns([1, 1], gap="large")

    with chat_col:
        render_chat_panel(course)

    with actions_col:
        render_quick_actions(course)


if __name__ == "__main__":
    main()
