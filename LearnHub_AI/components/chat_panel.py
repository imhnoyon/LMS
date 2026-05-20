# components/chat_panel.py
# Renders the left chat panel: conversation history and message input.
# Maintains full session-scoped conversation history.

import streamlit as st
from services.ai_service import chat_with_assistant


def render_chat_panel(course: dict) -> None:
    """
    Render the chat interface for conversational AI interaction.

    Args:
        course: The currently selected course dict.
    """
    st.markdown("### 💬 Chat with AI Assistant")
    st.caption(f"Talking about: **{course.get('title') or 'N/A'}**")

    # ── Conversation history display ────────────────────────────────────────
    chat_container = st.container(height=420, border=False)
    with chat_container:
        if not st.session_state.chat_history:
            with st.chat_message("assistant"):
                st.markdown(
                    "Hello! I'm your AI teaching assistant. I can help you:\n\n"
                    "- 🏗️ **Suggest course structures** based on your topic\n"
                    "- 📝 **Generate lesson drafts** and content outlines\n"
                    "- ❓ **Create quiz questions** and assessments\n"
                    "- ✨ **Improve existing content** for clarity and engagement\n"
                    "- 🎯 **Write learning objectives** aligned with outcomes\n\n"
                    "What would you like help with today?"
                )
        else:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    # ── Input area ──────────────────────────────────────────────────────────
    col_input, col_clear = st.columns([6, 1])

    with col_clear:
        if st.button("🗑️", help="Clear conversation", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    with col_input:
        user_input = st.chat_input(
            placeholder="Type your message…",
            key="chat_input",
        )

    if user_input:
        # Append user message to history
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        with st.spinner("Thinking…"):
            try:
                response = chat_with_assistant(
                    course=course,
                    conversation_history=st.session_state.chat_history[:-1],
                    user_message=user_input,
                )
            except ValueError as e:
                response = f"⚠️ **Configuration Error:** {str(e)}"
            except Exception as e:
                response = f"⚠️ **Error:** {str(e)}"

        # Append assistant message to history
        st.session_state.chat_history.append(
            {"role": "assistant", "content": response}
        )
        st.rerun()
