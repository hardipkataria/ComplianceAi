# Entry point for Streamlit UI
# main.py
import streamlit as st
from agent_manager import run_compliance_agent

st.set_page_config(page_title="Compliance AI Agent", layout="centered")
st.title("🔐 AI Compliance Agent")

# ✅ Initialize chat history in Streamlit session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_input = st.chat_input("Ask me about compliance scan findings...")
if user_input:
    # Add to history as user message
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # ✅ Run the agent with current history
    response = run_compliance_agent(user_input, st.session_state.chat_history)

    # Add assistant response to history
    st.session_state.chat_history.append({"role": "assistant", "content": response})

# 🧠 Show full chat thread
for msg in st.session_state.chat_history:
    with st.chat_message("👤" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
