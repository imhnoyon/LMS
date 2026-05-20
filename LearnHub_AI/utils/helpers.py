# utils/helpers.py
# Shared utility functions used across the Streamlit UI components.

import streamlit as st


def format_price(price: str, discount_price: str | None = None) -> str:
    """Format course price with optional discount display."""
    try:
        p = float(price)
        if discount_price:
            d = float(discount_price)
            return f"~~৳{p:,.0f}~~ **৳{d:,.0f}**"
        return f"**৳{p:,.0f}**"
    except (ValueError, TypeError):
        return price


def get_level_badge(level: str) -> str:
    """Return an emoji badge for a course level."""
    badges = {
        "beginner": "🟢 Beginner",
        "intermediate": "🟡 Intermediate",
        "advanced": "🔴 Advanced",
    }
    return badges.get(level.lower(), level.title())


def get_all_lectures(course: dict) -> list[dict]:
    """
    Flatten all lectures across all sections into a single list,
    adding section_name to each lecture for display purposes.
    """
    lectures = []
    for section in (course.get("sections") or []):
        for lecture in (section.get("lectures") or []):
            lectures.append({**lecture, "section_name": section.get("name", "")})
    return lectures


def truncate_text(text: str, max_chars: int = 120) -> str:
    """Truncate long text with an ellipsis."""
    if not text:
        return ""
    return text if len(text) <= max_chars else text[:max_chars].rstrip() + "…"


def display_ai_response(response_text: str) -> None:
    """
    Render an AI response inside a styled container.
    Uses st.markdown so that the AI can use bold, lists, headers, etc.
    """
    with st.container(border=True):
        st.markdown(response_text)


def init_session_state() -> None:
    """Initialise all required Streamlit session state keys."""
    defaults = {
        "chat_history": [],          # List of {"role": str, "content": str}
        "selected_course": None,     # Currently loaded course dict
        "use_dummy_data": True,      # Toggle between dummy and live API
        "last_action_result": None,  # Last quick-action AI response
        "last_action_label": None,   # Label for the last quick action
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
